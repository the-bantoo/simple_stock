// Copyright (c) 2022, Bantoo and Contributors and contributors
// For license information, please see license.txt
let company = frappe.defaults.get_user_default("Company") || frappe.defaults.get_global_default("company");

frappe.ui.form.on('Stock In', {
	refresh: function(frm) {
		
		let company_currency = get_company_currency(company)
		if (frm.doc.currency == company_currency) {
			frm.set_value("conversion_rate", 1);
			cur_frm.set_df_property("conversion_rate", "description", "Company currency = 1 " + company_currency);
		}
	},
	onload(frm) {
	    frm.set_query("receiving_warehouse", function() {
            return {
                "filters": {
                    "is_group": 0
                }
            };
        });
        
        cur_frm.set_query("item", "items", function(doc, cdt, cdn) {
		    return {
                "filters": {
                    "is_stock_item": 1
            }
		};
	});
	},
	is_purchase: (frm) => {
		if (frm.doc.is_purchase == 0) {
			frm.set_value("naming_series", "IN-.YY.MM.DD.-.####");
			refresh_field("naming_series");
		}
		else {
			frm.set_value("naming_series", "IN-.YY.MM.DD.-.####. - .supplier");
			refresh_field("naming_series");
		}
	},
	currency: function(frm) {
		check_currency(frm);
	},
	edit_date: function(frm) {
		if(frm.doc.docstatus == 0 && frm.doc.edit_date) {
			frm.set_df_property('t_date', 'read_only', 0);
		} else {
			frm.set_df_property('t_date', 'read_only', 1);
		}
	},
	taxes: function(frm, cdt, cdn) {
		update_doc_totals(frm, cdt, cdn);
	}
});

frappe.ui.form.on('Stock In Items', {
	qty: function(frm, cdt, cdn) {
		line_total(frm, cdt, cdn);
		update_doc_totals(frm, cdt, cdn);
		conversion_factor(frm, cdt, cdn);
		cur_frm.refresh_field("items");
	},
	unit(frm, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		if(item.item && item.unit) {
			console.log("unit " + item.unit + " | len "+ item.unit.length)
			if (item.unit.length < 1 ) return;

			return frappe.call({
				method: "erpnext.stock.get_item_details.get_conversion_factor",
				args: {
					item_code: item.item,
					uom: item.unit
				},
				callback: function(r) {
					if(!r.exc) {
						console.log(r.message.conversion_factor)
						frappe.model.set_value(cdt, cdn, 'conversion_factor', r.message.conversion_factor);
					}
				}
			});
		}
		calculate_stock_uom_rate(frm, cdt, cdn);
		frm.refresh_field("items");
	},
	price: function(frm, cdt, cdn) {
		line_total(frm, cdt, cdn);
		update_doc_totals(frm, cdt, cdn);
	},
	items_remove: function(frm, cdt, cdn){
        update_doc_totals(frm, cdt, cdn);
	},
    item: function(frm, cdt, cdn){
		var item = frappe.get_doc(cdt, cdn);

		item.weight_per_unit = 0;
		item.weight_uom = '';
		item.conversion_factor = 1;
		
		set_wh_balances(frm, item);
		conversion_factor(frm, cdt, cdn);

		get_incoming_rate(item, frm.doc.t_date, frm.doc.t_date, frm.doc.doctype, company);
        
		cur_frm.refresh_field("items");
	}
	
});

function set_wh_balances(frm, item) {
	// set item balances
	console.log("set_wh_balances");
	frappe.call({
		method: 'erpnext.stock.dashboard.item_dashboard.get_data',
		args: {
				item_code: item.item,
		},
		callback: (r) => {
			let res = r.message;
			// console.log(res);
			
			let wh_bal = 0, total_qty = 0;

			for (var key in res) {
				
				// console.log(key +" "+res[key].warehouse +" "+res[key].actual_qty);
				total_qty = total_qty + res[key].actual_qty;
				
				if (frm.doc.receiving_warehouse == res[key].warehouse){
					wh_bal = res[key].actual_qty;
				}
			}
			frappe.model.set_value(item.doctype, item.name, 'company_balance', total_qty);
			frappe.model.set_value(item.doctype, item.name, 'warehouse_balance', wh_bal);
			
		}
	});	
}

function line_total(frm, cdt, cdn){
	let line = locals[cdt][cdn];
	let line_total = parseFloat(line.qty) * parseFloat(line.price);
	line.line_value = line_total;
	refresh_field("items");
}

function update_doc_totals(frm, cdt, cdn){
	var items = locals[cdt][cdn];
    var total = 0;
    var quantity = 0;
    frm.doc.items.forEach(
        function(items) { 
            total += items.line_value;
            quantity += items.qty;
        });
    frm.set_value("grand_total", total + (parseFloat(frm.doc.taxes) || 0) );
    refresh_field("grand_total");
    frm.set_value("total_qty", quantity);
    refresh_field("total_qty");
}


