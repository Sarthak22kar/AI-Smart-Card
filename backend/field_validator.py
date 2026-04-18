"""
Field Validation & Constraint Layer  v3
=========================================
Rule-based validation and cleaning for all extracted contact fields.

Design principles
-----------------
- Every validator returns (cleaned_value, error_msg | None)
- cleaned_value is ALWAYS the best possible value (original if nothing better)
- error_msg is None when the field is valid, a string when it is not
- Non-strict mode (default): keep best available value even if invalid
- Strict mode: clear invalid fields

Edge cases handled
------------------
- Emails with non-.com TLDs: .energy, .in, .co.in, .org, .net, .io, etc.
- Phones labeled T: / M: on same line (h2e card pattern)
- Phones with spaces inside digits: +91-80070 27575
- Websites without www: h2e.energy, company.in
- Websites labeled "W:" on card
- Multiple phones on one line separated by spaces
- OCR noise in all fields
"""

import re
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# PHONE
# ═══════════════════════════════════════════════════════════════════════════════

_MOBILE_PREFIXES = set('6789')

# Labels that indicate a landline/fax — skip these
_LANDLINE_LABEL = re.compile(
    r'^\s*(tel|telephone|fax|office|o|t)\s*[:\-\.]',
    re.I
)

# "M: +91-91684 03315"  or  "M. +91-91684 03315"
_M_LABEL = re.compile(
    r'(?:^|[\s,;])[Mm][\s\.\:\-]+(\+?[\d][\d\s\-\.]{9,})',
    re.MULTILINE
)

# "T +91-80070 27575" — T-labeled (could be Tel or T for telephone)
_T_LABEL = re.compile(
    r'(?:^|[\s,;])[Tt][\s\.\:\-]+(\+?[\d][\d\s\-\.]{9,})',
    re.MULTILINE
)


def _digits_only(s: str) -> str:
    return re.sub(r'\D', '', s)


def _format_mobile(digits: str) -> str:
    """Format 10-digit mobile as +91 XXXXX XXXXX."""
    return f'+91 {digits[:5]} {digits[5:]}'


