import pandas as pd
import streamlit as st
from app.services.customer_service import CustomerService
from app.ui.styles import render_html, trigger_toast

def render_customers_tab():
    render_html('<div class="section-head"><i class="fa-solid fa-users"></i> Customer Directory & Discounts</div>')
    st.caption("Manage customer profiles, default discount percentages, GST numbers, and payment terms.")
    
    col_cu1, col_cu2 = st.columns([2, 1])
    with col_cu1:
        c_search = st.text_input("🔍 Search Customer Name or GSTIN", key="cust_dir_search")
    with col_cu2:
        st.markdown("<br>", unsafe_allow_html=True)
        show_add = st.button("➕ Add New Customer", use_container_width=True, type="primary")

    if show_add:
        with st.expander("📝 Create New Customer Profile", expanded=True):
            with st.form("form_add_cust"):
                new_name = st.text_input("Customer Name *")
                new_disc = st.number_input("Default Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                new_gst = st.text_input("GSTIN Number")
                new_terms = st.text_input("Payment Terms", value="Net 30 Days")
                
                if st.form_submit_button("Save Customer"):
                    try:
                        CustomerService.create_customer(
                            name=new_name,
                            discount_percentage=new_disc,
                            gst_number=new_gst,
                            payment_terms=new_terms
                        )
                        trigger_toast(f"Created customer '{new_name}'!", icon="👤")
                        st.rerun()
                    except Exception as ex:
                        st.error(str(ex))

    customers = CustomerService.get_customers(search_query=c_search)
    if not customers:
        st.info("No customers found in directory.")
        return

    df_cust = []
    for c in customers:
        df_cust.append({
            "ID": c['id'],
            "Customer Name": c['name'],
            "Discount %": f"{c['discount_percentage']:.1f}%",
            "GSTIN": c['gst_number'] or "N/A",
            "Payment Terms": c['payment_terms'] or "Net 30 Days",
            "Updated At": c['updated_at'][:10]
        })

    st.dataframe(pd.DataFrame(df_cust), use_container_width=True, hide_index=True)
