import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Optional, List, Dict, Any

class TallyXMLBuilder:
    """Utility builder for constructing clean, formatted TallyPrime XML export and import envelopes."""

    @staticmethod
    def _prettify(elem: ET.Element) -> str:
        """Converts ElementTree to clean formatted XML string."""
        rough_string = ET.tostring(elem, encoding="utf-8")
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    @classmethod
    def build_export_request(
        cls, 
        report_name: str, 
        static_variables: Optional[Dict[str, str]] = None,
        company_name: Optional[str] = None
    ) -> str:
        """
        Builds standard Tally XML Export Data request envelope.
        """
        envelope = ET.Element("ENVELOPE")
        header = ET.SubElement(envelope, "HEADER")
        tally_req = ET.SubElement(header, "TALLYREQUEST")
        tally_req.text = "Export Data"

        body = ET.SubElement(envelope, "BODY")
        export_data = ET.SubElement(body, "EXPORTDATA")
        req_desc = ET.SubElement(export_data, "REQUESTDESC")

        report = ET.SubElement(req_desc, "REPORTNAME")
        report.text = report_name

        static_vars = ET.SubElement(req_desc, "STATICVARIABLES")
        
        # Mandatory export format
        fmt = ET.SubElement(static_vars, "SVEXPORTFORMAT")
        fmt.text = "$$SYSNAME:XML"
        
        if company_name:
            comp = ET.SubElement(static_vars, "SVCURRENTCOMPANY")
            comp.text = company_name

        if static_variables:
            for k, v in static_variables.items():
                var_elem = ET.SubElement(static_vars, k)
                var_elem.text = str(v)

        return ET.tostring(envelope, encoding="utf-8").decode("utf-8")

    @classmethod
    def build_ledger_export_request(cls, company_name: Optional[str] = None) -> str:
        """Builds XML request for fetching all Ledgers."""
        return cls.build_export_request("List of Ledgers", company_name=company_name)

    @classmethod
    def build_stock_item_export_request(cls, company_name: Optional[str] = None) -> str:
        """Builds XML request for fetching Stock Items & Stock Groups."""
        return cls.build_export_request("Stock Summary", company_name=company_name)

    @classmethod
    def build_voucher_post_request(cls, voucher_data: Dict[str, Any], company_name: Optional[str] = None) -> str:
        """
        Builds Tally XML Import Data envelope for posting a Sales/Purchase Voucher.
        """
        envelope = ET.Element("ENVELOPE")
        header = ET.SubElement(envelope, "HEADER")
        tally_req = ET.SubElement(header, "TALLYREQUEST")
        tally_req.text = "Import Data"

        body = ET.SubElement(envelope, "BODY")
        import_data = ET.SubElement(body, "IMPORTDATA")
        req_desc = ET.SubElement(import_data, "REQUESTDESC")

        req_type = ET.SubElement(req_desc, "REPORTNAME")
        req_type.text = "Vouchers"
        
        static_vars = ET.SubElement(req_desc, "STATICVARIABLES")
        if company_name:
            comp = ET.SubElement(static_vars, "SVCURRENTCOMPANY")
            comp.text = company_name

        req_data = ET.SubElement(import_data, "REQUESTDATA")
        tally_msg = ET.SubElement(req_data, "TALLYMESSAGE", xmlns="TallyServer")

        voucher = ET.SubElement(tally_msg, "VOUCHER", VCHTYPE=voucher_data.get("voucher_type", "Sales"))
        
        date_elem = ET.SubElement(voucher, "DATE")
        date_elem.text = voucher_data.get("date", "")
        
        vch_num = ET.SubElement(voucher, "VOUCHERNUMBER")
        vch_num.text = voucher_data.get("voucher_number", "")
        
        party = ET.SubElement(voucher, "PARTYLEDGERNAME")
        party.text = voucher_data.get("party_name", "")

        for entry in voucher_data.get("ledger_entries", []):
            entry_elem = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
            l_name = ET.SubElement(entry_elem, "LEDGERNAME")
            l_name.text = entry.get("ledger_name", "")
            amt = ET.SubElement(entry_elem, "AMOUNT")
            amt.text = str(entry.get("amount", 0.0))

        return ET.tostring(envelope, encoding="utf-8").decode("utf-8")
