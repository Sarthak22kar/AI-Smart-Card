"""
Smart Recommendation Engine  v2
=================================
Ranks contacts by relevance to a search query using:
  - Service/designation match
  - Company domain match
  - Name match
  - Services field match
  - Weighted scoring
"""

import re


# ── Keyword expansion ─────────────────────────────────────────────────────────
KEYWORD_MAP = {
    # Trades
    'plumber':          ['plumber', 'plumbing', 'pipe', 'water supply', 'sanitation'],
    'electrician':      ['electrician', 'electrical', 'wiring', 'electric', 'power'],
    'carpenter':        ['carpenter', 'carpentry', 'furniture', 'wood', 'woodwork'],
    'painter':          ['painter', 'painting', 'interior design', 'wall'],
    'mechanic':         ['mechanic', 'automobile', 'car repair', 'vehicle', 'auto'],
    'ac repair':        ['ac', 'air conditioning', 'hvac', 'cooling', 'refrigeration'],
    'welder':           ['welder', 'welding', 'fabrication', 'metal'],
    # Professional
    'doctor':           ['doctor', 'physician', 'medical', 'clinic', 'hospital', 'health', 'medicine'],
    'lawyer':           ['lawyer', 'advocate', 'legal', 'attorney', 'law', 'court'],
    'ca':               ['chartered accountant', 'accountant', 'audit', 'tax', 'gst', 'finance', 'ca'],
    'architect':        ['architect', 'architecture', 'building design', 'construction'],
    'engineer':         ['engineer', 'engineering', 'technical'],
    'consultant':       ['consultant', 'consulting', 'advisory', 'advisor'],
    'professor':        ['professor', 'teacher', 'education', 'training', 'faculty'],
    # Business
    'marketing':        ['marketing', 'digital marketing', 'seo', 'advertising', 'brand', 'promotion'],
    'software':         ['software', 'developer', 'technology', 'tech', 'computer', 'programming', 'app'],
    'sales':            ['sales', 'business development', 'representative', 'account manager'],
    'hr':               ['hr', 'human resource', 'recruitment', 'hiring', 'staffing'],
    'logistics':        ['logistics', 'transport', 'delivery', 'supply chain', 'courier', 'shipping'],
    'real estate':      ['real estate', 'property', 'builder', 'developer', 'construction', 'flat', 'plot'],
    'insurance':        ['insurance', 'policy', 'claim', 'coverage', 'life insurance'],
    'banking':          ['banking', 'bank', 'finance', 'loan', 'investment', 'mutual fund'],
    # Energy
    'solar':            ['solar', 'renewable energy', 'solar panel', 'electrolyser', 'fuel cell'],
    # Events
    'event management': ['event', 'wedding', 'party', 'catering', 'decoration', 'venue'],
    'photographer':     ['photographer', 'photography', 'photo', 'videographer', 'video'],
    # Healthcare
    'dentist':          ['dentist', 'dental', 'teeth', 'oral'],
    'physiotherapist':  ['physiotherapy', 'physio', 'rehabilitation'],
    'eye surgeon':      ['eye', 'surgeon', 'ophth', 'ophthalm', 'ophthalmologist', 'eye surgeon',
                         'eye doctor', 'eye clinic', 'vision', 'eyenation', 'optometrist', 'retina',
                         'cataract', 'glaucoma', 'lasik', 'spectacles', 'lens', 'eye care'],
    'doctor':           ['doctor', 'physician', 'medical', 'clinic', 'hospital', 'health', 'medicine',
                         'surgeon', 'specialist', 'consultant physician', 'mbbs', 'md', 'ms', 'dr'],
    'cardiologist':     ['cardiologist', 'cardiology', 'heart', 'cardiac'],
    'dermatologist':    ['dermatologist', 'dermatology', 'skin', 'skin care'],
    'orthopedic':       ['orthopedic', 'ortho', 'bone', 'joint', 'spine'],
    'neurologist':      ['neurologist', 'neurology', 'brain', 'nerve'],
    'pediatrician':     ['pediatrician', 'pediatrics', 'child', 'children'],
    'gynecologist':     ['gynecologist', 'gynecology', 'women', 'obstetrics'],
    # Other
    'security':         ['security', 'guard', 'cctv', 'surveillance'],
    'cleaning':         ['cleaning', 'housekeeping', 'pest control', 'sanitization'],
    'tutor':            ['tutor', 'coaching', 'classes', 'teaching'],
    'travel':           ['travel', 'tour', 'tourism', 'hotel', 'booking'],
    'printing':         ['printing', 'banner', 'flex', 'stationery'],
    'interior':         ['interior', 'interior design', 'decor', 'furnishing'],
    'gym':              ['gym', 'fitness', 'trainer', 'yoga', 'health club'],
    'restaurant':       ['restaurant', 'food', 'catering', 'hotel', 'chef'],
    'director':         ['director', 'managing director', 'executive director', 'ceo'],
    'manager':          ['manager', 'general manager', 'project manager', 'senior manager'],
}


