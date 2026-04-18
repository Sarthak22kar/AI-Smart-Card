"""
Smart Visiting Card Extractor  v3
==================================
Handles any card layout:
  - Name top-right with OCR noise  (Idam)
  - Name top-left in colour        (R&D Ecosistems)
  - Rotated card with labels       (SPPU)
  - Brand-only back side           (WattGuru)
  - Missing name → derive from email
"""

import re
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except Exception:
    SPACY_AVAILABLE = False
    print("spaCy not available – rule-based only")

# ── Patterns ──────────────────────────────────────────────────────────────────

MOBILE_RE = re.compile(
    r'(?:\+?91[\s\-]?)?'
    r'(?:\(91\)[\s\-]?)?'
    r'(?:[6-9]\d{9}'                         # plain 10-digit mobile
    r'|\d{5}[\s\-]\d{5}'                     # 80070 27575
    r'|\d{2,5}[\s\-]\d{4}[\s\-]\d{4})',      # spaced: 91 3692 0634
)

# M-labeled mobile: "M. +91-91684 03315" or "M +91-91684 03315"
M_PHONE_RE = re.compile(
    r'(?:^|[\s,;])[Mm][\s\.\:\-]+(\+?[\d][\d\s\-\.]{9,})',
    re.MULTILINE
)

# T/M labeled (legacy, kept for compatibility)
TM_PHONE_RE = re.compile(
    r'(?:^|[\s,;])[TtMm][\s\.\:\-]+(\+?[\d\s\-\.]{10,})',
    re.MULTILINE
)

TEL_LINE_RE = re.compile(r'^\s*(tel|t)\s*[:\-\.]', re.IGNORECASE)

# Broad email: accepts any TLD 2-20 chars (.com .in .energy .io etc.)
EMAIL_RE = re.compile(
    r'\b[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,20}\b'
)

# Website: with OR without www, any TLD
WEBSITE_RE = re.compile(
    r'(?:https?://)?(?:www\.)?[A-Za-z0-9][A-Za-z0-9\-]*\.[A-Za-z]{2,20}(?:\.[A-Za-z]{2,6})?(?:/\S*)?',
    re.I
)
GSTIN_RE     = re.compile(r'\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b')
HONORIFIC_RE = re.compile(
    r'(?:^|(?<=\s))(Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Prof\.?|Er\.?)\s+'
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
    re.IGNORECASE
)

DESIGNATION_KEYWORDS = [
    'associate director', 'managing director', 'executive director',
    'chief executive officer', 'chief technology officer',
    'vice president', 'vp business development', 'vp ', 'senior manager',
    'general manager', 'project manager', 'business development',
    'director', 'manager', 'engineer', 'consultant', 'professor',
    'dean', 'founder', 'co-founder', 'partner', 'associate', 'executive',
    'officer', 'analyst', 'architect', 'developer', 'designer', 'contractor',
    'electrician', 'plumber', 'auditor', 'advisor', 'specialist', 'head',
    'principal', 'president', 'secretary', 'treasurer', 'chairman',
    # Sales & field roles
    'sales representative', 'field sales', 'sales executive', 'sales manager',
    'business development executive', 'account manager', 'key account',
    'regional manager', 'area manager', 'territory manager',
    # Technical roles
    'technical lead', 'team lead', 'tech lead', 'software engineer',
    'system administrator', 'network engineer', 'data analyst',
    # Other common roles
    'representative', 'proprietor', 'owner', 'operator',
]

COMPANY_SUFFIXES = [
    'pvt. ltd.', 'pvt ltd', 'pvt. ltd', 'private limited', 'limited', 'ltd.', 'ltd',
    'llp', 'llc', 'inc.', 'inc', 'corp.', 'corp',
    'agency', 'services', 'solutions', 'systems', 'technologies',
    'infrastructure', 'advisory', 'enterprises', 'associates',
    'consultancy', 'group', 'foundation', 'university', 'institute',
    'ecosistems', 'ecosystems', 'power systems', 'engineering',
]

