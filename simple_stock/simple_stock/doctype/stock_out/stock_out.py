# Copyright (c) 2022, Bantoo and Contributors and contributors
# For license information, please see license.txt

import frappe
import time
from frappe.model.document import Document

"""
	STOCK IN
	- check qty in stock in (using stock_uom)
	- conversion_factor
	- remarks

	STOCK OUT
	- Fix stock balances using for checker from Stock Entry - d
	- Warn low stock in Warehouse - d
	- Custom fields - d
	- submission - d
	- return doctype

	BUGS
	- STOCK BAL
		- clear transactions -t
			- test receipting after
		- find issue
		- update erpnext

	- conversion factor
		- Qty in Default UOM

	EXTRAS
	- Default user WH
	- Stock Out Employee field
	- verify edit_date - use now if its not checked

"""

class StockOut(Document):

	def before_submit(self):

		tm = time.strptime(self.t_date, "%Y-%m-%d %H:%M:%S")
		self.t_time =  str(tm.tm_hour) + ":" + str(tm.tm_min) + ":" + str(tm.tm_sec)

		if self.is_transfer == 1:
			self.make_stock_entry_transfer()
		else:
			self.make_stock_entry_issue()

	def make_stock_entry_issue(self):
		#convert stock_in items to stock_entry items

		items = []
		
		for item in self.items:
			if item.price == 0:
				frappe.throw("{0} unit value can not be 0".format(item.item))

			items.append({
				"item_code": item.item,
				"item_name": item.item_name,
				"qty": item.qty,
				"transfer_qty": item.qty,
				"conversion_factor": item.conversion_factor,
				"s_warehouse": self.transacting_warehouse,
				"uom": item.unit,
				"stock_uom": item.stock_uom,
				"basic_rate": item.price,
				"valuation_rate": item.price,
				"basic_amount": item.line_value,
				"expense_account": "5111 - Cost of Goods Sold - EF", #get
				"spray_program": self.spray_program,
				"crops": self.user_crops,
				"area_of_application": self.application,
				"employee": self.employee
			})

		se = frappe.get_doc({
			"company": "Enviro Flor Limited", #doc.company,
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"items": items,
			"naming_series": "MAT-STE-.YYYY.-",
			"set_posting_time": 1,
			"posting_date": self.t_date,
			"posting_time": self.t_time,
			"from_warehouse": self.transacting_warehouse,
			"remarks": self.remarks,
			"docstatus": 1
		})
		inserted = se.insert()
		#inserted.submit()

		self.db_set("stock_entry_reference", inserted.name)
		self.notify_update()


	def make_stock_entry_transfer(self):
		#convert stock_in items to stock_entry items

		if self.transacting_warehouse == self.receiving_wh:
			frappe.throw("Transacting Warehouse and Receiving Warehouse cannot be the same")
		
		items = []
		
		for item in self.items:
			if item.price == 0:
				frappe.throw("{0} unit value can not be 0".format(item.item))
				
			items.append({
				"item_code": item.item,
				"item_name": item.item_name,
				"qty": item.qty,
				"transfer_qty": item.qty,
				"conversion_factor": item.conversion_factor,
				"s_warehouse": self.transacting_warehouse,
				"t_warehouse": self.receiving_wh,
				"uom": item.unit,
				"stock_uom": item.stock_uom,
				"basic_rate": item.price,
				"basic_amount": item.line_value,
				"employee": self.employee,
				"expense_account": "5119 - Stock Adjustment - EF" #get
			})

		se = frappe.get_doc({
			"company": "Enviro Flor Limited", #doc.company,
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Transfer",
			"items": items,
			"naming_series": "MAT-STE-.YYYY.-",
			"set_posting_time": 1,
			"posting_date": self.t_date,
			"posting_time": self.t_time,
			"from_warehouse": self.transacting_warehouse,
			"to_warehouse": self.receiving_wh,
			"remarks": self.remarks,
			"docstatus": 1
		})

		inserted = se.insert()

		self.db_set("stock_entry_reference", inserted.name)
		self.notify_update()