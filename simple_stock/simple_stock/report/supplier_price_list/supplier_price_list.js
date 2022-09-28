// Copyright (c) 2022, Bantoo and Contributors and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Supplier Price List"] = {
	"filters": [
		{
			"fieldname": "items",
			"label": __("Items Filter"),
			"fieldtype": "Select",
			"options": "Enabled Items only\nDisabled Items only\nAll Items",
			"default": "Enabled Items only",
			"on_change": function(query_report) {
				query_report.trigger_refresh();
			}
		}
	]
}
