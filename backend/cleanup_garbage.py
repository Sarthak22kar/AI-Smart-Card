#!/usr/bin/env python3
"""
Clean up garbage contacts from the database
"""
import database

database.init_database()

# Get low confidence contacts
low_conf = database.get_low_confidence_contacts(threshold=0.5)

if not low_conf:
    print("✅ No garbage contacts found!")
else:
    print(f"Found {len(low_conf)} low-confidence contacts:\n")
    
    for contact in low_conf:
        contact_id = contact[0]
        name = contact[1]
        confidence = float(contact[8]) if contact[8] else 0.0
        
        print(f"ID {contact_id}: {name} (confidence: {confidence:.2f})")
        
        # Auto-delete if confidence < 0.4 (likely garbage)
        if confidence < 0.4:
            database.delete_contact(contact_id)
            print(f"  ❌ DELETED (too low confidence)")
        else:
            print(f"  ⚠️  KEPT (borderline)")
    
    print(f"\n✅ Cleanup complete!")

# Show final stats
stats = database.get_contact_stats()
print(f"\nFinal database stats:")
print(f"  Total contacts: {stats['total_contacts']}")
print(f"  Average confidence: {stats['average_confidence']:.2%}")
