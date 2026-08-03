def generate_quotation_html(quotation_data):
    """Generates print-ready HTML for Quotation documents."""
    q = quotation_data
    items = q['items']
    
    rows_html = ""
    for idx, item in enumerate(items, 1):
        price_per_100 = float(item['unit_price'])
        rate_per_pc = price_per_100 / 100.0
        
        rows_html += f"""
        <tr>
            <td style="text-align: center;">{idx}</td>
            <td><strong>{item['part_number_snapshot']}</strong><br><small>{item['part_name_snapshot'] or ''}</small></td>
            <td style="text-align: right;">{item['quantity']:,.0f}</td>
            <td style="text-align: right;">Rs. {rate_per_pc:,.2f}</td>
            <td style="text-align: right;">{item['discount_percentage']:.1f}%</td>
            <td style="text-align: right;">Rs. {item['line_total']:,.2f}</td>
        </tr>
        """
        
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 1.5cm;
            }}
            body {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 11pt;
                color: #1E293B;
                line-height: 1.4;
            }}
            .header-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            .company-name {{
                font-size: 20pt;
                font-weight: bold;
                color: #0F172A;
            }}
            .doc-title {{
                font-size: 22pt;
                font-weight: bold;
                color: #D97706;
                text-align: right;
            }}
            .meta-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                background-color: #FEF3C7;
                border: 1px solid #FCD34D;
            }}
            .meta-table td {{
                padding: 10px;
                vertical-align: top;
            }}
            .items-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            .items-table th {{
                background-color: #0F172A;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px;
                font-size: 10pt;
            }}
            .items-table td {{
                padding: 8px;
                border-bottom: 1px solid #E2E8F0;
                font-size: 10pt;
            }}
            .summary-table {{
                width: 40%;
                float: right;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            .summary-table td {{
                padding: 6px;
                text-align: right;
            }}
            .total-row {{
                font-weight: bold;
                font-size: 12pt;
                background-color: #FEF3C7;
                border-top: 2px solid #D97706;
            }}
            .footer {{
                margin-top: 50px;
                font-size: 9pt;
                color: #64748B;
                text-align: center;
                border-top: 1px solid #E2E8F0;
                padding-top: 10px;
            }}
        </style>
    </head>
    <body>
        <table class="header-table">
            <tr>
                <td>
                    <div class="company-name">PIONEER AUTOMATION</div>
                    <div style="color: #64748B; font-size: 9pt;">Mechanical & Industrial Billing Solutions</div>
                </td>
                <td style="text-align: right;">
                    <div class="doc-title">QUOTATION</div>
                    <div><strong>Quotation #:</strong> {q['quotation_number']}</div>
                    <div><strong>Date:</strong> {q['created_at'][:10]}</div>
                </td>
            </tr>
        </table>
        
        <table class="meta-table">
            <tr>
                <td width="50%">
                    <strong style="color: #B45309;">PREPARED FOR:</strong><br>
                    <strong>{q['customer_name_snapshot']}</strong><br>
                    GSTIN: {q['customer_gst_snapshot'] or 'N/A'}<br>
                    Terms: {q['customer_terms_snapshot'] or 'Net 30 Days'}
                </td>
                <td width="50%">
                    <strong style="color: #B45309;">VALIDITY & TERMS:</strong><br>
                    Valid For: 30 Days<br>
                    Created: {q['created_at'][:10]}
                </td>
            </tr>
        </table>
        
        <table class="items-table">
            <thead>
                <tr>
                    <th width="8%">SR NO</th>
                    <th width="42%">PART NUMBER / DESCRIPTION</th>
                    <th width="15%" style="text-align: right;">QTY (PCS)</th>
                    <th width="15%" style="text-align: right;">RATE (PER PC)</th>
                    <th width="10%" style="text-align: right;">DISC %</th>
                    <th width="10%" style="text-align: right;">TOTAL</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        
        <table class="summary-table">
            <tr>
                <td>Subtotal:</td>
                <td><strong>Rs. {q['subtotal']:,.2f}</strong></td>
            </tr>
            <tr>
                <td>GST ({q['gst_rate']}%):</td>
                <td><strong>Rs. {q['gst_amount']:,.2f}</strong></td>
            </tr>
            <tr class="total-row">
                <td>Grand Total:</td>
                <td>Rs. {q['grand_total']:,.2f}</td>
            </tr>
        </table>
        
        <div style="clear: both;"></div>
        
        <div class="footer">
            Thank you for considering Pioneer Automation! | Commercial Proposal<br>
            This is a computer generated quotation. Prices are subject to final confirmation.
        </div>
    </body>
    </html>
    """
    return html
