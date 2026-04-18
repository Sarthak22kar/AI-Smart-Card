"""
Google Gemini OCR  –  Visiting Card Extraction
================================================
Three modes:

  1. gemini_extract_structured(image_bytes) → dict
     PRIMARY: sends the image + a structured JSON prompt.
     Returns a fully-parsed contact dict directly from Gemini.

  2. gemini_enrich_from_text(raw_text, current_contact) → dict
     LAST-RESORT ENRICHMENT: when any field is still empty after all
     other extraction steps, send the raw OCR text to Gemini and ask
     it to fill in only the missing fields.  No image needed — just text.

  3. gemini_ocr(image_bytes) → str
     LEGACY: raw text extraction used by ocr.py as a fallback.

Model: gemini-2.5-flash  (free tier: 250 req/day, 10 req/min)
"""

import os
import io
import re
import time
import base64
import json
import urllib.request
import urllib.error
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL   = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')

if not GEMINI_API_KEY:
    _env = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(_env):
        with open(_env) as f:
            for line in f:
                line = line.strip()
                if line.startswith('GEMINI_API_KEY='):
                    GEMINI_API_KEY = line.split('=', 1)[1].strip().strip('"\'')
                elif line.startswith('GEMINI_MODEL='):
                    GEMINI_MODEL = line.split('=', 1)[1].strip().strip('"\'')

if GEMINI_API_KEY:
    print(f"✅ Gemini API key loaded (model: {GEMINI_MODEL})")
else:
    print("⚠️  No Gemini API key — using EasyOCR/Tesseract fallback")

# All contact field keys (order matters for prompts)
_FIELDS = ('name', 'phone', 'email', 'designation', 'company',
           'address', 'website', 'gstin')


# ── Prompts ───────────────────────────────────────────────────────────────────

_STRUCTURED_PROMPT = """You are an expert visiting card OCR system. Carefully read the TEXT on this visiting card.

IMPORTANT: The card may be rotated (sideways or upside down). Read the text regardless of orientation.

STEP 1 — Find the person's name:
- The name is usually the LARGEST or most prominent text on the card
- It appears ABOVE the job title/designation
- It is 2-3 words, each starting with a capital letter (e.g. "Krushnakant Masal", "Rohish Kalvit")
- It is NEVER a company name, logo text, slogan, or random letters
- If the name area has a colorful logo or graphic next to it, IGNORE the graphic — read only the plain text
- Common Indian names: Rohish, Kalvit, Rajesh, Anant, Santosh, Priya, Neha, Kiran, Ravi, Amit, Krushnakant, Masal, etc.

STEP 2 — Find all other fields:
- phone: Look for M: or Mobile: label (mobile numbers). Format: +91 XXXXX XXXXX
- email: Look for E: or Email: label. Accept ANY domain (.com, .in, .energy, .io, etc.)
- designation: Job title (VP, Director, Manager, Engineer, Field Sales Representative, etc.)
- company: Company name (often has Pvt. Ltd., Limited, etc.)
- address: Street address with city and PIN code
- website: Look for W: or Website: label. Accept any domain.
- gstin: 15-character GST number

Return ONLY this JSON (no markdown, no explanation):
{
  "name": "person full name here",
  "phone": "+91 XXXXX XXXXX",
  "email": "email@domain.ext",
  "designation": "job title",
  "company": "company name",
  "address": "full address",
  "website": "http://website.url",
  "gstin": "15char gstin or empty"
}

RULES:
- If name is unclear or looks like random letters/logo text, return "" for name
- Do NOT invent data not on the card
- Email TLD can be anything: .energy .io .in .co.in .org .net .tech
- Taglines are NOT addresses
- The card may be rotated — read text in any orientation"""

