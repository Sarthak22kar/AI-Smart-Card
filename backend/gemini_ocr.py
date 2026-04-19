"""
Google Gemini OCR  –  Visiting Card Extraction  v7
====================================================
Single-call extraction: sends BOTH card images in ONE Gemini request.
Handles every card type:
  - Standard cards (name top, company bottom)
  - Rotated / sideways cards
  - Single-sided cards (back is blank or same image)
  - Company-only front, person on back
  - Non-standard TLDs (.energy, .io, .in, .co.in)
  - T:/M: labeled phones
  - Cards with logos/QR codes next to text
  - Cards with only partial information
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

_FIELDS = ('name', 'phone', 'email', 'designation', 'company',
           'address', 'website', 'gstin')


# ── Master extraction prompt ──────────────────────────────────────────────────

_MASTER_PROMPT = """You are an expert visiting card OCR and data extraction system.

I am sending you images of a visiting card (front and/or back side).

YOUR TASK: Extract ALL contact information and return it as a JSON object.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CARD READING RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ORIENTATION: Cards may be rotated 90°, 180°, or sideways. Read text in ANY direction.

2. BOTH SIDES: Combine information from front AND back. The person's name/designation 
   is often on the back, while address/website may be on the front.

3. SINGLE SIDE: If both images look the same or one is blank, treat as single-sided card.

4. DARK/COLORED CARDS: Some cards have dark backgrounds (green, blue, black, purple).
   Look carefully for light-colored text on dark backgrounds.
   The text IS there — read it carefully even if contrast appears low.

5. LOGO-ONLY SIDE: If one side shows only a company logo with no readable contact text,
   extract what you can from the other side only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD EXTRACTION RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NAME:
- The person's full name (2-4 words, each starting with capital letter)
- Usually the LARGEST text or appears at the TOP of the card
- Examples: "Rohish Kalvit", "Dr. Aditya Abhyankar", "Pooja Shimpi", "Krushnakant Masal"
- Include honorific if present: Dr., Mr., Mrs., Ms., Prof., Er., CA
- STRICTLY IGNORE: company logos, background textures, decorative patterns, watermarks
- STRICTLY IGNORE: text that looks like random letters or noise (e.g. "Se Bs 2 aoe", "SG ie oe See")
- If the card has a DARK or COLORED background, look for light-colored text on that background
- If name is unclear or looks like noise/logo text, return ""

PHONE:
- Mobile numbers only (10 digits starting with 6, 7, 8, or 9)
- Look for labels: M:, Mobile:, Mob:, Cell: → these are mobile numbers
- Labels T:, Tel:, Telephone:, Fax: → these are landlines (include only if no mobile)
- Format: +91 XXXXX XXXXX
- Multiple phones: separate with " / "
- Examples: "+91 98765 43210", "+91 91684 03315 / +91 80070 27575"

EMAIL:
- Look for labels: E:, Email:, E-mail:, Mail:
- Accept ANY domain extension: .com, .in, .energy, .io, .org, .net, .co.in, .edu, .ac.in, etc.
- Convert to lowercase
- Fix OCR errors: spaces in domain → dots (e.g. "iiae edu.in" → "iiae.edu.in")

DESIGNATION:
- Job title exactly as written on card
- Examples: "Director", "VP Business Development", "Field Sales Representative", "Dean"
- Do NOT include OCR noise symbols like @, #, |

COMPANY:
- Full company/organization name
- Preserve exact capitalization and special characters (&, -)
- Examples: "h2e Power Systems Private Limited", "R & D ECOSISTEMS", "SAVITRIBAI PHULE PUNE UNIVERSITY"

ADDRESS:
- Complete postal address with street, area, city, PIN code
- Combine multiple address lines into one string
- Example: "Office 405, 4th floor, A-wing, Kapil Zenith I.T. Park, Bavdhan, Pune 411021"
- Do NOT include taglines or slogans as address

WEBSITE:
- Look for labels: W:, Website:, Web:
- Accept ANY domain: www.company.com, company.in, startup.io, h2e.energy
- Include http:// prefix
- Do NOT confuse with email addresses

