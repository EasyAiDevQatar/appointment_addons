
import frappe

def test_guest_access():
    frappe.set_user("Guest")
    print(f"Current user: {frappe.session.user}")
    
    try:
        # Try finding the doc with parenttype (as in book_appointment.py)
        slots = frappe.get_all(
            "Appointment Booking Slots",
            filters={"parent": "Appointment Booking Settings", "parenttype": "Appointment Booking Settings"},
            fields=["day_of_week", "from_time", "to_time"]
        )
        print(f"Fetched {len(slots)} slots with parenttype filter")
        
        # compare without parenttype
        slots2 = frappe.get_all(
            "Appointment Booking Slots",
            filters={"parent": "Appointment Booking Settings"},
            fields=["day_of_week", "from_time", "to_time"]
        )
        print(f"Fetched {len(slots2)} slots without parenttype filter")
        
    except Exception as e:
        print(f"Error: {e}")

test_guest_access()
