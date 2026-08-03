import pandas as pd
import streamlit as st
from app.models.database import query_db, execute_db
from app.ui.styles import render_html, draw_metric_card, trigger_toast

def render_catalog_tab():
    render_html('<div class="section-head"><i class="fa-solid fa-boxes-stacked"></i> Master Product Catalog & Inventory</div>')
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        search_kw = st.text_input("🔍 Search Part Number or Make", placeholder="e.g. 209-120 or WAGO", key="cat_search")
    with col_c2:
        series_opts = ["All Series"] + [r['series'] for r in query_db("SELECT DISTINCT series FROM PRODUCTS WHERE series IS NOT NULL ORDER BY series") if r['series']]
        sel_series = st.selectbox("🏷️ Filter by Series", series_opts, key="cat_series_filter")
    with col_c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Clear Filter / Refresh Grid", use_container_width=True):
            st.rerun()

    # Query DB Products & Stock
    sql = """
        SELECT 
            p.id as product_id,
            p.part_number as "Part Number",
            p.series as "Series",
            p.make as "Make",
            p.packing_quantity as "Packing Qty",
            COALESCE(i.current_stock, 0.0) as "Current Stock (PCS)",
            COALESCE(c.price_per_100_pcs, 0.0) as "Cost / 100 Pcs (INR)",
            COALESCE(c.price_per_unit, 0.0) as "Rate / Pc (INR)"
        FROM PRODUCTS p
        LEFT JOIN INVENTORY i ON p.id = i.product_id
        LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
        WHERE 1=1
    """
    params = []
    if search_kw:
        sql += " AND (p.part_number LIKE ? OR p.make LIKE ?)"
        params.extend([f"%{search_kw}%", f"%{search_kw}%"])
    if sel_series != "All Series":
        sql += " AND p.series = ?"
        params.append(sel_series)
        
    sql += " ORDER BY p.part_number ASC LIMIT 10000"
    
    rows = query_db(sql, params)
    if not rows:
        st.info("No products found matching your search criteria.")
        return
        
    df_cat = pd.DataFrame([dict(r) for r in rows])
    
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
                execute_db(
                    "UPDATE INVENTORY SET current_stock = ?, last_updated = datetime('now') WHERE product_id = ?",
                    (float(row['Current Stock (PCS)']), p_id)
                )
                updated_cnt += 1
                
            # Check price change
            if float(row['Cost / 100 Pcs (INR)']) != float(orig['Cost / 100 Pcs (INR)']):
                new_p100 = float(row['Cost / 100 Pcs (INR)'])
                new_punit = new_p100 / 100.0
                execute_db("UPDATE PRODUCT_COSTS SET is_current = 0 WHERE product_id = ? AND is_current = 1", (p_id,))
                execute_db(
                    "INSERT INTO PRODUCT_COSTS (product_id, price_per_100_pcs, price_per_unit, effective_from, is_current) VALUES (?, ?, ?, datetime('now'), 1)",
                    (p_id, new_p100, new_punit)
                )
                updated_cnt += 1
                
        if updated_cnt > 0:
            trigger_toast(f"Successfully saved {updated_cnt} product modifications!", icon="💾")
            st.rerun()
        else:
            st.info("No modifications detected.")
