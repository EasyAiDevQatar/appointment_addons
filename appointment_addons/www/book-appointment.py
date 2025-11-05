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
def get_settings_info():
	"""Debug function to check settings configuration"""
	try:
		settings = frappe.get_single("Appointment Settings")
		
		if not settings:
			return {
				"error": "Appointment Settings not found",
				"message": "Please create Appointment Settings from Setup menu"
			}
		
		# Get working days
		working_days = []
		day_mapping = {
			'monday': 'Monday',
			'tuesday': 'Tuesday',
			'wednesday': 'Wednesday',
			'thursday': 'Thursday',
			'friday': 'Friday',
			'saturday': 'Saturday',
			'sunday': 'Sunday'
		}
		
		for field_name, day_name in day_mapping.items():
			if getattr(settings, field_name, 0):
				working_days.append(day_name)
		
		return {
			"working_start_time": str(settings.working_start_time) if settings.working_start_time else "Not set",
			"working_end_time": str(settings.working_end_time) if settings.working_end_time else "Not set",
			"default_slot_duration": settings.default_slot_duration or "Not set",
			"working_days": working_days or "None selected",
			"company_location": settings.company_location or "Not set"
		}
	except Exception as e:
		import traceback
		return {
			"error": str(e),
			"traceback": traceback.format_exc()
		}


@frappe.whitelist(allow_guest=True)
def get_time_slots():
	"""Get available time slots for the next 30 days based on business hours and service duration"""
	try:
		from datetime import timedelta, datetime, time as time_module
		
		# Get appointment settings
		settings = frappe.get_single("Appointment Settings")
		if not settings:
			frappe.log_error("Appointment Settings not found", "Time Slots Error")
			return []
		
		# Get working hours - ensure they are time objects
		start_time = settings.working_start_time
		end_time = settings.working_end_time
		
		# Handle if start_time/end_time are strings or None
		if not start_time:
			start_time = time_module(9, 0)
		elif isinstance(start_time, str):
			# Parse time string like "09:00:00"
			parts = start_time.split(':')
			start_time = time_module(int(parts[0]), int(parts[1]))
		
		if not end_time:
			end_time = time_module(18, 0)
		elif isinstance(end_time, str):
			parts = end_time.split(':')
			end_time = time_module(int(parts[0]), int(parts[1]))
		
		# Get slot duration - use the smallest service duration or default
		services = frappe.get_all(
			"Appointment Service",
			filters={"is_active": 1},
			fields=["duration"]
		)
		
		if services:
			# Use the smallest service duration as slot interval
			slot_duration = min([s.duration for s in services])
		else:
			# Fall back to default
			slot_duration = settings.default_slot_duration or 60
		
		# Get working days from checkboxes
		working_days = []
		day_mapping = {
			'monday': 'Monday',
			'tuesday': 'Tuesday',
			'wednesday': 'Wednesday',
			'thursday': 'Thursday',
			'friday': 'Friday',
			'saturday': 'Saturday',
			'sunday': 'Sunday'
		}
		
		for field_name, day_name in day_mapping.items():
			if getattr(settings, field_name, 0):
				working_days.append(day_name)
		
		# Default to weekdays if no days selected
		if not working_days:
			working_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
		
		slots = []
		today = getdate()
		now = datetime.now()
		
		# Generate slots for next 30 days
		for i in range(30):
			date = today + timedelta(days=i)
			day_name = date.strftime("%A")
			
			# Skip if not a working day
			if day_name not in working_days:
				continue
			
			# Generate time slots for this day
			current_time = datetime.combine(date, start_time)
			end_datetime = datetime.combine(date, end_time)
			
			while current_time + timedelta(minutes=slot_duration) <= end_datetime:
				slot_time = current_time.time()
				slot_time_str = slot_time.strftime("%H:%M:%S")
				
				# Only add if time hasn't passed (for today)
				slot_datetime = datetime.combine(date, slot_time)
				if slot_datetime <= now:
					current_time += timedelta(minutes=slot_duration)
					continue
				
				# Check if slot is not already booked
				existing_bookings = frappe.get_all(
					"Appointment Booking",
					filters={
						"booking_date": date,
						"booking_time": slot_time_str,
						"status": ["in", ["Pending", "Confirmed"]]
					}
				)
				
				if not existing_bookings:
					slots.append({
						"date": str(date),
						"date_display": date.strftime("%B %d, %Y"),
						"day": day_name,
						"from_time": slot_time.strftime("%H:%M"),
						"to_time": (slot_datetime + timedelta(minutes=slot_duration)).strftime("%H:%M"),
						"time_display": slot_time.strftime("%H:%M")
					})
				
				current_time += timedelta(minutes=slot_duration)
		
		return slots
	except Exception as e:
		import traceback
		frappe.log_error(
			message=f"{str(e)}\n\n{traceback.format_exc()}", 
			title="Error fetching time slots"
		)
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
			"naming_series": "APT-.YYYY.-",
			"customer_name": data.get("customer_name"),
			"phone_number": data.get("phone_number"),
			"email": data.get("email"),
			"meeting_location": data.get("meeting_location"),
			"booking_date": data.get("booking_date"),
			"booking_time": data.get("booking_time")
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

