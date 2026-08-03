import os
import streamlit as st
import pandas as pd
from app.services.import_service import ImportService
from app.models.database import query_db, execute_db
from app.ui.styles import render_html, trigger_toast

def render_settings_tab():
    render_html('<div class="section-head"><i class="fa-solid fa-sliders"></i> System Settings & Data Importers</div>')
    st.caption("Import inventory stock sheets, cost price lists, Google Sheets, or configure application tax defaults.")
    
    # 1. Tax & Configuration Defaults
    render_html('<div class="setting-section"><div class="setting-section-title"><i class="fa-solid fa-gear"></i> Default System Configuration</div></div>')
    
    cur_gst = query_db("SELECT value FROM APP_SETTINGS WHERE key = 'gst_rate'", one=True)
    gst_val = float(cur_gst['value']) if cur_gst else 18.0
    
    c_set1, c_set2 = st.columns([2, 1])
    with c_set1:
        new_gst_val = st.number_input("Default GST Rate (%)", min_value=0.0, max_value=50.0, value=gst_val, step=0.5, key="set_gst_rate")
    with c_set2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Update GST Configuration", use_container_width=True):
            execute_db("INSERT INTO APP_SETTINGS (key, value) VALUES ('gst_rate', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(new_gst_val),))
            trigger_toast(f"GST Rate updated to {new_gst_val}%!", icon="⚙️")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Excel Import Utilities
    render_html('<div class="setting-section"><div class="setting-section-title"><i class="fa-solid fa-file-excel"></i> Import Data Sheets (Excel / Web URL)</div></div>')
    
    tab_imp1, tab_imp2, tab_imp3 = st.tabs(["📦 Stock Group Reorder Sheet", "💰 Price Cost List Sheet", "🌐 Google Sheets Web Sync"])
    
    with tab_imp1:
        st.caption("Upload 'Stock Group Reorder Status.xlsx' to update inventory stock, purchase orders, sales due, and reorder levels.")
        up_stock = st.file_uploader("Choose Stock Excel File", type=["xlsx", "xls"], key="file_up_stock")
        if up_stock and st.button("🚀 Process Stock Import", type="primary", key="btn_imp_stock"):
            with st.spinner("Parsing stock reorder status sheet..."):
                res = ImportService.import_inventory(up_stock, filename=up_stock.name, imported_by="Streamlit Admin")
                if res['status'] in ('success', 'partial_success'):
                    trigger_toast(f"Imported {res['successful_records']:,} stock records!", icon="✅")
                    st.rerun()
                else:
                    st.error(f"Import failed: {', '.join(res['errors'])}")
                    
    with tab_imp2:
        st.caption("Upload 'PRICE LIST.xlsx' to update product cost price rates.")
        up_cost = st.file_uploader("Choose Cost List Excel File", type=["xlsx", "xls"], key="file_up_cost")
        if up_cost and st.button("🚀 Process Cost List Import", type="primary", key="btn_imp_cost"):
            with st.spinner("Parsing cost list price sheet..."):
                res = ImportService.import_costs(up_cost, filename=up_cost.name, imported_by="Streamlit Admin")
                if res['status'] in ('success', 'partial_success'):
                    trigger_toast(f"Imported {res['successful_records']:,} cost rates!", icon="✅")
                    st.rerun()
                else:
                    st.error(f"Import failed: {', '.join(res['errors'])}")
                    
    with tab_imp3:
        st.caption("Sync live inventory data from a published Google Spreadsheet or remote Excel URL.")
        web_url = st.text_input("Enter Spreadsheet Web URL", placeholder="https://docs.google.com/spreadsheets/d/.../edit", key="input_web_url")
        if web_url and st.button("⚡ Sync From Web URL", key="btn_sync_web"):
            with st.spinner("Downloading and parsing remote spreadsheet..."):
                res = ImportService.sync_from_web_url(web_url, imported_by="Web URL Sync")
                if res['status'] in ('success', 'partial_success'):
                    trigger_toast(f"Synced {res['successful_records']:,} items from Web URL!", icon="🌐")
                    st.rerun()
                else:
                    st.error(f"Web sync failed: {', '.join(res['errors'])}")
