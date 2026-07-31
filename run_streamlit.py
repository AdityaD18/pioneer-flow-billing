import os
import sys
import pandas as pd
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
import textwrap

# Ensure project modules are on path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.models.database import init_db, query_db, execute_db
from app.services.import_service import ImportService
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.services.invoice_service import InvoiceService
from app.services.quotation_service import QuotationService

# 1. Page Configuration
st.set_page_config(
    page_title="PIONEER FLOW - Billing Automation",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize database
init_db()

# 2. Inject Premium Custom Styling (Glassmorphism Dark Theme + Layout optimizations)
IS_DARK = True # Force dark aesthetic for that premium WOW factor

CSS_STYLE = """
<style>
:root {
    --bg: #09090b;
    --bg-subtle: #0f0f13;
    --card: #121217;
    --card-hover: #171720;
    --border: rgba(255,255,255,0.08);
    --border-subtle: rgba(255,255,255,0.04);
    --text: #fafafa;
    --text-muted: #71717a;
    --text-dim: #52525b;
    --accent: #7c3aed;
    --accent-hover: #6d28d9;
    --cyan: #06b6d4;
    --green: #10b981;
    --green-muted: rgba(16,185,129,0.12);
    --red: #ef4444;
    --red-muted: rgba(239,68,68,0.12);
    --amber: #f59e0b;
    --amber-muted: rgba(245,158,11,0.12);
    --radius: 10px;
}

/* Hide Streamlit components */
header[data-testid="stHeader"], footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"], .stDeployButton,
div[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container, section[data-testid="stMain"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
}

.block-container {
    padding: 1.5rem 2rem 2rem !important;
    max-width: 1400px !important;
}

/* Metric Cards style */
.metric-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem 1.4rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    margin-bottom: 1rem;
}
.metric-label { font-size: 0.8rem; color: var(--text-muted); font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
.metric-value { font-size: 1.85rem; font-weight: 700; color: var(--text); margin-top: 0.25rem; }
.metric-footer { font-size: 0.72rem; color: var(--cyan); margin-top: 0.5rem; display: flex; align-items: center; gap: 4px; }

/* Custom HTML tables for timelines and details */
.data-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.825rem;
    margin-top: 0.5rem;
}
.data-table th {
    text-align: left;
    padding: 0.65rem 0.85rem;
    color: var(--text-muted);
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid var(--border);
    background-color: rgba(255,255,255,0.02);
}
.data-table td {
    padding: 0.7rem 0.85rem;
    color: var(--text);
    border-bottom: 1px solid var(--border-subtle);
}
.data-table tbody tr:hover {
    background-color: rgba(255,255,255,0.02);
}

/* Badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
}
.badge-green { color: var(--green); background: var(--green-muted); }
.badge-red { color: var(--red); background: var(--red-muted); }
.badge-amber { color: var(--amber); background: var(--amber-muted); }
.badge-blue { color: var(--cyan); background: rgba(6,182,212,0.12); }

/* Header Brand container */
.brand-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
}
.brand-title {
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: 1px;
}
.brand-title span {
    color: var(--accent);
}
.brand-subtitle {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: 2px;
}

/* Tabs overriding styling */
button[data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.25rem !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    transition: all 0.3s ease;
}
button[data-baseweb="tab"]:hover {
    color: var(--text) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--text) !important;
    background: rgba(124,58,237,0.15) !important;
    border-color: var(--accent) !important;
}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {
    display: none !important;
}
[data-baseweb="tab-list"] {
    gap: 6px !important;
    background: var(--bg-subtle) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    margin-bottom: 1.5rem;
}
</style>
"""
st.markdown(CSS_STYLE, unsafe_allow_html=True)

# 3. Helpers for layout components
def render_html(html_content):
    st.markdown(textwrap.dedent(html_content), unsafe_allow_html=True)

def draw_metric_card(label, value, footer_text=None, icon_class="fa-solid fa-chart-line"):
    footer_html = f'<div class="metric-footer"><i class="{icon_class}"></i> {footer_text}</div>' if footer_text else ""
    render_html(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {footer_html}
    </div>
    """)

def generate_invoice_html(invoice_data):
    """Generates the clean printable tax invoice HTML with direct styles embedded."""
    # Safety mapping for quotations to prevent KeyError
    if 'invoice_number' not in invoice_data:
        invoice_data['invoice_number'] = invoice_data.get('quotation_number', '')
    if 'invoice_date' not in invoice_data:
        c_at = invoice_data.get('created_at', '')
        invoice_data['invoice_date'] = c_at[:10] if len(c_at) >= 10 else c_at

    order = invoice_data['order']
    subtotal = order['subtotal']
    gst_rate = order['gst_rate']
    gst_amount = order['gst_amount']
    half_gst = gst_rate / 2.0
    half_gst_amount = gst_amount / 2.0
    grand_total = order['grand_total']
    
    inv_num = invoice_data['invoice_number']
    is_qtn = inv_num.startswith("QTN")
    doc_title = "PROFORMA QUOTATION" if is_qtn else "TAX INVOICE"
    num_lbl = "Quotation No:" if is_qtn else "Invoice No:"
    
    items_rows = ""
    for idx, item in enumerate(invoice_data['items']):
        items_rows += f"""
        <tr>
            <td>{idx + 1}</td>
            <td><strong>{item['part_number_snapshot']}</strong></td>
            <td>WAGO</td>
            <td>PCS</td>
            <td style="text-align: right;">{int(item['quantity'])}</td>
            <td style="text-align: right;">₹{item['unit_price']:.2f}</td>
            <td style="text-align: right;">{item['discount_percentage']:.1f}%</td>
            <td style="text-align: right;">₹{item['line_total']:.2f}</td>
        </tr>
        """
        
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{doc_title} {invoice_data['invoice_number']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; color: #111; padding: 20px; background-color: #fff; }}
            .sheet {{ max-width: 800px; margin: 0 auto; border: 1px solid #ccc; padding: 30px; border-radius: 6px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            .header-row {{ display: flex; justify-content: space-between; align-items: flex-start; }}
            .brand h2 {{ margin: 0; font-size: 20px; font-weight: bold; color: #111; }}
            .brand p {{ margin: 3px 0; font-size: 12px; color: #555; line-height: 1.4; }}
            .doc-title {{ text-align: right; }}
            .doc-title h1 {{ margin: 0 0 10px 0; font-size: 24px; font-weight: bold; color: #7c3aed; }}
            .badge-row {{ display: flex; justify-content: flex-end; gap: 10px; font-size: 12px; margin-bottom: 3px; }}
            .badge-lbl {{ font-weight: bold; color: #555; }}
            .divider {{ border: none; border-top: 1.5px solid #eee; margin: 20px 0; }}
            .bill-to h4 {{ margin: 0 0 5px 0; font-size: 12px; color: #6b7280; text-transform: uppercase; }}
            .bill-to h3 {{ margin: 0 0 5px 0; font-size: 16px; font-weight: bold; }}
            .bill-to p {{ margin: 2px 0; font-size: 13px; color: #444; }}
            .items-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            .items-table th {{ background-color: #f3f4f6; color: #374151; font-weight: bold; font-size: 11px; text-transform: uppercase; border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; }}
            .items-table td {{ padding: 6px 10px; border: 1px solid #d1d5db; font-size: 12px; }}
            .items-table tr:nth-child(even) {{ background-color: #f9fafb; }}
            .totals-row {{ display: flex; justify-content: space-between; margin-top: 20px; }}
            .bank {{ width: 45%; border: 1px solid #eee; border-radius: 6px; padding: 12px; font-size: 11px; color: #555; line-height: 1.5; }}
            .bank h4 {{ margin: 0 0 5px 0; color: #111; font-weight: bold; }}
            .totals-tbl {{ width: 45%; border-collapse: collapse; }}
            .totals-tbl td {{ padding: 5px; font-size: 13px; color: #444; }}
            .totals-tbl tr.grand-row td {{ font-weight: bold; font-size: 16px; color: #111; border-top: 2px solid #111; padding-top: 8px; }}
            .sig-row {{ display: flex; justify-content: space-between; align-items: flex-end; margin-top: 40px; }}
            .decl {{ width: 50%; font-size: 10px; color: #888; line-height: 1.4; }}
            .sig-block {{ width: 40%; text-align: center; font-size: 12px; }}
            .sig-space {{ height: 50px; border-bottom: 1px solid #ccc; margin-bottom: 5px; }}
            @media print {{
                body {{ padding: 0; }}
                .sheet {{ border: none; box-shadow: none; padding: 0; max-width: 100%; }}
                .items-table th {{ border: 1.5px solid #000; background-color: #eaeaea !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                .items-table td {{ border: 1.5px solid #000; }}
                .bank {{ border: 1.5px solid #000; }}
                .totals-tbl tr.grand-row td {{ border-top: 2.5px solid #000; }}
            }}
        </style>
    </head>
    <body>
        <div class="sheet">
            <div class="header-row">
                <div class="brand">
                    <h2>PIONEER TECHNOLOGY</h2>
                    <p>Sai Datta Reality, Survey No 452/1/1/10,<br>Alankapuram Road, Tapkir Nagar, Bhosari, Pune-412105</p>
                    <p>Email: rajesh@pioneerautomation.in | UDYAM-MH-26-0071108</p>
                </div>
                <div class="doc-title">
                    <h1>{doc_title}</h1>
                    <div class="badge-row">
                        <div class="badge-lbl">{num_lbl}</div>
                        <div>{invoice_data['invoice_number']}</div>
                    </div>
                    <div class="badge-row">
                        <div class="badge-lbl">Date:</div>
                        <div>{invoice_data['invoice_date']}</div>
                    </div>
                    <div class="badge-row">
                        <div class="badge-lbl">Order Ref:</div>
                        <div>{order['order_number']}</div>
                    </div>
                </div>
            </div>
            
            <div class="divider"></div>
            
            <div class="bill-to">
                <h4>BILL TO:</h4>
                <h3>{order['customer_name_snapshot']}</h3>
                <p><strong>GSTIN:</strong> {order['customer_gst_snapshot'] or 'N/A'}</p>
                <p><strong>Payment Terms:</strong> {order['customer_terms_snapshot'] or 'Due on Receipt'}</p>
            </div>
            
            <table class="items-table">
                <thead>
                    <tr>
                        <th>Sr No.</th>
                        <th>Part Number / Item Code</th>
                        <th>Make</th>
                        <th>Packing Qty</th>
                        <th style="text-align: right;">Qty</th>
                        <th style="text-align: right;">Rate / 100 Pcs</th>
                        <th style="text-align: right;">Dis. %</th>
                        <th style="text-align: right;">Net Value</th>
                    </tr>
                </thead>
                <tbody>
                    {items_rows}
                </tbody>
            </table>
            
            <div class="totals-row">
                <div class="bank">
                    <h4>Bank Details:</h4>
                    <p>Bank Name: HDFC Bank Ltd</p>
                    <p>A/C No: 50200067645167</p>
                    <p>IFSC Code: HDFC0000104</p>
                    <p>Branch: Bhosari, Pune</p>
                </div>
                <table class="totals-tbl">
                    <tr>
                        <td>Subtotal (Excl. GST):</td>
                        <td style="text-align: right;">₹{subtotal:.2f}</td>
                    </tr>
                    <tr>
                        <td>CGST ({half_gst:.1f}%):</td>
                        <td style="text-align: right;">₹{half_gst_amount:.2f}</td>
                    </tr>
                    <tr>
                        <td>SGST ({half_gst:.1f}%):</td>
                        <td style="text-align: right;">₹{half_gst_amount:.2f}</td>
                    </tr>
                    <tr class="grand-row">
                        <td>Grand Total:</td>
                        <td style="text-align: right;">₹{grand_total:.2f}</td>
                    </tr>
                </table>
            </div>
            
            <div class="sig-row">
                <div class="decl">
                    <p><strong>Declaration:</strong> We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.</p>
                </div>
                <div class="sig-block">
                    <p>For PIONEER TECHNOLOGY</p>
                    <div class="sig-space"></div>
                    <p style="color: #555; font-size: 11px;">Authorized Signatory</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

# 4. Brand Header Layout
st.markdown("""
<div class="brand-container">
    <div>
        <div class="brand-title">PIONEER <span>FLOW</span></div>
        <div class="brand-subtitle">Streamlit Session Manager &bull; Mechanical Billing MVP</div>
    </div>
    <div style="font-size: 0.8rem; color: #71717a; text-align: right;">
        Status: <span class="badge badge-green">Online</span><br>
        Relational Engine: <span class="badge badge-blue">SQLite3</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 5. Core Navigation Tabs
t_dash, t_imports, t_catalog, t_inventory, t_customers, t_invoice, t_quotation, t_history, t_manual, t_settings = st.tabs([
    "📊 Dashboard", 
    "📁 Import Sheets", 
    "📦 Product Catalog", 
    "🔍 Available Inventory",
    "👥 Customers", 
    "📝 New Invoice", 
    "📄 New Quotation",
    "📜 History Ledger",
    "➕ Manual Entry",
    "⚙️ Settings"
])

# Toast persistence manager
if "toast_msg" not in st.session_state:
    st.session_state.toast_msg = None
if "toast_icon" not in st.session_state:
    st.session_state.toast_icon = "ℹ️"

if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg, icon=st.session_state.toast_icon)
    st.session_state.toast_msg = None

def trigger_toast(message, icon="ℹ️"):
    st.session_state.toast_msg = message
    st.session_state.toast_icon = icon

# Initialize session states for UI controllers
if "invoice_items" not in st.session_state:
    st.session_state.invoice_items = []
if "quotation_items" not in st.session_state:
    st.session_state.quotation_items = []
if "prod_search_val" not in st.session_state:
    st.session_state.prod_search_val = ""
if "cust_search_val" not in st.session_state:
    st.session_state.cust_search_val = ""
if "last_invoice_generated" not in st.session_state:
    st.session_state.last_invoice_generated = None
if "last_quotation_generated" not in st.session_state:
    st.session_state.last_quotation_generated = None

# --- 24/7 BACKGROUND EXCEL AUTO-SYNC DAEMON ---
if not hasattr(st, "_background_sync_thread_started"):
    st._background_sync_thread_started = True
    import threading
    import time
    
    def sync_loop():
        while True:
            try:
                from app.models.database import get_db_connection
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT key, value FROM APP_SETTINGS WHERE key IN ('stock_excel_url', 'auto_sync_interval', 'auto_sync_enabled')")
                rows = cur.fetchall()
                conn.close()
                
                settings = {r['key']: r['value'] for r in rows}
                url = settings.get('stock_excel_url')
                interval = 15.0
                try:
                    interval = float(settings.get('auto_sync_interval', 15.0))
                except:
                    pass
                enabled = settings.get('auto_sync_enabled', '0') == '1'
                
                if enabled and url and url.strip():
                    from app.services.import_service import ImportService
                    ImportService.sync_from_web_url(url, imported_by="24/7 Daemon Sync")
                
                time.sleep(max(60, interval * 60))
            except Exception:
                time.sleep(60)

    t = threading.Thread(target=sync_loop, daemon=True, name="StockExcelBackgroundSync")
    t.start()


# --- TAB: DASHBOARD ---
with t_dash:
    # Fetch statistics
    prod_count = query_db("SELECT COUNT(*) as c FROM PRODUCTS", one=True)['c']
    cust_count = query_db("SELECT COUNT(*) as c FROM CUSTOMERS", one=True)['c']
    inv_count = query_db("SELECT COUNT(*) as c FROM INVOICES", one=True)['c']
    
    inv_import = query_db("SELECT imported_at FROM IMPORT_LOG WHERE import_type='inventory' ORDER BY imported_at DESC LIMIT 1", one=True)
    last_inventory = new_date = datetime.fromisoformat(inv_import['imported_at']).strftime('%b %d, %Y %H:%M') if inv_import else "Never"
    
    price_import = query_db("SELECT imported_at FROM IMPORT_LOG WHERE import_type='cost' ORDER BY imported_at DESC LIMIT 1", one=True)
    last_price = datetime.fromisoformat(price_import['imported_at']).strftime('%b %d, %Y %H:%M') if price_import else "Never"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        draw_metric_card("Total Products", f"{prod_count:,}", f"Last Price: {last_price}", "fa-solid fa-barcode")
    with col2:
        draw_metric_card("Total Customers", f"{cust_count:,}", "Active billing registry", "fa-solid fa-users")
    with col3:
        draw_metric_card("Total Invoices", f"{inv_count:,}", "Generated ledger entries", "fa-solid fa-receipt")
    with col4:
        draw_metric_card("Last Inventory Sync", last_inventory, "Upload timeline sync date", "fa-solid fa-clock")



# --- TAB: IMPORTS ---
with t_imports:
    st.markdown("### Upload Annual Price List")
    
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Import Price List Sheet")
    st.write("Upload the Excel workbook (.xlsx, .xls) containing the pricing list sheet. Note: Warehouse stock levels are auto-synchronized from your cloud Excel connection.")
    
    price_file = st.file_uploader("Select Price List Excel Workbook", type=["xlsx", "xls"], key="price_file")
    
    cost_sheet = st.text_input("Price List Sheet Name", "PRICE LIST", key="cost_sheet")
        
    if st.button("Run Price List Import", use_container_width=True, type="primary"):
        if price_file is None:
            st.error("Please upload an Excel workbook first.")
        else:
            # Save temp file
            temp_path = os.path.join("uploads", price_file.name)
            os.makedirs("uploads", exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(price_file.getvalue())
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Process Costs
            status_text.text("Importing product pricing lists...")
            progress_bar.progress(50)
            cost_res = ImportService.import_costs(temp_path, sheet_name=cost_sheet, filename=price_file.name)
            
            progress_bar.progress(100)
            status_text.text("Import finished.")
            
            # clean up temp file
            try: os.remove(temp_path)
            except: pass
            
            if cost_res['status'] == 'failed':
                st.error(f"Price list upload failed: {', '.join(cost_res['errors'])}")
            else:
                trigger_toast(f"Price list sync successful! Loaded {cost_res['successful_records']} items.", icon="✅")
                st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)



# --- TAB: PRODUCT CATALOG ---
with t_catalog:
    st.markdown("### Part Catalog Inventory")
    q_search = st.text_input("Search catalog parts (Part Number, Make, Series)", placeholder="e.g. 206-804")
    
    if q_search:
        search_str = f"%{q_search.strip()}%"
        products_list = query_db(
            """SELECT p.*, i.current_stock, c.price_per_100_pcs 
               FROM PRODUCTS p
               LEFT JOIN INVENTORY i ON p.id = i.product_id
               LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
               WHERE p.part_number LIKE ? OR p.part_name LIKE ? OR p.make LIKE ? OR p.series LIKE ?
               ORDER BY p.part_number ASC LIMIT 100""",
            (search_str, search_str, search_str, search_str)
        )
    else:
        products_list = query_db(
            """SELECT p.*, i.current_stock, c.price_per_100_pcs 
               FROM PRODUCTS p
               LEFT JOIN INVENTORY i ON p.id = i.product_id
               LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
               ORDER BY p.part_number ASC LIMIT 50"""
        )
        
    if len(products_list) == 0:
        st.info("No matching products found in catalog database.")
    else:
        # Load as pandas df
        display_data = []
        for p in products_list:
            display_data.append({
                "Part Number": p["part_number"],
                "Make": p["make"] or "-",
                "Series": p["series"] or "-",
                "Packing Qty": p["packing_quantity"],
                "Unit": p["unit"],
                "Stock": p["current_stock"] if p["current_stock"] is not None else 0.0,
                "Price per 100 Pcs": f"₹{p['price_per_100_pcs']:.2f}" if p["price_per_100_pcs"] is not None else "₹0.00"
            })
        st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)

