# Copyright (c) 2025, Ebkar and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime
from datetime import timedelta


class VideoProductionAppointment(Document):
	def validate(self):
		"""Validate required fields based on appointment type"""
		if self.appointment_type == "New Customer":
			if not self.industry:
				frappe.throw("Industry is required for New Customer appointments")
			if not self.requirements:
				frappe.throw("Requirements is required for New Customer appointments")
			if not self.budget:
				frappe.throw("Budget is required for New Customer appointments")
		elif self.appointment_type == "Current Active Client":
			if not self.brand_name:
				frappe.throw("Name of Your Brand is required for Current Active Client appointments")
			if not self.booking_date:
				frappe.throw("Schedule is required for Current Active Client appointments")
			if not self.acknowledgment_checkbox:
				frappe.throw("Please acknowledge the cancellation policy")
	
	def before_insert(self):
		# Validate if current active client exists
		if self.appointment_type == "Current Active Client":
			self.validate_active_client()
	
	def validate_active_client(self):
		"""Validate that the client exists and is active"""
		# Check if customer exists - try multiple email fields
		customer_exists = False
		
		# Try to find customer by email in various fields
		if frappe.db.exists("Customer", {"email_id": self.email}):
			customer_exists = True
		elif frappe.db.exists("Customer", {"customer_email": self.email}):
			customer_exists = True
		elif frappe.db.exists("Customer", {"email": self.email}):
			customer_exists = True
		
		# Also check Contact linked to Customer
		if not customer_exists:
			contact = frappe.db.get_value("Contact", {"email_id": self.email}, "name")
			if contact:
				# Check if contact is linked to a customer
				links = frappe.get_all("Dynamic Link", 
					filters={"link_doctype": "Customer", "parent": contact},
					fields=["link_name"])
				if links:
					customer_exists = True
		
		if not customer_exists:
			# Note: We'll allow the appointment to be created but log a warning
			# The admin can verify and cancel if needed via the email notification
			# We'll log this after insert when we have the name
			self.flags.customer_verification_needed = True
	
	def after_insert(self):
		"""Send email notification after appointment is created"""
		# Log customer verification warning if needed
		if getattr(self.flags, 'customer_verification_needed', False):
			frappe.log_error(
				message=f"Video Production Appointment {self.name} created for email {self.email} but customer not found in system. Please verify if this is an active client.",
				title="Customer Verification Needed"
			)
		
		self.send_email_notification()
	
	def send_email_notification(self):
		"""Send email to khloud@directlinez.com"""
		recipients = ["khloud@directlinez.com"]
		
		# Build email subject
		subject = f"New Video Production Appointment - {self.name}"
		
		# Build email message
		message = self.build_email_message()
		
		try:
			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=message,
				reference_doctype=self.doctype,
				reference_name=self.name
			)
		except Exception as e:
			frappe.log_error(
				message=f"Failed to send email notification for appointment {self.name}: {str(e)}",
				title="Email Notification Error"
			)
	
	def build_email_message(self):
		"""Build HTML email message"""
		import html
		
		def safe_html(text):
			"""Safely convert text to HTML, preserving line breaks"""
			if not text:
				return ""
			# Escape HTML and convert newlines to <br>
			escaped = html.escape(str(text))
			return escaped.replace('\n', '<br>')
		
		html_content = f"""
		<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
			<h2 style="color: #333;">New Video Production Appointment</h2>
			
			<div style="background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
				<h3 style="margin-top: 0;">Appointment Information</h3>
				<p><strong>Appointment ID:</strong> {html.escape(str(self.name))}</p>
				<p><strong>Customer Name:</strong> {html.escape(str(self.customer_name))}</p>
				<p><strong>Phone Number:</strong> {html.escape(str(self.phone_number))}</p>
				<p><strong>Email:</strong> {html.escape(str(self.email))}</p>
				<p><strong>Appointment Type:</strong> {html.escape(str(self.appointment_type))}</p>
				<p><strong>Meeting Location:</strong> {html.escape(str(self.meeting_location)) if self.meeting_location else 'Not specified'}</p>
				<p><strong>Booking Date:</strong> {html.escape(str(self.booking_date)) if self.booking_date else 'Not specified'}</p>
				<p><strong>Booking Time:</strong> {html.escape(str(self.booking_time)) if self.booking_time else 'Not specified'}</p>
				<p><strong>Status:</strong> {html.escape(str(self.status))}</p>
			</div>
		"""
		
		if self.appointment_type == "New Customer":
			html_content += f"""
			<div style="background: #e8f4f8; padding: 20px; border-radius: 5px; margin: 20px 0;">
				<h3 style="margin-top: 0;">New Customer Details</h3>
				<p><strong>Industry:</strong> {html.escape(str(self.industry)) if self.industry else 'Not specified'}</p>
				<p><strong>Requirements:</strong> {html.escape(str(self.requirements)) if self.requirements else 'Not specified'}</p>
				<p><strong>Budget:</strong> {html.escape(str(self.budget)) if self.budget else 'Not specified'}</p>
				{f'<p><strong>Notes:</strong><br>{safe_html(self.notes)}</p>' if self.notes else ''}
				{f'<p><strong>References:</strong><br>{safe_html(self.references)}</p>' if self.references else ''}
			</div>
			"""
		else:  # Current Active Client
			html_content += f"""
			<div style="background: #e8f4f8; padding: 20px; border-radius: 5px; margin: 20px 0;">
				<h3 style="margin-top: 0;">Current Active Client Details</h3>
				<p><strong>Brand Name:</strong> {html.escape(str(self.brand_name)) if self.brand_name else 'Not specified'}</p>
				<p><strong>Acknowledgment:</strong> {'Yes' if self.acknowledgment_checkbox else 'No'}</p>
				{f'<p><strong>References:</strong><br>{safe_html(self.current_client_references)}</p>' if self.current_client_references else ''}
			</div>
			"""
		
		# Add Location details
		if self.meeting_location:
			location_html = """
			<div style="background: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0;">
				<h3 style="margin-top: 0;">Location Details</h3>
			"""
			
			location_html += f'<p><strong>Meeting Location:</strong> {html.escape(str(self.meeting_location))}</p>'
			
			if self.meeting_location == "Our Location":
				location_html += f'<p><strong>Company Location:</strong> {html.escape(str(self.company_location)) if self.company_location else "Not set"}</p>'
			else:
				if self.location:
					location_html += f'<p><strong>Location:</strong> {html.escape(str(self.location))}</p>'
				if self.street_name:
					location_html += f'<p><strong>Street Name:</strong> {html.escape(str(self.street_name))}</p>'
				if self.building_name:
					location_html += f'<p><strong>Building Name:</strong> {html.escape(str(self.building_name))}</p>'
				if self.apartment_number:
					location_html += f'<p><strong>Apartment Number:</strong> {html.escape(str(self.apartment_number))}</p>'
			
			location_html += "</div>"
			html_content += location_html
		
		html_content += """
			<div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
				<p>This is an automated notification from the Video Production Appointment System.</p>
			</div>
		</div>
		"""
		
		return html_content

