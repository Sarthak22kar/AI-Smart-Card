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
# Maps common search terms to related keywords
KEYWORD_MAP = {
    # Trades
    'plumber':      ['plumber', 'plumbing', 'pipe', 'water'],
    'electrician':  ['electrician', 'electrical', 'wiring', 'electric'],
    'carpenter':    ['carpenter', 'carpentry', 'furniture', 'wood'],
    'painter':      ['painter', 'painting', 'interior'],
    'mechanic':     ['mechanic', 'automobile', 'car', 'vehicle', 'auto'],
    'ac':           ['ac', 'air condition', 'hvac', 'cooling', 'refrigeration'],
    # Professional
    'doctor':       ['doctor', 'physician', 'medical', 'clinic', 'hospital', 'health'],
    'lawyer':       ['lawyer', 'advocate', 'legal', 'attorney', 'law'],
    'ca':           ['ca', 'chartered accountant', 'accountant', 'audit', 'tax', 'finance'],
    'architect':    ['architect', 'architecture', 'design', 'construction'],
    'engineer':     ['engineer', 'engineering', 'technical'],
    'consultant':   ['consultant', 'consulting', 'advisory', 'advisor'],
    # Business
    'marketing':    ['marketing', 'digital marketing', 'seo', 'advertising', 'brand'],
    'it':           ['it', 'software', 'developer', 'technology', 'tech', 'computer'],
    'sales':        ['sales', 'business development', 'bd', 'representative'],
    'hr':           ['hr', 'human resource', 'recruitment', 'hiring'],
    'logistics':    ['logistics', 'transport', 'delivery', 'supply chain', 'courier'],
    'real estate':  ['real estate', 'property', 'builder', 'developer', 'construction'],
    'insurance':    ['insurance', 'policy', 'claim', 'coverage'],
    'banking':      ['banking', 'bank', 'finance', 'loan', 'investment'],
    # Energy
    'solar':        ['solar', 'renewable', 'energy', 'power', 'electrolyser'],
    'electrical':   ['electrical', 'power', 'energy', 'systems'],
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
    q_words = q.split()  # individual words from query

    # Fields to search in, with weights
    fields = {
        'designation': 0.35,
        'services':    0.30,
        'company':     0.15,
        'name':        0.10,
        'address':     0.05,
        'email':       0.05,
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
            if len(word) >= 2 and word in val:
                score += weight * 0.7
                word_match = True
                break

        if word_match:
            continue

        # Keyword expansion match
        for kw in keywords:
            if len(kw) >= 2 and kw in val:
                score += weight * 0.5
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
