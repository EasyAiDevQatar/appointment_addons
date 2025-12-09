
import frappe
import json

def test_video_appointment():
    frappe.set_user("Guest")
    
    data = {
        "company": "Directlines",
        "customer_name": "Test User",
        "phone_number": "12345678",
        "email": "test@example.com",
        "appointment_type": "New Customer",
        "industry": "Others",
        "service": "Test Service",
        "requirements": "Both",
        "budget": "Open",
        "meeting_location": "Customer Location",
        "booking_date": "2025-12-12",
        "booking_time": "10:00:00",
        "notes": "Test note",
        "references": "Test ref",
        "location": "Doha",
        "street_number": "1",
        "building_number": "1",
        "zone_number": "1"
    }
    
    try:
        # Import the method directly to test the changes
        from appointment_addons.www.video_production_appointment import create_appointment
        
        result = create_appointment(data)
        print("Success:", result)
        
        # Verify document created
        if result.get("success"):
            name = result.get("appointment_id")
            doc = frappe.get_doc("Video Production Appointment", name)
            print(f"Created doc: {doc.name}, Company: {doc.company}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

test_video_appointment()
