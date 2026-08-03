import streamlit as st

def inject_custom_css():
    """Injects modern, premium CSS styling with Google Fonts, micro-animations, and styled cards."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main App Header Gradient */
    .header-banner {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 24px;
        border-radius: 12px;
        color: #F8FAFC;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    .header-title {
        font-size: 26px;
        font-weight: 700;
        margin: 0;
        color: #38BDF8;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .header-subtitle {
        font-size: 14px;
        color: #94A3B8;
        margin-top: 4px;
    }
    
    /* Metric Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    
    .metric-title {
        font-size: 13px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #0F172A;
        margin: 8px 0 4px 0;
    }
    
    .metric-sub {
        font-size: 12px;
        color: #94A3B8;
    }
    
    .metric-icon-blue { color: #0284C7; background: #E0F2FE; padding: 8px; border-radius: 8px; }
    .metric-icon-green { color: #16A34A; background: #DCFCE7; padding: 8px; border-radius: 8px; }
    .metric-icon-amber { color: #D97706; background: #FEF3C7; padding: 8px; border-radius: 8px; }
    .metric-icon-purple { color: #9333EA; background: #F3E8FF; padding: 8px; border-radius: 8px; }
    .metric-icon-cyan { color: #0891B2; background: #CFFAFE; padding: 8px; border-radius: 8px; }
    .metric-icon-red { color: #DC2626; background: #FEE2E2; padding: 8px; border-radius: 8px; }

    /* Section Headers */
    .section-head {
        font-size: 18px;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Settings Panels */
    .setting-section {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }
    
    .setting-section-title {
        font-size: 14px;
        font-weight: 600;
        color: #334155;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Table styling tweaks */
    div[data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #E2E8F0;
    }

    /* Font Awesome icons CDN */
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
    </style>
    """, unsafe_allow_html=True)

def render_html(html_code):
    st.markdown(html_code, unsafe_allow_html=True)

def draw_metric_card(title, value, subtext, icon_class, color_theme="blue"):
    html = f"""
    <div class="metric-card">
        <div class="metric-title">
            <span>{title}</span>
            <i class="{icon_class} metric-icon-{color_theme}"></i>
        </div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{subtext}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def trigger_toast(msg, icon="✅"):
    st.toast(msg, icon=icon)
