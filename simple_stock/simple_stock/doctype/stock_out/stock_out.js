// Copyright (c) 2022, Bantoo and Contributors and contributors
// For license information, please see license.txt

let company = frappe.defaults.get_user_default("Company") || frappe.defaults.get_global_default("company");
//let company_currency = get_company_currency(company)

frappe.ui.form.on('Stock Out', {
    refresh: function(frm) {
        
    },
    onload(frm) {

        frm.set_query("transacting_warehouse", function() {
            return {
                "filters": {
                    "is_group": 0
                }
            };
        });

        frm.set_query("receiving_wh", function() {
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
        
        cur_frm.set_query("chemical_type", "items", function(doc, cdt, cdn) {
            return {
                "filters": {
                    /**"is_group": 0,
					"parent": "Chemicals"
					["name" not in [
						"All Item Gr*/
                }
            };
        });
    },
    spray_program(frm){
        if(frm.doc.spray_program){

            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Spray Program",
                    name: frm.doc.spray_program,
                    async: true
                },
                callback: (rs) => {
                    let r = rs.message;
                    
                    // console.log(r.sp_crops);
                    
                    frm.doc.user_crops = r.sp_crops;
                    frm.refresh_field('user_crops');
                    
                }
            });
        }
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

    // improved
    edit_date: function(frm) {
        if( !(frm.docstatus in [1, 2]) && frm.doc.edit_date == 0 ) {
            frm.set_df_property('t_date', 'read_only', 1);
        } else {
            frm.set_df_property('t_date', 'read_only', 0);
        }
    },

	transacting_warehouse: (frm) => {
		// cur_frm.set_df_property("warehouse_balance", "description", "Warehouse: " + frm.doc.transacting_warehouse);
	}

});


frappe.ui.form.on('Stock Out Items', {
    qty: function(frm, cdt, cdn) {
        conversion_factor(frm, cdt, cdn);
    },
    unit: (frm, cdt, cdn) => {
        var me = this;
        var item = frappe.get_doc(cdt, cdn);
        if(item.item && item.unit) {
            
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
        conversion_factor(frm, cdt, cdn);
        frm.refresh_field("items");
    },
    price: function(frm, cdt, cdn) {
        calculate_item_total(frm, cdt, cdn);
    },
    items_remove: function(frm, cdt, cdn){
        update_totals(frm, cdt, cdn);
    },
    item: function(frm, cdt, cdn){
        var item = frappe.get_doc(cdt, cdn);

        item.weight_per_unit = 0;
        item.weight_uom = '';
        item.conversion_factor = 0;
        item.qty = 0;

        conversion_factor(frm, cdt, cdn);
        //calculate_item_total(frm, cdt, cdn);

        cur_frm.refresh_field("items");
    }
    
});

/*
function line_total(frm, cdt, cdn){
    let line = locals[cdt][cdn];
    let line_total = parseFloat(line.qty) * parseFloat(line.price);
    line.line_value = line_total;
    refresh_field("items");
}
*/

function set_wh_balances(frm, item) {
	// set item balances
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
				
				//console.log(key +" "+res[key].warehouse +" "+res[key].actual_qty);
				total_qty = total_qty + res[key].actual_qty;
				
				if (frm.doc.transacting_warehouse == res[key].warehouse){
					wh_bal = res[key].actual_qty;
				}
			}
			frappe.model.set_value(item.doctype, item.name, 'company_balance', total_qty);
			frappe.model.set_value(item.doctype, item.name, 'warehouse_balance', wh_bal);

            if ( (item.parenttype == "Stock Out") && item.qty > wh_bal) {
                frappe.warn(
                    "Insufficient Stock",
                    "<p>You entered <strong>"+ item.qty +"</strong> but <strong>" + frm.doc.transacting_warehouse + 
                        "</strong> warehouse only has <strong>" + wh_bal + "</strong> of <strong>" + item.item + "</strong>.</p>" +
                        "<p> The company has a total of <strong>"+ total_qty +"</strong> in all warehouses combined.</p>",
                    () => {
                        // action to perform if Continue is selected
                        //The required quantity of <strong>" + item.item + "</strong> is insufficient in
                        $("[data-fieldname=qty]").focus()
                    },
                    'Adjust it',
                    false // Sets dialog as minimizable
                );
            }
		}
	});
}


function conversion_factor(frm, cdt, cdn) {
    if(frappe.meta.get_docfield(cdt, "stock_qty", cdn)) {
        var item = frappe.get_doc(cdt, cdn);
        frappe.model.round_floats_in(item, ["qty", "conversion_factor"]);
        
		item.line_value = flt(item.qty * item.conversion_factor, precision("stock_qty", item));

        refresh_field("stock_qty", item.name, item.parentfield);
        toggle_conversion_factor(frm, item);
		
        calculate_item_total(frm, cdt, cdn);
		set_wh_balances(frm, item);
    }
}


function toggle_conversion_factor(frm, item) {
	// toggle read only property for conversion factor field if the uom and stock uom are same
	if(frm.get_field('items').grid.fields_map.conversion_factor) {
		frm.fields_dict.items.grid.toggle_enable("conversion_factor",
			((item.unit != item.stock_uom) && !frappe.meta.get_docfield(cur_frm.fields_dict.items.grid.doctype, "conversion_factor").read_only)? true: false);
	}

}

function calculate_item_total(frm, cdt, cdn) {
    var item = frappe.get_doc(cdt, cdn);
    item.stock_uom_rate = flt(item.price)/(flt(item.conversion_factor) || 1);

    item.line_value = flt(item.qty) * flt(item.price);		

    refresh_field("line_value", item.item, item.parentfield);

    update_totals(frm, cdt, cdn);
}

function update_totals(frm, cdt, cdn){
    //var items = locals[cdt][cdn];
    var total = 0;
    var quantity = 0;
    frm.doc.items.forEach(
        function(item) { 
            total += item.line_value;
            quantity += item.qty;
        });
    frm.set_value("grand_total", total);
    refresh_field("grand_total");

    frm.set_value("total_qty", quantity);
    refresh_field("total_qty");
}