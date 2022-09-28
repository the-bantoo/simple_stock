# Copyright (c) 2022, Bantoo and Contributors and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from typing import Any, Dict, List, Optional, TypedDict

from frappe.query_builder.functions import CombineDatetime
from frappe.utils import cint, date_diff, flt, getdate


class StockUsageByAreaOfApplication(TypedDict):
	from_date: str
	to_date: str
	area_of_application: Optional[str]

def execute(filters: Optional[StockUsageByAreaOfApplication] = None):

	if not filters:
		filters = {}

	if filters.get("company"):
		company_currency = erpnext.get_company_currency(filters.get("company"))
	else:
		company_currency = frappe.db.get_single_value("Global Defaults", "default_currency")
	
	columns = get_columns()
	data = get_data(filters)

	return columns, data

def apply_conditions(filters):
	#sle = frappe.qb.DocType("Stock Ledger Entry")
	#warehouse_table = frappe.qb.DocType("Warehouse")

	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if not filters.get("to_date"):
		frappe.throw(_("'To Date' is required"))


def get_data(filters):
	data = []
	report_data = {}

	total = 0

	apply_conditions(filters)

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	areas = frappe.get_all("Stock Issue", 
		fields = [ 'area_of_application' ], 
		pluck = "area_of_application",
    	order_by='area_of_application asc',
		filters = [
			[	
				'docstatus', '=', 1
			],
			[
				'posting_date', 'between', [ from_date, to_date]
			]
		]
	)

	# removing duplicates from area list
	areas = list(dict.fromkeys(areas))

	if filters.get("area_of_application"):
			areas = [ filters.get("area_of_application") ]


	# per area of application 
	# get kids with this area in parent
	for area in areas:
		subtotal = 0

		# area title
		report_data = {
			"area_of_application": "<strong>" + area + "</strong>",
			"spray_program": "",
			"item_code": "",
			"qty": "",
			"uom": "",
			"basic_rate": "",
			"amount": ""
		}
		data.append(report_data)
		
		#get parent with area within date
		issue_list = frappe.get_all("Stock Issue", 
			fields = [ 'name' ], 
			pluck = "name",
			filters = [
				[	
					'docstatus', '=', 1
				],
				[	
					'area_of_application', '=', area
				],
				[
					'posting_date', 'between', [ from_date, to_date]
				]
			]
		)

		details = frappe.get_all("Stock Issue Detail", 
			fields = [ "parent", "item_code",  "qty", "uom", "basic_rate", "amount" ], 
    		order_by='item_code asc',
			filters = [
				[
					'parent', 'IN', issue_list
				]
			]
		)
		
		for d in details:
			report_data = {
				"area_of_application": "",
				"spray_program": frappe.get_value("Stock Issue", d.parent, "spray_program"),
				"item_code": d.item_code,
				"qty": d.qty,
				"uom": d.uom,
				"basic_rate": d.basic_rate,
				"amount": d.amount,
			}
			data.append(report_data)
			subtotal = subtotal + d.amount

		# area subtotal
		report_data = {
			"area_of_application": "<strong>Total Cost of Inputs</strong>",
			"spray_program": "",
			"item_code": "",
			"qty": "",
			"uom": "",
			"basic_rate": "",
			"amount": subtotal
		}
		data.append(report_data)

		report_data = {
			"area_of_application": "",
			"spray_program": "",
			"item_code": "",
			"qty": "",
			"uom": "",
			"basic_rate": "",
			"amount": ""
		}
		data.append(report_data)

		total = total + subtotal

	report_data = {
		"area_of_application": "<strong>Overall Total Cost of Inputs</strong>",
		"spray_program": "",
		"item_code": "",
		"qty": "",
		"uom": "",
		"basic_rate": "",
		"amount": total
	}
	data.append(report_data)

	return data

def get_columns():
	"""return columns"""

	columns = [
		{
			"label": _("Area of Application"),
			"fieldname": "area_of_application",
			"fieldtype": "Link",
			"options": "Area of Application",
			"width": 200,
		},
		{
			"label": _("Spray Program"),
			"fieldname": "spray_program",
			"fieldtype": "Link",
			"options": "Spray Program",
        	'align': 'left',
			"width": 300,
		},
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
        	'align': 'left',
			"width": 200,
		},
		{
			"label": _("Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": _("Unit"),
			"fieldname": "uom",
			"fieldtype": "Link",
			"options": "UOM",
        	'align': 'left',
			"width": 100,
		},
		{
			"label": _("Price"),
			"fieldname": "basic_rate",
			"fieldtype": "Currency",
			"width": 150,
			"options": "currency",
		},
		{
			"label": _("Cost"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 150,
			"options": "currency",
		}
	]

	return columns