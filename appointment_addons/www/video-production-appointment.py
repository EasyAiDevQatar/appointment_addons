# Copyright (c) 2025, Ebkar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address, get_datetime, now_datetime

no_cache = 1


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=100, seconds=60 * 60)
def create_appointment(data):
	"""Create a new video production appointment"""
	try:
		if isinstance(data, str):
			import json
			data = json.loads(data)
		
		# Validate required fields
		if not data.get("customer_name"):
			frappe.throw(_("Customer Name is required"))
		
		if not data.get("phone_number"):
			frappe.throw(_("Phone Number is required"))
		
		if not data.get("email"):
			frappe.throw(_("Email is required"))
		
		# Validate email
		validate_email_address(data.get("email"), throw=True)
		
		if not data.get("appointment_type"):
			frappe.throw(_("Appointment Type is required"))
		
		if not data.get("meeting_location"):
			frappe.throw(_("Meeting Location is required"))
		
		if not data.get("booking_date"):
			frappe.throw(_("Booking Date is required"))
		
		if not data.get("booking_time"):
			frappe.throw(_("Booking Time is required"))
		
		# Validate company
		company = data.get("company", "Directlines")
		if company in ["Direct Line", "Directlines"]:
			company = "Directlines"  # Normalize to "Directlines"
		if company not in ["Easy AI", "Directlines"]:
			frappe.throw(_("Invalid company selected"))
		
		# Create appointment document
		doc = frappe.get_doc({
			"doctype": "Video Production Appointment",
			"naming_series": "VPA-.YYYY.-",
			"company": company,
			"customer_name": data.get("customer_name"),
			"phone_number": data.get("phone_number"),
			"email": data.get("email"),
			"appointment_type": data.get("appointment_type"),
			"meeting_location": data.get("meeting_location"),
			"booking_date": data.get("booking_date"),
			"booking_time": data.get("booking_time"),
			"status": "Pending"
		})
		
		# Add fields based on appointment type
		if data.get("appointment_type") == "New Customer":
			doc.industry = data.get("industry", "")
			doc.service = data.get("service", "")
			doc.requirements = data.get("requirements", "")
			doc.budget = data.get("budget", "")
			doc.notes = data.get("notes", "")
			doc.references = data.get("references", "")
		else:  # Current Active Client
			doc.brand_name = data.get("brand_name", "")
			doc.acknowledgment_checkbox = data.get("acknowledgment_checkbox", 0)
			doc.current_client_references = data.get("current_client_references", "")
		
		# Add location details (always Customer Location for Direct Line)
		doc.meeting_location = data.get("meeting_location", "Customer Location")
		doc.google_location = data.get("google_location", "")
		doc.city = data.get("city", "")
		doc.zone_number = data.get("zone_number", "")
		doc.street_number = data.get("street_number", "")
		doc.building_number = data.get("building_number", "")
		
		# Keep old fields for backward compatibility if they exist
		if data.get("location"):
			doc.location = data.get("location", "")
		if data.get("street_name"):
			doc.street_name = data.get("street_name", "")
		if data.get("building_name"):
			doc.building_name = data.get("building_name", "")
		if data.get("apartment_number"):
			doc.apartment_number = data.get("apartment_number", "")
		
		# Insert document (this will trigger after_insert and send email)
		doc.insert(ignore_permissions=True)
		
		return {
			"success": True,
			"message": _("Your appointment request has been submitted successfully! We will contact you soon."),
			"appointment_id": doc.name
		}
	
	except Exception as e:
		frappe.log_error(message=str(e), title="Video Production Appointment Booking Error")
		return {
			"success": False,
			"message": str(e)
		}

