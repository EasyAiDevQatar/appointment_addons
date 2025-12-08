# Copyright (c) 2025, Ebkar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address, getdate
import json

no_cache = 1


@frappe.whitelist(allow_guest=True)
def debug_appointment_settings():
	"""Debug function to check Appointment Booking Settings"""
	try:
		settings_doc = frappe.get_single("Appointment Booking Settings")
		
		debug_info = {
			"settings_exists": bool(settings_doc),
			"enable_scheduling": getattr(settings_doc, 'enable_scheduling', None),
			"appointment_duration": getattr(settings_doc, 'appointment_duration', None),
			"advance_booking_days": getattr(settings_doc, 'advance_booking_days', None),
			"has_availability_of_slots": hasattr(settings_doc, 'availability_of_slots'),
			"availability_slots_count": len(settings_doc.availability_of_slots) if hasattr(settings_doc, 'availability_of_slots') else 0,
			"availability_slots": []
		}
		
		if hasattr(settings_doc, 'availability_of_slots') and settings_doc.availability_of_slots:
			for idx, slot in enumerate(settings_doc.availability_of_slots):
				debug_info["availability_slots"].append({
					"index": idx,
					"day_of_week": getattr(slot, 'day_of_week', None),
					"from_time": str(getattr(slot, 'from_time', None)),
					"to_time": str(getattr(slot, 'to_time', None)),
					"from_time_type": type(getattr(slot, 'from_time', None)).__name__,
					"to_time_type": type(getattr(slot, 'to_time', None)).__name__
				})
		
		return debug_info
	except Exception as e:
		import traceback
		return {
			"error": str(e),
			"traceback": traceback.format_exc()
		}


