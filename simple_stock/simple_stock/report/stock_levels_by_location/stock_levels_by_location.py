# Copyright (c) 2022, Bantoo and Contributors and contributors
# For license information, please see license.txt


from operator import itemgetter
from typing import Any, Dict, List, Optional, TypedDict

import frappe
from frappe import _
from frappe.query_builder.functions import CombineDatetime
from frappe.utils import cint, date_diff, flt, getdate
from frappe.utils.nestedset import get_descendants_of
from pypika.terms import ExistsCriterion

import erpnext
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots, get_average_age
from erpnext.stock.utils import add_additional_uom_columns, is_reposting_item_valuation_in_progress


class StockLevelsByLocationFilter(TypedDict):
	from_date: str
	to_date: str
	item_group: Optional[str]
	item: Optional[str]
	warehouse: Optional[str]







SLEntry = Dict[str, Any]


def execute(filters: Optional[StockLevelsByLocationFilter] = None):
	is_reposting_item_valuation_in_progress()
	if not filters:
		filters = {}

	if filters.get("company"):
		company_currency = erpnext.get_company_currency(filters.get("company"))
	else:
		company_currency = frappe.db.get_single_value("Global Defaults", "default_currency")

	include_uom = filters.get("include_uom")
	columns = get_columns(filters)
	items = get_items(filters)
	sle = get_stock_ledger_entries(filters, items)

	if filters.get("show_stock_ageing_data"):
		filters["show_warehouse_wise_stock"] = True
		item_wise_fifo_queue = FIFOSlots(filters, sle).generate()

	# if no stock ledger entry found return
	if not sle:
		return columns, []

	iwb_map = get_item_warehouse_map(filters, sle)
	item_map = get_item_details(items, sle, filters)
	item_reorder_detail_map = get_item_reorder_details(item_map.keys())

	data = []
	conversion_factors = {}

	_func = itemgetter(1)

	to_date = filters.get("to_date")

	for group_by_key in iwb_map:
		item = group_by_key[1]
		warehouse = group_by_key[2]
		company = group_by_key[0]

		if item_map.get(item):
			qty_dict = iwb_map[group_by_key]
			item_reorder_level = 0
			item_reorder_qty = 0
			if item + warehouse in item_reorder_detail_map:
				item_reorder_level = item_reorder_detail_map[item + warehouse]["warehouse_reorder_level"]
				item_reorder_qty = item_reorder_detail_map[item + warehouse]["warehouse_reorder_qty"]

			report_data = {
				"warehouse": warehouse,
				"currency": company_currency,
				"item_code": item,
				"company": company,
			}
			report_data.update(item_map[item])
			report_data.update(qty_dict)

			if filters.get("show_stock_ageing_data"):
				fifo_queue = item_wise_fifo_queue[(item, warehouse)].get("fifo_queue")

				stock_ageing_data = {
					"reorder_level": item_reorder_level,
					"reorder_qty": item_reorder_qty,
					"average_age": 0, 
					"earliest_age": 0, 
					"latest_age": 0
				}
				if fifo_queue:
					fifo_queue = sorted(filter(_func, fifo_queue), key=_func)
					if not fifo_queue:
						continue

					stock_ageing_data["average_age"] = get_average_age(fifo_queue, to_date)
					stock_ageing_data["earliest_age"] = date_diff(to_date, fifo_queue[0][1])
					stock_ageing_data["latest_age"] = date_diff(to_date, fifo_queue[-1][1])

				report_data.update(stock_ageing_data)

			data.append(report_data)

	add_additional_uom_columns(columns, data, include_uom, conversion_factors)
	return columns, data


