# Copyright (c) 2022, Bantoo and Contributors and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class StockIn(Document):

	def validate(self):
		if self.is_purchase == 1:
			self.make_purchase_invoice()
		else:
			self.make_stock_entry_receipt()


	def make_purchase_invoice(self):
		p_items = []
		
		for item in self.items:
			if item.price == 0:
				frappe.throw("{0} price can not be 0".format(item.item))

			p_items.append({
				"item_code": item.item,
				"item_name": item.item_name,
				"supplier_batch": item.batch,
				"qty": item.qty,
				"stock_qty": item.stock_uom,
				"conversion_factor": 1, #fetch
				"rate": item.price,
				"warehouse": self.receiving_warehouse,
				"uom": item.unit,
				"stock_uom": item.stock_uom,
				"amount": item.line_value,
				"base_rate": item.price * self.conversion_rate,
				"base_amount": item.line_value * self.conversion_rate,
				"valuation_rate": item.price * self.conversion_rate,
				"expense_account": "1410 - Stock In Hand - EF" #get
			})

		pinv = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"items": p_items,
			"naming_series": "ACC-PINV-.YYYY.-",
			"supplier": self.supplier,
			"posting_date": self.t_date,
			"currency": self.currency,
			"conversion_rate": self.conversion_rate,
			"posting_time": self.t_date,
			"set_warehouse": self.receiving_warehouse,
			"update_stock": 1,
			"set_posting_time": 1,
			"is_paid": 1,
			"mode_of_payment": "Cash",
			"cash_bank_account": "1110 - Cash - EF", # get from comp
			"paid_amount": self.grand_total,
			"credit_to": "2110 - Creditors - EF", #get from comp
			"taxes": [{
				"category": "Total",
				"add_deduct_tax": "Add",
				"charge_type": "Actual",
				"tax_amount": self.taxes,
				"description": "Expenses Included In Valuation",
				"account_head": "5118 - Expenses Included In Valuation - EF" #get ???
			}],
			"docstatus": 0
		})
		inserted = pinv.insert()

		self.db_set("purchase_invoice", inserted.name)


	def make_stock_entry_receipt(self):
		#convert stock_in items to stock_entry items
		
		items = []
		
		for item in self.items:
			if item.price == 0:
				frappe.throw("{0} price can not be 0".format(item.item))
				
			items.append({
				"item_code": item.item,
				"item_name": item.item_name,
				"supplier_batch": item.batch,
				"qty": item.qty,
				"transfer_qty": item.stock_uom,
				"conversion_factor": 1, #fetch
				#"rate": item.price,
				#"amount": item.line_value,
				"t_warehouse": self.receiving_warehouse,
				"uom": item.unit,
				"stock_uom": item.stock_uom,
				"basic_rate": item.price * self.conversion_rate,
				"basic_amount": item.line_value * self.conversion_rate,
				"valuation_rate": item.price * self.conversion_rate,
				"expense_account": "5111 - Cost of Goods Sold - EF" #get
			})

		se = frappe.get_doc({
			"company": "Enviro Flor Limited", #doc.company,
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"items": items,
			"naming_series": "MAT-STE-.YYYY.-",
			"set_posting_time": 1,
			"posting_date": self.t_date,
			"currency": self.currency,
			"conversion_rate": self.conversion_rate,
			"posting_time": self.t_date,
			"to_warehouse": self.receiving_warehouse,
			"additional_costs": [{
				"exchange_rate": self.conversion_rate,
				"amount": self.taxes,
				"description": "Expenses Included In Valuation",
				"expense_account": "5118 - Expenses Included In Valuation - EF" #get ???
			}],
			"docstatus": 1
		})
		inserted = se.insert()

		self.db_set("stock_entry_reference", inserted.name)

	def cancel(doc):
		pass