# --- TAB: AVAILABLE INVENTORY ---
with t_inventory:
    st.markdown("### 🔍 Stock Group Reorder Status & Inventory")
    
    settings = OrderService.get_settings()
    excel_url = settings.get('stock_excel_url', '')
    sync_enabled = settings.get('auto_sync_enabled', '0') == '1'
    
    # 1. Fetch available stock KPIs
    stock_stats = query_db(
        """SELECT 
             COUNT(CASE WHEN current_stock > 0 THEN 1 END) as active_skus,
             SUM(CASE WHEN current_stock > 0 THEN current_stock ELSE 0 END) as total_stock,
             COUNT(CASE WHEN short_fall > 0 THEN 1 END) as shortfall_skus,
             SUM(CASE WHEN current_stock > 0 THEN current_stock * (COALESCE(c.price_per_100_pcs, 0) / 100.0) ELSE 0 END) as total_value
           FROM INVENTORY i
           LEFT JOIN PRODUCT_COSTS c ON i.product_id = c.product_id AND c.is_current = 1""",
        one=True
    )
    
    # Sync status header
    if excel_url:
        st.caption(f"☁️ Cloud Excel Sync: Linked to `{excel_url[:70]}...` (Auto-Sync: {'ON' if sync_enabled else 'OFF'})")
    else:
        st.caption("⚠️ No Cloud Excel Sync linked. Setup in settings to update inventory automatically.")
        
    # KPIs layout
    col_st1, col_st2, col_st3, col_st4 = st.columns(4)
    with col_st1:
        draw_metric_card("Stocked SKUs", f"{stock_stats['active_skus'] or 0:,}", "Items with stock > 0", "fa-solid fa-boxes-stacked")
    with col_st2:
        draw_metric_card("Total Stock", f"{int(stock_stats['total_stock'] or 0):,} pcs", "Total pieces in warehouse", "fa-solid fa-layer-group")
    with col_st3:
        draw_metric_card("Shortfall Items", f"{stock_stats['shortfall_skus'] or 0:,}", "SKUs below reorder level", "fa-solid fa-triangle-exclamation")
    with col_st4:
        draw_metric_card("Asset Value", f"₹{stock_stats['total_value'] or 0:,.2f}", "Calculated via current cost rates", "fa-solid fa-indian-rupee-sign")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Search & Filters
    col_inv_s1, col_inv_s2 = st.columns([2, 1])
    with col_inv_s1:
        q_inv_search = st.text_input("Search Inventory (Part Number, Make, Series)", placeholder="e.g. 206-118", key="inv_stock_search_input")
    with col_inv_s2:
        filter_status = st.selectbox("Stock Level Filter", ["Show All", "Stocked Only (>0)", "Below Reorder Level (Shortfall)"])
        
    # Build query
    sql = """SELECT p.part_number, p.part_name, p.make, p.series, i.*, c.price_per_100_pcs 
             FROM INVENTORY i
             JOIN PRODUCTS p ON i.product_id = p.id
             LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
             WHERE 1=1"""
    params = []
    
    if q_inv_search:
        search_str = f"%{q_inv_search.strip()}%"
        sql += " AND (p.part_number LIKE ? OR p.part_name LIKE ? OR p.make LIKE ? OR p.series LIKE ?)"
        params.extend([search_str, search_str, search_str, search_str])
        
    if filter_status == "Stocked Only (>0)":
        sql += " AND i.current_stock > 0"
    elif filter_status == "Below Reorder Level (Shortfall)":
        sql += " AND i.short_fall > 0"
        
    sql += " ORDER BY i.short_fall DESC, i.current_stock DESC, p.part_number ASC LIMIT 250"
    
    stocked_items = query_db(sql, tuple(params))
    
    if len(stocked_items) == 0:
        st.info("No stock records found matching your filters.")
    else:
        df_display = []
        for p in stocked_items:
            df_display.append({
                "Item Code": p['part_number'],
                "Closing Stock (PCS)": int(p['current_stock'] or 0),
                "Purc Orders Pending": int(p['purc_orders_pending'] or 0),
                "Sale Orders Due": int(p['sale_orders_due'] or 0),
                "Nett Available": int(p['nett_available'] or 0),
                "Re-order Level": int(p['reorder_level'] or 0),
                "Short fall": int(p['short_fall'] or 0),
                "Min Reorder Qty": int(p['min_reorder_qty'] or 0),
                "Order to be Placed": int(p['order_to_be_placed'] or 0)
            })
            
        st.dataframe(
            pd.DataFrame(df_display), 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Item Code": st.column_config.TextColumn("Item Code", width="medium"),
                "Closing Stock (PCS)": st.column_config.NumberColumn("Closing Stock", format="%d"),
                "Purc Orders Pending": st.column_config.NumberColumn("Purc Pending", format="%d"),
                "Sale Orders Due": st.column_config.NumberColumn("Sale Due", format="%d"),
                "Nett Available": st.column_config.NumberColumn("Nett Available", format="%d"),
                "Re-order Level": st.column_config.NumberColumn("Re-order Level", format="%d"),
                "Short fall": st.column_config.NumberColumn("Short fall", format="%d"),
                "Min Reorder Qty": st.column_config.NumberColumn("Min Reorder Qty", format="%d"),
                "Order to be Placed": st.column_config.NumberColumn("Order to be Placed", format="%d")
            }
        )

