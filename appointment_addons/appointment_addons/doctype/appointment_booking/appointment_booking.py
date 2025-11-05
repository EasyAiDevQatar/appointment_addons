# Copyright (c) 2025, Ebkar and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AppointmentBooking(Document):
	def before_insert(self):
		if self.meeting_location == "Our Location":
			# Get company location from settings
			company_settings = frappe.get_single("Appointment Settings")
			if company_settings:
				self.company_location = company_settings.company_location