@frappe.whitelist(allow_guest=True)
def test_settings():
	"""Test function to verify settings are accessible"""
	try:
		settings_doc = frappe.get_doc("Appointment Booking Settings", "Appointment Booking Settings")
		
		slots = frappe.get_all(
			"Appointment Booking Slots",
			filters={"parent": "Appointment Booking Settings"},
			fields=["day_of_week", "from_time", "to_time"]
		)
		
		return {
			"success": True,
			"enable_scheduling": settings_doc.enable_scheduling,
			"appointment_duration": settings_doc.appointment_duration,
			"advance_booking_days": settings_doc.advance_booking_days,
			"slots_count": len(slots),
			"slots": slots
		}
	except Exception as e:
		return {
			"success": False,
			"error": str(e)
		}


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
	"""Get available time slots from Appointment Booking Settings"""
	try:
		from datetime import timedelta, datetime, time as time_module
		
		print("=== get_time_slots called ===")
		
		# Get Appointment Booking Settings - use get_doc for better child table access
		try:
			settings_doc = frappe.get_doc("Appointment Booking Settings", "Appointment Booking Settings")
			print(f"Settings doc loaded: {settings_doc.name}")
		except:
			try:
				settings_doc = frappe.get_single("Appointment Booking Settings")
				print(f"Settings doc loaded via get_single: {settings_doc.name}")
			except Exception as e:
				error_msg = f"Error getting Appointment Booking Settings: {str(e)}"
				print(error_msg)
				frappe.log_error(message=error_msg, title="Time Slots Error")
				return []
		
		if not settings_doc:
			frappe.log_error(message="Appointment Booking Settings not found", title="Time Slots Error")
			return []
		
		# Check if scheduling is enabled
		enable_scheduling = int(getattr(settings_doc, 'enable_scheduling', 0))
		print(f"Enable scheduling: {enable_scheduling}")
		if not enable_scheduling:
			error_msg = "Scheduling is not enabled in Appointment Booking Settings"
			print(error_msg)
			frappe.log_error(message=error_msg, title="Time Slots Error")
			return []
		
		# Get settings values
		appointment_duration = int(getattr(settings_doc, 'appointment_duration', 60) or 60)
		advance_booking_days = int(getattr(settings_doc, 'advance_booking_days', 7) or 7)
		print(f"Duration: {appointment_duration}, Advance days: {advance_booking_days}")
		
		# Get availability slots - fetch directly from database for reliability
		availability_slots = frappe.get_all(
			"Appointment Booking Slots",
			filters={"parent": "Appointment Booking Settings", "parenttype": "Appointment Booking Settings"},
			fields=["day_of_week", "from_time", "to_time"],
			order_by="idx"
		)
		print(f"Found {len(availability_slots)} availability slots: {availability_slots}")
		
		if not availability_slots:
			frappe.log_error(message="No availability slots found in Appointment Booking Settings", title="Time Slots Error")
			return []
		
		# Group availability by day
		availability_by_day = {}
		for slot in availability_slots:
			day = slot.get('day_of_week', '').strip()
			if not day:
				continue
			
			# Normalize day name (capitalize first letter only)
			day_normalized = day[0].upper() + day[1:].lower() if len(day) > 0 else ""
			
			if day_normalized not in availability_by_day:
				availability_by_day[day_normalized] = []
			
			availability_by_day[day_normalized].append({
				"from_time": slot.get('from_time'),
				"to_time": slot.get('to_time')
			})
		
		if not availability_by_day:
			error_msg = "No valid availability slots configured"
			print(error_msg)
			frappe.log_error(message=error_msg, title="Time Slots Error")
			return []
		
		print(f"Availability by day: {availability_by_day}")
		
		# Generate time slots
		slots = []
		today = getdate()
		now = datetime.now()
		print(f"Generating slots from {today} for {advance_booking_days} days")
		print(f"Current datetime: {now}")
		
		for i in range(advance_booking_days):
			date = today + timedelta(days=i)
			day_name = date.strftime("%A")  # e.g., "Sunday", "Monday"
			
			print(f"Checking date {date} ({day_name})")
			
			# Check if we have availability for this day
			if day_name not in availability_by_day:
				print(f"  No availability configured for {day_name}")
				continue
			
			print(f"  Found availability for {day_name}: {availability_by_day[day_name]}")
			
			# Process each time range for this day
			for time_range in availability_by_day[day_name]:
				from_time_val = time_range.get("from_time")
				to_time_val = time_range.get("to_time")
				
				if not from_time_val or not to_time_val:
					continue
				
				# Parse time values
				def parse_time(time_val):
					if isinstance(time_val, time_module):
						return time_val
					elif isinstance(time_val, str):
						parts = time_val.split(':')
						if len(parts) >= 2:
							hour = int(parts[0])
							minute = int(parts[1])
							second = int(parts[2]) if len(parts) > 2 else 0
							return time_module(hour, minute, second)
					elif isinstance(time_val, timedelta):
						# Convert timedelta to time
						total_seconds = int(time_val.total_seconds())
						hours = total_seconds // 3600
						minutes = (total_seconds % 3600) // 60
						seconds = total_seconds % 60
						return time_module(hours, minutes, seconds)
					elif hasattr(time_val, 'hour'):
						return time_module(time_val.hour, time_val.minute, getattr(time_val, 'second', 0))
					return None
				
				from_time = parse_time(from_time_val)
				to_time = parse_time(to_time_val)
				
				if not from_time or not to_time:
					print(f"  Failed to parse times: {from_time_val} -> {from_time}, {to_time_val} -> {to_time}")
					continue
				
				print(f"  Generating slots from {from_time} to {to_time}")
				
				# Generate slots for this time range
				current_time = datetime.combine(date, from_time)
				end_datetime = datetime.combine(date, to_time)
				
				# Initialize slot counter for this time range
				slot_count = 0
				print(f"  Initialized slot_count, starting loop from {current_time} to {end_datetime}")
				
				while current_time + timedelta(minutes=appointment_duration) <= end_datetime:
					slot_datetime = current_time
					
					# Skip past times (allow 5 minute buffer)
					if slot_datetime < (now - timedelta(minutes=5)):
						if slot_count == 0:  # Only log first skip
							print(f"    Skipping past times (first skip: {slot_datetime} < {now})")
						current_time += timedelta(minutes=appointment_duration)
						continue
					
					slot_from_time = current_time.time()
					slot_to_time = (current_time + timedelta(minutes=appointment_duration)).time()
					
					# Format for display and storage
					from_time_str = slot_from_time.strftime("%H:%M")
					to_time_str = slot_to_time.strftime("%H:%M")
					from_time_full = slot_from_time.strftime("%H:%M:%S")
					
					# Check if slot is already booked
					booked = False
					
					# Check Appointment Booking
					existing = frappe.db.count("Appointment Booking", {
						"booking_date": date,
						"booking_time": from_time_full,
						"status": ["in", ["Pending", "Confirmed"]]
					})
					if existing > 0:
						print(f"    Slot {from_time_str} already booked in Appointment Booking")
						booked = True
					
					# Check Video Production Appointment
					if not booked:
						existing_video = frappe.db.count("Video Production Appointment", {
							"booking_date": date,
							"booking_time": from_time_full,
							"status": ["in", ["Pending", "Confirmed"]]
						})
						if existing_video > 0:
							print(f"    Slot {from_time_str} already booked in Video Production")
							booked = True
					
					# Add slot if not booked
					if not booked:
						slots.append({
							"date": str(date),
							"date_display": date.strftime("%B %d, %Y"),
							"day": day_name,
							"from_time": from_time_str,
							"to_time": to_time_str,
							"time_display": f"{from_time_str} - {to_time_str}"
						})
						slot_count += 1
						if slot_count <= 3:  # Only log first 3
							print(f"    Added slot: {from_time_str} - {to_time_str}")
					
					current_time += timedelta(minutes=appointment_duration)
				
				print(f"  Generated {slot_count} slots for this time range")
		
		print(f"Total slots generated: {len(slots)}")
		print(f"Sample slots: {slots[:3] if len(slots) > 0 else 'None'}")
		
		if len(slots) == 0:
			print("WARNING: Returning empty slots list!")
			print(f"  Today: {today}, Now: {now}")
			print(f"  Availability days configured: {list(availability_by_day.keys())}")
		
		return slots
		
	except Exception as e:
		import traceback
		error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
		frappe.log_error(message=error_msg, title="Error fetching time slots")
		print(f"ERROR in get_time_slots: {error_msg}")
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