# --- TAB: CUSTOMERS ---
with t_customers:
    st.markdown("### Customer Billing Profiles")
    c_form, c_table = st.columns([1, 2])
    
    customers = CustomerService.get_customers()
    
    with c_form:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        # Add a selector to edit existing or create new
        edit_options = ["- Add New Customer -"] + [c['name'] for c in customers]
        selected_to_edit = st.selectbox("Action / Select Profile to Edit", edit_options)
        
        # Populate form
        editing_customer = None
        if selected_to_edit != "- Add New Customer -":
            editing_customer = CustomerService.get_customer_by_name(selected_to_edit)
            
        form_name = st.text_input("Customer Company Name *", value=editing_customer['name'] if editing_customer else "")
        form_discount = st.number_input("Default Discount %", min_value=0.0, max_value=100.0, step=0.01, value=editing_customer['discount_percentage'] if editing_customer else 0.0)
        form_gst = st.text_input("GSTIN Number", value=editing_customer['gst_number'] or "" if editing_customer else "")
        form_terms = st.text_input("Payment Terms", value=editing_customer['payment_terms'] or "" if editing_customer else "", placeholder="e.g. Net 30 Days")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("Save Billing Profile", use_container_width=True):
                if not form_name:
                    st.error("Customer Name is mandatory.")
                else:
                    try:
                        if editing_customer:
                            # Update
                            CustomerService.update_customer(editing_customer['id'], form_name, form_discount, form_gst, form_terms)
                            trigger_toast(f"Customer '{form_name}' updated successfully!", icon="👥")
                        else:
                            # Create
                            CustomerService.create_customer(form_name, form_discount, form_gst, form_terms)
                            trigger_toast(f"New customer '{form_name}' registered successfully!", icon="🎉")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
        with col_s2:
            if editing_customer:
                if st.button("Delete Profile", type="primary", use_container_width=True):
                    try:
                        CustomerService.delete_customer(editing_customer['id'])
                        trigger_toast("Customer profile deleted.", icon="🗑️")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            else:
                if st.button("Clear Form", use_container_width=True):
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with c_table:
        # If editing a customer, display their specific invoice history
        if editing_customer:
            st.markdown(f"### Invoicing History: {editing_customer['name']}")
            cust_invoices = query_db(
                """SELECT i.*, o.grand_total, o.order_number 
                   FROM INVOICES i
                   JOIN ORDERS o ON i.order_id = o.id
                   WHERE o.customer_id = ?
                   ORDER BY i.invoice_date DESC""",
                (editing_customer['id'],)
            )
            if len(cust_invoices) == 0:
                st.info("No invoices have been generated for this customer yet.")
            else:
                inv_rows = ""
                for inv in cust_invoices:
                    inv_rows += f"<tr><td><strong>{inv['invoice_number']}</strong></td><td>{inv['invoice_date']}</td><td>{inv['order_number']}</td><td><strong>₹{inv['grand_total']:.2f}</strong></td></tr>"
                render_html(f"""
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Invoice No</th>
                            <th>Billing Date</th>
                            <th>Order Ref</th>
                            <th>Grand Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {inv_rows}
                    </tbody>
                </table>
                """)
            st.markdown("<br><hr><br>", unsafe_allow_html=True)
            
        st.markdown("### Customer Registry")
        if len(customers) == 0:
            st.info("No customers profiles registered yet.")
        else:
            cust_rows = ""
            for c in customers:
                gst_val = c['gst_number'] or "-"
                terms_val = c['payment_terms'] or "-"
                cust_rows += f"<tr><td><strong>{c['name']}</strong></td><td>{c['discount_percentage']:.2f}%</td><td>{gst_val}</td><td>{terms_val}</td></tr>"
            render_html(f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Customer / Company Name</th>
                        <th>Default Discount</th>
                        <th>GSTIN Number</th>
                        <th>Payment Terms</th>
                    </tr>
                </thead>
                <tbody>
                    {cust_rows}
                </tbody>
            </table>
            """)

# --- TAB: NEW INVOICE ---
with t_invoice:
    st.markdown("### Interactive Invoice Generator")
    
    # Left column for Item additions (Catalog Item Details)
    # Right column for Customer & Billing Details + Totals (Live totals & settings)
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.subheader("1. Enter / Paste Line Items")
        st.write("Copy and paste cells (Part Number and Quantity columns) from Excel directly into the table below.")
        
        # Load all products for validation and registration
        all_prods = query_db(
            """SELECT p.*, i.current_stock, c.price_per_100_pcs 
               FROM PRODUCTS p
               LEFT JOIN INVENTORY i ON p.id = i.product_id
               LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
               ORDER BY p.part_number ASC"""
        )
        
        # We present an editable grid
        if "inv_bulk_input_df" not in st.session_state:
            st.session_state.inv_bulk_input_df = pd.DataFrame(
                [{"Part Number": "", "Quantity": 1}],
                columns=["Part Number", "Quantity"]
            )
            
        edited_inv_df = st.data_editor(
            st.session_state.inv_bulk_input_df,
            num_rows="dynamic",
            column_config={
                "Part Number": st.column_config.TextColumn("Part Number / Item Code", width="medium"),
                "Quantity": st.column_config.NumberColumn("Quantity (PCS)", min_value=1, step=1)
            },
            use_container_width=True,
            key="bulk_inv_data_editor"
        )
        
        # Add buttons to process grid
        col_grid_btn1, col_grid_btn2 = st.columns([1, 1])
        with col_grid_btn1:
            if st.button("Add Items to Invoice Draft", type="primary", use_container_width=True, key="bulk_add_to_inv_draft_btn"):
                # Clean up empty rows
                non_empty_rows = edited_inv_df[edited_inv_df["Part Number"].astype(str).str.strip() != ""]
                if len(non_empty_rows) == 0:
                    st.error("No valid items entered in the grid.")
                else:
                    db_prods = {p['part_number'].strip().lower(): p for p in all_prods}
                    added_count = 0
                    registered_count = 0
                    
                    for idx, row in non_empty_rows.iterrows():
                        part_no = str(row["Part Number"]).strip()
                        part_no_clean = part_no.replace('"', '').replace("'", "")
                        
                        try:
                            qty = int(float(str(row["Quantity"]).replace(',', '').strip()))
                        except:
                            qty = 1
                            
                        key_lower = part_no_clean.lower()
                        
                        # Resolve product
                        if key_lower in db_prods:
                            matched_prod = db_prods[key_lower]
                            product_id = matched_prod['id']
                            current_stock = matched_prod['current_stock'] if matched_prod['current_stock'] is not None else 0.0
                            unit_price_100 = matched_prod['price_per_100_pcs'] if matched_prod['price_per_100_pcs'] is not None else 0.0
                        else:
                            # Auto register
                            series = part_no_clean.split('-')[0] if '-' in part_no_clean else None
                            conn_ins = get_db_connection()
                            cur_ins = conn_ins.cursor()
                            try:
                                cur_ins.execute("INSERT INTO PRODUCTS (part_number, part_name, series, make) VALUES (?, ?, ?, ?)",
                                                (part_no_clean, part_no_clean, series, 'WAGO'))
                                product_id = cur_ins.lastrowid
                                cur_ins.execute("INSERT INTO INVENTORY (product_id, current_stock) VALUES (?, 0.0)", (product_id,))
                                cur_ins.execute("INSERT INTO PRODUCT_COSTS (product_id, price_per_100_pcs, price_per_unit, is_current) VALUES (?, 0.0, 0.0, 1)", (product_id,))
                                conn_ins.commit()
                                registered_count += 1
                            except:
                                product_id = None
                            finally:
                                conn_ins.close()
                                
                            current_stock = 0.0
                            unit_price_100 = 0.0
                            
                        if product_id is not None:
                            # Check if already in draft
                            found = False
                            for i in st.session_state.invoice_items:
                                if i['product_id'] == product_id:
                                    i['quantity'] += qty
                                    found = True
                                    break
                            if not found:
                                st.session_state.invoice_items.append({
                                    "product_id": product_id,
                                    "part_number": part_no_clean,
                                    "part_name": part_no_clean,
                                    "quantity": qty,
                                    "current_stock": current_stock,
                                    "unit_price_100": unit_price_100,
                                    "discount_percentage": None
                                })
                            added_count += 1
                            
                    if added_count > 0:
                        msg = f"Added {added_count} items to invoice draft!"
                        if registered_count > 0:
                            msg += f" (Registered {registered_count} new parts with 0 cost)"
                        # Clear input grid state
                        st.session_state.inv_bulk_input_df = pd.DataFrame(
                            [{"Part Number": "", "Quantity": 1}],
                            columns=["Part Number", "Quantity"]
                        )
                        trigger_toast(msg, icon="🛒")
                        st.rerun()
        with col_grid_btn2:
            if st.button("Clear Grid Editor", use_container_width=True, key="clear_inv_grid_btn"):
                st.session_state.inv_bulk_input_df = pd.DataFrame(
                    [{"Part Number": "", "Quantity": 1}],
                    columns=["Part Number", "Quantity"]
                )
                st.rerun()
                    
    with col_right:
        st.subheader("2. Customer & billing details")
        customers = CustomerService.get_customers()
        cust_names = ["- Create New Inline -"] + [c['name'] for c in customers]
        
        # Select active profile
        selected_cust_name = st.selectbox("Search / Select Active Billing Profile", cust_names, key="inv_cust_select")
        
        # Initialize sync state if missing
        if "prev_selected_cust" not in st.session_state:
            st.session_state.prev_selected_cust = "- Create New Inline -"
            st.session_state.inv_billing_name = ""
            st.session_state.inv_billing_discount = 0.0
            st.session_state.inv_billing_gst = ""
            st.session_state.inv_billing_terms = ""
            
        # Detect selection change and update widget state values
        if selected_cust_name != st.session_state.prev_selected_cust:
            if selected_cust_name == "- Create New Inline -":
                st.session_state.inv_billing_name = ""
                st.session_state.inv_billing_discount = 0.0
                st.session_state.inv_billing_gst = ""
                st.session_state.inv_billing_terms = ""
            else:
                cust_profile = CustomerService.get_customer_by_name(selected_cust_name)
                if cust_profile:
                    st.session_state.inv_billing_name = cust_profile['name']
                    st.session_state.inv_billing_discount = cust_profile['discount_percentage']
                    st.session_state.inv_billing_gst = cust_profile['gst_number'] or ""
                    st.session_state.inv_billing_terms = cust_profile['payment_terms'] or ""
            st.session_state.prev_selected_cust = selected_cust_name
            
        cust_profile = None
        if selected_cust_name != "- Create New Inline -":
            cust_profile = CustomerService.get_customer_by_name(selected_cust_name)
            
        col_c_in1, col_c_in2 = st.columns(2)
        with col_c_in1:
            billing_name = st.text_input("Billing Name *", key="inv_billing_name", disabled=(selected_cust_name != "- Create New Inline -"))
            billing_discount = st.number_input("Discount Profile (%)", min_value=0.0, max_value=100.0, step=0.01, key="inv_billing_discount")
        with col_c_in2:
            billing_gst = st.text_input("GSTIN Snapshot", key="inv_billing_gst")
            billing_terms = st.text_input("Payment Terms Snapshot", placeholder="e.g. Net 30 Days", key="inv_billing_terms")
            
        inv_date = st.date_input("Billing Date", datetime.now(), key="inv_date_input")
        
        # Calculate
        cust_payload = {
            "name": billing_name,
            "discount_percentage": billing_discount,
            "gst_number": billing_gst,
            "payment_terms": billing_terms
        }
        
        st.subheader("3. Live totals & actions")
        if len(st.session_state.invoice_items) == 0:
            render_html("""
            <div class="metric-card">
                <div class="metric-label">Subtotal:</div>
                <div class="metric-value">₹0.00</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Grand Total (Incl Tax):</div>
                <div class="metric-value" style="color: var(--cyan);">₹0.00</div>
            </div>
            """)
            st.info("Assemble line items on the left to see calculations.")
        else:
            calc = OrderService.calculate_order(cust_payload, st.session_state.invoice_items)
            
            render_html(f"""
            <div class="metric-card">
                <div class="metric-label">Subtotal:</div>
                <div class="metric-value">₹{calc['subtotal']:.2f}</div>
                <div class="metric-label" style="margin-top: 10px;">GST ({calc['gst_rate']}%):</div>
                <div class="metric-value">₹{calc['gst_amount']:.2f}</div>
                <hr style="border: none; border-top: 1px solid var(--border); margin: 10px 0;">
                <div class="metric-label">Grand Total (Excl. Shipping):</div>
                <div class="metric-value" style="color: var(--cyan);">₹{calc['grand_total']:.2f}</div>
            </div>
            """)
            
            # Stock warnings
            if calc['has_warnings']:
                st.warning("⚠️ Warning: Quantities of one or more items exceed current stock levels!")
                for item in calc['items']:
                    if item['insufficient_stock']:
                        st.markdown(f"- **{item['part_number']}**: Required: {int(item['quantity'])}, Available: {int(item['current_stock'])}")
            
            # Generate Button
            if st.button("Generate Invoice & Print", type="primary", use_container_width=True, key="inv_gen_btn"):
                if not billing_name:
                    st.error("Customer name is required.")
                else:
                    try:
                        # 1. Create Order
                        order_id = OrderService.create_order(
                            customer_input={
                                "id": cust_profile['id'] if cust_profile else None,
                                "name": billing_name,
                                "discount_percentage": billing_discount,
                                "gst_number": billing_gst,
                                "payment_terms": billing_terms
                            },
                            items_input=st.session_state.invoice_items
                        )
                        # 2. Create Invoice
                        invoice_id = InvoiceService.generate_invoice_for_order(order_id, inv_date.strftime('%Y-%m-%d'))
                        invoice_data = InvoiceService.get_invoice_by_id(invoice_id)
                        
                        st.session_state.last_invoice_generated = invoice_data
                        # Reset items list
                        st.session_state.invoice_items = []
                        trigger_toast(f"Invoice '{invoice_data['invoice_number']}' generated successfully!", icon="📄")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Failed to generate invoice: {str(ex)}")

    # Display items table below configuration
    st.subheader("📋 Invoice Line Items Grid")
    if len(st.session_state.invoice_items) == 0:
        st.info("No items added to invoice draft yet. Use the catalog item details panel on the left to add parts.")
    else:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        col_gr1, col_gr2 = st.columns([5, 1])
        with col_gr1:
            st.markdown("*Use the table editor below to modify quantities or check 'Remove Item' to delete a row.*")
        with col_gr2:
            if st.button("Reset Draft", use_container_width=True, key="reset_draft_items"):
                st.session_state.invoice_items = []
                st.rerun()
                
        # Build pandas dataframe for the st.data_editor
        df_editor_data = []
        for idx, i in enumerate(st.session_state.invoice_items):
            df_editor_data.append({
                "Part Number": i["part_number"],
                "Available Stock": i["current_stock"],
                "Quantity": i["quantity"],
                "List Price/100": i["unit_price_100"],
                "Custom Disc %": i["discount_percentage"] if i["discount_percentage"] is not None else 0.0,
                "Action": False # checkbox to remove
            })
            
        df_editor = pd.DataFrame(df_editor_data)
        edited_df = st.data_editor(
            df_editor,
            column_config={
                "Part Number": st.column_config.TextColumn("Part Number", disabled=True),
                "Available Stock": st.column_config.NumberColumn("Available Stock", disabled=True),
                "List Price/100": st.column_config.NumberColumn("List Price/100", disabled=True),
                "Quantity": st.column_config.NumberColumn("Quantity", min_value=1, step=1),
                "Custom Disc %": st.column_config.NumberColumn("Custom Disc %", min_value=0.0, max_value=100.0),
                "Action": st.column_config.CheckboxColumn("Remove Item")
            },
            hide_index=True,
            use_container_width=True,
            key="inv_data_editor"
        )
        
        # Check updates
        sync_items = []
        for idx, row in edited_df.iterrows():
            if row["Action"] is True:
                continue # Skip / delete this row
            
            orig_item = st.session_state.invoice_items[idx]
            orig_item["quantity"] = int(row["Quantity"])
            orig_item["discount_percentage"] = float(row["Custom Disc %"]) if row["Custom Disc %"] > 0 else None
            sync_items.append(orig_item)
            
        if len(sync_items) != len(st.session_state.invoice_items) or any(
            sync_items[x]['quantity'] != st.session_state.invoice_items[x]['quantity'] for x in range(len(sync_items))
        ):
            st.session_state.invoice_items = sync_items
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)

    # If last invoice generated is active, show the printable view and download
    if st.session_state.last_invoice_generated:
        st.write("---")
        st.subheader("Invoice Output Preview")
        
        invoice_info = st.session_state.last_invoice_generated
        
        col_pr1, col_pr2 = st.columns([3, 1])
        with col_pr1:
            st.info(f"Invoice **{invoice_info['invoice_number']}** generated successfully. You can download the printable HTML document on the right to print as a PDF.")
        with col_pr2:
            html_content = generate_invoice_html(invoice_info)
            st.download_button(
                label="📥 Download Printable HTML Invoice",
                data=html_content,
                file_name=f"invoice_{invoice_info['invoice_number']}.html",
                mime="text/html",
                use_container_width=True
            )
            if st.button("Close Preview", use_container_width=True):
                st.session_state.last_invoice_generated = None
                st.rerun()
                
        # Render the raw HTML template in Streamlit
        components.html(html_content, height=850, scrolling=True)

# --- TAB: NEW QUOTATION ---
with t_quotation:
    st.markdown("### Interactive Proforma Quotation Generator")
    
    # Left column for Item additions (tabulated grid)
    # Right column for Customer & Billing Details + Totals (Live totals & settings)
    col_q_left, col_q_right = st.columns([1.2, 1])
    
    with col_q_left:
        st.subheader("1. Enter / Paste Line Items")
        st.write("Copy and paste cells (Part Number and Quantity columns) from Excel directly into the table below.")
        
        # Load all products for validation and registration
        all_q_prods = query_db(
            """SELECT p.*, i.current_stock, c.price_per_100_pcs 
               FROM PRODUCTS p
               LEFT JOIN INVENTORY i ON p.id = i.product_id
               LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
               ORDER BY p.part_number ASC"""
        )
        
        # We present an editable grid
        if "qtn_bulk_input_df" not in st.session_state:
            st.session_state.qtn_bulk_input_df = pd.DataFrame(
                [{"Part Number": "", "Quantity": 1}],
                columns=["Part Number", "Quantity"]
            )
            
        edited_qtn_df = st.data_editor(
            st.session_state.qtn_bulk_input_df,
            num_rows="dynamic",
            column_config={
                "Part Number": st.column_config.TextColumn("Part Number / Item Code", width="medium"),
                "Quantity": st.column_config.NumberColumn("Quantity (PCS)", min_value=1, step=1)
            },
            use_container_width=True,
            key="bulk_qtn_data_editor"
        )
        
        # Add buttons to process grid
        col_q_grid_btn1, col_q_grid_btn2 = st.columns([1, 1])
        with col_q_grid_btn1:
            if st.button("Add Items to Quotation Draft", type="primary", use_container_width=True, key="bulk_add_to_qtn_draft_btn"):
                # Clean up empty rows
                non_empty_q_rows = edited_qtn_df[edited_qtn_df["Part Number"].astype(str).str.strip() != ""]
                if len(non_empty_q_rows) == 0:
                    st.error("No valid items entered in the grid.")
                else:
                    db_prods = {p['part_number'].strip().lower(): p for p in all_q_prods}
                    added_count = 0
                    registered_count = 0
                    
                    for idx, row in non_empty_q_rows.iterrows():
                        part_no = str(row["Part Number"]).strip()
                        part_no_clean = part_no.replace('"', '').replace("'", "")
                        
                        try:
                            qty = int(float(str(row["Quantity"]).replace(',', '').strip()))
                        except:
                            qty = 1
                            
                        key_lower = part_no_clean.lower()
                        
                        # Resolve product
                        if key_lower in db_prods:
                            matched_prod = db_prods[key_lower]
                            product_id = matched_prod['id']
                            current_stock = matched_prod['current_stock'] if matched_prod['current_stock'] is not None else 0.0
                            unit_price_100 = matched_prod['price_per_100_pcs'] if matched_prod['price_per_100_pcs'] is not None else 0.0
                        else:
                            # Auto register
                            series = part_no_clean.split('-')[0] if '-' in part_no_clean else None
                            conn_ins = get_db_connection()
                            cur_ins = conn_ins.cursor()
                            try:
                                cur_ins.execute("INSERT INTO PRODUCTS (part_number, part_name, series, make) VALUES (?, ?, ?, ?)",
                                                (part_no_clean, part_no_clean, series, 'WAGO'))
                                product_id = cur_ins.lastrowid
                                cur_ins.execute("INSERT INTO INVENTORY (product_id, current_stock) VALUES (?, 0.0)", (product_id,))
                                cur_ins.execute("INSERT INTO PRODUCT_COSTS (product_id, price_per_100_pcs, price_per_unit, is_current) VALUES (?, 0.0, 0.0, 1)", (product_id,))
                                conn_ins.commit()
                                registered_count += 1
                            except:
                                product_id = None
                            finally:
                                conn_ins.close()
                                
                            current_stock = 0.0
                            unit_price_100 = 0.0
                            
                        if product_id is not None:
                            # Check if already in draft
                            found = False
                            for i in st.session_state.quotation_items:
                                if i['product_id'] == product_id:
                                    i['quantity'] += qty
                                    found = True
                                    break
                            if not found:
                                st.session_state.quotation_items.append({
                                    "product_id": product_id,
                                    "part_number": part_no_clean,
                                    "part_name": part_no_clean,
                                    "quantity": qty,
                                    "current_stock": current_stock,
                                    "unit_price_100": unit_price_100,
                                    "discount_percentage": None
                                })
                            added_count += 1
                            
                    if added_count > 0:
                        msg = f"Added {added_count} items to quotation draft!"
                        if registered_count > 0:
                            msg += f" (Registered {registered_count} new parts with 0 cost)"
                        # Clear input grid state
                        st.session_state.qtn_bulk_input_df = pd.DataFrame(
                            [{"Part Number": "", "Quantity": 1}],
                            columns=["Part Number", "Quantity"]
                        )
                        trigger_toast(msg, icon="🛒")
                        st.rerun()
        with col_q_grid_btn2:
            if st.button("Clear Grid Editor", use_container_width=True, key="clear_qtn_grid_btn"):
                st.session_state.qtn_bulk_input_df = pd.DataFrame(
                    [{"Part Number": "", "Quantity": 1}],
                    columns=["Part Number", "Quantity"]
                )
                st.rerun()
                
    with col_q_right:
        st.subheader("2. Customer & billing details")
        customers = CustomerService.get_customers()
        cust_names = ["- Create New Inline -"] + [c['name'] for c in customers]
        
        # Select active profile
        selected_cust_name = st.selectbox("Search / Select Active Billing Profile", cust_names, key="qtn_cust_select")
        
        # Initialize sync state if missing
        if "prev_selected_cust_q" not in st.session_state:
            st.session_state.prev_selected_cust_q = "- Create New Inline -"
            st.session_state.qtn_billing_name = ""
            st.session_state.qtn_billing_discount = 0.0
            st.session_state.qtn_billing_gst = ""
            st.session_state.qtn_billing_terms = ""
            
        # Detect selection change and update widget state values
        if selected_cust_name != st.session_state.prev_selected_cust_q:
            if selected_cust_name == "- Create New Inline -":
                st.session_state.qtn_billing_name = ""
                st.session_state.qtn_billing_discount = 0.0
                st.session_state.qtn_billing_gst = ""
                st.session_state.qtn_billing_terms = ""
            else:
                cust_profile = CustomerService.get_customer_by_name(selected_cust_name)
                if cust_profile:
                    st.session_state.qtn_billing_name = cust_profile['name']
                    st.session_state.qtn_billing_discount = cust_profile['discount_percentage']
                    st.session_state.qtn_billing_gst = cust_profile['gst_number'] or ""
                    st.session_state.qtn_billing_terms = cust_profile['payment_terms'] or ""
            st.session_state.prev_selected_cust_q = selected_cust_name
            
        # Display inputs
        inv_billing_name = st.text_input("Customer Name / Company *", key="qtn_billing_name", placeholder="e.g. Demo1")
        inv_billing_discount = st.number_input("Discount Percentage (%)", min_value=0.0, max_value=100.0, step=0.01, key="qtn_billing_discount")
        inv_billing_gst = st.text_input("GSTIN Number", key="qtn_billing_gst", placeholder="e.g. 27DEMO11234A1Z1")
        inv_billing_terms = st.text_input("Payment Terms", key="qtn_billing_terms", placeholder="e.g. Net 30 Days")
        
        # Prepare customer object
        cust_payload = {
            "name": inv_billing_name.strip(),
            "discount_percentage": inv_billing_discount,
            "gst_number": inv_billing_gst.strip() or None,
            "payment_terms": inv_billing_terms.strip() or None
        }
        
        qtn_date = st.date_input("Quotation Date", datetime.now(), key="qtn_date")
        
        st.subheader("3. Live totals & actions")
        if len(st.session_state.quotation_items) == 0:
            render_html("""
            <div class="metric-card">
                <div class="metric-label">Subtotal:</div>
                <div class="metric-value">₹0.00</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Grand Total (Incl Tax):</div>
                <div class="metric-value" style="color: var(--cyan);">₹0.00</div>
            </div>
            """)
            st.info("Assemble line items on the left to see calculations.")
        else:
            calc = OrderService.calculate_order(cust_payload, st.session_state.quotation_items)
            
            render_html(f"""
            <div class="metric-card">
                <div class="metric-label">Subtotal:</div>
                <div class="metric-value">₹{calc['subtotal']:.2f}</div>
                <div class="metric-label" style="margin-top: 10px;">GST ({calc['gst_rate']}%):</div>
                <div class="metric-value">₹{calc['gst_amount']:.2f}</div>
                <hr style="border: none; border-top: 1px solid var(--border); margin: 10px 0;">
                <div class="metric-label">Grand Total (Excl. Shipping):</div>
                <div class="metric-value" style="color: var(--cyan);">₹{calc['grand_total']:.2f}</div>
            </div>
            """)
            
            if calc['has_warnings']:
                st.warning("⚠️ Some items in this quotation draft exceed available physical stock.")
                
            if st.button("Generate Quotation", type="primary", use_container_width=True, key="generate_qtn_btn"):
                if not inv_billing_name.strip():
                    st.error("Customer name is required.")
                else:
                    try:
                        quotation_id = QuotationService.generate_quotation(
                            customer_input=cust_payload,
                            items_input=st.session_state.quotation_items,
                            quotation_date=qtn_date.strftime('%Y-%m-%d')
                        )
                        qtn_data = QuotationService.get_quotation_by_id(quotation_id)
                        st.session_state.last_quotation_generated = qtn_data
                        st.session_state.quotation_items = []
                        trigger_toast(f"Quotation {qtn_data['quotation_number']} generated!", icon="📄")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Failed to generate quotation: {str(ex)}")

    # Display items table below configuration
    st.subheader("📋 Quotation Line Items Grid")
    if len(st.session_state.quotation_items) == 0:
        st.info("No items added to quotation draft yet. Enter details in the grid panel above.")
    else:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        col_q_gr1, col_q_gr2 = st.columns([5, 1])
        with col_q_gr1:
            st.markdown("*Use the table editor below to modify quantities or check 'Remove Item' to delete a row.*")
        with col_q_gr2:
            if st.button("Reset Draft", use_container_width=True, key="reset_qtn_draft_items"):
                st.session_state.quotation_items = []
                st.rerun()
                
        # Build pandas dataframe for the st.data_editor
        df_editor_data = []
        for idx, i in enumerate(st.session_state.quotation_items):
            df_editor_data.append({
                "Part Number": i["part_number"],
                "Available Stock": i["current_stock"],
                "Quantity": i["quantity"],
                "List Price/100": i["unit_price_100"],
                "Custom Disc %": i["discount_percentage"] if i["discount_percentage"] is not None else 0.0,
                "Action": False
            })
            
        df_editor = pd.DataFrame(df_editor_data)
        edited_df = st.data_editor(
            df_editor,
            column_config={
                "Part Number": st.column_config.TextColumn("Part Number", disabled=True),
                "Available Stock": st.column_config.NumberColumn("Available Stock", disabled=True),
                "List Price/100": st.column_config.NumberColumn("List Price/100", disabled=True),
                "Quantity": st.column_config.NumberColumn("Quantity", min_value=1, step=1),
                "Custom Disc %": st.column_config.NumberColumn("Custom Disc %", min_value=0.0, max_value=100.0),
                "Action": st.column_config.CheckboxColumn("Remove Item")
            },
            hide_index=True,
            use_container_width=True,
            key="qtn_data_editor"
        )
        
        # Check updates
        sync_items = []
        for idx, row in edited_df.iterrows():
            if row["Action"] is True:
                continue
            
            orig_item = st.session_state.quotation_items[idx]
            orig_item["quantity"] = int(row["Quantity"])
            orig_item["discount_percentage"] = float(row["Custom Disc %"]) if row["Custom Disc %"] > 0 else None
            sync_items.append(orig_item)
            
        if len(sync_items) != len(st.session_state.quotation_items) or any(
            sync_items[x]['quantity'] != st.session_state.quotation_items[x]['quantity'] for x in range(len(sync_items))
        ):
            st.session_state.quotation_items = sync_items
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.last_quotation_generated:
        st.write("---")
        st.subheader("Quotation Output Preview")
        
        qtn_info = st.session_state.last_quotation_generated
        
        col_q_pr1, col_q_pr2 = st.columns([3, 1])
        with col_q_pr1:
            st.info(f"Quotation **{qtn_info['quotation_number']}** generated successfully. You can download the printable HTML document on the right to print as a PDF.")
        with col_q_pr2:
            html_content = generate_invoice_html(qtn_info)
            st.download_button(
                label="📥 Download Printable HTML Quotation",
                data=html_content,
                file_name=f"quotation_{qtn_info['quotation_number']}.html",
                mime="text/html",
                use_container_width=True
            )
            if st.button("Close Preview", use_container_width=True, key="close_qtn_preview_btn"):
                st.session_state.last_quotation_generated = None
                st.rerun()
                
        components.html(html_content, height=850, scrolling=True)

# --- TAB: LEDGER HISTORY ---
with t_history:
    st.markdown("### 📜 System History Ledger")
    
    ledger_type = st.radio("Choose Ledger Type", ["Invoices Ledger", "Quotations Ledger"], horizontal=True, key="ledger_history_type")
    
    if ledger_type == "Invoices Ledger":
        q_inv_search = st.text_input("Search Invoices (Invoice Number, Customer Name)", placeholder="e.g. INV-2026", key="inv_search_inp")
        
        if q_inv_search:
            q = f"%{q_inv_search.strip()}%"
            invoices = query_db(
                """SELECT i.*, o.customer_name_snapshot, o.grand_total, o.order_number 
                   FROM INVOICES i
                   JOIN ORDERS o ON i.order_id = o.id
                   WHERE i.invoice_number LIKE ? OR o.customer_name_snapshot LIKE ?
                   ORDER BY i.created_at DESC""",
                (q, q)
            )
        else:
            invoices = query_db(
                """SELECT i.*, o.customer_name_snapshot, o.grand_total, o.order_number 
                   FROM INVOICES i
                   JOIN ORDERS o ON i.order_id = o.id
                   ORDER BY i.created_at DESC"""
            )
            
        if len(invoices) == 0:
            st.info("No invoices found in ledger database.")
        else:
            inv_options = ["- Select Invoice to Print -"] + [f"{i['invoice_number']} - {i['customer_name_snapshot']} (₹{i['grand_total']:.2f})" for i in invoices]
            selected_to_print = st.selectbox("Choose Invoice to View & Download Print Sheet", inv_options, key="hist_inv_select")
            
            if selected_to_print != "- Select Invoice to Print -":
                selected_idx = inv_options.index(selected_to_print) - 1
                inv_record = invoices[selected_idx]
                invoice_full = InvoiceService.get_invoice_by_id(inv_record['id'])
                
                col_print1, col_print2 = st.columns([3, 1])
                with col_print1:
                    st.markdown(f"#### 📄 Invoice Details: {invoice_full['invoice_number']}")
                with col_print2:
                    html_invoice = generate_invoice_html(invoice_full)
                    st.download_button(
                        label="📥 Download Print Sheet (HTML)",
                        data=html_invoice,
                        file_name=f"invoice_{invoice_full['invoice_number']}.html",
                        mime="text/html",
                        use_container_width=True,
                        key="dl_inv_hist_btn"
                    )
                components.html(html_invoice, height=850, scrolling=True)
            else:
                rows_html = ""
                for inv in invoices:
                    rows_html += f"<tr><td><strong>{inv['invoice_number']}</strong></td><td>{inv['invoice_date']}</td><td>{inv['customer_name_snapshot']}</td><td>{inv['order_number']}</td><td><strong>₹{inv['grand_total']:.2f}</strong></td></tr>"
                render_html(f"""
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Invoice No</th>
                            <th>Billing Date</th>
                            <th>Customer / Company</th>
                            <th>Order Ref</th>
                            <th>Grand Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
                """)
    else:
        # Quotations Ledger
        q_qtn_search = st.text_input("Search Quotations (Quotation Number, Customer Name)", placeholder="e.g. QTN-2026", key="qtn_search_inp")
        
        quotations = QuotationService.get_quotations(q_qtn_search.strip() if q_qtn_search else None)
        
        if len(quotations) == 0:
            st.info("No quotations found in ledger database.")
        else:
            qtn_options = ["- Select Quotation to Print -"] + [f"{q['quotation_number']} - {q['customer_name_snapshot']} (₹{q['grand_total']:.2f})" for q in quotations]
            selected_to_print = st.selectbox("Choose Quotation to View & Download Print Sheet", qtn_options, key="hist_qtn_select")
            
            if selected_to_print != "- Select Quotation to Print -":
                selected_idx = qtn_options.index(selected_to_print) - 1
                qtn_record = quotations[selected_idx]
                qtn_full = QuotationService.get_quotation_by_id(qtn_record['id'])
                
                col_print1, col_print2 = st.columns([3, 1])
                with col_print1:
                    st.markdown(f"#### 📄 Quotation Details: {qtn_full['quotation_number']}")
                with col_print2:
                    html_qtn = generate_invoice_html(qtn_full)
                    st.download_button(
                        label="📥 Download Print Sheet (HTML)",
                        data=html_qtn,
                        file_name=f"quotation_{qtn_full['quotation_number']}.html",
                        mime="text/html",
                        use_container_width=True,
                        key="dl_qtn_hist_btn"
                    )
                components.html(html_qtn, height=850, scrolling=True)
            else:
                rows_html = ""
                for qtn in quotations:
                    rows_html += f"<tr><td><strong>{qtn['quotation_number']}</strong></td><td>{qtn['created_at'][:10]}</td><td>{qtn['customer_name_snapshot']}</td><td>-</td><td><strong>₹{qtn['grand_total']:.2f}</strong></td></tr>"
                render_html(f"""
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Quotation No</th>
                            <th>Date</th>
                            <th>Customer / Company</th>
                            <th>Order Ref</th>
                            <th>Grand Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
                """)

# --- TAB: MANUAL ENTRY ---
with t_manual:
    st.markdown("### Manual Database Entry")
    
    m_choice = st.radio("Choose Entry Type", ["Add New Product Catalog Entry", "Add New Customer Profile"], horizontal=True, key="manual_choice")
    
    if m_choice == "Add New Product Catalog Entry":
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("➕ Add Product to Catalog")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_part = st.text_input("Part Number / Item Code *", "", placeholder="e.g. 209-120", key="man_prod_part")
            m_make = st.text_input("Make / Manufacturer *", "", placeholder="WAGO", key="man_prod_make")
            m_name = st.text_input("Product Name / Description", "", key="man_prod_name")
        with col_m2:
            m_packing = st.number_input("Packing Quantity (PCS)", min_value=1, value=1, key="man_prod_pack")
            m_stock = st.number_input("Initial Stock Quantity", min_value=0.0, step=1.0, value=0.0, key="man_prod_stock")
            m_price = st.number_input("Cost Rate (INR per 100 pcs)", min_value=0.0, step=0.01, value=0.0, key="man_prod_price")
            
        if st.button("Save New Product Catalog Entry", type="primary", use_container_width=True, key="man_prod_save_btn"):
            make_val = m_make.strip() or "WAGO"
            if not m_part.strip() or not make_val:
                st.error("Part Number and Make are mandatory fields.")
            else:
                conn = get_db_connection()
                cur = conn.cursor()
                try:
                    cur.execute("BEGIN TRANSACTION;")
                    
                    # 1. Check if product already exists
                    cur.execute("SELECT id FROM PRODUCTS WHERE part_number = ?", (m_part.strip(),))
                    prod = cur.fetchone()
                    
                    if prod:
                        st.error(f"Product '{m_part.strip()}' already exists in catalog. Use uploads to update, or enter a different Part Number.")
                        cur.execute("ROLLBACK;")
                    else:
                        series = m_part.split('-')[0] if '-' in m_part else None
                        cur.execute(
                            "INSERT INTO PRODUCTS (part_number, part_name, series, make, packing_quantity) VALUES (?, ?, ?, ?, ?)",
                            (m_part.strip(), m_name.strip() or m_part.strip(), series, make_val, m_packing)
                        )
                        product_id = cur.lastrowid
                        
                        # Add initial stock
                        cur.execute(
                            "INSERT INTO INVENTORY (product_id, current_stock, last_updated) VALUES (?, ?, ?)",
                            (product_id, m_stock, datetime.now().isoformat())
                        )
                        
                        # Add price list
                        price_per_unit = m_price / 100.0
                        cur.execute(
                            "INSERT INTO PRODUCT_COSTS (product_id, price_per_100_pcs, price_per_unit, effective_from, is_current) VALUES (?, ?, ?, ?, ?)",
                            (product_id, m_price, price_per_unit, datetime.now().isoformat(), 1)
                        )
                        
                        cur.execute("COMMIT;")
                        trigger_toast(f"Product '{m_part.strip()}' added to catalog!", icon="📦")
                        st.rerun()
                except Exception as ex:
                    try: cur.execute("ROLLBACK;")
                    except: pass
                    st.error(f"Failed to add product: {str(ex)}")
                finally:
                    conn.close()
        st.markdown('</div>', unsafe_allow_html=True)
        
    else:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("➕ Add Customer Profile")
        
        col_mc1, col_mc2 = st.columns(2)
        with col_mc1:
            mc_name = st.text_input("Customer/Company Name *", "", key="man_cust_name")
            mc_discount = st.number_input("Default Discount %", min_value=0.0, max_value=100.0, step=0.01, value=0.0, key="man_cust_disc")
        with col_mc2:
            mc_gst = st.text_input("GSTIN Number", "", key="man_cust_gst")
            mc_terms = st.text_input("Payment Terms", placeholder="e.g. Net 30 Days", key="man_cust_terms")
            
        if st.button("Save New Customer Profile", type="primary", use_container_width=True, key="man_cust_save_btn"):
            if not mc_name.strip():
                st.error("Customer Company Name is mandatory.")
            else:
                try:
                    CustomerService.create_customer(mc_name.strip(), mc_discount, mc_gst.strip() or None, mc_terms.strip() or None)
                    trigger_toast(f"Customer '{mc_name.strip()}' registered!", icon="🎉")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB: SETTINGS ---
with t_settings:
    st.markdown("### ⚙️ System Configurations")
    
    settings = OrderService.get_settings()
    current_gst = float(settings.get('gst_rate', 18.0))
    current_url = settings.get('stock_excel_url', '')
    current_sync_enabled = settings.get('auto_sync_enabled', '0') == '1'
    current_interval = float(settings.get('auto_sync_interval', 15.0))
    
    st.subheader("1. General Configurations")
    new_gst_rate = st.number_input("Default GST Percentage (%)", min_value=0.0, max_value=100.0, step=0.1, value=current_gst)
    
    st.subheader("2. Stock Group Reorder Excel Cloud Sync")
    st.write("Link your local Stock Group Reorder Excel file. Upload it to Google Drive/OneDrive, share as 'Anyone with link can view', and paste the URL below.")
    
    new_url = st.text_input("Excel / Google Sheets Share URL", value=current_url, placeholder="https://docs.google.com/spreadsheets/d/...")
    new_sync_enabled = st.checkbox("Enable 24/7 Background Auto-Sync", value=current_sync_enabled)
    new_interval = st.number_input("Auto-Sync Interval (Minutes)", min_value=1.0, max_value=1440.0, step=1.0, value=current_interval)
    
    col_set1, col_set2 = st.columns([1, 1])
    with col_set1:
        if st.button("Apply Config Settings", type="primary", use_container_width=True):
            execute_db("INSERT OR REPLACE INTO APP_SETTINGS (key, value) VALUES ('gst_rate', ?)", (str(new_gst_rate),))
            execute_db("INSERT OR REPLACE INTO APP_SETTINGS (key, value) VALUES ('stock_excel_url', ?)", (str(new_url),))
            execute_db("INSERT OR REPLACE INTO APP_SETTINGS (key, value) VALUES ('auto_sync_enabled', ?)", ('1' if new_sync_enabled else '0',))
            execute_db("INSERT OR REPLACE INTO APP_SETTINGS (key, value) VALUES ('auto_sync_interval', ?)", (str(new_interval),))
            trigger_toast("Settings updated successfully!", icon="⚙️")
            st.rerun()
            
    with col_set2:
        if st.button("Sync Stock Status Now", use_container_width=True):
            if not new_url.strip():
                st.error("Please configure a valid Excel Share URL first.")
            else:
                with st.spinner("Downloading and parsing Excel sheet from cloud..."):
                    res = ImportService.sync_from_web_url(new_url.strip(), imported_by="Manual Admin Sync")
                    if res['status'] in ('success', 'partial_success'):
                        msg = f"Stock status synced successfully! Loaded {res['successful_records']} rows."
                        if res['failed_records'] > 0:
                            msg += f" ({res['failed_records']} rows failed)"
                        trigger_toast(msg, icon="🔄")
                        st.rerun()
                    else:
                        st.error(f"Sync failed: {', '.join(res['errors'])}")
