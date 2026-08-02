import re
import xml.etree.ElementTree as ET
from .logger import tally_logger

class TallyXMLParser:
    """Safe, robust XML parser for Tally Prime XML responses."""

    @staticmethod
    def sanitize_xml(xml_content):
        if isinstance(xml_content, bytes):
            xml_content = xml_content.decode('utf-8', errors='ignore')
            
        # Fix unescaped ampersands in company names / addresses
        clean_xml = re.sub(r'&(?!amp;|lt;|gt;|apos;|quot;)', '&amp;', xml_content)
        clean_xml = re.sub(r'&[a-zA-Z0-9#]+;', ' ', clean_xml)
        return clean_xml

    @classmethod
    def parse_stock_items(cls, xml_raw):
        clean_xml = cls.sanitize_xml(xml_raw)
        items = []
        
        try:
            root = ET.fromstring(clean_xml)
            for s_elem in root.findall('.//STOCKITEM'):
                item_dict = cls._parse_single_stock_item(s_elem)
                if item_dict:
                    items.append(item_dict)
        except Exception as parse_err:
            tally_logger.warning(f"ElementTree XML parse fallback engaged for StockItems: {parse_err}")
            items = cls._parse_stock_items_regex(clean_xml if isinstance(clean_xml, str) else xml_raw)
            
        return items

    @classmethod
    def parse_ledgers(cls, xml_raw):
        clean_xml = cls.sanitize_xml(xml_raw)
        ledgers = []
        
        try:
            root = ET.fromstring(clean_xml)
            for l_elem in root.findall('.//LEDGER'):
                l_dict = cls._parse_single_ledger(l_elem)
                if l_dict:
                    ledgers.append(l_dict)
        except Exception as parse_err:
            tally_logger.warning(f"ElementTree XML parse fallback engaged for Ledgers: {parse_err}")
            ledgers = cls._parse_ledgers_regex(clean_xml if isinstance(clean_xml, str) else xml_raw)
            
        return ledgers

    @classmethod
    def parse_stock_groups(cls, xml_raw):
        clean_xml = cls.sanitize_xml(xml_raw)
        groups = []
        try:
            root = ET.fromstring(clean_xml)
            for g_elem in root.findall('.//STOCKGROUP'):
                g_name = g_elem.attrib.get('NAME') or g_elem.findtext('NAME')
                if g_name:
                    groups.append({
                        "guid": g_elem.findtext('GUID') or "",
                        "master_id": int(g_elem.findtext('MASTERID') or 0),
                        "alter_id": int(g_elem.findtext('ALTERID') or 0),
                        "name": g_name.strip(),
                        "parent": (g_elem.findtext('PARENT') or "").strip()
                    })
        except Exception:
            pass
        return groups

    @classmethod
    def parse_active_company(cls, xml_raw):
        clean_xml = cls.sanitize_xml(xml_raw)
        try:
            root = ET.fromstring(clean_xml)
            for c_elem in root.findall('.//COMPANY'):
                c_name = c_elem.attrib.get('NAME') or c_elem.findtext('NAME')
                if c_name:
                    return c_name.strip()
        except Exception:
            pass
        # Regex search fallback
        match = re.search(r'<COMPANY[^>]*NAME="([^"]+)"', clean_xml, re.IGNORECASE)
        return match.group(1) if match else "Primary Company"

    @staticmethod
    def _parse_single_stock_item(s_elem):
        name = s_elem.attrib.get('NAME') or s_elem.findtext('NAME')
        if not name:
            nl = s_elem.find('.//LANGUAGENAME.LIST/NAME.LIST/NAME')
            if nl is not None: name = nl.text
        if not name or name.strip().lower() in ('nan', 'total'):
            return None
            
        name = name.strip()
        parent = (s_elem.findtext('PARENT') or 'WAGO').strip()
        category = (s_elem.findtext('CATEGORY') or '').strip()
        base_units = (s_elem.findtext('BASEUNITS') or 'PCS').strip()
        
        q_str = s_elem.findtext('CLOSINGBALANCE') or '0'
        r_str = s_elem.findtext('CLOSINGRATE') or '0'
        v_str = s_elem.findtext('CLOSINGVALUE') or '0'
        
        m_q = re.search(r'[-+]?\d*\.?\d+', q_str.replace(',', ''))
        m_r = re.search(r'[-+]?\d*\.?\d+', r_str.replace(',', ''))
        m_v = re.search(r'[-+]?\d*\.?\d+', v_str.replace(',', ''))
        
        return {
            "guid": s_elem.findtext('GUID') or "",
            "master_id": int(s_elem.findtext('MASTERID') or 0),
            "alter_id": int(s_elem.findtext('ALTERID') or 0),
            "name": name,
            "parent": parent,
            "category": category,
            "base_units": base_units,
            "closing_stock": float(m_q.group(0)) if m_q else 0.0,
            "closing_rate": float(m_r.group(0)) if m_r else 0.0,
            "closing_value": float(m_v.group(0)) if m_v else 0.0
        }

    @staticmethod
    def _parse_single_ledger(l_elem):
        name = l_elem.attrib.get('NAME') or l_elem.findtext('NAME')
        if not name:
            nl = l_elem.find('.//LANGUAGENAME.LIST/NAME.LIST/NAME')
            if nl is not None: name = nl.text
        if not name or name.strip().lower() in ('nan', 'total'):
            return None
            
        name = name.strip()
        parent = (l_elem.findtext('PARENT') or '').strip()
        gstin = (l_elem.findtext('PARTYGSTIN') or l_elem.findtext('GSTIN') or '').strip()
        phone = (l_elem.findtext('LEDGERPHONE') or l_elem.findtext('MOBILE') or '').strip()
        email = (l_elem.findtext('EMAIL') or '').strip()
        
        addr_list = [a.text for a in l_elem.findall('.//ADDRESS') if a is not None and a.text]
        address = " | ".join(addr_list) if addr_list else ""
        
        return {
            "guid": l_elem.findtext('GUID') or "",
            "master_id": int(l_elem.findtext('MASTERID') or 0),
            "alter_id": int(l_elem.findtext('ALTERID') or 0),
            "name": name,
            "parent": parent,
            "gstin": gstin,
            "phone": phone,
            "email": email,
            "address": address
        }

    @staticmethod
    def _parse_stock_items_regex(xml_text):
        items = []
        raw_blocks = re.findall(r'<STOCKITEM[^>]*NAME="([^"]+)"[^>]*>(.*?)</STOCKITEM>', xml_text, re.DOTALL | re.IGNORECASE)
        for s_name, s_content in raw_blocks:
            q_m = re.search(r'<CLOSINGBALANCE>([^<]+)</CLOSINGBALANCE>', s_content)
            r_m = re.search(r'<CLOSINGRATE>([^<]+)</CLOSINGRATE>', s_content)
            v_m = re.search(r'<CLOSINGVALUE>([^<]+)</CLOSINGVALUE>', s_content)
            p_m = re.search(r'<PARENT>([^<]+)</PARENT>', s_content)
            c_m = re.search(r'<CATEGORY>([^<]+)</CATEGORY>', s_content)
            
            q_val = float(re.search(r'[-+]?\d*\.?\d+', q_m.group(1).replace(',', '')).group(0)) if q_m else 0.0
            r_val = float(re.search(r'[-+]?\d*\.?\d+', r_m.group(1).replace(',', '')).group(0)) if r_m else 0.0
            v_val = float(re.search(r'[-+]?\d*\.?\d+', v_m.group(1).replace(',', '')).group(0)) if v_m else 0.0
            
            items.append({
                "guid": "",
                "master_id": 0,
                "alter_id": 0,
                "name": s_name.strip(),
                "parent": p_m.group(1).strip() if p_m else "WAGO",
                "category": c_m.group(1).strip() if c_m else "",
                "base_units": "PCS",
                "closing_stock": q_val,
                "closing_rate": r_val,
                "closing_value": v_val
            })
        return items

    @staticmethod
    def _parse_ledgers_regex(xml_text):
        ledgers = []
        raw_blocks = re.findall(r'<LEDGER[^>]*NAME="([^"]+)"[^>]*>(.*?)</LEDGER>', xml_text, re.DOTALL | re.IGNORECASE)
        for l_name, l_content in raw_blocks:
            p_m = re.search(r'<PARENT>([^<]+)</PARENT>', l_content)
            g_m = re.search(r'<PARTYGSTIN>([^<]+)</PARTYGSTIN>', l_content)
            ph_m = re.search(r'<LEDGERPHONE>([^<]+)</LEDGERPHONE>', l_content)
            em_m = re.search(r'<EMAIL>([^<]+)</EMAIL>', l_content)
            
            ledgers.append({
                "guid": "",
                "master_id": 0,
                "alter_id": 0,
                "name": l_name.strip(),
                "parent": p_m.group(1).strip() if p_m else "",
                "gstin": g_m.group(1).strip() if g_m else "",
                "phone": ph_m.group(1).strip() if ph_m else "",
                "email": em_m.group(1).strip() if em_m else "",
                "address": ""
            })
        return ledgers
