# Copyright (c) 2022, Bantoo and Contributors and contributors
# For license information, please see license.txt

import frappe
import time
from frappe.model.document import Document

class StockReturn(Document):
	def before_submit(self):

		tm = time.strptime(self.t_date, "%Y-%m-%d %H:%M:%S")
		self.t_time =  str(tm.tm_hour) + ":" + str(tm.tm_min) + ":" + str(tm.tm_sec)

		self.make_stock_entry_receipt()

	def make_stock_entry_receipt(self):
		#convert stock items to stock_entry items

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
				"t_warehouse": self.receiving_warehouse,
				"uom": item.unit,
				"stock_uom": item.stock_uom,
				"basic_rate": item.price,
				"basic_amount": item.line_value,
				"employee": self.employee,
				"return_reason": self.reason_for_return,
				"expense_account": "5119 - Stock Adjustment - EF" #get
			})

		se = frappe.get_doc({
			"company": "Enviro Flor Limited", #doc.company,
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"items": items,
			"naming_series": "MAT-STE-.YYYY.-",
			"set_posting_time": 1,
			"posting_date": self.t_date,
			"posting_time": self.t_time,
			"to_warehouse": self.receiving_warehouse,
			"remarks": self.remarks,
			"docstatus": 1
		})

		entry = se.insert()

		self.db_set("stock_entry_reference", entry.name)
		self.notify_update()
