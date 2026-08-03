import pandas as pd
import streamlit as st
from app.repositories.inventory_repository import InventoryRepository
from app.ui.styles import render_html

def render_stock_status_tab():
    render_html('<div class="section-head"><i class="fa-solid fa-clipboard-list"></i> Stock Group Reorder Status Sheet</div>')
    st.caption("Live Inventory Reorder Analysis synced from Excel Stock Sheets")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        s_search = st.text_input("🔍 Filter Stock Sheet Part Number", key="stock_sheet_search")
    with col_s2:
        only_reorder = st.checkbox("⚠️ Show Only Items Needing Reorder (Shortfall > 0)", key="chk_only_reorder")
        
    stock_rows = InventoryRepository.get_stock_sheet(search_kw=s_search, only_reorder=only_reorder)
    if not stock_rows:
        st.info("No stock records match the selected filter criteria.")
        return
        
    df_stock = pd.DataFrame(stock_rows)
    
    st.dataframe(
        df_stock,
        use_container_width=True,
        hide_index=True
    )
