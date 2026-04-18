#!/usr/bin/env python3

import database
import json
from datetime import datetime

def display_contacts():
    """Display all contacts in a readable format"""
    print("📇 AI Smart Visiting Card - Contact Database\n")
    print("=" * 80)
    
    contacts = database.get_all_contacts()
    
    if not contacts:
        print("No contacts found. Scan some visiting cards first!")
        return
    
    print(f"Total Contacts: {len(contacts)}\n")
    
    for i, contact in enumerate(contacts, 1):
        # contact format: id, name, phone, email, profession, company, location, confidence, created_at, updated_at
        contact_id = contact[0]
        name = contact[1] or "Unknown Name"
        phone = contact[2] or "Not provided"
        email = contact[3] or "Not provided"
        profession = contact[4] or "Not specified"
        company = contact[5] or "Not provided"
        location = contact[6] or "Not provided"
        confidence = contact[7] if len(contact) > 7 else 0.0
        created_at = contact[8] if len(contact) > 8 else "Unknown"
        
        print(f"📋 Contact #{i} (ID: {contact_id})")
        print(f"👤 Name: {name}")
        print(f"📞 Phone: {phone}")
        print(f"📧 Email: {email}")
        print(f"💼 Profession: {profession}")
        print(f"🏢 Company: {company}")
        print(f"📍 Location: {location}")
        print(f"📊 Confidence: {confidence:.1%}")
        print(f"📅 Added: {created_at}")
        print("-" * 80)

def display_statistics():
    """Display database statistics"""
    print("\n📊 Database Statistics")
    print("=" * 50)
    
    stats = database.get_contact_stats()
    
    print(f"Total Contacts: {stats['total_contacts']}")
    print(f"Average Confidence: {stats['average_confidence']:.1%}")
    
    print(f"\n📋 Field Completion:")
    for field, count in stats['field_completion'].items():
        percentage = (count / stats['total_contacts'] * 100) if stats['total_contacts'] > 0 else 0
        print(f"  {field.title()}: {count}/{stats['total_contacts']} ({percentage:.1f}%)")
    
    if stats['by_profession']:
        print(f"\n💼 By Profession:")
        for profession, count in stats['by_profession'].items():
            print(f"  {profession}: {count}")

def export_to_json():
    """Export contacts to JSON file"""
    try:
        count = database.backup_contacts_to_json("contacts_export.json")
        print(f"\n💾 Exported {count} contacts to 'contacts_export.json'")
    except Exception as e:
        print(f"❌ Export failed: {e}")

def main():
    """Main function"""
    print("🚀 Contact Database Viewer\n")
    
    while True:
        print("\nChoose an option:")
        print("1. 📇 View all contacts")
        print("2. 📊 View statistics")
        print("3. 💾 Export to JSON")
        print("4. 🚪 Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            display_contacts()
        elif choice == "2":
            display_statistics()
        elif choice == "3":
            export_to_json()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")

if __name__ == "__main__":
    main()