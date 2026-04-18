"""
AI Smart Visiting Card API  –  FastAPI backend  v6
===================================================
Optimised pipeline — 1 Gemini call per scan (was 4):

  Fast path  (Gemini, ~3-5s):
    1. Preprocess both images in parallel (~0.1s)
    2. ONE Gemini call with both images → complete contact dict
    3. Clean garbage name → derive from email if needed
    4. Validate → save

  Fallback path  (no Gemini, ~5-8s):
    1. Full preprocess both images in parallel
    2. Tesseract on both in parallel
    3. smart_extractor → validate → save
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor
import asyncio
import time
import json
import base64
import re

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

import database
from smart_extractor import process_visiting_card, name_from_email
from recommendation import recommend_best_contact
from field_validator import validate_contact_info
from gemini_ocr import (
    gemini_extract_both_cards,
    gemini_enrich_from_text,
    GEMINI_API_KEY,
    _looks_like_garbage_name,
)
from image_preprocessor import fast_preprocess, full_preprocess
from ocr import tesseract_extract

app = FastAPI(title="AI Smart Visiting Card API", version="6.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database.create_table()

_pool = ThreadPoolExecutor(max_workers=4)

_FIELDS = ('name', 'phone', 'email', 'designation',
           'company', 'address', 'website', 'gstin')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_b64(image_bytes: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode('utf-8')


def _empty_fields(contact: dict) -> list:
    return [k for k in _FIELDS if not (contact.get(k) or '').strip()]


def _clean_designation(d: str) -> str:
    """Remove OCR noise from designation field."""
    d = re.sub(r'[\s@#|]+$', '', d).strip()          # trailing symbols
    d = re.sub(r'\s*[@#|]+\s*', ' ', d).strip()       # embedded symbols
    d = re.sub(r'\s+[A-Za-z]$', '', d).strip()        # trailing single letter
    return d


def _tesseract_fallback(image_bytes: bytes) -> str:
    """Tesseract OCR fallback."""
    return tesseract_extract(image_bytes) or ''


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {
        "message": "AI Smart Visiting Card API 🚀",
        "version": "6.0.0",
        "gemini":  bool(GEMINI_API_KEY),
    }


@app.post("/scan-card/")
async def scan_card(
    front_file: UploadFile = File(...),
    back_file:  UploadFile = File(...),
):
    try:
        t0 = time.time()

        # ── 1. Validate file types ──────────────────────────────────────────
        for label, f in (("Front", front_file), ("Back", back_file)):
            ct = f.content_type or ''
            if not ct.startswith('image/'):
                return {"status": "error",
                        "message": f"{label} file is not an image (got {ct})"}

        # ── 2. Read bytes ───────────────────────────────────────────────────
        front_bytes = await front_file.read()
        back_bytes  = await back_file.read()

        if not front_bytes or not back_bytes:
            return {"status": "error",
                    "message": "One or both uploaded files are empty"}

        t_ocr = time.time()
        contact    = {k: '' for k in _FIELDS}
        ocr_engine = 'unknown'
        front_text = ''
        back_text  = ''

        # Base64 for before/after display
        before_front_b64 = _to_b64(front_bytes)
        before_back_b64  = _to_b64(back_bytes)
        after_front_b64  = ''
        after_back_b64   = ''

        # ══════════════════════════════════════════════════════════════════
        # FAST PATH: ONE Gemini call with both images
        # ══════════════════════════════════════════════════════════════════
        if GEMINI_API_KEY:

            # Step A: preprocess both images in parallel (~0.1s each)
            loop = asyncio.get_event_loop()
            fp_front, fp_back = await asyncio.gather(
                loop.run_in_executor(_pool, fast_preprocess, front_bytes),
                loop.run_in_executor(_pool, fast_preprocess, back_bytes),
            )
            t_prep = round(time.time() - t_ocr, 2)
            print(f"  ⚡ Preprocessing: {t_prep}s")

            after_front_b64 = _to_b64(fp_front)
            after_back_b64  = _to_b64(fp_back)

            # Step B: ONE Gemini call with both images
            t_gem = time.time()
            gem_result = await loop.run_in_executor(
                _pool, gemini_extract_both_cards, fp_front, fp_back
            )
            t_gem_done = round(time.time() - t_gem, 2)
            print(f"  ⚡ Gemini extraction: {t_gem_done}s")

            if gem_result:
                contact    = gem_result
                ocr_engine = 'gemini'

                # Clean garbage name → derive from email
                if _looks_like_garbage_name(contact.get('name', '')):
                    bad = contact.get('name', '')
                    contact['name'] = ''
                    if bad:
                        print(f"  ⚠️ Garbled name cleared: '{bad}'")
                    if contact.get('email'):
                        derived = name_from_email(contact['email'])
                        if derived:
                            contact['name'] = derived
                            print(f"  ✅ Name from email: '{derived}'")

                # Clean designation noise
                if contact.get('designation'):
                    contact['designation'] = _clean_designation(contact['designation'])

        # ══════════════════════════════════════════════════════════════════
        # FALLBACK PATH: Tesseract (when Gemini unavailable or returned nothing)
        # ══════════════════════════════════════════════════════════════════
        if not any(contact.values()):
            print("  ⚠️ Gemini unavailable — using Tesseract fallback")

            loop = asyncio.get_event_loop()
            fp_front, fp_back = await asyncio.gather(
                loop.run_in_executor(_pool, full_preprocess, front_bytes),
                loop.run_in_executor(_pool, full_preprocess, back_bytes),
            )
            after_front_b64 = _to_b64(fp_front)
            after_back_b64  = _to_b64(fp_back)

            front_fut = _pool.submit(_tesseract_fallback, fp_front)
            back_fut  = _pool.submit(_tesseract_fallback, fp_back)
            front_text = front_fut.result() or ''
            back_text  = back_fut.result()  or ''

            if len((front_text + back_text).strip()) < 5:
                return {
                    "status":  "error",
                    "message": "OCR failed to extract any text. Use a clearer, well-lit image.",
                }

            contact    = process_visiting_card(front_text, back_text)
            ocr_engine = 'tesseract'

        ocr_time = round(time.time() - t_ocr, 2)
        print(f"🔍 OCR total: {ocr_time}s  engine={ocr_engine}")

        # ── 3. Validate & clean ─────────────────────────────────────────────
        t_val = time.time()
        val_result   = validate_contact_info(contact, strict_mode=False)
        contact      = val_result['validated']
        val_errors   = val_result['errors']
        val_warnings = val_result['warnings']
        is_valid     = val_result['is_valid']
        val_time     = round(time.time() - t_val, 2)

        if val_warnings:
            print(f"  ⚠️ {len(val_warnings)} validation warnings")

        # ── 4. Ensure usable name ───────────────────────────────────────────
        name = contact.get('name', '').strip()
        has_contact_info = any([
            contact.get('phone', '').strip(),
            contact.get('email', '').strip(),
            contact.get('company', '').strip(),
        ])

        if not name:
            if contact.get('email'):
                derived = name_from_email(contact['email'])
                if derived:
                    contact['name'] = derived
                    name = derived

            if not name:
                if has_contact_info:
                    fallback = contact.get('company', '').strip() or 'Unknown Contact'
                    contact['name'] = fallback
                    name = fallback
                    print(f"  ℹ️ Using company as name fallback: '{fallback}'")
                else:
                    return {
                        "status":  "error",
                        "message": "Could not extract any contact information. Try a clearer image.",
                    }

        # ── 5. Duplicate check ──────────────────────────────────────────────
        dup = database.find_duplicate(
            contact.get('name', ''),
            contact.get('phone', ''),
            contact.get('email', ''),
        )
        if dup:
            return {
                "status":  "duplicate",
                "message": f"Contact already exists: {dup[1]}",
                "existing_contact": {
                    "id": dup[0], "name": dup[1],
                    "phone": dup[2], "email": dup[3],
                },
                "extracted_contact": contact,
            }

        # ── 6. Save ─────────────────────────────────────────────────────────
        t_db = time.time()
        contact_id = database.insert_contact(
            name                = contact.get('name', ''),
            phone               = contact.get('phone', ''),
            email               = contact.get('email', ''),
            designation         = contact.get('designation', ''),
            company             = contact.get('company', ''),
            address             = contact.get('address', ''),
            website             = contact.get('website', ''),
            gstin               = contact.get('gstin', ''),
            raw_text            = (front_text + '\n' + back_text)[:1000],
            image_formats       = f"{front_file.content_type},{back_file.content_type}",
            ocr_engine          = ocr_engine,
            validation_warnings = json.dumps(val_warnings) if val_warnings else '',
        )
        db_time = round(time.time() - t_db, 2)

        total = round(time.time() - t0, 2)
        print(f"⚡ Total: {total}s")

        return {
            "status":       "success",
            "message":      f"Contact saved in {total}s",
            "contact_id":   contact_id,
            "contact_info": contact,
            "ocr_engine":   ocr_engine,
            "images": {
                "before_front": before_front_b64,
                "before_back":  before_back_b64,
                "after_front":  after_front_b64,
                "after_back":   after_back_b64,
            },
            "validation": {
                "is_valid": is_valid,
                "errors":   val_errors,
                "warnings": val_warnings,
            },
            "processing_time": {
                "ocr":        ocr_time,
                "validation": val_time,
                "database":   db_time,
                "total":      total,
            },
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.get("/contacts/")
def get_contacts():
    rows = database.get_all_contacts()
    result = []
    for c in rows:
        result.append({
            "id":                    c[0],
            "name":                  c[1],
            "phone":                 c[2],
            "email":                 c[3],
            "designation":           c[4],
            "company":               c[5],
            "address":               c[6],
            "website":               c[7],
            "gstin":                 c[8],
            "extraction_confidence": c[9],
            "created_at":            c[10],
        })
    return {"contacts": result, "total": len(result)}


@app.get("/contacts/{contact_id}")
def get_contact_detail(contact_id: int):
    row = database.get_contact_by_id(contact_id)
    if not row:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {
        "id":                    row[0],
        "name":                  row[1],
        "phone":                 row[2],
        "email":                 row[3],
        "designation":           row[4],
        "company":               row[5],
        "address":               row[6],
        "website":               row[7],
        "gstin":                 row[8],
        "extraction_confidence": row[9],
        "ocr_engine":            row[11] if len(row) > 11 else '',
        "created_at":            row[14] if len(row) > 14 else '',
    }


@app.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int):
    database.delete_contact(contact_id)
    return {"status": "success", "message": f"Contact {contact_id} deleted"}


@app.get("/recommend/{service}")
def get_recommendation(service: str):
    contacts = database.get_all_contacts()
    if not contacts:
        return {"error": "No contacts in database",
                "suggestion": "Scan some visiting cards first"}
    formatted = []
    for c in contacts:
        formatted.append({
            "id": c[0], "name": c[1], "phone": c[2], "email": c[3],
            "profession": c[4] or "General",
            "company": c[5], "location": c[6],
            "review_score": 4.0, "response_rate": 0.8,
            "website_presence": 1 if c[7] else 0,
            "customer_interaction": 0.7, "distance": 10, "service_completion": 0.8,
        })
    return recommend_best_contact(formatted, service)


@app.get("/search/")
def search_contacts(query: str = ""):
    rows = (database.search_contacts_advanced(query)
            if query else database.get_all_contacts())
    result = []
    for c in rows:
        result.append({
            "id": c[0], "name": c[1], "phone": c[2], "email": c[3],
            "designation": c[4], "company": c[5], "address": c[6],
        })
    return {"contacts": result, "total": len(result)}


@app.get("/stats/")
def get_stats():
    return {"status": "success", "statistics": database.get_contact_stats()}
