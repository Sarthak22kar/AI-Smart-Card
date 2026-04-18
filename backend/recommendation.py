def calculate_contact_score(contact):
    """
    Calculate final score based on the algorithm from project guide:
    Final Score = (Review Score * 0.30) + (Response Rate * 0.20) + 
                  (Website Presence * 0.15) + (Customer Interaction * 0.15) + 
                  (Location Suitability * 0.10) + (Service Completion * 0.10)
    """
    # Normalize distance to location suitability (closer = better)
    # Assuming max practical distance is 50km
    location_suitability = max(0, (50 - contact.get('distance', 50)) / 50)
    
    score = (
        contact.get('review_score', 0) / 5 * 0.30 +  # Normalize to 0-1
        contact.get('response_rate', 0) * 0.20 +
        contact.get('website_presence', 0) * 0.15 +
        contact.get('customer_interaction', 0) * 0.15 +
        location_suitability * 0.10 +
        contact.get('service_completion', 0) * 0.10
    )
    
    return round(score, 3)


def recommend_best_contact(contacts, service_type):
    """
    Recommend the best contact for a given service type
    """
    if not contacts:
        return {"error": "No contacts found", "recommended_contact": None}
    
    # Filter contacts by profession/service type
    relevant_contacts = [
        contact for contact in contacts 
        if service_type.lower() in contact.get('profession', '').lower()
    ]
    
    if not relevant_contacts:
        return {
            "error": f"No contacts found for service: {service_type}",
            "recommended_contact": None,
            "suggestion": "Try scanning more visiting cards or search for a different service"
        }
    
    # Calculate scores for all relevant contacts
    scored_contacts = []
    for contact in relevant_contacts:
        score = calculate_contact_score(contact)
        contact_with_score = contact.copy()
        contact_with_score['calculated_score'] = score
        scored_contacts.append(contact_with_score)
    
    # Sort by score (highest first)
    scored_contacts.sort(key=lambda x: x['calculated_score'], reverse=True)
    
    best_contact = scored_contacts[0]
    
    return {
        "service_requested": service_type,
        "recommended_contact": best_contact,
        "alternatives": scored_contacts[1:3] if len(scored_contacts) > 1 else [],
        "total_matches": len(scored_contacts)
    }


# Test the recommendation system
if __name__ == "__main__":
    test_contacts = [
        {
            "name": "Ravi Plumber",
            "profession": "plumber",
            "review_score": 4.5,
            "response_rate": 0.9,
            "website_presence": 1,
            "customer_interaction": 0.8,
            "distance": 5,
            "service_completion": 0.85
        },
        {
            "name": "Amit Plumber",
            "profession": "plumber",
            "review_score": 4.0,
            "response_rate": 0.7,
            "website_presence": 0,
            "customer_interaction": 0.6,
            "distance": 2,
            "service_completion": 0.75
        }
    ]

    result = recommend_best_contact(test_contacts, "plumber")
    print("Recommended Contact:")
    print(result)