_BOTH_CARDS_PROMPT = """You are an expert visiting card OCR system. I am sending you TWO images of the same visiting card — the FRONT side and the BACK side.

IMPORTANT: Cards may be rotated (sideways or upside down). Read text in any orientation.

Combine information from BOTH images to extract the complete contact details.

FINDING THE PERSON'S NAME:
- The name is 2-3 proper words, each starting with a capital letter
- It appears above the job title on the card
- It is NEVER a company name, logo text, or random letters
- Examples: "Krushnakant Masal", "Rohish Kalvit", "Rajesh Kumar Singh"
- If the name area has a logo next to it, IGNORE the logo — read only plain text

Return ONLY this JSON (no markdown, no explanation):
{
  "name": "person full name",
  "phone": "+91 XXXXX XXXXX (mobile only, multiple separated by ' / ')",
  "email": "email@domain.ext (any TLD accepted)",
  "designation": "job title",
  "company": "company name",
  "address": "full street address with city and PIN",
  "website": "http://website.url",
  "gstin": "15-char GST number or empty"
}

RULES:
- Combine data from BOTH card images
- If name is unclear or looks like logo/noise, return "" for name
- Do NOT invent data not visible on the cards
- Email/website TLD can be anything: .energy .io .in .co.in .org .net
- Taglines and slogans are NOT addresses
- Phone: prefer M:/Mobile: labeled numbers; T:/Tel: are landlines"""

_ENRICH_PROMPT_TEMPLATE = """You are an expert at parsing visiting card text.

Below is the raw text extracted from a visiting card by OCR.
Some fields have already been extracted (shown as ALREADY FOUND).
Your job is to find ONLY the fields marked as MISSING.

RAW CARD TEXT:
---
{raw_text}
---

ALREADY FOUND (do NOT change these):
{already_found}

MISSING FIELDS TO FIND:
{missing_fields}

RULES:
1. Return ONLY a valid JSON object with ONLY the missing field keys
2. No explanation, no markdown, no code blocks
3. If a missing field is genuinely not in the text, use empty string ""
4. For phone: extract mobile numbers (10 digits, starting with 6-9)
   - Format as +91 XXXXX XXXXX
   - Look for M: or Mobile: labels for mobile numbers
   - T: or Tel: labels are landlines — include only if no mobile found
5. For email: accept ANY domain (.com, .in, .energy, .io, .org, .net, .tech, etc.)
   - Look for E: or Email: labels
6. For website: accept ANY domain — look for W: or Website: labels
   - Include www. prefix if shown on card
7. For name: person's full name only (not company, not slogan)
   - Include honorific (Dr./Mr./Mrs.) if present
8. For address: full postal address with street, city, PIN
9. For company: exact company name with proper capitalization
10. For designation: job title exactly as written
11. For gstin: 15-character GST number

Return JSON with only these keys: {missing_keys_list}"""


# ── Image preparation ─────────────────────────────────────────────────────────

def _prepare_image(image_bytes: bytes, max_side: int = 1600) -> str:
    """Resize if needed and return base64-encoded JPEG string."""
    pil = Image.open(io.BytesIO(image_bytes))
    if pil.mode != 'RGB':
        pil = pil.convert('RGB')
    if max(pil.size) > max_side:
        ratio = max_side / max(pil.size)
        pil = pil.resize(
            (int(pil.width * ratio), int(pil.height * ratio)),
            Image.LANCZOS
        )
    buf = io.BytesIO()
    pil.save(buf, format='JPEG', quality=92)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


# ── Core API calls ────────────────────────────────────────────────────────────