def _clean_phone_single(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate and format a single phone token.
    Returns (formatted, error).  formatted is None on hard failure.
    """
    raw = raw.strip()
    if not raw:
        return None, 'empty'

    digits = _digits_only(raw)

    # Strip country code variants: 91XXXXXXXXXX, 0XXXXXXXXXX
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith('91'):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]

    if len(digits) < 10:
        return None, f'too short ({len(digits)} digits, need 10)'
    if len(digits) > 10:
        # Take last 10 digits (handles cases like 9191684 03315 → 9168403315)
        digits = digits[-10:]

    if digits[0] not in _MOBILE_PREFIXES:
        return None, f'invalid prefix "{digits[0]}" (must be 6-9)'

    return _format_mobile(digits), None


def _extract_phones_from_raw(raw: str) -> List[str]:
    """
    Extract all valid mobile numbers from a raw string.
    Handles:
      - Plain 10-digit: 9168403315
      - With country code: +91-91684 03315
      - Spaced: 91684 03315
      - Multiple on one line: 80070 27575  M. +91-91684 03315
    """
    good, seen = [], set()

    # First try M-labeled numbers (most reliable for mobile)
    for m in _M_LABEL.finditer(raw):
        cleaned, err = _clean_phone_single(m.group(1))
        if cleaned:
            d = _digits_only(cleaned)
            if d not in seen:
                seen.add(d)
                good.append(cleaned)

    # Then scan for any 10-12 digit sequences
    for m in re.finditer(r'\+?91[\s\-]?[\d][\d\s\-]{8,11}|[6-9]\d{9}|\d{5}[\s\-]\d{5}', raw):
        cleaned, err = _clean_phone_single(m.group())
        if cleaned:
            d = _digits_only(cleaned)
            if d not in seen:
                seen.add(d)
                good.append(cleaned)

    return good


def validate_phone(phone: str) -> Tuple[str, Optional[str]]:
    """
    Handle single or multiple phones (separated by / , ; or space-separated T/M labels).
    Returns (best_cleaned_value, error_msg | None).
    """
    if not phone or not phone.strip():
        return '', 'empty'

    # Split on explicit separators first
    parts = re.split(r'[/,;]', phone)
    good, bad_msgs = [], []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Skip T-labeled (landline) but keep M-labeled
        if _LANDLINE_LABEL.match(part):
            bad_msgs.append('landline label skipped')
            continue

        # Try to extract phones from this part (handles "M. +91-91684 03315")
        extracted = _extract_phones_from_raw(part)
        if extracted:
            good.extend(extracted)
        else:
            cleaned, err = _clean_phone_single(part)
            if cleaned:
                good.append(cleaned)
            elif err:
                bad_msgs.append(err)

    # Deduplicate while preserving order
    seen, unique = set(), []
    for p in good:
        d = _digits_only(p)
        if d not in seen:
            seen.add(d)
            unique.append(p)

    if unique:
        return ' / '.join(unique[:3]), None  # max 3 phones

    return phone.strip(), bad_msgs[0] if bad_msgs else 'no valid mobile found'


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL
# ═══════════════════════════════════════════════════════════════════════════════

# Broad email pattern — accepts ANY valid TLD (2-20 chars)
# Handles: .com .in .energy .co.in .org .net .io .tech .info etc.
_EMAIL_RE = re.compile(
    r'^[a-zA-Z0-9][a-zA-Z0-9._%+\-]*@[a-zA-Z0-9][a-zA-Z0-9.\-]*\.[a-zA-Z]{2,20}$'
)

# OCR substitutions to fix before validating
_EMAIL_FIXES = [
    (r'\.\.+',   '.'),    # double dots → single dot
    (r'\s+',     ''),     # spaces inside email
    (r'[,;]',    '.'),    # comma/semicolon → dot (OCR confusion)
    (r'@{2,}',   '@'),    # double @
    (r'\[at\]',  '@'),    # [at] → @
    (r'\(at\)',  '@'),    # (at) → @
    (r' at ',    '@'),    # " at " → @
    (r'\.con$',  '.com'), # .con → .com (common OCR error)
    (r'\.coni$', '.com'), # .comi → .com
    (r'\.cam$',  '.com'), # .cam → .com
]

# Known valid TLDs for secondary validation (non-exhaustive, just common ones)
_KNOWN_TLDS = {
    'com', 'in', 'org', 'net', 'edu', 'gov', 'co',
    'io', 'ai', 'tech', 'info', 'biz', 'me', 'us',
    # New gTLDs common in India/business
    'energy', 'solutions', 'services', 'systems', 'digital',
    'online', 'store', 'shop', 'app', 'dev', 'cloud',
    'global', 'world', 'group', 'team', 'work', 'pro',
    'business', 'company', 'agency', 'studio', 'media',
    # Country codes
    'uk', 'au', 'ca', 'de', 'fr', 'jp', 'cn', 'sg', 'ae',
}


def validate_email(email: str) -> Tuple[str, Optional[str]]:
    if not email or not email.strip():
        return '', 'empty'

    cleaned = email.strip().lower()

    # Apply OCR fixes
    for pattern, replacement in _EMAIL_FIXES:
        cleaned = re.sub(pattern, replacement, cleaned)

    # Must contain exactly one @
    if cleaned.count('@') != 1:
        return email.strip().lower(), f'invalid: {cleaned.count("@")} @ symbols'

    local, domain = cleaned.split('@')

    # Local part must be non-empty
    if not local:
        return email.strip().lower(), 'empty local part'

    # Domain must have at least one dot
    if '.' not in domain:
        return email.strip().lower(), f'invalid domain (no dot): {domain}'

    # Full format check
    if not _EMAIL_RE.match(cleaned):
        # Try to salvage: maybe OCR added a space in the domain
        cleaned_no_space = re.sub(r'\s', '', cleaned)
        if _EMAIL_RE.match(cleaned_no_space):
            cleaned = cleaned_no_space
        else:
            return email.strip().lower(), f'invalid format: {cleaned}'

    # Extract TLD for secondary check
    tld = domain.rsplit('.', 1)[-1].lower()

    # Accept if TLD is known OR is 2-6 chars (reasonable TLD length)
    if tld not in _KNOWN_TLDS and len(tld) > 6:
        return cleaned, f'unusual TLD: .{tld} (kept anyway)'

    return cleaned, None


# ═══════════════════════════════════════════════════════════════════════════════
# NAME
# ═══════════════════════════════════════════════════════════════════════════════

_HONORIFICS = {
    'dr.', 'dr', 'mr.', 'mr', 'mrs.', 'mrs', 'ms.', 'ms',
    'prof.', 'prof', 'er.', 'er', 'ca', 'ca.', 'adv', 'adv.',
    'col.', 'col', 'lt.', 'lt', 'maj.', 'maj', 'gen.', 'gen',
}

_NAME_ILLEGAL = re.compile(r'[|\\@#$%^*()+={}\[\]<>~`]')

_NOT_NAME_PATTERNS = [
    re.compile(r'\d{3,}'),
    re.compile(r'^[a-z]{1,2}\s', re.I),
    re.compile(r'\b(pvt|ltd|llp|inc|corp|private|limited)\b', re.I),
    re.compile(r'\b(road|street|nagar|sector|flat|plot|phase|floor)\b', re.I),
    re.compile(r'(gmail|yahoo|outlook|hotmail|@)'),
    re.compile(r'(www\.|http)', re.I),
    re.compile(r'\b(energy|power|systems|solutions|technologies)\b', re.I),
]


def validate_name(name: str) -> Tuple[str, Optional[str]]:
    if not name or not name.strip():
        return '', 'empty'

    cleaned = name.strip()
    cleaned = _NAME_ILLEGAL.sub('', cleaned).strip()
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)

    if not cleaned:
        return name.strip(), 'only illegal characters'

    for pat in _NOT_NAME_PATTERNS:
        if pat.search(cleaned):
            return name.strip(), 'looks like non-name content'

    words = cleaned.split()
    words = [w for w in words if len(w) > 1 or w.lower().rstrip('.') in _HONORIFICS]

    if len(words) < 2:
        return name.strip(), f'too few words ({len(words)}, need ≥2)'
    if len(words) > 5:
        words = words[:5]

    result_words = [w.capitalize() for w in words]
    return ' '.join(result_words), None


# ═══════════════════════════════════════════════════════════════════════════════
# COMPANY
# ═══════════════════════════════════════════════════════════════════════════════

_COMPANY_SUFFIXES = [
    'pvt. ltd.', 'pvt ltd', 'private limited', 'limited', 'ltd.', 'ltd',
    'llp', 'llc', 'inc.', 'inc', 'corp.', 'corp', 'co.',
    'services', 'solutions', 'systems', 'technologies', 'tech',
    'infrastructure', 'advisory', 'enterprises', 'associates',
    'consultancy', 'group', 'foundation', 'university', 'institute',
    'engineering', 'agency', 'authority', 'board', 'power systems',
    'energy', 'cleantech', 'electrolyser', 'fuel cell',
]

_COMPANY_NOISE_PREFIX = re.compile(r'^[a-z]{1,2}\s+(?=[A-Z])', re.M)


def validate_company(company: str) -> Tuple[str, Optional[str]]:
    if not company or not company.strip():
        return '', 'empty'

    cleaned = company.strip()
    cleaned = _COMPANY_NOISE_PREFIX.sub('', cleaned).strip()

    if len(cleaned) < 2:
        return company.strip(), f'too short ({len(cleaned)} chars)'

    cl = cleaned.lower()
    has_suffix = any(s in cl for s in _COMPANY_SUFFIXES)
    word_count = len(cleaned.split())

    if not has_suffix and word_count < 2:
        return cleaned, 'no recognised company suffix and only one word'

    return cleaned, None


# ═══════════════════════════════════════════════════════════════════════════════
# ADDRESS
# ═══════════════════════════════════════════════════════════════════════════════

_ADDR_KEYWORDS = re.compile(
    r'\b(flat|plot|no\.|door|house|shop|road|rd|street|st|lane|marg|nagar|'
    r'colony|sector|phase|floor|building|tower|complex|park|plaza|'
    r'sangam|wellesley|rto|nr\b|near|project|'
    r'pune|mumbai|delhi|bangalore|hyderabad|chennai|kolkata|india|'
    r'maharashtra|gujarat|karnataka|rajasthan)\b',
    re.I
)
_PIN_CODE = re.compile(r'\b\d{6}\b')
_HOUSE_NUM = re.compile(r'^\d+\s*[,/]')  # starts with house number


def validate_address(address: str) -> Tuple[str, Optional[str]]:
    if not address or not address.strip():
        return '', 'empty'

    cleaned = address.strip()
    cleaned = re.sub(r',\s*,+', ',', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)

    if len(cleaned) < 8:
        return cleaned, f'too short ({len(cleaned)} chars)'

    has_kw  = bool(_ADDR_KEYWORDS.search(cleaned))
    has_pin = bool(_PIN_CODE.search(cleaned))
    has_num = bool(_HOUSE_NUM.match(cleaned))

    if not has_kw and not has_pin and not has_num:
        return cleaned, 'no address keywords or PIN code found'

    return cleaned, None


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSITE
# ═══════════════════════════════════════════════════════════════════════════════

# Broad URL pattern — accepts any TLD 2-20 chars, with or without www
_WEBSITE_RE = re.compile(
    r'^(https?://)?(www\.)?'
    r'[a-zA-Z0-9][a-zA-Z0-9\-]*'
    r'(\.[a-zA-Z0-9\-]+)+'
    r'(/[^\s]*)?$'
)

# OCR artefacts in URLs
_URL_FIXES = [
    (r'\s+', ''),          # spaces
    (r'[,;]', '.'),        # comma → dot
    (r'\.\.+', '.'),       # double dots
    (r'^W\s*:\s*', ''),    # "W : www.h2e.energy" → "www.h2e.energy"
    (r'^w\s*:\s*', ''),    # lowercase variant
]


def validate_website(website: str) -> Tuple[str, Optional[str]]:
    if not website or not website.strip():
        return '', 'empty'

    cleaned = website.strip().lower()

    # Apply OCR fixes
    for pattern, replacement in _URL_FIXES:
        cleaned = re.sub(pattern, replacement, cleaned)

    # Add protocol if missing
    if not cleaned.startswith('http'):
        cleaned = 'http://' + cleaned

    if not _WEBSITE_RE.match(cleaned):
        return website.strip().lower(), f'invalid URL: {cleaned}'

    # Must have at least one dot after the protocol
    without_proto = re.sub(r'^https?://', '', cleaned)
    if '.' not in without_proto:
        return website.strip().lower(), 'no dot in domain'

    return cleaned, None


# ═══════════════════════════════════════════════════════════════════════════════
# GSTIN
# ═══════════════════════════════════════════════════════════════════════════════

_GSTIN_RE = re.compile(r'^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$')


def validate_gstin(gstin: str) -> Tuple[str, Optional[str]]:
    if not gstin or not gstin.strip():
        return '', 'empty'

    cleaned = re.sub(r'[\s\-]', '', gstin.strip()).upper()

    if len(cleaned) != 15:
        return gstin.strip(), f'must be 15 chars (got {len(cleaned)})'

    if not _GSTIN_RE.match(cleaned):
        return gstin.strip(), f'invalid GSTIN pattern: {cleaned}'

    return cleaned, None


# ═══════════════════════════════════════════════════════════════════════════════
# DESIGNATION
# ═══════════════════════════════════════════════════════════════════════════════

_VALID_DESIG_KEYWORDS = [
    'director', 'manager', 'engineer', 'consultant', 'professor',
    'dean', 'founder', 'co-founder', 'partner', 'associate',
    'executive', 'officer', 'analyst', 'architect', 'developer',
    'designer', 'contractor', 'electrician', 'plumber', 'auditor',
    'advisor', 'specialist', 'head', 'principal', 'president',
    'secretary', 'treasurer', 'chairman', 'ceo', 'cto', 'cfo', 'coo',
    'vp', 'vice president', 'senior', 'general', 'project',
    'business development', 'managing', 'proprietor', 'owner',
    'sales', 'marketing', 'operations', 'finance', 'hr', 'legal',
    'technical', 'regional', 'zonal', 'national', 'global',
]


def validate_designation(designation: str) -> Tuple[str, Optional[str]]:
    if not designation or not designation.strip():
        return '', 'empty'

    cleaned = designation.strip().title()
    dl = cleaned.lower()

    is_known = any(kw in dl for kw in _VALID_DESIG_KEYWORDS)
    if not is_known:
        return cleaned, f'unrecognised designation: "{cleaned}"'

    return cleaned, None


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

_VALIDATORS = {
    'phone':       validate_phone,
    'email':       validate_email,
    'name':        validate_name,
    'company':     validate_company,
    'address':     validate_address,
    'website':     validate_website,
    'gstin':       validate_gstin,
    'designation': validate_designation,
}


def validate_contact_info(
    contact: Dict[str, str],
    strict_mode: bool = False,
) -> Dict:
    """
    Validate and clean all fields in a contact dictionary.

    Parameters
    ----------
    contact     : dict with keys matching _VALIDATORS
    strict_mode : if True, invalid fields are cleared to ''.
                  if False (default), the best available value is kept.

    Returns
    -------
    {
        'validated'          : dict  – cleaned field values
        'errors'             : dict  – field → error message (invalid fields)
        'warnings'           : dict  – field → info about cleaning applied
        'is_valid'           : bool  – True if name + (phone or email) pass validation
        'has_critical_fields': bool  – True if name + (phone or email) are present
    }
    """
    validated: Dict[str, str] = {}
    errors:    Dict[str, str] = {}
    warnings:  Dict[str, str] = {}

    for field, validator in _VALIDATORS.items():
        raw = (contact.get(field) or '').strip()

        if not raw:
            validated[field] = ''
            continue

        cleaned, err = validator(raw)

        if err is None:
            validated[field] = cleaned
            if cleaned != raw:
                warnings[field] = f'auto-cleaned: "{raw}" → "{cleaned}"'
        else:
            errors[field] = err
            if strict_mode:
                validated[field] = ''
            else:
                # Keep best available value
                validated[field] = cleaned if cleaned else raw
                warnings[field] = f'kept with warning – {err}'

    # Critical-field check: a field is "ok" only if it has a value AND no error
    name_ok  = bool(validated.get('name'))  and 'name'  not in errors
    phone_ok = bool(validated.get('phone')) and 'phone' not in errors
    email_ok = bool(validated.get('email')) and 'email' not in errors

    has_name    = bool(validated.get('name'))
    has_contact = bool(validated.get('phone')) or bool(validated.get('email'))

    is_valid = name_ok and (phone_ok or email_ok)

    return {
        'validated':           validated,
        'errors':              errors,
        'warnings':            warnings,
        'is_valid':            is_valid,
        'has_critical_fields': has_name and has_contact,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    TESTS = [
        {
            'label': 'h2e card — non-.com TLD, T/M phones, W: website',
            'input': {
                'name':        'Rohish Kalvit',
                'phone':       'T +91-80070 27575  M. +91-91684 03315',
                'email':       'rohish.kalvit@h2e.energy',
                'designation': 'VP Business Development',
                'company':     'h2e Power Systems Private Limited',
                'address':     '20, Sangam Project, Phase II, Wellesley Rd., Nr RTO, Pune - 411001',
                'website':     'W : www.h2e.energy',
                'gstin':       '',
            },
            'expect_valid': True,
            'expect': {
                'email':   'rohish.kalvit@h2e.energy',
                'phone':   '+91 91684 03315',
                'website': 'http://www.h2e.energy',
            },
        },
        {
            'label': 'Clean real-world card',
            'input': {
                'name':        'Dr. Rajesh Kumar Singh',
                'phone':       '9876543210',
                'email':       'rajesh@techsolutions.com',
                'company':     'Tech Solutions Pvt. Ltd.',
                'address':     'Plot 123, Sector 5, Pune 411001',
                'website':     'www.techsolutions.com',
                'gstin':       '27AAAAA0000A1Z5',
                'designation': 'Senior Manager',
            },
            'expect_valid': True,
            'expect': {
                'phone':   '+91 98765 43210',
                'website': 'http://www.techsolutions.com',
            },
        },
        {
            'label': 'OCR noise in phone / email',
            'input': {
                'name':  'Anant Sant',
                'phone': '(91) 91 3692 0634',
                'email': 'anant.sant@idaminfra..com',
            },
            'expect_valid': True,
            'expect': {
                'email': 'anant.sant@idaminfra.com',
            },
        },
        {
            'label': 'Multiple phones',
            'input': {
                'name':  'Rajesh Kumar',
                'phone': '8605203066 / 8788505650',
                'email': 'rndecosistemspune@gmail.com',
            },
            'expect_valid': True,
            'expect': {
                'phone': '+91 86052 03066 / +91 87885 05650',
            },
        },
        {
            'label': 'Garbage data',
            'input': {
                'name':  '123 abc',
                'phone': '12345',
                'email': 'not-an-email',
                'gstin': 'BADGSTIN',
            },
            'expect_valid': False,
            'expect': {},
        },
        {
            'label': 'Non-standard TLDs',
            'input': {
                'name':  'John Doe',
                'phone': '9876543210',
                'email': 'john@startup.io',
                'website': 'startup.io',
            },
            'expect_valid': True,
            'expect': {
                'email':   'john@startup.io',
                'website': 'http://startup.io',
            },
        },
    ]

    all_pass = True
    for tc in TESTS:
        print(f"\n{'='*65}")
        print(f"  {tc['label']}")
        print('='*65)
        result = validate_contact_info(tc['input'], strict_mode=False)

        valid_mark = '✅' if result['is_valid'] == tc['expect_valid'] else '❌'
        if result['is_valid'] != tc['expect_valid']:
            all_pass = False
        print(f"  {valid_mark} is_valid={result['is_valid']} (expected {tc['expect_valid']})")

        for field, val in result['validated'].items():
            if val:
                status = '✓' if field not in result['errors'] else '⚠'
                print(f"    {status} {field:12}: {val}")

        # Check expected values
        for field, expected in tc.get('expect', {}).items():
            actual = result['validated'].get(field, '')
            ok = expected.lower() in actual.lower()
            mark = '✅' if ok else '❌'
            if not ok:
                all_pass = False
            print(f"    {mark} CHECK {field}: expected '{expected}' → got '{actual}'")

        if result['errors']:
            print("  Errors:")
            for f, e in result['errors'].items():
                print(f"    ✗ {f}: {e}")

    print(f"\n{'='*65}")
    print(f"  {'ALL TESTS PASSED ✅' if all_pass else 'SOME TESTS FAILED ❌'}")
    print('='*65)
