import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tally.xml.xml_builder import TallyXMLBuilder
from tally.parser.xml_validator import TallyXMLValidator, XMLValidationError
from tally.parser.xml_parser import TallyXMLParser

class TestXMLEngine(unittest.TestCase):
    def test_xml_builder_export_request(self):
        xml_str = TallyXMLBuilder.build_export_request("List of Companies")
        self.assertIn("<REPORTNAME>List of Companies</REPORTNAME>", xml_str)
        self.assertIn("<SVEXPORTFORMAT>$$SYSNAME:XML</SVEXPORTFORMAT>", xml_str)

    def test_xml_builder_voucher_post(self):
        vch = {
            "voucher_type": "Sales",
            "date": "20260803",
            "voucher_number": "INV-101",
            "party_name": "Acme Industrial",
            "ledger_entries": [{"ledger_name": "Sales Account", "amount": -5000.0}]
        }
        xml_str = TallyXMLBuilder.build_voucher_post_request(vch)
        self.assertIn("<VOUCHERNUMBER>INV-101</VOUCHERNUMBER>", xml_str)
        self.assertIn("<PARTYLEDGERNAME>Acme Industrial</PARTYLEDGERNAME>", xml_str)

    def test_xml_validator_success(self):
        valid_xml = "<ENVELOPE><BODY><DATA>Test</DATA></BODY></ENVELOPE>"
        root = TallyXMLValidator.validate_xml(valid_xml)
        self.assertEqual(root.tag, "ENVELOPE")

    def test_xml_validator_malformed_raises(self):
        malformed = "<ENVELOPE><BODY>Unclosed Tag"
        with self.assertRaises(XMLValidationError):
            TallyXMLValidator.validate_xml(malformed)

    def test_xml_validator_tally_lineerror_raises(self):
        tally_err = "<ENVELOPE><LINEERROR>Ledger does not exist</LINEERROR></ENVELOPE>"
        with self.assertRaises(XMLValidationError):
            TallyXMLValidator.validate_xml(tally_err)

    def test_xml_parser_ledgers(self):
        sample_ledger_xml = """<ENVELOPE>
            <BODY>
                <DATA>
                    <TALLYMESSAGE>
                        <LEDGER>
                            <NAME>WAGO India Pvt Ltd</NAME>
                            <PARENT>Sundry Creditors</PARENT>
                            <CLOSINGBALANCE>25000.00 Dr</CLOSINGBALANCE>
                            <PARTYGSTIN>27AAACW1234F1Z0</PARTYGSTIN>
                        </LEDGER>
                    </TALLYMESSAGE>
                </DATA>
            </BODY>
        </ENVELOPE>"""
        ledgers = TallyXMLParser.parse_ledgers(sample_ledger_xml)
        self.assertEqual(len(ledgers), 1)
        self.assertEqual(ledgers[0].name, "WAGO India Pvt Ltd")
        self.assertEqual(ledgers[0].parent_group, "Sundry Creditors")
        self.assertEqual(ledgers[0].closing_balance, 25000.0)
        self.assertEqual(ledgers[0].gstin, "27AAACW1234F1Z0")

    def test_xml_parser_stock_items(self):
        sample_stock_xml = """<ENVELOPE>
            <BODY>
                <DATA>
                    <TALLYMESSAGE>
                        <STOCKITEM>
                            <NAME>209-120</NAME>
                            <PARENT>209 Series</PARENT>
                            <CLOSINGBALANCE>150.00 PCS</CLOSINGBALANCE>
                            <CLOSINGRATE>45.50</CLOSINGRATE>
                        </STOCKITEM>
                    </TALLYMESSAGE>
                </DATA>
            </BODY>
        </ENVELOPE>"""
        items = TallyXMLParser.parse_stock_items(sample_stock_xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "209-120")
        self.assertEqual(items[0].parent_group, "209 Series")
        self.assertEqual(items[0].closing_balance, 150.0)

if __name__ == '__main__':
    unittest.main()
