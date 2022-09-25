// Copyright (c) 2022, Bantoo and Contributors and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Stock Levels By Category"] = {
	"filters": [

		{
			"fieldname": "item_group",
			"label": __("Category / Item Group"),
			"fieldtype": "Link",
			"width": "250",
			"options": "Item Group"
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"width": "135",
			"options": "Warehouse",
			get_query: () => {
				let warehouse_type = frappe.query_report.get_filter_value("warehouse_type");
				let company = frappe.query_report.get_filter_value("company");

				return {
					filters: {
						...warehouse_type && {warehouse_type},
						...company && {company}
					}
				}
			}
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Company",
			"default": frappe.defaults.get_default("company"),
			"hidden": 1,
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.get_today(),
			"hidden": 1,
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.get_today(),
			"hidden": 1,
		},
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Item",
			"get_query": function() {
				return {
					query: "erpnext.controllers.queries.item_query",
				};
			}
		},
		{
			"fieldname": 'show_stock_ageing_data',
			"label": __('Show More Details'),
			"fieldtype": 'Check',
			"hidden": 1
		},
	],

	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "bal_qty" && data) {
			value = "<span style='font-weight:600'>" + value + "</span>";
		}
		else if (column.fieldname == "in_qty" && data && data.in_qty > 0) {
			value = "<span style='color:green'>" + value + "</span>";
		}

		return value;
	}
};

erpnext.utils.add_inventory_dimensions('Stock Levels By Category', 8);