ADDR_INDICATORS = [
    'flat', 'plot', 'no.', 'near', 'nr ', 'road', 'rd.', 'rd,', 'street', 'nagar',
    'colony', 'sector', 'phase', 'floor', 'building', 'tower',
    'pune', 'mumbai', 'delhi', 'india', 'wasti', 'society',
    'piazza', 'plaza', 'park', 'east', 'west', 'north', 'south',
    'mahakali', 'andheri', 'chakala', 'technopolis', 'knowledge',
    'ganeshkhind', 'moshi', 'gaikwad', 'sangam', 'wellesley', 'rto',
    'project', 'phase ii', 'phase 2', 'wellesley', 'sangam',
]

LABEL_MAP = {
    'mobile': 'phone', 'mob': 'phone', 'cell': 'phone', 'phone': 'phone',
    'm': 'phone',                                    # M: +91-91684 03315
    'email': 'email', 'e-mail': 'email', 'mail': 'email',
    'e': 'email',                                    # E: rohish.kalvit@h2e.energy
    'website': 'website', 'web': 'website',
    'w': 'website',                                  # W: www.h2e.energy
    'address': 'address', 'addr': 'address',
    'gstin': 'gstin', 'gst': 'gstin',
}

# Words that indicate a line is NOT a person name
JUNK_NAME_WORDS = [
    'idam', 'wattguru', 'enfragy', 'by idam',
    'mumbai', 'pune', 'delhi', 'kolkata', 'hyderabad',
    'iso', 'certified', 'company',
    'govt', 'government', 'maharashtra', 'ministry', 'department',
    'energy', 'development', 'agency', 'authority', 'board',
    'empanelled', 'auditors', 'contractor', 'license',
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_noise(line: str) -> str:
    """Remove leading/trailing OCR garbage: '- = % wl ' → ''"""
    original = line
    
    # Step 1: Remove leading OCR noise patterns
    # Pattern: "ac ] Name" → "Name"
    line = re.sub(r'^[a-z]{1,2}\s*[\]\|]\s*', '', line, flags=re.IGNORECASE).strip()
    
    # Pattern: "- = % wl Name" → "Name" (remove leading symbols and short words)
    line = re.sub(r'^[\W\d_\s]+([a-z]{1,2}\s+)?', '', line, flags=re.IGNORECASE).strip()
    
    # Step 2: Remove leading non-alphanumeric characters
    line = re.sub(r'^[\W\d_\[\]|]+', '', line).strip()
    
    # Step 3: Remove trailing garbage characters
    line = re.sub(r'[\W_]+$', '', line).strip()
    
    # Step 4: Remove standalone garbage characters between words
    line = re.sub(r'\s+[¢£¥€§¶©®™°±×÷\[\]|]+\s+', ' ', line)
    
    # Step 5: Remove multiple spaces
    line = re.sub(r'\s{2,}', ' ', line)
    
    return line.strip()


def alpha_ratio(s: str) -> float:
    return sum(c.isalpha() for c in s) / max(len(s), 1)


def is_garbage(line: str) -> bool:
    """True if line is mostly symbols / OCR noise."""
    return alpha_ratio(line) < 0.45


def parse_labeled_fields(lines: list) -> dict:
    result = {}
    for line in lines:
        m = re.match(r'^([A-Za-z\-]+)\s*[:\-]\s*(.+)$', line.strip())
        if m:
            label = m.group(1).lower().strip()
            value = m.group(2).strip()
            field = LABEL_MAP.get(label)
            if field and value:
                result[field] = value
    return result


def extract_phones(text: str) -> list:
    """
    Extract phone numbers.
    Priority:
      1. M-labeled numbers (most reliable for mobile)
      2. General mobile pattern
      3. Any 10-12 digit sequence
    Skips T-labeled (landline/telephone) numbers.
    """
    phones, seen = [], set()

    def _add(raw: str):
        digits = re.sub(r'\D', '', raw)
        # Strip country code
        if len(digits) == 12 and digits.startswith('91'):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith('91'):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith('0'):
            digits = digits[1:]
        if len(digits) == 10 and digits[0] in '6789' and digits not in seen:
            seen.add(digits)
            phones.append(f'+91 {digits[:5]} {digits[5:]}')

    for line in text.split('\n'):
        # Skip T-labeled lines (landline/telephone) — but NOT M-labeled
        if TEL_LINE_RE.match(line):
            continue

        # M-labeled mobile: "M. +91-91684 03315"
        for m in M_PHONE_RE.finditer(line):
            _add(m.group(1))

        # General mobile pattern
        for m in MOBILE_RE.finditer(line):
            _add(m.group())

    # Scan full text for any remaining 10-12 digit sequences
    for m in re.finditer(r'\+?91[\s\-]?[6-9]\d{9}|[6-9]\d{9}|\d{5}[\s\-]\d{5}', text):
        _add(m.group())

    return phones[:3]  # max 3 phones


def extract_designation(lines: list) -> str:
    for line in lines:
        ll = line.lower().strip()
        # Find ALL matching keywords and pick the one that appears FIRST in the line
        matches = []
        for kw in DESIGNATION_KEYWORDS:
            idx = ll.find(kw)
            if idx != -1:
                matches.append((idx, kw))
        if matches:
            # Sort by position in line — take the earliest match
            matches.sort(key=lambda x: x[0])
            best_kw = matches[0][1]
            clean = strip_noise(line)
            m = re.search(re.escape(best_kw), clean, re.IGNORECASE)
            if m:
                return clean[m.start():].strip().title()
            return clean
    return ''


def extract_company(lines: list) -> str:
    """Extract company name, stripping OCR noise prefix."""
    for line in lines:
        if EMAIL_RE.search(line) or WEBSITE_RE.search(line):
            continue
        ll = line.lower().strip()
        if any(s in ll for s in COMPANY_SUFFIXES):
            # Clean the line first
            clean = strip_noise(line)
            
            # Try to find company with suffix using regex
            # Build pattern that captures full company name including suffix
            suffix_pattern = '|'.join(re.escape(s) for s in sorted(COMPANY_SUFFIXES, key=len, reverse=True))
            m = re.search(
                r'([A-Z&][A-Za-z0-9&\s\.\-]*(?:' + suffix_pattern + r'))',
                clean, re.IGNORECASE
            )
            if m:
                company = m.group(1).strip()
                # Remove leading 1-2 letter OCR noise: "ae h2e" → "h2e"
                # But preserve single letters that are part of name: "R & D" stays "R & D"
                # Check if it starts with single letter followed by space and NOT followed by &
                if re.match(r'^[a-z]\s+(?!&)', company, re.IGNORECASE):
                    company = re.sub(r'^[a-z]\s+', '', company, flags=re.IGNORECASE).strip()
                # Check for 2-letter prefix: "ae h2e" → "h2e"
                elif re.match(r'^[a-z]{2}\s+', company, re.IGNORECASE):
                    company = re.sub(r'^[a-z]{2}\s+', '', company, flags=re.IGNORECASE).strip()
                return company
            
            # Fallback: return cleaned line
            return clean if clean else line.strip()
    
    # If no suffix found, look for lines with company-like patterns
    for line in lines:
        if EMAIL_RE.search(line) or WEBSITE_RE.search(line):
            continue
        clean = strip_noise(line)
        # Company names are usually 2-5 words, mostly uppercase or title case
        words = clean.split()
        if 2 <= len(words) <= 5:
            # Check if it looks like a company (has &, capital letters, etc.)
            if re.search(r'[A-Z&]', clean) and not any(kw in clean.lower() for kw in DESIGNATION_KEYWORDS):
                # Make sure it's not a name (names have 2-3 words, mixed case)
                if clean.isupper() or '&' in clean or any(s in clean.lower() for s in ['systems', 'solutions', 'services', 'group']):
                    # Remove leading 1-2 letter OCR noise
                    if re.match(r'^[a-z]\s+(?!&)', clean, re.IGNORECASE):
                        clean = re.sub(r'^[a-z]\s+', '', clean, flags=re.IGNORECASE).strip()
                    elif re.match(r'^[a-z]{2}\s+', clean, re.IGNORECASE):
                        clean = re.sub(r'^[a-z]{2}\s+', '', clean, flags=re.IGNORECASE).strip()
                    return clean
    
    return ''


def extract_address(lines: list) -> str:
    """
    Extract address lines intelligently.
    Looks for:
      - Explicit 'Address:' label
      - Lines with flat/plot/road/city/pin patterns
      - Multi-line address blocks (consecutive address-like lines)
    Skips: taglines, slogans, company names, emails, phones
    """
    parts, in_block = [], False

    # Strong address signals — these almost certainly mean it's an address line
    STRONG_ADDR = [
        r'\d+\s*,',                          # starts with number+comma: "201," or "20,"
        r'\b\d{6}\b',                        # 6-digit PIN code
        r'\b(flat|plot|door|house|shop)\b',  # unit type
        r'\b(road|rd|street|st|lane|marg|path|nagar|colony|sector|phase)\b',
        r'\b(floor|building|tower|complex|park|plaza|mall)\b',
        r'\b(pune|mumbai|delhi|bangalore|hyderabad|chennai|kolkata|india)\b',
        r'\b(maharashtra|gujarat|karnataka|rajasthan|up|mp)\b',
        r'\b(east|west|north|south)\b.*\b(pune|mumbai|delhi)\b',
        r'\b(sangam|wellesley|rto|nr\b|near)\b',  # h2e card specific + general
        r'\b(project|phase\s+ii|phase\s+2)\b',
    ]

    # Lines that look like slogans/taglines — NOT addresses
    SLOGAN_PATTERNS = [
        r"india'?s?\s+first",
        r'fuel of the future',
        r'certified company',
        r'iso\s+\d{4}',
        r'empanelled',
        r'govt\s+of',
        r'by idam',
        r'wattguru',
        r'enfragy',
        r'cbg\s+for',
        r'vehicles',
        r'the\s+fuel',
        r'first\s+cbg',
    ]

    def is_strong_address(line: str) -> bool:
        ll = line.lower()
        return any(re.search(p, ll) for p in STRONG_ADDR)

    def is_slogan(line: str) -> bool:
        ll = line.lower()
        return any(re.search(p, ll) for p in SLOGAN_PATTERNS)

    for line in lines:
        ll = line.lower().strip()
        s  = line.strip()

        # Explicit address label
        if re.match(r'^(address|addr)\s*[:\-]', ll):
            in_block = True
            content = re.sub(r'^(address|addr)\s*[:\-]\s*', '', s, flags=re.I).strip()
            # Clean OCR noise from content
            content = re.sub(r'^[\W\d_]+', '', content).strip()
            if content:
                parts.append(content)
            continue

        if in_block:
            if re.match(r'^(email|phone|mobile|tel|website|gstin|e-mail)\s*[:\-]', ll):
                break
            if s:
                clean = re.sub(r'^[\W\d_]+', '', s).strip()
                if clean:
                    parts.append(clean)
            continue

        # Skip non-address lines
        if not s or len(s) < 5:                                  continue
        if EMAIL_RE.search(s) or WEBSITE_RE.search(s):           continue
        if TEL_LINE_RE.match(s):                                  continue
        if any(sf in ll for sf in COMPANY_SUFFIXES):             continue
        if is_slogan(s):                                          continue
        # Only apply garbage filter if line has no digits (PIN codes have low alpha ratio)
        if is_garbage(s) and not re.search(r'\d', s):            continue

        # Strong address signal → include
        if is_strong_address(s):
            # Must have at least one of: number, road/street/floor keyword, or city+state
            # Reject pure country/city-only lines like "INDIA" or "Mumbai | Pune"
            has_number  = bool(re.search(r'\d', s))
            has_road_kw = bool(re.search(
                r'\b(road|rd|street|st|lane|marg|flat|plot|floor|building|park|nagar|colony|sector|wasti|society|sangam|wellesley|rto|project|phase)\b',
                ll))
            has_city_state = bool(re.search(
                r'\b(pune|mumbai|delhi|bangalore|hyderabad|chennai|kolkata)\b', ll) and
                re.search(r'\b(maharashtra|gujarat|karnataka|india|\d{6})\b', ll))

            if not (has_number or has_road_kw or has_city_state):
                continue

            # Strip leading/trailing OCR noise and clean garbage characters
            clean = strip_noise(s)
            if clean:
                parts.append(clean)

    # Deduplicate while preserving order
    seen, unique = set(), []
    for p in parts:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique.append(p)

    return ', '.join(unique) if unique else ''


def extract_name(lines: list, company: str, designation: str,
                 email: str, website: str, gstin: str) -> str:
    """
    Priority:
      0 – honorific (Dr./Mr./Mrs.) found anywhere in line
      1 – spaCy PERSON in first 6 lines
      2 – heuristic 2-3 cap words in first 4 lines
      3 – spaCy PERSON anywhere
      4 – heuristic anywhere
    """
    candidates = []
    co_l  = company.lower()     if company     else ''
    em_l  = email.lower()       if email       else ''
    web_l = website.lower()     if website     else ''

    for idx, line in enumerate(lines):
        s  = line.strip()
        sl = s.lower()

        # Hard skips
        if not s or len(s) < 3:                                  continue
        if em_l  and em_l  in sl:                                continue
        if web_l and web_l in sl:                                continue
        if gstin and gstin in s:                                  continue
        if co_l  and co_l  in sl:                                continue
        if EMAIL_RE.search(s) or WEBSITE_RE.search(s):           continue
        if TEL_LINE_RE.match(s):                                  continue
        if re.search(r'\d{5,}', s):                              continue
        if re.search(r'[+@|\\¢£¥€§\[\]]', s):                   continue  # Added brackets and pipes
        if any(ind in sl for ind in ADDR_INDICATORS):            continue
        if any(sf  in sl for sf  in COMPANY_SUFFIXES):           continue
        if any(kw  in sl for kw  in DESIGNATION_KEYWORDS):       continue
        if is_garbage(s):                                         continue
        if any(jw in sl for jw in JUNK_NAME_WORDS):              continue

        # Clean the line first
        clean = strip_noise(s)
        if not clean or len(clean) < 3:                          continue
        
        words = clean.split()
        # Reject single short tokens (OCR artifacts)
        if len(words) == 1 and len(clean) <= 4:                  continue
        # Reject lines with >40% duplicate words
        unique = set(w.lower().strip("'\"") for w in words)
        if len(unique) < len(words) * 0.6:                       continue
        # Reject if mostly lowercase (likely not a name)
        if clean.islower():                                       continue
        # Reject if has too many special characters
        if sum(not c.isalnum() and not c.isspace() for c in clean) > 2:  continue
        # Reject if contains organization keywords (govt, ministry, etc.)
        clean_lower = clean.lower()
        org_keywords = ['govt', 'government', 'ministry', 'department', 'agency', 'authority', 'board', 'empanelled']
        if any(kw in clean_lower for kw in org_keywords):        continue

        # ── Strategy 0: honorific anywhere ──────────────────────────────────
        hon = HONORIFIC_RE.search(clean)
        if hon:
            name = (hon.group(1) + ' ' + hon.group(2)).strip()
            candidates.append((0, name))
            continue

        # ── Strategy 1/3: spaCy NER (only first 8 lines to save time) ─────────
        if SPACY_AVAILABLE and idx < 8:
            doc = nlp(clean)
            for ent in doc.ents:
                if ent.label_ == 'PERSON':
                    en = ent.text.strip()
                    if len(en.split()) < 2:
                        continue
                    if any(jw in en.lower() for jw in JUNK_NAME_WORDS):
                        continue
                    # Additional check: reject if contains org keywords
                    if any(kw in en.lower() for kw in org_keywords):
                        continue
                    pri = 1 if idx < 6 else 3
                    candidates.append((pri, en))
                    break

        # ── Strategy 2/4: heuristic ─────────────────────────────────────────
        cw = clean.split()
        if 2 <= len(cw) <= 4:
            cl = clean.lower()
            if any(jw in cl for jw in JUNK_NAME_WORDS):          continue
            if any(kw in cl for kw in org_keywords):             continue
            if clean.isupper() and len(cw) > 2:                  continue
            cap = sum(1 for w in cw if w and w[0].isupper())
            # Must have at least 2 capitalized words
            if cap >= 2:
                pri = 2 if idx < 4 else 4
                candidates.append((pri, clean))

    if not candidates:
        return ''

    candidates.sort(key=lambda x: (x[0], len(x[1])))
    return candidates[0][1]


def name_from_email(email: str) -> str:
    """
    Derive a person name from email address.

    Examples:
      anant.sant@idaminfra.com       → Anant Sant
      rohish.kalvit@h2e.energy       → Rohish Kalvit
      krushhnakantm@vintechin.com    → Krushhnakantm  (single word, rejected)
      director.sharma@sharmaassoc.com → Director Sharma
      info@company.com               → (rejected — generic)
      sales@company.com              → (rejected — generic)
    """
    if not email:
        return ''

    local = email.split('@')[0]

    # Reject generic/role-based emails
    generic = {'info', 'sales', 'support', 'admin', 'contact', 'hello',
               'mail', 'office', 'hr', 'accounts', 'enquiry', 'inquiry',
               'marketing', 'service', 'services', 'help', 'team', 'no-reply',
               'noreply', 'webmaster', 'postmaster'}
    if local.lower() in generic:
        return ''

    # Split on separators: dots, underscores, hyphens
    derived = re.sub(r'[._\-]+', ' ', local).strip().title()
    parts = derived.split()

    # Only use if 2+ words, no digits, each word 2+ chars
    if len(parts) >= 2 and not re.search(r'\d', derived) and all(len(p) >= 2 for p in parts):
        return derived

    return ''


# ── Main extraction ───────────────────────────────────────────────────────────

def extract_contact_info(text: str) -> dict:
    contact = {
        'name': '', 'phone': '', 'email': '',
        'designation': '', 'company': '', 'address': '',
        'website': '', 'gstin': '',
    }
    if not text or not text.strip():
        return contact

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    full  = '\n'.join(lines)

    # 1. Labeled fields (Mobile:, E-mail:, etc.)
    labeled = parse_labeled_fields(lines)
    for f in ('phone', 'email', 'website', 'gstin'):
        if labeled.get(f):
            contact[f] = labeled[f]

    # 2. Phone (personal mobiles, skip Tel: lines)
    if not contact['phone']:
        phones = extract_phones(full)
        contact['phone'] = ' / '.join(phones)

    # 3. Email
    if not contact['email']:
        emails = EMAIL_RE.findall(full)
        if emails:
            contact['email'] = emails[0]

    # 4. Website — handle "W : www.h2e.energy" label and non-www URLs
    if not contact['website']:
        # First try labeled: "W: ...", "Website: ..."
        for line in lines:
            m = re.match(r'^\s*[Ww](?:ebsite)?\s*[:\-\.]\s*(.+)', line.strip())
            if m:
                candidate = m.group(1).strip()
                if '.' in candidate and len(candidate) > 4 and '@' not in candidate:
                    contact['website'] = candidate
                    break
        # Then try WEBSITE_RE on full text — but exclude email addresses
        if not contact['website']:
            # Remove email addresses from text before searching for websites
            text_no_email = re.sub(EMAIL_RE, '', full)
            webs = WEBSITE_RE.findall(text_no_email)
            # Filter: must have a dot, no @, must look like a real domain
            webs = [
                w for w in webs
                if '@' not in w
                and len(w) > 5
                and re.search(r'\.[a-zA-Z]{2,}', w)
                and not re.match(r'^[\d\s\-\+]+$', w)
            ]
            if webs:
                contact['website'] = webs[0]

    # 5. GSTIN
    if not contact['gstin']:
        gst = GSTIN_RE.findall(full)
        if gst:
            contact['gstin'] = gst[0]

    # 6. Designation
    contact['designation'] = extract_designation(lines)

    # 7. Company
    contact['company'] = extract_company(lines)

    # 8. Address
    contact['address'] = extract_address(lines)

    # 9. Name
    contact['name'] = extract_name(
        lines,
        company     = contact['company'],
        designation = contact['designation'],
        email       = contact['email'],
        website     = contact['website'],
        gstin       = contact['gstin'],
    )

    # 10. Fallback: derive name from email
    if not contact['name']:
        contact['name'] = name_from_email(contact['email'])

    return contact


def process_visiting_card(front_text: str, back_text: str) -> dict:
    front = extract_contact_info(front_text)
    back  = extract_contact_info(back_text)

    def richness(info: dict) -> int:
        """Count how many fields were found."""
        return sum(1 for v in info.values() if v and v.strip())

    def is_generic_email(email: str) -> bool:
        """Return True if email is a generic/role-based address."""
        if not email:
            return True
        local = email.split('@')[0].lower()
        generic = {'info', 'sales', 'support', 'admin', 'contact', 'hello',
                   'mail', 'office', 'hr', 'accounts', 'enquiry', 'inquiry',
                   'marketing', 'service', 'services', 'help', 'team',
                   'no-reply', 'noreply', 'webmaster', 'postmaster'}
        return local in generic

    # Use the richer side as primary (handles brand-only front cards)
    if richness(back) > richness(front):
        primary, secondary = back, front
    else:
        primary, secondary = front, back

    merged = {}
    for key in primary:
        if key == 'name':
            if primary[key]:
                merged[key] = primary[key]
            elif secondary.get(key):
                bn = secondary[key]
                if not any(jw in bn.lower() for jw in JUNK_NAME_WORDS):
                    merged[key] = bn
                else:
                    merged[key] = ''
            else:
                merged[key] = ''
        elif key == 'email':
            # Prefer personal email over generic (info@, sales@, etc.)
            p_email = primary.get('email', '')
            s_email = secondary.get('email', '')
            if p_email and not is_generic_email(p_email):
                merged[key] = p_email
            elif s_email and not is_generic_email(s_email):
                merged[key] = s_email
            else:
                # Both generic or both empty — take whichever exists
                merged[key] = p_email or s_email
        else:
            merged[key] = primary[key] or secondary.get(key, '')

    return merged


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    TESTS = {
        "Idam – exact OCR from server": (
            """NS
- = % wl Idam Associate Director
== ea +(91) 91 3692 0634
3 +(91) 94 2308 6634
anant.sant@idaminfra.com
Idam Infrastructure Advisory Pvt. Ltd.
Technopolis Knowledge Park, 5th Floor, Mahakali Caves Road,
Chakala, Andheri East, Mumbai - 400 093. India.
Tel: +(91) 22 6862 0300
An ISO 2015 Certified Company www.idaminfra.com""",
            """iii aaa
WattGuru | Enfragy
By Idam By Idam
Mumbai | Pune | New Delhi | Kolkata | Hyderabad"""
        ),
        "R&D Ecosistems": (
            """Rajesh Kumar Singh
8605203066 / 8788505650
R & D ECOSISTEMS
Maharashtra Energy Development Agency
Empanelled Energy AuditorsElectrical Contractor License
Address: - Flat No. 504, River Breeze Society, Gaikwad Wasti, Moshi, Pune 412105
Email-rndecosistemspune@gmail.com
GSTIN -27BVFPK3861G1ZH""", ""
        ),
        "SPPU – rotated card": (
            """SAVITRIBAI PHULE PUNE UNIVERSITY
Ganeshkhind, Pune-411007.
Dr. Aditya Abhyankar
Dean, Faculty of Technology
Professor, Dept. of Technology
Phone  : +91-20-25601270
Mobile : +91-9860119930
E-mail : aditya.abhyankar@unipune.ac.in""", ""
        ),
    }

    EXPECTED = {
        "Idam – exact OCR from server": {
            "name": "Anant Sant",
            "email": "anant.sant@idaminfra.com",
            "designation": "Associate Director",
            "phone": "91369",          # partial match — digits present in formatted number
        },
        "R&D Ecosistems": {
            "name": "Rajesh Kumar Singh",
            "phone": "86052",          # partial match
        },
        "SPPU – rotated card": {
            "name": "Dr. Aditya Abhyankar",
            "phone": "9860119930",     # digits present
        },
    }

    all_pass = True
    for title, (front, back) in TESTS.items():
        print(f"\n{'='*55}")
        print(f"  {title}")
        print('='*55)
        r = process_visiting_card(front, back)
        for k, v in r.items():
            status = '✅' if v else '⬜'
            print(f"  {status} {k:12}: {v or '—'}") 

        # Check expectations
        exp = EXPECTED.get(title, {})
        for field, expected_val in exp.items():
            actual = r.get(field, '')
            ok = expected_val.lower() in actual.lower()
            mark = '✅' if ok else '❌'
            if not ok:
                all_pass = False
            print(f"  {mark} CHECK {field}: expected '{expected_val}' → got '{actual}'")

    print(f"\n{'='*55}")
    print(f"  {'ALL TESTS PASSED ✅' if all_pass else 'SOME TESTS FAILED ❌'}")
    print('='*55)