def _expand_query(query: str) -> list:
    """Expand query with related keywords."""
    q = query.lower().strip()
    keywords = [q]
    for key, expansions in KEYWORD_MAP.items():
        if q in key or key in q or any(q in e or e in q for e in expansions):
            keywords.extend(expansions)
    return list(set(keywords))


def _score_contact(contact: dict, keywords: list, query: str) -> float:
    """
    Score a contact against the search query.
    Uses fuzzy/partial matching — even single word matches count.
    Returns 0.0 - 1.0
    """
    score = 0.0
    q = query.lower().strip()
    q_words = [w for w in q.split() if len(w) >= 2]

    # Short keywords that must match as whole words (not substrings)
    # e.g. "ms" should NOT match "ecosistems"
    WHOLE_WORD_ONLY = {'ms', 'md', 'dr', 'ca', 'hr', 'ac', 'it', 'ceo', 'cto', 'cfo'}

    def _kw_matches(kw: str, text: str) -> bool:
        """Check if keyword matches text, using word-boundary for short/ambiguous terms."""
        if kw in WHOLE_WORD_ONLY or len(kw) <= 2:
            # Must be a whole word — surrounded by non-alphanumeric chars
            return bool(re.search(r'(?<![a-z0-9])' + re.escape(kw) + r'(?![a-z0-9])', text))
        return kw in text

    # Fields to search in, with weights
    # designation and services are the most important — they describe what the person does
    fields = {
        'designation': 0.40,
        'services':    0.30,
        'company':     0.15,
        'name':        0.10,
        'address':     0.03,
        'email':       0.02,
    }

    for field, weight in fields.items():
        val = (contact.get(field) or '').lower()
        if not val:
            continue

        # Full query match (highest score)
        if q in val:
            score += weight * 1.0
            continue

        # Any single word from query matches (partial match)
        word_match = False
        for word in q_words:
            if _kw_matches(word, val):
                score += weight * 0.8
                word_match = True
                break

        if word_match:
            continue

        # Keyword expansion match
        for kw in keywords:
            if len(kw) >= 2 and _kw_matches(kw, val):
                score += weight * 0.6
                break

        # Partial word match (e.g. "elec" matches "electrician")
        for word in q_words:
            if len(word) >= 3:
                for val_word in val.split():
                    if word in val_word or val_word in word:
                        score += weight * 0.3
                        break

    # Bonus: has website (more established)
    if contact.get('website'):
        score += 0.03

    # Bonus: has email (contactable)
    if contact.get('email'):
        score += 0.02

    # Bonus: has phone (reachable)
    if contact.get('phone'):
        score += 0.02

    return round(min(score, 1.0), 3)


def recommend_best_contact(contacts: list, service_type: str) -> dict:
    """
    Find and rank contacts matching the service type.
    Returns top matches with scores.
    """
    if not contacts:
        return {
            "error": "No contacts in database",
            "suggestion": "Scan some visiting cards first",
            "results": [],
            "total_matches": 0,
        }

    keywords = _expand_query(service_type)
    scored = []

    for c in contacts:
        score = _score_contact(c, keywords, service_type)
        if score > 0:
            c_copy = dict(c)
            c_copy['match_score'] = score
            c_copy['calculated_score'] = score  # backward compat
            scored.append(c_copy)

    scored.sort(key=lambda x: x['match_score'], reverse=True)

    if not scored:
        return {
            "error": f"No contacts found for: {service_type}",
            "suggestion": "Try different keywords or scan more cards",
            "results": [],
            "total_matches": 0,
            "service_requested": service_type,
        }

    return {
        "service_requested": service_type,
        "recommended_contact": scored[0],
        "alternatives": scored[1:5],
        "results": scored[:10],
        "total_matches": len(scored),
    }