def _post(url: str, payload: dict) -> str:
    """Make a POST request and return the text response."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode('utf-8'))

    candidates = result.get('candidates', [])
    if not candidates:
        raise ValueError("Gemini returned no candidates")
    parts = candidates[0].get('content', {}).get('parts', [])
    if not parts or 'text' not in parts[0]:
        raise ValueError("Gemini returned no text in parts")
    return parts[0]['text'].strip()


def _call_gemini_with_two_images(prompt: str, front_b64: str, back_b64: str,
                                  temperature: float = 0.05) -> str:
    """Single Gemini call with BOTH card images — saves API quota."""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}")
    payload = {
        "contents": [{"parts": [
            {"text": "FRONT of card:"},
            {"inline_data": {"mime_type": "image/jpeg", "data": front_b64}},
            {"text": "BACK of card:"},
            {"inline_data": {"mime_type": "image/jpeg", "data": back_b64}},
            {"text": prompt},
        ]}],
        "generationConfig": {
            "temperature": temperature, "topK": 1, "topP": 0.8,
            "maxOutputTokens": 1024,
        }
    }
    return _post(url, payload)


def _call_gemini_with_image(prompt: str, img_b64: str,
                             temperature: float = 0.05) -> str:
    """Gemini API call with image."""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}")
    payload = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
        ]}],
        "generationConfig": {
            "temperature": temperature, "topK": 1, "topP": 0.8,
            "maxOutputTokens": 1024,
        }
    }
    return _post(url, payload)


def _call_gemini_text_only(prompt: str, temperature: float = 0.05) -> str:
    """Gemini API call with text only (no image)."""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature, "topK": 1, "topP": 0.8,
            "maxOutputTokens": 512,
        }
    }
    return _post(url, payload)


# ── JSON parsing ──────────────────────────────────────────────────────────────

def _parse_json_response(raw: str) -> dict:
    """
    Parse Gemini's response as JSON.
    Handles markdown code fences, trailing commas, and other common issues.
    """
    raw = raw.strip()

    # Strip markdown code fences
    if raw.startswith('```'):
        lines = raw.split('\n')
        inner = []
        in_block = False
        for line in lines:
            if line.startswith('```'):
                in_block = not in_block
                continue
            inner.append(line)
        raw = '\n'.join(inner).strip()

    # Find the JSON object boundaries
    start = raw.find('{')
    end   = raw.rfind('}')
    if start != -1 and end != -1:
        raw = raw[start:end + 1]

    # Fix trailing commas before } or ] (common Gemini quirk)
    raw = re.sub(r',\s*([}\]])', r'\1', raw)

    return json.loads(raw)


# ── Error handling ────────────────────────────────────────────────────────────

def _handle_http_error(e: urllib.error.HTTPError) -> None:
    try:
        body = e.read().decode('utf-8')
        data = json.loads(body) if body else {}
        msg  = data.get('error', {}).get('message', body[:120])
    except Exception:
        msg = str(e)

    if e.code == 400:
        if 'API_KEY_INVALID' in msg or 'API key not valid' in msg:
            print("  ❌ Gemini: invalid API key")
        elif 'quota' in msg.lower():
            print("  ⚠️ Gemini: daily quota exceeded (250 req/day free tier)")
        else:
            print(f"  ❌ Gemini 400: {msg[:100]}")
    elif e.code == 429:
        print("  ⚠️ Gemini: rate limit (10 req/min) — retrying")
    elif e.code == 403:
        print("  ❌ Gemini: access forbidden — check API key permissions")
    elif e.code == 503:
        print("  ⚠️ Gemini: service temporarily unavailable")
    else:
        print(f"  ❌ Gemini HTTP {e.code}: {msg[:100]}")


def _with_retry(fn, *args, **kwargs):
    """Call fn(); on 429 wait 6s and retry once, then use fallback."""
    try:
        return fn(*args, **kwargs)
    except urllib.error.HTTPError as e:
        _handle_http_error(e)
        if e.code == 429:
            print("  ⏳ Rate limited — waiting 6s then retrying once...")
            time.sleep(6)
            try:
                return fn(*args, **kwargs)
            except urllib.error.HTTPError as e2:
                if e2.code == 429:
                    print("  ⚡ Still rate limited — using Tesseract fallback")
                else:
                    _handle_http_error(e2)
            except Exception as e2:
                print(f"  ❌ Gemini retry failed: {e2}")
        return None
    except Exception as e:
        print(f"  ❌ Gemini error: {str(e)[:100]}")
        return None


# ── Name quality check ───────────────────────────────────────────────────────

def _looks_like_garbage_name(name: str) -> bool:
    """
    Return True if the name looks like OCR noise rather than a real person name.
    Examples of garbage: "SG ie oe See", "h2e", "@ @", "Vp Business Development @ @ I"
    """
    if not name or not name.strip():
        return True

    name = name.strip()
    words = name.split()

    # Too few or too many words
    if len(words) < 2 or len(words) > 5:
        return True

    # Contains symbols that don't belong in names
    if re.search(r'[@#$%^&*()+=\[\]{}<>|\\~`]', name):
        return True

    # Contains digits
    if re.search(r'\d', name):
        return True

    honorifics = {'dr', 'mr', 'mrs', 'ms', 'prof', 'er', 'ca', 'adv',
                  'dr.', 'mr.', 'mrs.', 'ms.', 'prof.', 'er.', 'ca.', 'adv.'}

    # Check each word
    for word in words:
        clean = word.rstrip('.')
        if not clean:
            continue

        # Honorifics are always OK
        if word.lower() in honorifics:
            continue

        # Word must start with uppercase
        if not word[0].isupper():
            return True

        # Word must be at least 2 chars
        if len(clean) < 2:
            return True

        # All-uppercase short words (≤2 chars) are likely initials/noise, not name words
        if clean.isupper() and len(clean) <= 2:
            return True

        # Word must be mostly alphabetic
        alpha = sum(c.isalpha() for c in clean)
        if alpha < len(clean) * 0.8:
            return True

    # At least 2 words must start with uppercase (excluding honorifics)
    non_honorific_words = [w for w in words if w.lower() not in honorifics]
    cap_words = sum(1 for w in non_honorific_words if w and w[0].isupper())
    if cap_words < 2:
        return True

    # All non-honorific words must start with uppercase (real names are title case)
    for w in non_honorific_words:
        if w and not w[0].isupper():
            return True

    return False


# ── Public API ────────────────────────────────────────────────────────────────

def gemini_extract_both_cards(front_bytes: bytes, back_bytes: bytes) -> dict | None:
    """
    PRIMARY path: send BOTH card images in ONE Gemini call.
    Returns dict with all 8 fields, or None on failure.

    Uses 1 API call instead of 2 — avoids rate limiting.
    """
    if not GEMINI_API_KEY:
        return None

    def _do():
        front_b64 = _prepare_image(front_bytes)
        back_b64  = _prepare_image(back_bytes)
        raw  = _call_gemini_with_two_images(_BOTH_CARDS_PROMPT, front_b64, back_b64,
                                             temperature=0.05)
        data = _parse_json_response(raw)
        result = {k: str(data.get(k, '') or '').strip() for k in _FIELDS}
        if not any(result.values()):
            raise ValueError("all fields empty")
        return result

    result = _with_retry(_do)

    if result:
        # Check for garbage name and clear it
        name = result.get('name', '')
        if _looks_like_garbage_name(name):
            print(f"  ⚠️ Garbled name cleared: '{name}'")
            result['name'] = ''

        found = sum(1 for v in result.values() if v)
        print(f"  ✅ Gemini both-cards: {found}/8 fields  name='{result.get('name', '')}'")

    return result


def gemini_extract_structured(image_bytes: bytes,
                               original_bytes: bytes | None = None) -> dict | None:
    """
    Single-image structured extraction (kept for compatibility).
    Prefer gemini_extract_both_cards() for new code.
    """
    if not GEMINI_API_KEY:
        return None

    def _do(img_bytes: bytes):
        img_b64 = _prepare_image(img_bytes)
        raw = _call_gemini_with_image(_STRUCTURED_PROMPT, img_b64, temperature=0.05)
        data = _parse_json_response(raw)
        result = {k: str(data.get(k, '') or '').strip() for k in _FIELDS}
        if not any(result.values()):
            raise ValueError("all fields empty")
        return result

    result = _with_retry(_do, image_bytes)

    if result:
        name = result.get('name', '')
        if _looks_like_garbage_name(name):
            result['name'] = ''
        found = sum(1 for v in result.values() if v)
        print(f"  ✅ Gemini structured: {found}/8 fields  name='{result.get('name', '')}'")

    return result


def gemini_enrich_from_text(raw_text: str, current_contact: dict) -> dict:
    """
    LAST-RESORT ENRICHMENT: text-only Gemini call to fill empty fields.

    Sends raw OCR text + already-found fields to Gemini.
    Asks it to fill ONLY the missing fields.
    Returns enriched contact dict.
    """
    if not GEMINI_API_KEY:
        return current_contact

    if not raw_text or not raw_text.strip():
        return current_contact

    missing = [k for k in _FIELDS if not (current_contact.get(k) or '').strip()]
    found   = [k for k in _FIELDS if (current_contact.get(k) or '').strip()]

    if not missing:
        print("  ✅ Gemini enrich: all fields already filled, skipping")
        return current_contact

    print(f"  🔍 Gemini enrich: filling {len(missing)} empty fields: {missing}")

    already_lines = '\n'.join(
        f'  {k}: {current_contact[k]}' for k in found
    ) or '  (none yet)'

    field_descriptions = {
        'name':        'Full name of the person (not company, not slogan)',
        'phone':       'Mobile phone number(s) — format +91 XXXXX XXXXX',
        'email':       'Email address (any TLD: .com, .in, .energy, .io, etc.)',
        'designation': 'Job title / designation',
        'company':     'Company or organization name',
        'address':     'Full postal address with street, city, PIN code',
        'website':     'Website URL (any TLD, include www. if shown)',
        'gstin':       'GST identification number (15 characters)',
    }
    missing_lines = '\n'.join(
        f'  {k}: {field_descriptions[k]}' for k in missing
    )
    missing_keys_list = ', '.join(f'"{k}"' for k in missing)

    prompt = _ENRICH_PROMPT_TEMPLATE.format(
        raw_text          = raw_text.strip()[:3000],
        already_found     = already_lines,
        missing_fields    = missing_lines,
        missing_keys_list = missing_keys_list,
    )

    def _do():
        raw = _call_gemini_text_only(prompt, temperature=0.05)
        return _parse_json_response(raw)

    data = _with_retry(_do)

    if not data:
        print("  ⚠️ Gemini enrich: failed, keeping existing values")
        return current_contact

    enriched = dict(current_contact)
    filled = []
    for key in missing:
        val = str(data.get(key, '') or '').strip()
        if val:
            enriched[key] = val
            filled.append(f"{key}='{val[:40]}'")

    if filled:
        print(f"  ✅ Gemini enrich: filled {len(filled)} fields → {', '.join(filled)}")
    else:
        print("  ⚠️ Gemini enrich: no new fields found in text")

    return enriched


def gemini_ocr(image_bytes: bytes, model: str = None) -> str:
    """LEGACY path: raw text extraction used by ocr.py."""
    if not GEMINI_API_KEY:
        return ''

    def _do():
        img_b64 = _prepare_image(image_bytes)
        text = _call_gemini_with_image(_RAW_TEXT_PROMPT, img_b64, temperature=0.1)
        if text:
            print(f"  ✅ Gemini raw OCR: {len(text.split())} words")
        return text

    result = _with_retry(_do)
    return result or ''


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        path = sys.argv[1]
        print(f"Testing Gemini with: {path}")
        with open(path, 'rb') as f:
            raw = f.read()

        print("\n── Structured extraction (image) ──")
        t0 = time.time()
        result = gemini_extract_structured(raw)
        print(f"Time: {time.time()-t0:.2f}s")
        if result:
            for k, v in result.items():
                print(f"  {k:12}: {v or '—'}")
        else:
            print("  Failed")
    else:
        print("Usage: python gemini_ocr.py <image_path>")
