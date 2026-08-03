import streamlit as st
from app.providers.factory import ProviderFactory
from app.providers.connector_client import ConnectorClient

def render_connection_status():
    """Renders real-time status indicators in UI header for connector health and active provider mode."""
    provider_name = ProviderFactory.get_configured_provider_name()

    if provider_name == "tally":
        client = ConnectorClient(timeout=1.5, max_retries=1)
        health = client.get_health() or {}
        tally = health.get("tally_health", {})

        if tally.get("connected", False):
            company = tally.get("company_name", "Pioneer Automation")
            version = tally.get("tally_version", "TallyPrime 7.1")
            st.markdown(
                f'<div style="padding: 8px 14px; background: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; border-radius: 8px; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; margin-bottom: 12px;">'
                f'<span style="font-size: 14px;">🟢 Connected</span> | <span style="font-weight: 400;">Company: <b>{company}</b> ({version})</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div style="padding: 8px 14px; background: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; border-radius: 8px; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; margin-bottom: 12px;">'
                f'<span style="font-size: 14px;">🔴 Connector Offline</span> | <span style="font-weight: 400;">Serving Cached Local Data</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            st.warning("⚠️ Pioneer Connector Microservice is currently offline. The ERP is operating smoothly using cached local data snapshots.")
    else:
        st.markdown(
            f'<div style="padding: 8px 14px; background: #E0F2FE; color: #0369A1; border: 1px solid #7DD3FC; border-radius: 8px; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; margin-bottom: 12px;">'
            f'<span style="font-size: 14px;">🔵 Provider: Excel Mode</span>'
            f'</div>',
            unsafe_allow_html=True
        )
