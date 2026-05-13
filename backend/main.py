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
import math

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
from ocr import tesseract_extract, easyocr_extract

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


# ── Distance utility ──────────────────────────────────────────────────────────
# City coordinates (lat, lng) for Indian cities
_CITY_COORDS = {
    # Maharashtra
    "pune":          (18.5204, 73.8567),
    "pimpri":        (18.6298, 73.7997),
    "chinchwad":     (18.6279, 73.8009),
    "bavdhan":       (18.5089, 73.7838),
    "hinjewadi":     (18.5912, 73.7389),
    "wakad":         (18.5975, 73.7598),
    "baner":         (18.5590, 73.7868),
    "kothrud":       (18.5074, 73.8077),
    "hadapsar":      (18.5018, 73.9260),
    "viman nagar":   (18.5679, 73.9143),
    "koregaon":      (18.5362, 73.8938),
    "paud road":     (18.5089, 73.7838),
    "aundh":         (18.5590, 73.8077),
    "shivajinagar":  (18.5308, 73.8474),
    "deccan":        (18.5167, 73.8407),
    "katraj":        (18.4529, 73.8654),
    "kondhwa":       (18.4648, 73.8952),
    "wanowrie":      (18.4893, 73.9001),
    "magarpatta":    (18.5089, 73.9260),
    "kharadi":       (18.5512, 73.9442),
    "wagholi":       (18.5793, 73.9800),
    "mumbai":        (19.0760, 72.8777),
    "thane":         (19.2183, 72.9781),
    "navi mumbai":   (19.0330, 73.0297),
    "kalyan":        (19.2437, 73.1355),
    "nashik":        (19.9975, 73.7898),
    "aurangabad":    (19.8762, 75.3433),
    "solapur":       (17.6805, 75.9064),
    "kolhapur":      (16.7050, 74.2433),
    "nagpur":        (21.1458, 79.0882),
    "amravati":      (20.9374, 77.7796),
    "nanded":        (19.1383, 77.3210),
    # Delhi NCR
    "delhi":         (28.6139, 77.2090),
    "new delhi":     (28.6139, 77.2090),
    "gurugram":      (28.4595, 77.0266),
    "gurgaon":       (28.4595, 77.0266),
    "noida":         (28.5355, 77.3910),
    "faridabad":     (28.4089, 77.3178),
    "ghaziabad":     (28.6692, 77.4538),
    # Karnataka
    "bangalore":     (12.9716, 77.5946),
    "bengaluru":     (12.9716, 77.5946),
    "mysore":        (12.2958, 76.6394),
    "hubli":         (15.3647, 75.1240),
    "dharwad":       (15.4589, 75.0078),
    # Telangana / AP
    "hyderabad":     (17.3850, 78.4867),
    "secunderabad":  (17.4399, 78.4983),
    "visakhapatnam": (17.6868, 83.2185),
    # Tamil Nadu
    "chennai":       (13.0827, 80.2707),
    "coimbatore":    (11.0168, 76.9558),
    "madurai":       (9.9252, 78.1198),
    # West Bengal
    "kolkata":       (22.5726, 88.3639),
    # Gujarat
    "ahmedabad":     (23.0225, 72.5714),
    "surat":         (21.1702, 72.8311),
    "vadodara":      (22.3072, 73.1812),
    "rajkot":        (22.3039, 70.8022),
    # Rajasthan
    "jaipur":        (26.9124, 75.7873),
    "jodhpur":       (26.2389, 73.0243),
    # Madhya Pradesh
    "bhopal":        (23.2599, 77.4126),
    "indore":        (22.7196, 75.8577),
    # Uttar Pradesh
    "lucknow":       (26.8467, 80.9462),
    "kanpur":        (26.4499, 80.3319),
    "agra":          (27.1767, 78.0081),
    "varanasi":      (25.3176, 82.9739),
    # Punjab / Haryana
    "chandigarh":    (30.7333, 76.7794),
    "ludhiana":      (30.9010, 75.8573),
    "amritsar":      (31.6340, 74.8723),
    # J&K
    "jammu":         (32.7266, 74.8570),
    "srinagar":      (34.0837, 74.7973),
    # Other
    "bhubaneswar":   (20.2961, 85.8245),
    "patna":         (25.5941, 85.1376),
    "raipur":        (21.2514, 81.6296),
    "guwahati":      (26.1445, 91.7362),
    "kochi":         (9.9312, 76.2673),
    "thiruvananthapuram": (8.5241, 76.9366),
}

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in km between two GPS coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return round(R * 2 * math.asin(math.sqrt(a)), 1)

