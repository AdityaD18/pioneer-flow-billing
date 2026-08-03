import pandas as pd
import streamlit as st
from app.providers import get_data_provider
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService
from app.ui.styles import render_html, draw_metric_card, trigger_toast

def render_catalog_tab():
    render_html('<div class="section-head"><i class="fa-solid fa-boxes-stacked"></i> Master Product Catalog & Inventory</div>')
    
    provider = get_data_provider()
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        search_kw = st.text_input("🔍 Search Part Number or Make", placeholder="e.g. 209-120 or WAGO", key="cat_search")
    with col_c2:
        stock_groups = provider.get_stock_groups()
        series_opts = ["All Series"] + [g.series_code for g in stock_groups if g.series_code]
        sel_series = st.selectbox("🏷️ Filter by Series", series_opts, key="cat_series_filter")
    with col_c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Clear Filter / Refresh Grid", use_container_width=True):
            st.rerun()

    # Retrieve Catalog StockItem Business Models via Provider
    stock_items = provider.get_stock_items(search_kw=search_kw, series=sel_series)
    if not stock_items:
        st.info("No products found matching your search criteria.")
        return
        
    df_cat = pd.DataFrame([item.to_dict() for item in stock_items])
    
    # Render Data Editor
    st.caption("Double-click any cell to edit Stock levels or Cost Prices directly inline.")
    edited_df = st.data_editor(
        df_cat,
        key="cat_data_editor",
        disabled=["product_id", "Part Number", "Series", "Make", "Packing Qty", "Rate / Pc (INR)"],
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("💾 Save Product Updates", type="primary", key="btn_save_catalog"):
        updated_cnt = 0
        for idx, row in edited_df.iterrows():
            orig = df_cat.iloc[idx]
            p_id = row['product_id']
            
            # Check stock change
            if float(row['Current Stock (PCS)']) != float(orig['Current Stock (PCS)']):
                InventoryService.update_product_stock(p_id, float(row['Current Stock (PCS)']))
                updated_cnt += 1
                
            # Check price change
            if float(row['Cost / 100 Pcs (INR)']) != float(orig['Cost / 100 Pcs (INR)']):
                ProductService.update_product_cost_price(p_id, float(row['Cost / 100 Pcs (INR)']))
                updated_cnt += 1
                
        if updated_cnt > 0:
            trigger_toast(f"Successfully saved {updated_cnt} product modifications!", icon="💾")
            st.rerun()
        else:
            st.info("No modifications detected.")
