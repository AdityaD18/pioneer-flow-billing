import os
import streamlit as st
from app.core.config import Config
from app.core.logger import app_logger

# Log Application Startup
app_logger.info(f"Starting {Config.APP_NAME} v{Config.APP_VERSION} ({Config.APP_ENV} mode)...")

# Page Configuration
st.set_page_config(
    page_title=f"{Config.APP_NAME} - Mechanical ERP",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database & CSS Styles
from app.models.database import init_db
from app.ui.styles import inject_custom_css, render_html
from app.ui.connection_status import render_connection_status
from app.ui.views.catalog import render_catalog_tab
from app.ui.views.stock_status import render_stock_status_tab
from app.ui.views.billing import render_billing_tab
from app.ui.views.history import render_history_tab
from app.ui.views.customers import render_customers_tab
from app.ui.views.settings import render_settings_tab

# Initialize DB tables & seed data on startup
init_db()

# Inject Custom Styling
inject_custom_css()

# Render Application Header Banner
render_html(f"""
<div class="header-banner">
    <div class="header-title">
        <i class="fa-solid fa-bolt"></i> {Config.APP_NAME}
    </div>
    <div class="header-subtitle">
        {Config.COMPANY_SUBTITLE}
    </div>
</div>
""")

# Render Connector & Provider Connection Health Status Indicator
render_connection_status()

# Render Navigation Sidebar Tabs
t_catalog, t_stock, t_billing, t_history, t_customers, t_settings = st.tabs([
    "📦 Product Catalog",
    "📑 Stock Group Status",
    "📝 Invoice & Quote Builder",
    "📜 History Ledger",
    "👥 Customer Directory",
    "⚙️ System Settings"
])

with t_catalog:
    render_catalog_tab()

with t_stock:
    render_stock_status_tab()

with t_billing:
    render_billing_tab()

with t_history:
    render_history_tab()

with t_customers:
    render_customers_tab()

with t_settings:
    render_settings_tab()