def _calc_distance(address: str, user_lat: float, user_lng: float) -> float | None:
    """
    Extract city from address string and compute real Haversine distance
    from user's GPS location. Returns km or None if city not found.
    """
    if not address or user_lat is None or user_lng is None:
        return None
    addr_lower = address.lower()
    best_dist = None
    # Try longest city name first to avoid "pune" matching "navi mumbai" etc.
    for city in sorted(_CITY_COORDS.keys(), key=len, reverse=True):
        if city in addr_lower:
            city_lat, city_lng = _CITY_COORDS[city]
            best_dist = _haversine(user_lat, user_lng, city_lat, city_lng)
            break
    return best_dist


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


def _easyocr_fallback(image_bytes: bytes) -> str:
    """EasyOCR fallback — much better than Tesseract for real photos."""
    try:
        from ocr import easyocr_extract
        result = easyocr_extract(image_bytes)
        if result and len(result.strip()) > 5:
            return result
    except Exception as e:
        print(f"  EasyOCR fallback error: {e}")
    # Last resort: Tesseract
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
            # Pass original bytes as fallback in case preprocessed images fail
            t_gem = time.time()
            gem_result = await loop.run_in_executor(
                _pool, gemini_extract_both_cards,
                fp_front, fp_back, front_bytes, back_bytes
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
        # FALLBACK PATH: EasyOCR → Tesseract (when Gemini unavailable)
        # ══════════════════════════════════════════════════════════════════
        if not any(contact.values()):
            print("  ⚠️ Gemini unavailable — using EasyOCR/Tesseract fallback")

            loop = asyncio.get_event_loop()
            fp_front, fp_back = await asyncio.gather(
                loop.run_in_executor(_pool, full_preprocess, front_bytes),
                loop.run_in_executor(_pool, full_preprocess, back_bytes),
            )
            after_front_b64 = _to_b64(fp_front)
            after_back_b64  = _to_b64(fp_back)

            front_fut = _pool.submit(_easyocr_fallback, fp_front)
            back_fut  = _pool.submit(_easyocr_fallback, fp_back)
            front_text = front_fut.result() or ''
            back_text  = back_fut.result()  or ''

            print(f"  📝 Front OCR ({len(front_text)} chars): {front_text[:100]}")
            print(f"  📝 Back OCR ({len(back_text)} chars): {back_text[:100]}")

            if len((front_text + back_text).strip()) < 5:
                return {
                    "status":  "error",
                    "message": "OCR failed to extract any text. Use a clearer, well-lit image.",
                }

            contact    = process_visiting_card(front_text, back_text)
            ocr_engine = 'easyocr'

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
            "services":              c[9],
            "extraction_confidence": c[10],
            "created_at":            str(c[11]) if c[11] else '',
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


@app.put("/contacts/{contact_id}")
def update_contact(contact_id: int, data: dict):
    """Update contact fields — called when user edits extraction results."""
    row = database.get_contact_by_id(contact_id)
    if not row:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Only allow updating the 8 contact fields
    allowed = {'name', 'phone', 'email', 'designation', 'company',
               'address', 'website', 'gstin', 'services'}
    updates = {k: str(v).strip() for k, v in data.items() if k in allowed}

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    success = database.update_contact(contact_id, **updates)
    if not success:
        raise HTTPException(status_code=500, detail="Update failed")

    return {"status": "success", "message": f"Contact {contact_id} updated", "updated": updates}


@app.get("/recommend/{service}")
def get_recommendation(service: str):
    contacts = database.get_all_contacts()
    if not contacts:
        return {
            "error":      "No contacts in database",
            "suggestion": "Scan some visiting cards first",
        }
    formatted = []
    for c in contacts:
        formatted.append({
            "id": c[0], "name": c[1], "phone": c[2], "email": c[3],
            "profession": c[4] or "General",
            "designation": c[4], "company": c[5], "location": c[6],
            "address": c[6], "website": c[7], "gstin": c[8],
            "services": c[9] if len(c) > 9 else '',
            "review_score": 4.0, "response_rate": 0.8,
            "website_presence": 1 if c[7] else 0,
            "customer_interaction": 0.7, "distance": 10, "service_completion": 0.8,
        })
    return recommend_best_contact(formatted, service)


@app.get("/smart-search/")
def smart_search(q: str = "", limit: int = 10, lat: float = None, lng: float = None):
    """
    Smart fuzzy search with real GPS distance calculation and star ratings.
    """
    all_rows = database.get_all_contacts()

    def row_to_contact(c):
        conf = float(c[10]) if len(c) > 10 and c[10] else 0.0
        address = c[6] or ""
        dist = _calc_distance(address, lat, lng)
        return {
            "id": c[0], "name": c[1], "phone": c[2], "email": c[3],
            "designation": c[4], "company": c[5], "address": address,
            "website": c[7], "gstin": c[8],
            "services": c[9] if len(c) > 9 else '',
            "extraction_confidence": conf,
            "stars": round(conf * 5, 1),
            "distance_km": dist,
            "match_score": 1.0,
        }

    if not q or not q.strip():
        results = [row_to_contact(c) for c in all_rows]
        # Sort by distance if GPS provided, else by confidence
        if lat and lng:
            results.sort(key=lambda x: (
                x["distance_km"] if x["distance_km"] is not None else 99999,
                -x["extraction_confidence"]
            ))
        return {"results": results[:limit], "total": len(results), "query": q}

    # Score all contacts
    all_contacts = [row_to_contact(c) for c in all_rows]
    for c in all_contacts:
        c["profession"] = c["designation"]

    from recommendation import recommend_best_contact
    rec = recommend_best_contact(all_contacts, q)
    ranked = rec.get("results", [])

    # If GPS provided, re-sort: nearest first, then by match score
    if lat and lng:
        ranked.sort(key=lambda x: (
            x["distance_km"] if x["distance_km"] is not None else 99999,
            -x.get("match_score", 0)
        ))

    return {
        "results": ranked[:limit],
        "total": len(ranked),
        "query": q,
    }


@app.post("/chatbot/")
async def chatbot(request: dict):
    """
    AI Chatbot — full contact details, sorted by real GPS distance then relevance.
    Accepts optional lat/lng for accurate distance calculation.
    """
    message  = (request.get("message") or "").strip()
    user_lat = request.get("lat")
    user_lng = request.get("lng")
    if not message:
        return {"reply": "Please ask me something!", "contacts": []}

    all_rows = database.get_all_contacts()

    contacts_text = ""
    contact_list  = []

    for c in all_rows[:80]:
        name     = c[1] or ""
        phone    = c[2] or ""
        email    = c[3] or ""
        desig    = c[4] or ""
        company  = c[5] or ""
        address  = c[6] or ""
        website  = c[7] or ""
        services = c[9] if len(c) > 9 else ""
        conf     = float(c[10]) if len(c) > 10 and c[10] else 0.0

        # Real Haversine distance if GPS provided, else city-based fallback
        if user_lat is not None and user_lng is not None:
            dist = _calc_distance(address, float(user_lat), float(user_lng))
        else:
            dist = _calc_distance(address, None, None)

        if name:
            contacts_text += f"- {name} | {desig} | {company} | {services} | {phone} | {address[:40]}\n"
            contact_list.append({
                "id": c[0], "name": name, "phone": phone, "email": email,
                "designation": desig, "company": company, "address": address,
                "website": website, "services": services,
                "stars": round(conf * 5, 1),
                "extraction_confidence": conf,
                "distance_km": dist,
            })

    # Sort: nearest first, then by confidence
    contact_list.sort(key=lambda x: (
        x["distance_km"] if x["distance_km"] is not None else 9999,
        -x["extraction_confidence"]
    ))

    if GEMINI_API_KEY:
        try:
            from gemini_ocr import _call_gemini
            prompt = f"""You are a helpful assistant for a professional contact network app.
The user has {len(all_rows)} contacts sorted by distance (nearest first):

{contacts_text[:2000]}

User question: {message}

Answer in 2-3 sentences. Suggest the nearest AND most relevant contacts.

Format EXACTLY:
REPLY: <your 2-3 sentence answer>
CONTACTS: ["Name1", "Name2", "Name3"]"""

            raw = _call_gemini([{"text": prompt}], temperature=0.3)
            reply, suggested_names = "", []

            if "REPLY:" in raw:
                reply = raw.split("REPLY:")[1].split("CONTACTS:")[0].strip()
            if "CONTACTS:" in raw:
                import re as _re
                suggested_names = _re.findall(r'"([^"]+)"', raw.split("CONTACTS:")[1])[:3]

            if not reply:
                reply = raw[:300]

            # Match Gemini-suggested names against contact_list (fuzzy)
            def _name_match(contact_name: str, suggested: str) -> bool:
                cn = (contact_name or "").lower().strip()
                sn = suggested.lower().strip()
                # exact or substring match
                if sn in cn or cn in sn:
                    return True
                # first-word match (e.g. "Vikrant" matches "Vikrant Yadav")
                cn_words = cn.split()
                sn_words = sn.split()
                if cn_words and sn_words and cn_words[0] == sn_words[0]:
                    return True
                return False

            suggested = [c for c in contact_list
                         if any(_name_match(c["name"], n) for n in suggested_names)][:3]

            if not suggested:
                from recommendation import recommend_best_contact
                rec = recommend_best_contact(contact_list, message)
                suggested = rec.get("results", [])[:3]
                suggested.sort(key=lambda x: (
                    x.get("distance_km") if x.get("distance_km") is not None else 9999,
                    -x.get("extraction_confidence", 0)
                ))

            # Ensure stars and distance_km are always present
            for c in suggested:
                if "stars" not in c or c["stars"] is None:
                    conf = c.get("extraction_confidence", 0.0)
                    c["stars"] = round(float(conf) * 5, 1)
                if "distance_km" not in c:
                    c["distance_km"] = None

            return {"reply": reply, "contacts": suggested}

        except Exception as e:
            print(f"Chatbot error: {e}")

    from recommendation import recommend_best_contact
    rec = recommend_best_contact(contact_list, message)
    top = rec.get("results", [])[:3]
    top.sort(key=lambda x: (
        x.get("distance_km") if x.get("distance_km") is not None else 9999,
        -x.get("extraction_confidence", 0)
    ))
    # Ensure stars and distance_km are always present
    for c in top:
        if "stars" not in c or c["stars"] is None:
            conf = c.get("extraction_confidence", 0.0)
            c["stars"] = round(float(conf) * 5, 1)
        if "distance_km" not in c:
            c["distance_km"] = None
    reply = f"Here are the nearest matching contacts: {', '.join(c['name'] for c in top)}." if top else "No matching contacts found."
    return {"reply": reply, "contacts": top}

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


@app.get("/search-history/")
def get_search_history(limit: int = 20):
    """Get recent search history."""
    try:
        con = database._conn()
        cur = con.cursor()
        cur.execute("""
            SELECT query, source, results, created_at
            FROM search_history
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close(); con.close()
        return {
            "history": [
                {"query": r[0], "source": r[1], "results": r[2], "time": str(r[3])}
                for r in rows
            ]
        }
    except Exception:
        return {"history": []}


@app.post("/log-search/")
def log_search(request: dict):
    """Log a search query to history."""
    query   = (request.get("query") or "").strip()
    source  = (request.get("source") or "manual").strip()
    results = int(request.get("results") or 0)
    if not query:
        return {"status": "skipped"}
    try:
        con = database._conn()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO search_history (query, source, results) VALUES (%s, %s, %s)",
            (query[:255], source[:50], results)
        )
        con.commit()
        cur.close(); con.close()
        return {"status": "logged"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/extract-keywords/")
def extract_keywords(request: dict):
    """
    Extract service keywords from spoken/typed text.
    Input:  { "text": "my AC is not working I need someone to fix it" }
    Output: { "keywords": ["ac repair", "electrician"], "search": "ac repair" }
    """
    text = (request.get("text") or "").lower().strip()
    if not text:
        return {"keywords": [], "search": ""}

    from recommendation import KEYWORD_MAP

    # Priority-ordered phrase triggers (longer phrases checked first)
    phrase_map = [
        # AC / cooling
        ("air condition", "ac repair"), ("not cooling", "ac repair"),
        ("ac not working", "ac repair"), ("ac repair", "ac repair"),
        ("cooling problem", "ac repair"), ("refrigerator", "ac repair"),
        ("ac is not", "ac repair"), ("ac problem", "ac repair"),
        # Plumbing
        ("pipe leaking", "plumber"), ("water leaking", "plumber"),
        ("tap leaking", "plumber"), ("drain blocked", "plumber"),
        ("leaking pipe", "plumber"), ("water supply", "plumber"),
        ("pipe is", "plumber"), ("leaking in", "plumber"),
        ("bathroom leak", "plumber"), ("kitchen sink", "plumber"),
        # Electrical
        ("power cut", "electrician"), ("no electricity", "electrician"),
        ("short circuit", "electrician"), ("wiring problem", "electrician"),
        ("light not working", "electrician"), ("fan not working", "electrician"),
        ("power not", "electrician"), ("electricity problem", "electrician"),
        # Legal
        ("court case", "lawyer"), ("legal advice", "lawyer"),
        ("property dispute", "lawyer"), ("need advocate", "lawyer"),
        ("legal matter", "lawyer"), ("file case", "lawyer"),
        # Finance
        ("file gst", "ca"), ("income tax", "ca"), ("tax return", "ca"),
        ("audit", "ca"), ("balance sheet", "ca"), ("gst filing", "ca"),
        # Medical
        ("not feeling well", "doctor"), ("fever", "doctor"),
        ("body pain", "doctor"), ("need medicine", "doctor"),
        ("health problem", "doctor"), ("feeling sick", "doctor"),
        # Car
        ("car not starting", "mechanic"), ("car repair", "mechanic"),
        ("vehicle breakdown", "mechanic"), ("bike repair", "mechanic"),
        ("car problem", "mechanic"), ("car service", "mechanic"),
        # Construction
        ("build house", "architect"), ("home construction", "architect"),
        ("renovation", "architect"), ("interior work", "interior"),
        ("house construction", "architect"), ("building plan", "architect"),
        ("build a house", "architect"), ("build house", "architect"),
        # Solar
        ("solar panel", "solar"), ("solar installation", "solar"),
        ("renewable energy", "solar"), ("solar energy", "solar"),
        # IT
        ("website development", "software"), ("mobile app", "software"),
        ("software development", "software"), ("computer repair", "software"),
        ("app development", "software"), ("website design", "software"),
        # Events
        ("wedding planning", "event management"), ("event organize", "event management"),
        ("party planning", "event management"), ("wedding event", "event management"),
        # Real estate
        ("buy flat", "real estate"), ("sell property", "real estate"),
        ("rent house", "real estate"), ("property dealer", "real estate"),
        ("buy property", "real estate"), ("plot for sale", "real estate"),
        # Cleaning / pest
        ("pest control", "cleaning"), ("house cleaning", "cleaning"),
        ("deep cleaning", "cleaning"), ("sanitization", "cleaning"),
        # Generic (lowest priority)
        ("need to fix", "repair"), ("repair needed", "repair"),
        ("not working", "repair"), ("broken", "repair"),
    ]

    found_keywords = []
    found_set = set()

    # Check multi-word phrases first (most specific)
    for phrase, keyword in phrase_map:
        if phrase in text and keyword not in found_set:
            found_keywords.append(keyword)
            found_set.add(keyword)

    # Check direct keyword matches from KEYWORD_MAP
    for kw in KEYWORD_MAP.keys():
        if kw in text and kw not in found_set:
            # Skip very short generic words that cause false positives
            if len(kw) >= 3 and kw not in ('it', 'hr', 'bd'):
                found_keywords.append(kw)
                found_set.add(kw)

    # Check individual words
    words = [w.strip(".,!?") for w in text.split()]
    for word in words:
        if len(word) >= 4 and word in KEYWORD_MAP and word not in found_set:
            found_keywords.append(word)
            found_set.add(word)

    # Remove generic "repair" if a specific keyword was found
    if len(found_keywords) > 1 and "repair" in found_keywords:
        found_keywords = [k for k in found_keywords if k != "repair"]

    # Primary search = first specific keyword found
    primary = found_keywords[0] if found_keywords else ""

    return {
        "keywords": found_keywords[:5],
        "search": primary,
        "text": text,
    }


@app.get("/stats/")
def get_stats():
    return {"status": "success", "statistics": database.get_contact_stats()}