function check_currency(frm){
	console.log(frm.doc.currency);
	let company = frappe.defaults.get_user_default("Company") || frappe.defaults.get_global_default("company");
	let company_currency = get_company_currency(company)

	if (frm.doc.currency == company_currency) {
		frm.set_value("conversion_rate", 1);
		cur_frm.set_df_property("conversion_rate", "description", "Company currency = 1 " + company_currency);
	}
	else {
		get_exchange_rate(frm, frm.doc.t_date, frm.doc.currency, company_currency, function(exchange_rate) {
			frm.set_value("conversion_rate", exchange_rate);

			//exchange rate field label
			cur_frm.set_df_property("conversion_rate", "description", "1 " + frm.doc.currency
			+ " = " + exchange_rate + " " + company_currency);
		});
	}
	

	change_form_labels(frm);
	change_grid_labels(frm);
	frm.refresh_fields();
}

function change_form_labels(frm) {
	frm.set_currency_labels(["total", "net_total", "taxes", "discount_amount",
			"grand_total", "taxes_and_charges_added", "taxes_and_charges_deducted",
			"rounded_total", "in_words", "paid_amount", "write_off_amount", "operating_cost",
			"scrap_material_cost", "rounding_adjustment", "raw_material_cost",
			"total_cost"], frm.doc.currency);
	
}

function change_grid_labels(frm) {
	update_item_grid_labels(frm);

	//toggle_item_grid_columns(frm, company_currency);

	if (frm.doc.items && frm.doc.items.length > 0) {
		frm.set_currency_labels(["price", "line_value"], frm.doc.currency, "items");

		/**var item_grid = frm.fields_dict["items"].grid;
		$.each(["price", "line_value"], function(i, fname) {
			if(frappe.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, frm.doc.currency == company_currency);
		});
		*/
	}
}
function update_item_grid_labels(frm) {
	frm.set_currency_labels([
		"price", "line_value"
	], frm.doc.currency, "items");
}

function get_company_currency(company) {
	return erpnext.get_currency(company);
}

function get_exchange_rate(frm, transaction_date, from_currency, company_currency, callback) {
	var args;
	if (["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"].includes(frm.doctype)) {
		args = "for_selling";
	}
	else if (["Purchase Order", "Purchase Receipt", "Purchase Invoice", "Stock In"].includes(frm.doctype)) {
		args = "for_buying";
	}

	if (!transaction_date || !from_currency || !company_currency) return;

	return frappe.call({
		method: "erpnext.setup.utils.get_exchange_rate",
		args: {
			transaction_date: transaction_date,
			from_currency: from_currency,
			to_currency: company_currency,
			args: args
		},
		freeze: true,
		freeze_message: __("Fetching exchange rates ..."),
		callback: function(r) {
			callback(flt(r.message));
		}
	});
}

function conversion_factor(frm, cdt, cdn) {
	if(frappe.meta.get_docfield(cdt, "stock_qty", cdn)) {
		var item = frappe.get_doc(cdt, cdn);
		frappe.model.round_floats_in(item, ["qty", "conversion_factor"]);
		item.stock_uom = flt(item.qty * item.conversion_factor, precision("stock_qty", item));
		refresh_field("stock_qty", item.name, item.parentfield);
		toggle_conversion_factor(frm, item);

		/**
		if(doc.doctype != "Material Request") {
			item.total_weight = flt(item.stock_qty * item.weight_per_unit);
			refresh_field("total_weight", item.name, item.parentfield);
			this.calculate_net_weight();
		}
		*/
		calculate_stock_uom_rate(frm, cdt, cdn);
	}
}

function calculate_stock_uom_rate(frm, cdt, cdn) {
	let item = frappe.get_doc(cdt, cdn);
	item.stock_uom_rate = flt(item.price)/flt(item.conversion_factor);
	refresh_field("stock_uom_rate", item.item, item.parentfield);
}

function toggle_conversion_factor(frm, item) {
	// toggle read only property for conversion factor field if the uom and stock uom are same
	if(frm.get_field('items').grid.fields_map.conversion_factor) {
		frm.fields_dict.items.grid.toggle_enable("conversion_factor",
			((item.uom != item.stock_uom) && !frappe.meta.get_docfield(cur_frm.fields_dict.items.grid.doctype, "conversion_factor").read_only)? true: false);
	}

}

function get_incoming_rate(item, posting_date, posting_time, voucher_type, company) {
	if (!item.item) return;

	let item_args = {
		'item_code': item.item,
		'warehouse': in_list('Purchase Receipt', 'Purchase Invoice') ? item.from_warehouse : item.warehouse,
		'posting_date': posting_date,
		'posting_time': posting_time,
		'qty': item.qty * item.conversion_factor,
		'serial_no': item.serial_no,
		'batch_no': item.batch_no,
		'voucher_type': voucher_type,
		'company': company,
		'allow_zero_valuation_rate': item.allow_zero_valuation_rate
	}
	console.log(1)

	frappe.call({
		method: 'erpnext.stock.utils.get_incoming_rate',
		args: {
			args: item_args
		},
		callback: function(r) {
			console.log(2)
			console.log(company)
			frappe.model.set_value(item.doctype, item.name, 'price', r.message * item.conversion_factor);
		}
	});
}