GSTIN:
- 15-character Indian GST number
- Pattern: 2 digits + 5 letters + 4 digits + 1 letter + 1 alphanumeric + Z + 1 alphanumeric
- Example: "27BVFPK3861G1ZH"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY this JSON object. No markdown, no explanation, no code blocks:

{"name":"","phone":"","email":"","designation":"","company":"","address":"","website":"","gstin":""}

Use empty string "" for any field not found on the card.
Do NOT invent or guess information not visible on the card."""


# ── Image preparation ─────────────────────────────────────────────────────────

def _prepare_image(image_bytes: bytes, max_side: int = 1600) -> str:
    """Resize if needed, fix orientation, return base64 JPEG string."""
    pil = Image.open(io.BytesIO(image_bytes))
    if pil.mode != 'RGB':
        pil = pil.convert('RGB')
    # Auto-rotate portrait images (cards are landscape)
    if pil.height > pil.width * 1.2:
        pil = pil.rotate(90, expand=True)
    if max(pil.size) > max_side:
        ratio = max_side / max(pil.size)
        pil = pil.resize(
            (int(pil.width * ratio), int(pil.height * ratio)),
            Image.LANCZOS
        )
    buf = io.BytesIO()
    pil.save(buf, format='JPEG', quality=92)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


# ── API call ──────────────────────────────────────────────────────────────────

def _post(url: str, payload: dict) -> str:
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


def _call_gemini(parts_list: list, temperature: float = 0.05) -> str:
    """Generic Gemini call with any parts list."""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}")
    payload = {
        "contents": [{"parts": parts_list}],
        "generationConfig": {
            "temperature": temperature,
            "topK": 1,
            "topP": 0.8,
            "maxOutputTokens": 1024,
        }
    }
    return _post(url, payload)


# ── JSON parsing ──────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    """
    Parse Gemini JSON response robustly.
    Handles: markdown fences, trailing commas, unterminated strings,
    truncated JSON, extra text before/after JSON.
    """
    raw = raw.strip()

    # Strip markdown fences
    if '```' in raw:
        lines = raw.split('\n')
        inner = [l for l in lines if not l.startswith('```')]
        raw = '\n'.join(inner).strip()

    # Find JSON object start
    start = raw.find('{')
    if start == -1:
        raise ValueError(f"No JSON object found in: {raw[:100]}")

    raw = raw[start:]

    # Find JSON object end — if missing (truncated), add it
    end = raw.rfind('}')
    if end == -1:
        # Truncated JSON — close it
        raw = raw + '"}'
        # Try to find the last complete field
        end = raw.rfind('}')

    raw = raw[:end + 1]

    # Fix trailing commas before } or ]
    raw = re.sub(r',\s*([}\]])', r'\1', raw)

    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Field-by-field extraction for malformed JSON
    result = {}
    for field in _FIELDS:
        # Match complete field: "field": "value"
        m = re.search(rf'"{re.escape(field)}"\s*:\s*"([^"]*)"', raw)
        if m:
            result[field] = m.group(1).strip()
        else:
            # Match unterminated field: "field": "value (no closing quote)
            m2 = re.search(rf'"{re.escape(field)}"\s*:\s*"([^"{{}}]*?)(?:"|,|\}}|$)', raw)
            result[field] = m2.group(1).strip() if m2 else ''

    if any(result.values()):
        print(f"  ⚠️ Used field-by-field extraction (malformed JSON)")
        return result

    raise ValueError(f"Could not parse JSON: {raw[:200]}")


# ── Error handling ────────────────────────────────────────────────────────────

def _handle_error(e: urllib.error.HTTPError) -> str:
    """Log error and return error type string."""
    try:
        body = e.read().decode('utf-8')
        data = json.loads(body) if body else {}
        msg  = data.get('error', {}).get('message', body[:200])
    except Exception:
        msg = str(e)

    if e.code == 403:
        if 'not been used' in msg or 'disabled' in msg:
            print(f"  ❌ Gemini API not enabled for this project.")
            print(f"     Enable at: https://console.developers.google.com/apis/api/generativelanguage.googleapis.com/overview")
            return 'not_enabled'
        elif 'leaked' in msg.lower():
            print("  ❌ Gemini: API key reported as leaked — get a new key")
            return 'leaked'
        else:
            print(f"  ❌ Gemini 403: {msg[:100]}")
            return 'forbidden'
    elif e.code == 429:
        print("  ⚠️ Gemini: quota/rate limit exceeded")
        return 'quota'
    elif e.code == 400:
        if 'API_KEY_INVALID' in msg or 'API key not valid' in msg:
            print("  ❌ Gemini: invalid API key")
            return 'invalid_key'
        print(f"  ❌ Gemini 400: {msg[:100]}")
        return 'bad_request'
    else:
        print(f"  ❌ Gemini HTTP {e.code}: {msg[:100]}")
        return 'error'


def _with_retry(fn, *args, **kwargs):
    """Call fn(); on 429 wait 6s and retry once."""
    try:
        return fn(*args, **kwargs)
    except urllib.error.HTTPError as e:
        err_type = _handle_error(e)
        if err_type == 'quota':
            print("  ⏳ Waiting 6s then retrying once...")
            time.sleep(6)
            try:
                return fn(*args, **kwargs)
            except urllib.error.HTTPError as e2:
                _handle_error(e2)
            except Exception as e2:
                print(f"  ❌ Retry failed: {e2}")
        return None
    except Exception as e:
        print(f"  ❌ Gemini error: {str(e)[:100]}")
        return None


# ── Name quality check ────────────────────────────────────────────────────────

def _looks_like_garbage_name(name: str) -> bool:
    """Return True if name looks like OCR noise, not a real person name."""
    if not name or not name.strip():
        return True
    name = name.strip()
    words = name.split()
    if len(words) < 2 or len(words) > 5:
        return True
    if re.search(r'[@#$%^&*()+=\[\]{}<>|\\~`]', name):
        return True
    if re.search(r'\d', name):
        return True
    honorifics = {'dr', 'mr', 'mrs', 'ms', 'prof', 'er', 'ca', 'adv',
                  'dr.', 'mr.', 'mrs.', 'ms.', 'prof.', 'er.', 'ca.', 'adv.'}
    for word in words:
        clean = word.rstrip('.')
        if not clean:
            continue
        if word.lower() in honorifics:
            continue
        if not word[0].isupper():
            return True
        if len(clean) < 2:
            return True
        if clean.isupper() and len(clean) <= 2:
            return True
        alpha = sum(c.isalpha() for c in clean)
        if alpha < len(clean) * 0.8:
            return True
    non_hon = [w for w in words if w.lower() not in honorifics]
    if sum(1 for w in non_hon if w and w[0].isupper()) < 2:
        return True
    for w in non_hon:
        if w and not w[0].isupper():
            return True
    return False


# ── Public API ────────────────────────────────────────────────────────────────

def gemini_extract_both_cards(front_bytes: bytes, back_bytes: bytes,
                               orig_front: bytes = None, orig_back: bytes = None) -> dict | None:
    """
    PRIMARY: Send both card images in ONE Gemini call.
    Returns complete contact dict or None on failure.

    If preprocessed images fail (malformed JSON / empty result),
    automatically retries with original unprocessed images.
    """
    if not GEMINI_API_KEY:
        return None

    def _do(fb: bytes, bb: bytes):
        front_b64 = _prepare_image(fb)
        back_b64  = _prepare_image(bb)

        # Check if front and back are identical (single-sided card)
        if front_b64 == back_b64:
            parts = [
                {"text": "This is a visiting card (single side):"},
                {"inline_data": {"mime_type": "image/jpeg", "data": front_b64}},
                {"text": _MASTER_PROMPT},
            ]
        else:
            parts = [
                {"text": "FRONT side of visiting card:"},
                {"inline_data": {"mime_type": "image/jpeg", "data": front_b64}},
                {"text": "BACK side of visiting card:"},
                {"inline_data": {"mime_type": "image/jpeg", "data": back_b64}},
                {"text": _MASTER_PROMPT},
            ]

        raw    = _call_gemini(parts, temperature=0.05)
        data   = _parse_json(raw)
        result = {k: str(data.get(k, '') or '').strip() for k in _FIELDS}

        if not any(result.values()):
            raise ValueError("all fields empty")
        return result

    # First attempt with preprocessed images
    result = _with_retry(_do, front_bytes, back_bytes)

    # If failed AND we have original images, retry with originals
    if not result and orig_front and orig_back:
        print("  🔄 Retrying with original (unprocessed) images...")
        result = _with_retry(_do, orig_front, orig_back)

    if result:
        # Clear garbage names
        if _looks_like_garbage_name(result.get('name', '')):
            bad = result.get('name', '')
            result['name'] = ''
            if bad:
                print(f"  ⚠️ Garbled name cleared: '{bad}'")

        found = sum(1 for v in result.values() if v)
        print(f"  ✅ Gemini extracted: {found}/8 fields  name='{result.get('name', '')}'")

    return result


def gemini_extract_single_card(image_bytes: bytes) -> dict | None:
    """
    Extract from a single card image (front-only cards).
    """
    if not GEMINI_API_KEY:
        return None

    def _do():
        img_b64 = _prepare_image(image_bytes)
        parts = [
            {"text": "This is a visiting card:"},
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            {"text": _MASTER_PROMPT},
        ]
        raw    = _call_gemini(parts, temperature=0.05)
        data   = _parse_json(raw)
        result = {k: str(data.get(k, '') or '').strip() for k in _FIELDS}
        if not any(result.values()):
            raise ValueError("all fields empty")
        return result

    result = _with_retry(_do)
    if result:
        if _looks_like_garbage_name(result.get('name', '')):
            result['name'] = ''
        found = sum(1 for v in result.values() if v)
        print(f"  ✅ Gemini single-card: {found}/8 fields")
    return result


def gemini_enrich_from_text(raw_text: str, current_contact: dict) -> dict:
    """
    Text-only enrichment: fill empty fields using raw OCR text.
    No image needed — uses 1 API call.
    """
    if not GEMINI_API_KEY or not raw_text or not raw_text.strip():
        return current_contact

    missing = [k for k in _FIELDS if not (current_contact.get(k) or '').strip()]
    found   = [k for k in _FIELDS if (current_contact.get(k) or '').strip()]

    if not missing:
        return current_contact

    print(f"  🔍 Enriching {len(missing)} empty fields: {missing}")

    already = '\n'.join(f'  {k}: {current_contact[k]}' for k in found) or '  (none)'
    field_desc = {
        'name':        'Full person name (2-4 words, title case)',
        'phone':       'Mobile number → format +91 XXXXX XXXXX',
        'email':       'Email address (any TLD)',
        'designation': 'Job title',
        'company':     'Company name',
        'address':     'Full postal address with city and PIN',
        'website':     'Website URL',
        'gstin':       '15-character GST number',
    }
    missing_desc = '\n'.join(f'  {k}: {field_desc[k]}' for k in missing)
    keys_list    = ', '.join(f'"{k}"' for k in missing)

    prompt = f"""Parse this visiting card text and find ONLY these missing fields.

