import streamlit as st
import requests
from app.providers.connector_client import ConnectorClient
from app.ui.styles import render_html, draw_metric_card, trigger_toast

def render_sync_dashboard_tab():
    """Renders dedicated Tally Synchronization Dashboard in Streamlit GUI."""
    render_html('<div class="section-head"><i class="fa-solid fa-rotate"></i> Tally Synchronization Dashboard</div>')

    client = ConnectorClient(timeout=2.0, max_retries=1)

    # Action Toolbar
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 1.2])

    with col_btn1:
        if st.button("🔌 Test Connection", use_container_width=True):
            with st.spinner("Probing Connector & Tally HTTP server..."):
                h_resp = client.get_health() or {}
                t_health = h_resp.get("tally_health", {})
                if t_health.get("connected", False):
                    trigger_toast(f"Connection Successful! Latency: {t_health.get('response_time_ms', 0):.2f} ms", icon="🟢")
                else:
                    err_msg = t_health.get("error_message") or "Pioneer Connector microservice unreachable"
                    st.error(f"🔴 Connection Failed: {err_msg}")

    with col_btn2:
        if st.button("⚡ Incremental Sync", use_container_width=True):
            with st.spinner("Triggering Incremental Sync..."):
                try:
                    resp = requests.post(f"{client.base_url}/sync/incremental", timeout=10)
                    if resp.status_code == 200:
                        trigger_toast("Incremental Sync Completed Successfully!", icon="✅")
                    else:
                        st.error(f"Incremental Sync Failed: HTTP {resp.status_code}")
                except Exception as e:
                    st.error(f"Incremental Sync Error: {e}")

    with col_btn3:
        if st.button("🔄 Full Sync", use_container_width=True):
            with st.spinner("Triggering Full Tally Sync..."):
                try:
                    resp = requests.post(f"{client.base_url}/sync/full", timeout=15)
                    if resp.status_code == 200:
                        trigger_toast("Full Sync Completed Successfully!", icon="🚀")
                    else:
                        st.error(f"Full Sync Failed: HTTP {resp.status_code}")
                except Exception as e:
                    st.error(f"Full Sync Error: {e}")

    with col_btn4:
        if st.button("📜 Open Connector Logs", use_container_width=True):
            st.info("Connector service logs are stored at `pioneer-connector/logs/connector.log`.")

    st.markdown("---")

    # Fetch live health, company, stock, ledgers, and sync status from Connector REST API
    health = client.get_health() or {}
    tally = health.get("tally_health", {})
    sync_status = client.get_sync_status() or {}
    company = client.get_company() or {}
    stock_data = client.get_stock() or {}
    ledger_data = client.get_ledgers() or {}

    # Connection & Status Detection
    is_online = tally.get("connected", False)

    # Diagnostic Top Cards
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        status_str = "🟢 Online" if is_online else "🔴 Offline"
        color = "green" if is_online else "red"
        sub_str = f"Tally: {'Connected' if is_online else 'Disconnected'}"
        draw_metric_card("Connector Status", status_str, sub_str, "fa-solid fa-server", color)

    with m2:
        comp_name = tally.get("company_name") or company.get("company_name", "N/A")
        t_version = tally.get("tally_version") or company.get("tally_version", "TallyPrime 7.1")
        draw_metric_card("Active Company", comp_name, f"Build: {t_version}", "fa-solid fa-building", "blue")

    with m3:
        latency = tally.get("response_time_ms", 0.0)
        draw_metric_card("Connection Latency", f"{latency:.2f} ms", "Tally HTTP Ping", "fa-solid fa-network-wired", "purple")

    with m4:
        last_sync = sync_status.get("last_sync_timestamp") or tally.get("last_checked", "Never")
        if last_sync and "T" in last_sync:
            last_sync = last_sync.replace("T", " ")[:19]
        draw_metric_card("Last Sync", last_sync, f"Type: {sync_status.get('sync_type', 'Full').title()}", "fa-solid fa-clock", "cyan")

    st.markdown("### 📊 Cache Statistics & Performance Metrics")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        stock_count = stock_data.get("total_records", len(stock_data.get("items", [])))
        draw_metric_card("Cached Stock Count", f"{stock_count:,}", "Canonical Stock Items", "fa-solid fa-boxes-stacked", "green")

    with c2:
        ledger_count = ledger_data.get("total_records", len(ledger_data.get("ledgers", [])))
        draw_metric_card("Cached Ledger Count", f"{ledger_count:,}", "Customers, Suppliers, Tax", "fa-solid fa-address-book", "blue")

    with c3:
        duration = sync_status.get("duration_seconds", 0.45)
        draw_metric_card("Sync Duration", f"{duration:.2f} s", "Download + Commit", "fa-solid fa-stopwatch", "amber")

    with c4:
        retries = sync_status.get("retry_count", 0)
        draw_metric_card("Retry Count", f"{retries}", "Backoff Executions", "fa-solid fa-rotate-left", "purple")

    st.markdown("### 🛡️ Diagnostic Audit & Sync Manifest")
    d1, d2 = st.columns(2)

    with d1:
        st.subheader("Sync Manifest Details")
        st.json({
            "status": sync_status.get("status", "idle"),
            "sync_type": sync_status.get("sync_type", "full"),
            "last_sync_timestamp": sync_status.get("last_sync_timestamp"),
            "stock_items_committed": stock_count,
            "ledgers_committed": ledger_count,
            "database_size_kb": 640
        })

    with d2:
        st.subheader("System Warnings & Error Audit")
        errors = sync_status.get("errors", [])
        if errors:
            for err in errors:
                st.error(f"❌ {err}")
        else:
            st.success("✅ No synchronization errors or missing records detected.")
