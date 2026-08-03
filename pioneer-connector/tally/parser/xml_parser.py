import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from tally.parser.xml_validator import TallyXMLValidator
from tally.models.stock import TallyStockItem, TallyStockGroup
from tally.models.ledger import TallyLedger

class TallyXMLParser:
    """DOM-based parser converting validated Tally XML responses into strongly-typed objects."""

    @classmethod
    def parse_ledgers(cls, xml_content: str) -> List[TallyLedger]:
        """Parses Tally Ledgers XML response into a list of TallyLedger instances."""
        root = TallyXMLValidator.validate_xml(xml_content)
        ledgers = []

        for elem in root.iter():
            if elem.tag.upper() == "LEDGER":
                name_elem = elem.find("NAME")
                if name_elem is None:
                    name_elem = elem.find(".//NAME")
                    
                if name_elem is not None and name_elem.text:
                    guid_elem = elem.find("GUID")
                    parent_elem = elem.find("PARENT")
                    bal_elem = elem.find("CLOSINGBALANCE")
                    
                    gst_elem = elem.find("PARTYGSTIN")
                    if gst_elem is None:
                        gst_elem = elem.find("GSTIN")

                    phone_elem = elem.find("LEDGERPHONE") or elem.find("PHONE") or elem.find("MOBILE")
                    email_elem = elem.find("EMAIL")
                    state_elem = elem.find("LEDGERSTATENAME") or elem.find("STATE")
                    pin_elem = elem.find("PINCODE") or elem.find("PIN")

                    # Address multi-line concatenation
                    addr_lines = []
                    addr_list = elem.find("ADDRESS.LIST")
                    if addr_list is not None:
                        for addr_line in addr_list.findall("ADDRESS"):
                            if addr_line.text:
                                addr_lines.append(addr_line.text.strip())
                    elif elem.find("ADDRESS") is not None and elem.find("ADDRESS").text:
                        addr_lines.append(elem.find("ADDRESS").text.strip())

                    address_str = ", ".join(addr_lines) if addr_lines else None

                    closing_bal = 0.0
                    if bal_elem is not None and bal_elem.text:
                        try:
                            clean_bal = bal_elem.text.replace("Dr", "").replace("Cr", "").replace(",", "").strip()
                            closing_bal = float(clean_bal)
                        except ValueError:
                            closing_bal = 0.0

                    parent_grp = parent_elem.text.strip() if parent_elem is not None and parent_elem.text else "Primary"
                    ledger_type = cls._categorize_ledger_group(parent_grp)

                    ledgers.append(TallyLedger(
                        guid=guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None,
                        name=name_elem.text.strip(),
                        parent_group=parent_grp,
                        ledger_type=ledger_type,
                        closing_balance=closing_bal,
                        gstin=gst_elem.text.strip() if gst_elem is not None and gst_elem.text else None,
                        address=address_str,
                        phone=phone_elem.text.strip() if phone_elem is not None and phone_elem.text else None,
                        email=email_elem.text.strip() if email_elem is not None and email_elem.text else None,
                        state=state_elem.text.strip() if state_elem is not None and state_elem.text else None,
                        pin_code=pin_elem.text.strip() if pin_elem is not None and pin_elem.text else None
                    ))

        return ledgers

    @staticmethod
    def _categorize_ledger_group(parent_group: str) -> str:
        """Categorizes Tally parent group into canonical ledger type."""
        grp_lower = parent_group.lower()
        if "debtor" in grp_lower or "customer" in grp_lower:
            return "customer"
        elif "creditor" in grp_lower or "supplier" in grp_lower or "vendor" in grp_lower:
            return "supplier"
        elif "expense" in grp_lower:
            return "expense"
        elif "income" in grp_lower or "sales" in grp_lower:
            return "income"
        elif "duti" in grp_lower or "tax" in grp_lower or "gst" in grp_lower:
            return "tax"
        return "general"

    @classmethod
    def parse_stock_groups(cls, xml_content: str) -> List[TallyStockGroup]:
        """Parses Tally Stock Groups XML response into a list of TallyStockGroup instances."""
        root = TallyXMLValidator.validate_xml(xml_content)
        groups = []

        for elem in root.iter():
            if elem.tag.upper() in ("STOCKGROUP", "STOCKITEMGROUP"):
                name_elem = elem.find("NAME") or elem.find(".//NAME")
                if name_elem is not None and name_elem.text:
                    guid_elem = elem.find("GUID")
                    parent_elem = elem.find("PARENT")
                    name = name_elem.text.strip()
                    series = name.split()[0] if name else None

                    groups.append(TallyStockGroup(
                        guid=guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None,
                        name=name,
                        parent_group=parent_elem.text.strip() if parent_elem is not None and parent_elem.text else "Primary",
                        series_code=series
                    ))

        return groups

    @classmethod
    def parse_stock_items(cls, xml_content: str) -> List[TallyStockItem]:
        """Parses Tally Stock Items XML response into a list of TallyStockItem instances."""
        root = TallyXMLValidator.validate_xml(xml_content)
        items = []

        for elem in root.iter():
            if elem.tag.upper() == "STOCKITEM":
                name_elem = elem.find("NAME")
                if name_elem is None:
                    name_elem = elem.find(".//NAME")
                    
                if name_elem is not None and name_elem.text:
                    guid_elem = elem.find("GUID")
                    parent_elem = elem.find("PARENT")
                    
                    part_elem = elem.find("MAILINGNAME")
                    if part_elem is None:
                        part_elem = elem.find("PARTNUMBER")
                        
                    bal_elem = elem.find("CLOSINGBALANCE")
                    rate_elem = elem.find("CLOSINGRATE")
                    val_elem = elem.find("CLOSINGVALUE")

                    purc_elem = elem.find("PURCHASEORDERSDUE") or elem.find("PURCHASEPENDING")
                    sales_elem = elem.find("SALESORDERSDUE") or elem.find("SALEDUE")
                    reorder_elem = elem.find("REORDERLEVEL")

                    closing_bal = cls._parse_numeric(bal_elem)
                    closing_rate = cls._parse_numeric(rate_elem)
                    closing_val = cls._parse_numeric(val_elem)
                    purc_pending = cls._parse_numeric(purc_elem)
                    sales_due = cls._parse_numeric(sales_elem)
                    reorder_lvl = cls._parse_numeric(reorder_elem)

                    nett_avail = closing_bal + purc_pending - sales_due
                    shortfall = max(0.0, reorder_lvl - nett_avail)

                    items.append(TallyStockItem(
                        guid=guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None,
                        name=name_elem.text.strip(),
                        parent_group=parent_elem.text.strip() if parent_elem is not None and parent_elem.text else "Primary",
                        part_number=part_elem.text.strip() if part_elem is not None and part_elem.text else name_elem.text.strip(),
                        closing_balance=closing_bal,
                        closing_rate=closing_rate,
                        closing_value=closing_val,
                        purchase_pending=purc_pending,
                        sales_due=sales_due,
                        nett_available=nett_avail,
                        reorder_level=reorder_lvl,
                        shortfall=shortfall
                    ))

        return items

    @staticmethod
    def _parse_numeric(elem: Optional[ET.Element]) -> float:
        """Helper to parse numeric text from Tally XML tags safely."""
        if elem is None or not elem.text:
            return 0.0
        txt = elem.text.replace(",", "").replace("Pcs", "").replace("PCS", "").strip()
        txt_parts = [p for p in txt.split() if p.replace(".", "", 1).replace("-", "", 1).isdigit()]
        if txt_parts:
            try:
                return float(txt_parts[0])
            except ValueError:
                return 0.0
        try:
            return float(txt)
        except ValueError:
            return 0.0