RAW CARD TEXT:
---
{raw_text.strip()[:3000]}
---

ALREADY FOUND (do NOT change):
{already}

FIND ONLY THESE MISSING FIELDS:
{missing_desc}

Return ONLY a JSON object with keys: {keys_list}
Use "" for any field not found in the text.
No markdown, no explanation."""

    def _do():
        raw  = _call_gemini([{"text": prompt}], temperature=0.05)
        return _parse_json(raw)

    data = _with_retry(_do)
    if not data:
        return current_contact

    enriched = dict(current_contact)
    filled   = []
    for key in missing:
        val = str(data.get(key, '') or '').strip()
        if val:
            enriched[key] = val
            filled.append(f"{key}='{val[:40]}'")

    if filled:
        print(f"  ✅ Enriched: {', '.join(filled)}")
    return enriched


def gemini_ocr(image_bytes: bytes, model: str = None) -> str:
    """Raw text extraction (legacy fallback)."""
    if not GEMINI_API_KEY:
        return ''

    def _do():
        img_b64 = _prepare_image(image_bytes)
        parts = [
            {"text": "Extract ALL visible text from this visiting card. Return only the text, preserving line breaks. No explanation."},
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
        ]
        text = _call_gemini(parts, temperature=0.1)
        if text:
            print(f"  ✅ Gemini raw OCR: {len(text.split())} words")
        return text

    return _with_retry(_do) or ''
