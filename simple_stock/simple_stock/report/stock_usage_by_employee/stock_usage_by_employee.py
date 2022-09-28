# Copyright (c) 2022, Bantoo and Contributors and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from typing import Any, Dict, List, Optional, TypedDict

from frappe.query_builder.functions import CombineDatetime
from frappe.utils import cint, date_diff, flt, getdate


class StockUsageByEmployee(TypedDict):
	from_date: str
	to_date: str
	requesting_employee: Optional[str]

def execute(filters: Optional[StockUsageByEmployee] = None):

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

	employees = frappe.get_all("Stock Issue", 
		fields = [ 'requesting_employee' ], 
		pluck = "requesting_employee",
    	order_by='requesting_employee asc',
		filters = [
			[	
				'docstatus', '=', 1
			],
			[
				'posting_date', 'between', [ from_date, to_date]
			]
		]
	)

	# removing duplicates from employee list
	employees = list(dict.fromkeys(employees))

	if filters.get("requesting_employee"):
		employees = [ filters.get("requesting_employee") ]

	# per employee 
	# get kids with this employee in parent
	for employee in employees:
		subtotal = 0

		# employee title
		# "<strong>" + employee + "</strong>",
		report_data = {
			"requesting_employee": "<strong>" + employee + "</strong>",
			"spray_program": "",
			"item_code": "",
			"qty": "",
			"uom": "",
			"basic_rate": "",
			"amount": ""
		}
		data.append(report_data)
		
		#get parent with employee within date
		issue_list = frappe.get_all("Stock Issue", 
			fields = [ 'name' ], 
			pluck = "name",
			filters = [
				[	
					'docstatus', '=', 1
				],
				[	
					'requesting_employee', '=', employee
				],
				[
					'posting_date', 'between', [ from_date, to_date ]
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
				"requesting_employee": "",
				"spray_program": frappe.get_value("Stock Issue", d.parent, "spray_program"),
				"item_code": d.item_code,
				"qty": d.qty,
				"uom": d.uom,
				"basic_rate": d.basic_rate,
				"amount": d.amount,
			}
			data.append(report_data)
			subtotal = subtotal + d.amount

		# employee subtotal
		report_data = {
			"requesting_employee": "<strong>Total Cost of Inputs</strong>",
			"spray_program": "",
			"item_code": "",
			"qty": "",
			"uom": "",
			"basic_rate": "",
			"amount": subtotal
		}
		data.append(report_data)

		report_data = {
			"requesting_employee": "",
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
		"requesting_employee": "<strong>Overall Total Cost of Usage</strong>",
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
			"label": _("Employee"),
			"fieldname": "requesting_employee",
			"fieldtype": "Link",
			"options": "User Employee",
			"width": 200,
		},
		{
			"label": _("Spray Program"),
			"fieldname": "spray_program",
			"fieldtype": "Link",
			"options": "Spray Program",
        	'align': 'left',
			"width": 200,
		},
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
        	'align': 'left',
			"width": 300,
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