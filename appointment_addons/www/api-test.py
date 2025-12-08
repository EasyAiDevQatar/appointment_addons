import frappe

no_cache = 1

def get_context(context):
	try:
		from appointment_addons.www.book_appointment import get_time_slots
		slots = get_time_slots()
		context.slots = slots if slots else []
		context.slots_count = len(slots) if slots else 0
		context.error = None
	except Exception as e:
		import traceback
		context.slots = []
		context.slots_count = 0
		context.error = str(e)
		context.traceback = traceback.format_exc()
	
	return context

