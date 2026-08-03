import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from tally.parser.xml_validator import TallyXMLValidator
from tally.models.stock import TallyStockItem
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

                    closing_bal = 0.0
                    if bal_elem is not None and bal_elem.text:
                        try:
                            clean_bal = bal_elem.text.replace("Dr", "").replace("Cr", "").replace(",", "").strip()
                            closing_bal = float(clean_bal)
                        except ValueError:
                            closing_bal = 0.0

                    ledgers.append(TallyLedger(
                        guid=guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None,
                        name=name_elem.text.strip(),
                        parent_group=parent_elem.text.strip() if parent_elem is not None and parent_elem.text else "Primary",
                        closing_balance=closing_bal,
                        gstin=gst_elem.text.strip() if gst_elem is not None and gst_elem.text else None
                    ))

        return ledgers

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

                    closing_bal = cls._parse_numeric(bal_elem)
                    closing_rate = cls._parse_numeric(rate_elem)
                    closing_val = cls._parse_numeric(val_elem)

                    items.append(TallyStockItem(
                        guid=guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None,
                        name=name_elem.text.strip(),
                        parent_group=parent_elem.text.strip() if parent_elem is not None and parent_elem.text else "Primary",
                        part_number=part_elem.text.strip() if part_elem is not None and part_elem.text else name_elem.text.strip(),
                        closing_balance=closing_bal,
                        closing_rate=closing_rate,
                        closing_value=closing_val
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
