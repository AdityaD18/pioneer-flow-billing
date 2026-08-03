from io import BytesIO
from xhtml2pdf import pisa
from app.core.templates.invoice_template import generate_invoice_html
from app.core.templates.quotation_template import generate_quotation_html

def generate_pdf_from_html(html_str):
    """Converts HTML string into PDF binary stream using xhtml2pdf."""
    result = BytesIO()
    pisa_status = pisa.CreatePDF(html_str, dest=result)
    if pisa_status.err:
        return None
    return result.getvalue()
