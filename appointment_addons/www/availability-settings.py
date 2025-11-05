# Copyright (c) 2025, Ebkar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json

no_cache = 1


def get_context(context):
	# Check if user is logged in
	if frappe.session.user == "Guest":
		frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)
	
	context.no_cache = 1
	context.current_user = frappe.session.user
	
	# Get user's availability settings
	days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
	context.days_of_week = days_of_week
	
	# Get existing availability for the user
	context.availability = {}
	try:
		for day in days_of_week:
			availability_doc = frappe.db.exists("User Availability", {
				"user": frappe.session.user,
				"day_of_week": day
			})
			
			if availability_doc:
				doc = frappe.get_doc("User Availability", availability_doc)
				context.availability[day] = {
					"name": doc.name,
					"is_available": doc.is_available,
					"time_slots": doc.time_slots
				}
			else:
				context.availability[day] = {
					"name": None,
					"is_available": 0,
					"time_slots": []
				}
	except Exception:
		# If doctypes don't exist yet, initialize empty availability
		for day in days_of_week:
			context.availability[day] = {
				"name": None,
				"is_available": 0,
				"time_slots": []
			}
	
	# Get success message if any
	if frappe.form_dict.get("success"):
		context.success_message = _("Your availability settings have been saved successfully!")


@frappe.whitelist()
def save_availability(data):
	"""Save user's availability settings"""
	try:
		data = json.loads(data) if isinstance(data, str) else data
		
		user = frappe.session.user
		if user == "Guest":
			frappe.throw(_("You need to be logged in"))
		
		# Process each day's availability
		for day_data in data:
			day = day_data.get("day")
			is_available = day_data.get("is_available", 0)
			time_slots = day_data.get("time_slots", [])
			
			# Check if document exists
			existing = frappe.db.exists("User Availability", {
				"user": user,
				"day_of_week": day
			})
			
			if existing:
				# Update existing document
				doc = frappe.get_doc("User Availability", existing)
				doc.is_available = is_available
				doc.time_slots = []
				
				if is_available:
					for slot in time_slots:
						doc.append("time_slots", {
							"from_time": slot.get("from_time"),
							"to_time": slot.get("to_time")
						})
				
				doc.save(ignore_permissions=True)
			else:
				# Create new document
				doc = frappe.get_doc({
					"doctype": "User Availability",
					"user": user,
					"day_of_week": day,
					"is_available": is_available
				})
				
				if is_available:
					for slot in time_slots:
						doc.append("time_slots", {
							"from_time": slot.get("from_time"),
							"to_time": slot.get("to_time")
						})
				
				doc.insert(ignore_permissions=True)
		
		return {
			"success": True,
			"message": _("Availability settings saved successfully!")
		}
	
	except Exception as e:
		frappe.log_error(message=str(e), title="Availability Settings Error")
		return {
			"success": False,
			"message": str(e)
		}



