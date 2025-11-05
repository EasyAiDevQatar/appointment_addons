# Copyright (c) 2025, Ebkar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address, getdate
import json

no_cache = 1


@frappe.whitelist(allow_guest=True)
def get_services():
	"""Get all active services"""
	try:
		services = frappe.get_all(
			"Appointment Service",
			filters={"is_active": 1},
			fields=["name", "service_name", "description", "color", "duration"],
			order_by="service_name"
		)
		return services or []
	except Exception as e:
		frappe.log_error(message=str(e), title="Error fetching services")
		return []


@frappe.whitelist(allow_guest=True)
def get_company_location():
	"""Get company location from settings"""
	try:
		settings = frappe.get_single("Appointment Settings")
		return settings.company_location if settings and settings.company_location else ""
	except Exception as e:
		frappe.log_error(message=str(e), title="Error fetching company location")
		return ""


@frappe.whitelist(allow_guest=True)
def get_time_slots():
	"""Get available time slots for the next 30 days"""
	try:
		from datetime import timedelta
		
		slots = []
		today = getdate()
		
		# Generate slots for next 30 days
		for i in range(30):
			date = today + timedelta(days=i)
			day_name = date.strftime("%A")
			
			# Get available users for this day
			availabilities = frappe.get_all(
				"User Availability",
				filters={
					"day_of_week": day_name,
					"is_available": 1
				},
				fields=["name", "user"]
			)
			
			if availabilities:
				# Get time slots for the first available user (can be enhanced)
				availability = frappe.get_doc("User Availability", availabilities[0].name)
				
				if availability.time_slots:
					for slot in availability.time_slots:
						# Check if slot is not already booked
						existing_bookings = frappe.get_all(
							"Appointment Booking",
							filters={
								"booking_date": date,
								"booking_time": slot.from_time,
								"status": ["in", ["Pending", "Confirmed"]]
							}
						)
						
						if not existing_bookings:
							# Convert time to string format
							from_time_str = str(slot.from_time)
							to_time_str = str(slot.to_time)
							
							slots.append({
								"date": str(date),
								"date_display": date.strftime("%B %d, %Y"),
								"day": day_name,
								"from_time": from_time_str,
								"to_time": to_time_str,
								"time_display": f"{from_time_str} - {to_time_str}"
							})
		
		return slots
	except Exception as e:
		frappe.log_error(message=str(e), title="Error fetching time slots")
		return []


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=100, seconds=60 * 60)
def create_appointment(data):
	"""Create a new appointment booking"""
	try:
		data = json.loads(data) if isinstance(data, str) else data
		
		# Validate required fields
		if not data.get("customer_name"):
			frappe.throw(_("Customer Name is required"))
		
		if not data.get("phone_number"):
			frappe.throw(_("Phone Number is required"))
		
		if not data.get("email"):
			frappe.throw(_("Email is required"))
		
		# Validate email
		validate_email_address(data.get("email"), throw=True)
		
		if not data.get("selected_services"):
			frappe.throw(_("Please select at least one service"))
		
		if not data.get("meeting_location"):
			frappe.throw(_("Meeting Location is required"))
		
		if not data.get("booking_date"):
			frappe.throw(_("Booking Date is required"))
		
		if not data.get("booking_time"):
			frappe.throw(_("Booking Time is required"))
		
		# Create appointment booking
		doc = frappe.get_doc({
			"doctype": "Appointment Booking",
			"customer_name": data.get("customer_name"),
			"phone_number": data.get("phone_number"),
			"email": data.get("email"),
			"meeting_location": data.get("meeting_location"),
			"booking_date": data.get("booking_date"),
			"booking_time": data.get("booking_time"),
			"status": "Pending"
		})
		
		# Add services
		services = json.loads(data.get("selected_services")) if isinstance(data.get("selected_services"), str) else data.get("selected_services")
		for service_name in services:
			doc.append("services", {
				"service": service_name
			})
		
		# Add customer location if applicable
		if data.get("meeting_location") == "Customer Location":
			doc.location = data.get("location", "")
			doc.street_name = data.get("street_name", "")
			doc.building_name = data.get("building_name", "")
			doc.apartment_number = data.get("apartment_number", "")
		else:
			# Set company location
			settings = frappe.get_single("Appointment Settings")
			if settings:
				doc.company_location = settings.company_location
		
		doc.insert(ignore_permissions=True)
		
		# Send confirmation email (optional)
		try:
			send_confirmation_email(doc)
		except:
			pass
		
		return {
			"success": True,
			"message": _("Your appointment has been booked successfully!"),
			"appointment_id": doc.name
		}
	
	except Exception as e:
		frappe.log_error(message=str(e), title="Appointment Booking Error")
		return {
			"success": False,
			"message": str(e)
		}


def send_confirmation_email(doc):
	"""Send confirmation email to customer"""
	frappe.sendmail(
		recipients=doc.email,
		subject=_("Appointment Confirmation - {0}").format(doc.name),
		message=_("""
		<p>Dear {0},</p>
		
		<p>Your appointment has been booked successfully!</p>
		
		<p><strong>Appointment Details:</strong></p>
		<ul>
			<li>Appointment ID: {1}</li>
			<li>Date: {2}</li>
			<li>Time: {3}</li>
			<li>Location: {4}</li>
		</ul>
		
		<p>We will contact you shortly to confirm your appointment.</p>
		
		<p>Thank you!</p>
		""").format(
			doc.customer_name,
			doc.name,
			doc.booking_date,
			doc.booking_time,
			doc.meeting_location
		)
	)