def get_columns(filters: StockLevelsByLocationFilter):
	"""return columns"""
	columns = [
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 135,
		},
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 150,
		},
	]

	for dimension in get_inventory_dimensions():
		columns.append(
			{
				"label": _(dimension.doctype),
				"fieldname": dimension.fieldname,
				"fieldtype": "Link",
				"options": dimension.doctype,
				"width": 110,
			}
		)

	columns.extend(
		[
			{
				"label": _("Unit"),
				"fieldname": "stock_uom",
				"fieldtype": "Link",
				"options": "UOM",
				"width": 60,
			},
			{
				"label": _("Balance"),
				"fieldname": "bal_qty",
				"fieldtype": "Float",
				"width": 105,
				"convertible": "qty",
			}
		]
	)

	if filters.get("show_stock_ageing_data"):
		columns += [

			{
				"label": _("Value"),
				"fieldname": "bal_val",
				"fieldtype": "Currency",
				"width": 110,
				"options": "currency",
			},
			{
				"label": _("Price"),
				"fieldname": "val_rate",
				"fieldtype": "Currency",
				"width": 90,
				"convertible": "rate",
				"options": "currency",
			},
			{
				"label": _("Reorder Level"),
				"fieldname": "reorder_level",
				"fieldtype": "Float",
				"width": 100,
				"convertible": "qty",
			},
			{
				"label": _("Reorder Qty"),
				"fieldname": "reorder_qty",
				"fieldtype": "Float",
				"width": 100,
				"convertible": "qty",
			},
			{"label": _("Avg Age"), "fieldname": "average_age", "width": 80},
			{"label": _("Earliest Age"), "fieldname": "earliest_age", "width": 100},
			{"label": _("Latest Age"), "fieldname": "latest_age", "width": 100},
		]

	return columns


def apply_conditions(query, filters):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	warehouse_table = frappe.qb.DocType("Warehouse")

	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if to_date := filters.get("to_date"):
		query = query.where(sle.posting_date <= to_date)
	else:
		frappe.throw(_("'To Date' is required"))

	if company := filters.get("company"):
		query = query.where(sle.company == company)

	if warehouse := filters.get("warehouse"):
		lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
		chilren_subquery = (
			frappe.qb.from_(warehouse_table)
			.select(warehouse_table.name)
			.where(
				(warehouse_table.lft >= lft)
				& (warehouse_table.rgt <= rgt)
				& (warehouse_table.name == sle.warehouse)
			)
		)
		query = query.where(ExistsCriterion(chilren_subquery))
	elif warehouse_type := filters.get("warehouse_type"):
		query = (
			query.join(warehouse_table)
			.on(warehouse_table.name == sle.warehouse)
			.where(warehouse_table.warehouse_type == warehouse_type)
		)

	return query


def get_stock_ledger_entries(filters: StockLevelsByLocationFilter, items: List[str]) -> List[SLEntry]:
	sle = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(sle)
		.select(
			sle.warehouse,
			sle.item_code,
			sle.posting_date,
			sle.actual_qty,
			sle.valuation_rate,
			sle.company,
			sle.voucher_type,
			sle.qty_after_transaction,
			sle.stock_value_difference,
			sle.item_code.as_("name"),
			sle.voucher_no,
			sle.stock_value,
			sle.batch_no,
		)
		.where((sle.docstatus < 2) & (sle.is_cancelled == 0))
		.orderby(sle.warehouse)
		.orderby(sle.item_code)
		.orderby(CombineDatetime(sle.posting_date, sle.posting_time))
		.orderby(sle.actual_qty)
	)

	inventory_dimension_fields = get_inventory_dimension_fields()
	if inventory_dimension_fields:
		for fieldname in inventory_dimension_fields:
			query = query.select(fieldname)
			if fieldname in filters and filters.get(fieldname):
				query = query.where(sle[fieldname].isin(filters.get(fieldname)))

	if items:
		query = query.where(sle.item_code.isin(items))

	query = apply_conditions(query, filters)
	return query.run(as_dict=True)


def get_inventory_dimension_fields():
	return [dimension.fieldname for dimension in get_inventory_dimensions()]


