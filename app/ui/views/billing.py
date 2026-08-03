import streamlit as st
import pandas as pd
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.services.invoice_service import InvoiceService
from app.services.quotation_service import QuotationService
from app.models.database import query_db
from app.ui.styles import render_html, draw_metric_card, trigger_toast
from app.core.pdf_generator import generate_invoice_html, generate_quotation_html, generate_pdf_from_html

def render_billing_tab():
    render_html('<div class="section-head"><i class="fa-solid fa-file-invoice-dollar"></i> Invoice & Quotation Builder</div>')
    st.caption("Create Quotations and Tax Invoices with real-time pricing math and instant PDF downloads.")
    
    # 1. Customer Selection Header
    col_b1, col_b2, col_b3 = st.columns(3)
    customers = CustomerService.get_customers()
    cust_opts = ["-- Select Customer --"] + [f"{c['name']} (ID: {c['id']})" for c in customers]
    
    with col_b1:
        sel_cust_str = st.selectbox("👤 Select Customer", cust_opts, key="bill_cust_select")
        
    selected_cust = None
    if sel_cust_str != "-- Select Customer --":
        c_id = int(sel_cust_str.split("ID: ")[1].replace(")", ""))
        selected_cust = CustomerService.get_customer_by_id(c_id)
        
    with col_b2:
        disc_val = st.number_input(
            "🏷️ Customer Discount (%)", 
            min_value=0.0, max_value=100.0, 
            value=float(selected_cust['discount_percentage']) if selected_cust else 0.0, 
            step=0.5,
            key="bill_cust_discount"
        )
    with col_b3:
        gst_no = st.text_input("🏢 GSTIN Number", value=selected_cust['gst_number'] if selected_cust and selected_cust['gst_number'] else "", key="bill_gstin")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Line Items Builder
    render_html('<div class="setting-section"><div class="setting-section-title"><i class="fa-solid fa-cart-flatbed"></i> Line Items</div></div>')
    
    all_prods = query_db("""
        SELECT p.id, p.part_number, p.part_name, COALESCE(c.price_per_100_pcs, 0.0) as price_100
        FROM PRODUCTS p
        LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
        ORDER BY p.part_number ASC
    """)
    prod_map = {f"{p['part_number']} - {p['part_name'] or ''}": p for p in all_prods}
    prod_names = ["-- Select Product --"] + list(prod_map.keys())
    
    if "cart_items" not in st.session_state:
        st.session_state.cart_items = []
        
    c_add1, c_add2, c_add3, c_add4 = st.columns([3, 1, 1, 1])
    with c_add1:
        p_sel = st.selectbox("Add Product", prod_names, key="bill_add_prod")
    with c_add2:
        p_qty = st.number_input("Quantity (PCS)", min_value=1.0, value=100.0, step=10.0, key="bill_add_qty")
    with c_add3:
        p_disc = st.number_input("Disc %", min_value=0.0, max_value=100.0, value=disc_val, step=0.5, key="bill_add_disc")
    with c_add4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add Item", use_container_width=True, type="primary"):
            if p_sel != "-- Select Product --":
                prod_obj = prod_map[p_sel]
                st.session_state.cart_items.append({
                    "product_id": prod_obj['id'],
                    "part_number": prod_obj['part_number'],
                    "quantity": p_qty,
                    "discount_percentage": p_disc,
                    "unit_price_100": prod_obj['price_100']
                })
                trigger_toast(f"Added {prod_obj['part_number']} to billing list!", icon="🛒")
                st.rerun()

    # Render Cart Table
    if not st.session_state.cart_items:
        st.info("No line items added yet. Select a product above to build an order.")
        return

    # Calculate Order
    cust_payload = {
        "id": selected_cust['id'] if selected_cust else None,
        "name": selected_cust['name'] if selected_cust else "Guest Customer",
        "discount_percentage": disc_val,
        "gst_number": gst_no,
        "payment_terms": "Net 30 Days"
    }
    
    calc_res = OrderService.calculate_order(cust_payload, st.session_state.cart_items)
    
    df_cart = []
    for idx, item in enumerate(calc_res['items']):
        df_cart.append({
            "#": idx + 1,
            "Part Number": item['part_number'],
            "Qty (PCS)": item['quantity'],
            "Rate / Pc (INR)": f"Rs. {item['unit_price']:,.2f}",
            "Disc %": f"{item['discount_percentage']:.1f}%",
            "Line Total": f"Rs. {item['line_total']:,.2f}",
            "Stock Status": "⚠️ Insufficient" if item['insufficient_stock'] else "✅ Available"
        })
        
    st.dataframe(pd.DataFrame(df_cart), use_container_width=True, hide_index=True)
    
    # 3. Calculation Summary Cards
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        draw_metric_card("Subtotal", f"Rs. {calc_res['subtotal']:,.2f}", "Taxable Value", "fa-solid fa-calculator", "blue")
    with col_s2:
        draw_metric_card(f"GST ({calc_res['gst_rate']}%)", f"Rs. {calc_res['gst_amount']:,.2f}", "Calculated Tax", "fa-solid fa-percent", "amber")
    with col_s3:
        draw_metric_card("Grand Total", f"Rs. {calc_res['grand_total']:,.2f}", "Final Payable", "fa-solid fa-money-bill-wave", "green")
    with col_s4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Billing List", use_container_width=True):
            st.session_state.cart_items = []
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 4. Action Buttons (Generate Invoice / Quotation)
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button("📄 Generate & Save Quotation (QTN)", use_container_width=True, type="primary"):
            q_id = QuotationService.generate_quotation(cust_payload, st.session_state.cart_items)
            q_data = QuotationService.get_quotation_by_id(q_id)
            q_html = generate_quotation_html(q_data)
            q_pdf = generate_pdf_from_html(q_html)
            
            st.success(f"Quotation Created Successfully! Number: **{q_data['quotation_number']}**")
            st.download_button(
                label=f"📥 Download Quotation PDF ({q_data['quotation_number']})",
                data=q_pdf,
                file_name=f"{q_data['quotation_number']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
    with col_act2:
        if st.button("📜 Generate & Save Tax Invoice (INV)", use_container_width=True):
            o_id = OrderService.create_order(cust_payload, st.session_state.cart_items)
            inv_id = InvoiceService.generate_invoice_for_order(o_id)
            inv_data = InvoiceService.get_invoice_by_id(inv_id)
            inv_html = generate_invoice_html(inv_data)
            inv_pdf = generate_pdf_from_html(inv_html)
            
            st.success(f"Invoice Created Successfully! Number: **{inv_data['invoice_number']}**")
            st.download_button(
                label=f"📥 Download Invoice PDF ({inv_data['invoice_number']})",
                data=inv_pdf,
                file_name=f"{inv_data['invoice_number']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
