import xml.etree.ElementTree as ET

class XMLValidationError(Exception):
    """Raised when Tally XML payload is malformed, truncated, or contains errors."""
    pass

class TallyXMLValidator:
    """Validator verifying integrity and well-formedness of Tally XML payloads."""

    @classmethod
    def validate_xml(cls, xml_content: str) -> ET.Element:
        """
        Validates raw XML text for well-formedness and Tally error envelopes.
        Returns parsed ElementTree root element if valid.
        Raises XMLValidationError on malformed XML or explicit Tally errors.
        """
        if not xml_content or not xml_content.strip():
            raise XMLValidationError("Empty XML response received from Tally.")

        try:
            root = ET.fromstring(xml_content.strip())
        except ET.ParseError as e:
            raise XMLValidationError(f"Malformed XML response: {str(e)}")

        # Check for Tally error tags
        cls._check_for_tally_errors(root)
        return root

    @classmethod
    def _check_for_tally_errors(cls, root: ET.Element):
        """Recursively checks for Tally error indicators within the XML DOM."""
        for elem in root.iter():
            tag_name = elem.tag.upper()
            if tag_name in ("LINEERROR", "ERRORMESSAGE", "PARSEERROR"):
                if elem.text and elem.text.strip():
                    raise XMLValidationError(f"Tally server returned error: {elem.text.strip()}")
                    
            if tag_name == "STATUS" and elem.text and elem.text.strip() == "0":
                # Find sibling message if present
                msg = "Tally import failed with status 0."
                for sibling in root.iter():
                    if sibling.tag.upper() in ("LINEERROR", "MESSAGE", "RESPONSE"):
                        if sibling.text and sibling.text.strip():
                            msg = f"Tally import failed: {sibling.text.strip()}"
                            break
                raise XMLValidationError(msg)