def get_item_warehouse_map(filters: StockLevelsByLocationFilter, sle: List[SLEntry]):
	iwb_map = {}
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	inventory_dimensions = get_inventory_dimension_fields()

	for d in sle:
		group_by_key = get_group_by_key(d, filters, inventory_dimensions)
		if group_by_key not in iwb_map:
			iwb_map[group_by_key] = frappe._dict(
				{
					"opening_qty": 0.0,
					"opening_val": 0.0,
					"in_qty": 0.0,
					"in_val": 0.0,
					"out_qty": 0.0,
					"out_val": 0.0,
					"bal_qty": 0.0,
					"bal_val": 0.0,
					"val_rate": 0.0,
				}
			)

		qty_dict = iwb_map[group_by_key]
		
		for field in inventory_dimensions:
			qty_dict[field] = d.get(field)

		if d.voucher_type == "Stock Reconciliation" and not d.batch_no:
			qty_diff = flt(d.qty_after_transaction) - flt(qty_dict.bal_qty)
		else:
			qty_diff = flt(d.actual_qty)

		value_diff = flt(d.stock_value_difference)

		if d.posting_date < from_date or (
			d.posting_date == from_date
			and d.voucher_type == "Stock Reconciliation"
			and frappe.db.get_value("Stock Reconciliation", d.voucher_no, "purpose") == "Opening Stock"
		):
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff

		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(qty_diff, float_precision) >= 0:
				qty_dict.in_qty += qty_diff
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_qty += abs(qty_diff)
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = d.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff

	iwb_map = filter_items_with_no_transactions(iwb_map, float_precision, inventory_dimensions)

	return iwb_map


def get_group_by_key(row, filters, inventory_dimension_fields) -> tuple:
	group_by_key = [row.company, row.item_code, row.warehouse]

	for fieldname in inventory_dimension_fields:
		if filters.get(fieldname):
			group_by_key.append(row.get(fieldname))

	return tuple(group_by_key)


def filter_items_with_no_transactions(iwb_map, float_precision: float, inventory_dimensions: list):
	pop_keys = []
	for group_by_key in iwb_map:
		qty_dict = iwb_map[group_by_key]

		no_transactions = True
		for key, val in qty_dict.items():
			if key in inventory_dimensions:
				continue

			val = flt(val, float_precision)
			qty_dict[key] = val
			if key != "val_rate" and val:
				no_transactions = False

		if no_transactions:
			pop_keys.append(group_by_key)

	for key in pop_keys:
		iwb_map.pop(key)

	return iwb_map


def get_items(filters: StockLevelsByLocationFilter) -> List[str]:
	"Get items based on item code, item group."
	if item_code := filters.get("item_code"):
		return [item_code]
	else:
		item_filters = {}
		if item_group := filters.get("item_group"):
			children = get_descendants_of("Item Group", item_group, ignore_permissions=True)
			item_filters["item_group"] = ("in", children + [item_group])

		return frappe.get_all("Item", filters=item_filters, pluck="name", order_by=None)


def get_item_details(items: List[str], sle: List[SLEntry], filters: StockLevelsByLocationFilter):
	item_details = {}
	if not items:
		items = list(set(d.item_code for d in sle))

	if not items:
		return item_details

	item_table = frappe.qb.DocType("Item")

	query = (
		frappe.qb.from_(item_table)
		.select(
			item_table.name,
			item_table.description,
			item_table.item_group,
			item_table.stock_uom,
		)
		.where(item_table.name.isin(items))
	)

	result = query.run(as_dict=1)

	for item_table in result:
		item_details.setdefault(item_table.name, item_table)

	return item_details


def get_item_reorder_details(items):
	item_reorder_details = frappe._dict()

	if items:
		item_reorder_details = frappe.get_all(
			"Item Reorder",
			["parent", "warehouse", "warehouse_reorder_qty", "warehouse_reorder_level"],
			filters={"parent": ("in", items)},
		)

	return dict((d.parent + d.warehouse, d) for d in item_reorder_details)
