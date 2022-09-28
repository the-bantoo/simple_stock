// Copyright (c) 2022, Bantoo and Contributors and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Stock Usage By Area of Application"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname": "area_of_application",
			"label": __("Area of Application"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Area of Application"
		}
	]
};
