import time
import re
import os
import urllib.request
import json
import xml.etree.ElementTree as ET

# --- CONFIGURATION ---
TALLY_PORT_URL = "http://localhost:9000"
SYNC_INTERVAL_SECONDS = 300  # Syncs every 5 minutes (300 seconds)

# TDL XML Query to fetch Stock Summary from Tally Prime 7.1
TDL_QUERY = b"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Stock Summary</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <ISITEMWISE>Yes</ISITEMWISE>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

def fetch_tally_data():
    """Queries local Tally Prime on Port 9000 and parses all stock items."""
    req = urllib.request.Request(
        TALLY_PORT_URL,
        data=TDL_QUERY,
        headers={'Content-Type': 'text/xml'}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw_xml = resp.read().decode('utf-8', errors='ignore')
        
    xml_clean = re.sub(r'&(?!amp;|lt;|gt;|apos;|quot;)', '&amp;', raw_xml)
    root = ET.fromstring(xml_clean)
    
    acc_names = root.findall('.//DSPACCNAME')
    stk_infos = root.findall('.//DSPSTKINFO')
    
    items = []
    total = min(len(acc_names), len(stk_infos))
    for i in range(total):
        name_el = acc_names[i].find('.//DSPDISPNAME')
        qty_el = stk_infos[i].find('.//DSPCLQTY')
        rate_el = stk_infos[i].find('.//DSPCLRATE')
        
        if name_el is None or not name_el.text:
            continue
            
        item_code = name_el.text.strip()
        if not item_code or item_code.lower() in ('nan', 'total'):
            continue
            
        qty_str = qty_el.text.strip() if qty_el is not None and qty_el.text else '0'
        rate_str = rate_el.text.strip() if rate_el is not None and rate_el.text else '0'
        
        m_qty = re.search(r'[-+]?\d*\.?\d+', qty_str.replace(',', ''))
        stock_val = float(m_qty.group(0)) if m_qty else 0.0
        
        m_rate = re.search(r'[-+]?\d*\.?\d+', rate_str.replace(',', ''))
        rate_val = float(m_rate.group(0)) if m_rate else 0.0
        
        items.append({
            "part_number": item_code,
            "closing_stock": stock_val,
            "rate_per_100": rate_val
        })
        
    return items

def run_pusher():
    print("=" * 60)
    print(" ⚡ PIONEER FLOW — TALLY PRIME 7.1 LIVE BACKGROUND PUSHER ⚡")
    print("=" * 60)
    print(f" Connecting to Tally Prime on {TALLY_PORT_URL}...")
    print(f" Sync Interval: Every {SYNC_INTERVAL_SECONDS // 60} minutes")
    print(" Press Ctrl+C to stop.\n")
    
    while True:
        try:
            start_t = time.time()
            items = fetch_tally_data()
            elapsed = time.time() - start_t
            
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now_str}] ✅ Successfully fetched {len(items):,} items from Tally Prime ({elapsed:.2f}s)")
            
        except Exception as e:
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now_str}] ⚠️ Connection waiting... ({e})")
            
        time.sleep(SYNC_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_pusher()
