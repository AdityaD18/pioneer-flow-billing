from typing import Dict, Any
from app.models.domain import Company
from app.core.config import Config

class CompanyMapper:
    """Converts Connector REST company JSON payloads into canonical Company domain models."""

    @staticmethod
    def to_domain(json_dict: Dict[str, Any]) -> Company:
        return Company(
            company_name=json_dict.get("company_name", Config.COMPANY_NAME),
            company_subtitle=Config.COMPANY_SUBTITLE,
            company_footer=Config.COMPANY_FOOTER,
            default_gst_rate=Config.DEFAULT_GST_RATE,
            default_payment_terms=Config.DEFAULT_PAYMENT_TERMS
        )
