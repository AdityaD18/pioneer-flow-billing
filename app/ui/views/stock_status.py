import pandas as pd
import streamlit as st
from app.models.database import query_db
from app.ui.styles import render_html

def render_stock_status_tab():
    render_html('<div class="section-head"><i class="fa-solid fa-clipboard-list"></i> Stock Group Reorder Status Sheet</div>')
    st.caption("Live Inventory Reorder Analysis synced from Excel Stock Sheets")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        s_search = st.text_input("🔍 Filter Stock Sheet Part Number", key="stock_sheet_search")
    with col_s2:
        only_reorder = st.checkbox("⚠️ Show Only Items Needing Reorder (Shortfall > 0)", key="chk_only_reorder")
        
    sql = """
        SELECT 
            p.part_number as "Part Number",
            p.make as "Make",
            COALESCE(i.current_stock, 0.0) as "Closing Stock",
            COALESCE(i.purc_orders_pending, 0.0) as "Purc Orders Pending",
            COALESCE(i.sale_orders_due, 0.0) as "Sale Orders Due",
            COALESCE(i.nett_available, 0.0) as "Nett Available",
            COALESCE(i.reorder_level, 0.0) as "Reorder Level",
            COALESCE(i.short_fall, 0.0) as "Short Fall",
            COALESCE(i.min_reorder_qty, 0.0) as "Min Reorder Qty",
            COALESCE(i.order_to_be_placed, 0.0) as "Order To Be Placed",
            i.last_updated as "Last Updated"
        FROM INVENTORY i
        JOIN PRODUCTS p ON i.product_id = p.id
        WHERE 1=1
    """
    params = []
    if s_search:
        sql += " AND p.part_number LIKE ?"
        params.append(f"%{s_search}%")
    if only_reorder:
        sql += " AND (i.short_fall > 0 OR i.order_to_be_placed > 0)"
        
    sql += " ORDER BY p.part_number ASC LIMIT 10000"
    
    rows = query_db(sql, params)
    if not rows:
        st.info("No stock records match the selected filter criteria.")
        return
        
    df_stock = pd.DataFrame([dict(r) for r in rows])
    
    st.dataframe(
        df_stock,
        use_container_width=True,
        hide_index=True
    )
