"""
Accuracy Test Suite  –  AI Smart Visiting Card System
======================================================
Tests the full extraction pipeline (smart_extractor + field_validator)
against real-world card OCR text samples.

Run:  python test_accuracy.py
      python test_accuracy.py -v        # verbose: show all field values
      python test_accuracy.py -f name   # filter: only run tests with 'name' in title
"""

import sys
import re
import time
import argparse
from smart_extractor import process_visiting_card
from field_validator import validate_contact_info

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
RESET  = '\033[0m'
BOLD   = '\033[1m'

def ok(s):  return f"{GREEN}✅ {s}{RESET}"
def fail(s):return f"{RED}❌ {s}{RESET}"
def warn(s):return f"{YELLOW}⚠️  {s}{RESET}"
def info(s):return f"{CYAN}{s}{RESET}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CASES
# Each test has:
#   title       – human-readable name
#   front       – OCR text from front of card
#   back        – OCR text from back of card ('' if none)
#   expected    – dict of field → expected value (partial match, case-insensitive)
#   must_empty  – list of fields that MUST be empty (not extracted)
# ═══════════════════════════════════════════════════════════════════════════════

TESTS = [

    # ── 1. h2e Power Systems (the card from the screenshot) ──────────────────
    {
        'title': 'h2e Power Systems — non-.com email, T/M phones, W: website',
        'front': """Rohish Kalvit
VP  Business Development

h2e Power Systems Private Limited
20, Sangam Project, Phase II,
Wellesley Rd., Nr RTO, Pune - 411001
T  +91-80070 27575    M  +91- 91684 03315
E  rohish.kalvit@h2e.energy

24x7 Clean, Green, Reliable & Affordable Energy for all""",
        'back': """homiHydrogen  KALAM FC
HyFuels  O hm CleanTech

Electrolysers  Fuel Cell  e-Fuels  Skill Development

W : www.h2e.energy""",
        'expected': {
            'name':        'Rohish Kalvit',
            'phone':       '91684',          # mobile digits present
            'email':       'rohish.kalvit@h2e.energy',
            'designation': 'VP',
            'company':     'h2e Power Systems',
            'address':     'Pune',
            'website':     'h2e.energy',
        },
        'must_empty': ['gstin'],
    },

    # ── 2. Idam Infrastructure (OCR noise, T-labeled landline) ───────────────
    {
        'title': 'Idam Infrastructure — OCR noise, T-labeled landline, name from email',
        'front': """NS
- = % wl Idam Associate Director
== ea +(91) 91 3692 0634
3 +(91) 94 2308 6634
anant.sant@idaminfra.com
Idam Infrastructure Advisory Pvt. Ltd.
Technopolis Knowledge Park, 5th Floor, Mahakali Caves Road,
Chakala, Andheri East, Mumbai - 400 093. India.
Tel: +(91) 22 6862 0300
An ISO 2015 Certified Company www.idaminfra.com""",
        'back': """iii aaa
WattGuru | Enfragy
By Idam By Idam
Mumbai | Pune | New Delhi | Kolkata | Hyderabad""",
        'expected': {
            'name':        'Anant Sant',
            'phone':       '91369',          # mobile digits
            'email':       'anant.sant@idaminfra.com',
            'designation': 'Associate Director',
            'company':     'Idam',
            'address':     'Mumbai',
            'website':     'idaminfra.com',
        },
        'must_empty': [],
    },

    # ── 3. R&D Ecosistems (GSTIN, address label, multiple phones) ────────────
    {
        'title': 'R&D Ecosistems — GSTIN, labeled address, multiple phones',
        'front': """Rajesh Kumar Singh
8605203066 / 8788505650
R & D ECOSISTEMS
Maharashtra Energy Development Agency
Empanelled Energy AuditorsElectrical Contractor License
Address: - Flat No. 504, River Breeze Society, Gaikwad Wasti, Moshi, Pune 412105
Email-rndecosistemspune@gmail.com
GSTIN -27BVFPK3861G1ZH""",
        'back': '',
        'expected': {
            'name':    'Rajesh Kumar Singh',
            'phone':   '86052',
            'email':   'rndecosistemspune@gmail.com',
            'company': 'ECOSISTEMS',
            'address': 'Pune',
            'gstin':   '27BVFPK3861G1ZH',
        },
        'must_empty': [],
    },

    # ── 4. SPPU (university, honorific, Mobile: label) ────────────────────────
    {
        'title': 'SPPU University — honorific Dr., Mobile: label, .ac.in email',
        'front': """SAVITRIBAI PHULE PUNE UNIVERSITY
Ganeshkhind, Pune-411007.
Dr. Aditya Abhyankar
Dean, Faculty of Technology
Professor, Dept. of Technology
Phone  : +91-20-25601270
Mobile : +91-9860119930
E-mail : aditya.abhyankar@unipune.ac.in""",
        'back': '',
        'expected': {
            'name':        'Dr. Aditya Abhyankar',
            'phone':       '9860119930',
            'email':       'aditya.abhyankar@unipune.ac.in',
            'designation': 'Dean',
            'company':     'SAVITRIBAI PHULE PUNE UNIVERSITY',
            'address':     'Pune',
        },
        'must_empty': ['gstin'],
    },

    # ── 5. Leksa Lighting (all caps company, designation on same line) ────────
    {
        'title': 'Leksa Lighting — all-caps company, designation extraction',
        'front': """Abhijit Dattaram Hande
General Manager - West Region
LEKSA LIGHTING TECHNOLOGIES PVT LTD
abhijit.hande@leksalighting.com
+91 98765 12345
www.leksalighting.com""",
        'back': '',
        'expected': {
            'name':        'Abhijit',
            'phone':       '98765',
            'email':       'abhijit.hande@leksalighting.com',
            'designation': 'General Manager',
            'company':     'LEKSA LIGHTING',
            'website':     'leksalighting.com',
        },
        'must_empty': ['gstin'],
    },

    # ── 6. Primove Engineering (Director, Pvt. Ltd.) ──────────────────────────
    {
        'title': 'Primove Engineering — Director, Pvt. Ltd., standard layout',
        'front': """Santosh Gondhalekar
Director
PRIMOVE ENGINEERING PVT. LTD.
santosh@primove.in
+91 99876 54321
20, Industrial Estate, Hadapsar, Pune - 411028""",
        'back': '',
        'expected': {
            'name':        'Santosh Gondhalekar',
            'phone':       '99876',
            'email':       'santosh@primove.in',
            'designation': 'Director',
            'company':     'PRIMOVE ENGINEERING',
            'address':     'Pune',
        },
        'must_empty': [],
    },

    # ── 7. Phone edge cases ───────────────────────────────────────────────────
    {
        'title': 'Phone edge cases — country code variants, spaced digits',
        'front': """Test Person
Senior Engineer
Test Corp Pvt Ltd
Mob: 91-98765-43210
test@testcorp.com""",
        'back': '',
        'expected': {
            'name':  'Test Person',
            'phone': '98765',
            'email': 'test@testcorp.com',
        },
        'must_empty': [],
    },

    # ── 8. Email edge cases ───────────────────────────────────────────────────
    {
        'title': 'Email edge cases — .co.in, double dots, OCR noise',
        'front': """Priya Sharma
CEO
Sharma Enterprises
priya.sharma@company.co.in
+91 87654 32109
www.sharmaenterprises.co.in""",
        'back': '',
        'expected': {
            'name':    'Priya Sharma',
            'phone':   '87654',
            'email':   'priya.sharma@company.co.in',
            'website': 'sharmaenterprises.co.in',
        },
        'must_empty': [],
    },

    # ── 9. Minimal card (only name + phone) ───────────────────────────────────
    {
        'title': 'Minimal card — only name and phone, no email/website',
        'front': """Vikram Mehta
9876543210""",
        'back': '',
        'expected': {
            'name':  'Vikram Mehta',
            'phone': '98765',
        },
        'must_empty': ['email', 'website', 'gstin'],
    },

    # ── 10. OCR noise heavy ───────────────────────────────────────────────────
    {
        'title': 'Heavy OCR noise — garbage characters around real data',
        'front': """== ae ] Suresh Patel
-- Director --
@@ XYZ Solutions Pvt. Ltd. ##
suresh.patel@xyz.com
+91 76543 21098
Plot 45, MIDC, Nashik - 422010""",
        'back': '',
        'expected': {
            'name':        'Suresh Patel',
            'phone':       '76543',
            'email':       'suresh.patel@xyz.com',
            'designation': 'Director',
            'company':     'XYZ Solutions',
            'address':     'Nashik',
        },
        'must_empty': [],
    },

    # ── 11. Back-side only data ───────────────────────────────────────────────
    {
        'title': 'Back-side data — website and GSTIN only on back',
        'front': """Amit Joshi
Sales Manager
TechVision Systems Ltd
amit.joshi@techvision.com
+91 88776 65544""",
        'back': """www.techvision.com
GSTIN: 27AABCT1234A1Z5
Serving India since 2005""",
        'expected': {
            'name':    'Amit Joshi',
            'phone':   '88776',
            'email':   'amit.joshi@techvision.com',
            'website': 'techvision.com',
            'gstin':   '27AABCT1234A1Z5',
        },
        'must_empty': [],
    },

    # ── 12. Designation edge cases ────────────────────────────────────────────
    {
        'title': 'Designation edge cases — VP, Co-Founder, Chief Officer',
        'front': """Neha Gupta
Co-Founder & Chief Technology Officer
InnovateTech Pvt. Ltd.
neha@innovatetech.io
+91 99988 77766""",
        'back': '',
        'expected': {
            'name':        'Neha Gupta',
            'phone':       '99988',
            'email':       'neha@innovatetech.io',
            'designation': 'Co-Founder',
            'company':     'InnovateTech',
        },
        'must_empty': [],
    },

    # ── 13. Address with PIN code ─────────────────────────────────────────────
    {
        'title': 'Address extraction — multi-line with PIN code',
        'front': """Ravi Kumar
Manager Operations
Kumar Industries
ravi@kumarind.com
+91 77665 54433
B-12, Industrial Area,
Phase 2, Pimpri,
Pune - 411018""",
        'back': '',
        'expected': {
            'name':    'Ravi Kumar',
            'phone':   '77665',
            'email':   'ravi@kumarind.com',
            'address': '411018',
        },
        'must_empty': [],
    },

    # ── 14. Name with single word (should derive from email) ──────────────────
    {
        'title': 'Name derivation from email — single word name on card',
        'front': """Sharma
Director
Sharma & Associates
director.sharma@sharmaassoc.com
+91 66554 43322""",
        'back': '',
        'expected': {
            'phone': '66554',
            'email': 'director.sharma@sharmaassoc.com',
        },
        'must_empty': [],
    },

    # ── 15. Website without www ───────────────────────────────────────────────
    {
        'title': 'Website without www prefix — domain.tld format',
        'front': """Kiran Desai
Product Manager
Desai Tech Solutions
kiran@desaitech.in
+91 98443 32211
desaitech.in""",
        'back': '',
        'expected': {
            'name':    'Kiran Desai',
            'phone':   '98443',
            'email':   'kiran@desaitech.in',
            'website': 'desaitech.in',
        },
        'must_empty': [],
    },

    # ── 16. Vintech card — rotated, person on back, company on front ──────────
    {
        'title': 'Vintech — person on back side, company-only front, rotated card',
        'front': """Vintech Electronic Systems Pvt. Ltd.
Office 405, 4th floor, A-wing,
Kapil Zenith I.T. Park, Bavdhan, Pune 411021
(020) 2566 6233
info@vintechin.com
www.vintechin.com""",
        'back': """Krushnakant Masal
Field Sales Representative
krushhnakantm@vintechin.com
+91 98817 24167""",
        'expected': {
            'name':        'Krushnakant Masal',
            'phone':       '98817',
            'email':       'krushhnakantm@vintechin.com',
            'designation': 'Field Sales Representative',
            'company':     'Vintech',
            'address':     'Pune',
            'website':     'vintechin.com',
        },
        'must_empty': [],
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_test(tc: dict, verbose: bool = False) -> dict:
    """Run a single test case. Returns result dict."""
    front = tc['front']
    back  = tc.get('back', '')

    # Run extraction pipeline
    extracted = process_visiting_card(front, back)

    # Run validation
    val_result = validate_contact_info(extracted, strict_mode=False)
    validated  = val_result['validated']

    # Check expected fields
    field_results = {}
    for field, expected_val in tc.get('expected', {}).items():
        actual = validated.get(field, '') or ''
        # For phone fields: compare digit sequences (ignore formatting spaces/dashes)
        if field == 'phone':
            actual_digits   = re.sub(r'\D', '', actual)
            expected_digits = re.sub(r'\D', '', expected_val)
            passed = expected_digits in actual_digits
        else:
            passed = expected_val.lower() in actual.lower()
        field_results[field] = {
            'expected': expected_val,
            'actual':   actual,
            'passed':   passed,
        }

    # Check must_empty fields
    empty_results = {}
    for field in tc.get('must_empty', []):
        actual = validated.get(field, '') or ''
        passed = not actual.strip()
        empty_results[field] = {
            'actual': actual,
            'passed': passed,
        }

    all_passed = (
        all(r['passed'] for r in field_results.values()) and
        all(r['passed'] for r in empty_results.values())
    )

    return {
        'title':         tc['title'],
        'passed':        all_passed,
        'validated':     validated,
        'field_results': field_results,
        'empty_results': empty_results,
        'val_errors':    val_result['errors'],
        'val_warnings':  val_result['warnings'],
    }


def print_result(result: dict, verbose: bool = False):
    """Print a single test result."""
    status = ok('PASS') if result['passed'] else fail('FAIL')
    print(f"\n  {status}  {BOLD}{result['title']}{RESET}")

    # Show field checks
    for field, fr in result['field_results'].items():
        mark = ok('') if fr['passed'] else fail('')
        print(f"    {mark} {field:12}: expected '{fr['expected']}' "
              f"→ got '{fr['actual'][:60]}'")

    # Show must-empty checks
    for field, er in result['empty_results'].items():
        if not er['passed']:
            print(f"    {fail('')} {field:12}: should be empty but got '{er['actual'][:60]}'")

    # Show validation errors
    if result['val_errors'] and verbose:
        for field, err in result['val_errors'].items():
            print(f"    {warn('')} validation error {field}: {err}")

    # Show all extracted fields in verbose mode
    if verbose:
        print(f"    {'─'*50}")
        for field, val in result['validated'].items():
            mark = '✓' if val else '·'
            print(f"    {mark} {field:12}: {val or '—'}")


def main():
    parser = argparse.ArgumentParser(description='Run accuracy tests')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show all extracted field values')
    parser.add_argument('-f', '--filter', type=str, default='',
                        help='Only run tests containing this string in title')
    args = parser.parse_args()

    tests_to_run = TESTS
    if args.filter:
        tests_to_run = [t for t in TESTS
                        if args.filter.lower() in t['title'].lower()]
        if not tests_to_run:
            print(f"No tests match filter: '{args.filter}'")
            return

    print(f"\n{BOLD}{'═'*70}{RESET}")
    print(f"{BOLD}  AI Smart Visiting Card — Accuracy Test Suite{RESET}")
    print(f"{BOLD}{'═'*70}{RESET}")
    print(f"  Running {len(tests_to_run)} tests...\n")

    t0 = time.time()
    results = []
    for tc in tests_to_run:
        result = run_test(tc, verbose=args.verbose)
        results.append(result)
        print_result(result, verbose=args.verbose)

    elapsed = time.time() - t0

    # Summary
    passed = sum(1 for r in results if r['passed'])
    total  = len(results)
    pct    = passed / total * 100

    print(f"\n{BOLD}{'═'*70}{RESET}")
    print(f"{BOLD}  RESULTS: {passed}/{total} tests passed  ({pct:.0f}% accuracy){RESET}")
    print(f"  Time: {elapsed:.2f}s")

    # Per-field accuracy
    field_pass = {f: 0 for f in ('name','phone','email','designation',
                                  'company','address','website','gstin')}
    field_total = {f: 0 for f in field_pass}

    for result in results:
        for field, fr in result['field_results'].items():
            field_total[field] = field_total.get(field, 0) + 1
            if fr['passed']:
                field_pass[field] = field_pass.get(field, 0) + 1

    print(f"\n  Per-field accuracy:")
    for field in ('name','phone','email','designation','company',
                  'address','website','gstin'):
        t = field_total.get(field, 0)
        p = field_pass.get(field, 0)
        if t > 0:
            pct_f = p / t * 100
            bar = '█' * int(pct_f / 10) + '░' * (10 - int(pct_f / 10))
            color = GREEN if pct_f >= 80 else (YELLOW if pct_f >= 60 else RED)
            print(f"    {field:12}: {color}{bar}{RESET} {p}/{t} ({pct_f:.0f}%)")

    # Failed tests summary
    failed = [r for r in results if not r['passed']]
    if failed:
        print(f"\n  {RED}Failed tests:{RESET}")
        for r in failed:
            print(f"    ✗ {r['title']}")
            for field, fr in r['field_results'].items():
                if not fr['passed']:
                    print(f"      {field}: expected '{fr['expected']}' "
                          f"→ got '{fr['actual'][:50]}'")

    print(f"{BOLD}{'═'*70}{RESET}\n")

    # Exit code: 0 if all pass, 1 if any fail
    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
