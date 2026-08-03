def generate_invoice_html(invoice_data):
    """Generates print-ready HTML for Invoice documents."""
    inv = invoice_data
    order = inv['order']
    items = inv['items']
    
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
                color: #0284C7;
                text-align: right;
            }}
            .meta-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
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
                background-color: #F0F9FF;
                border-top: 2px solid #0284C7;
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
                    <div class="doc-title">TAX INVOICE</div>
                    <div><strong>Invoice #:</strong> {inv['invoice_number']}</div>
                    <div><strong>Date:</strong> {inv['invoice_date']}</div>
                </td>
            </tr>
        </table>
        
        <table class="meta-table">
            <tr>
                <td width="50%">
                    <strong style="color: #0284C7;">BILLED TO:</strong><br>
                    <strong>{order['customer_name_snapshot']}</strong><br>
                    GSTIN: {order['customer_gst_snapshot'] or 'N/A'}<br>
                    Terms: {order['customer_terms_snapshot'] or 'Net 30 Days'}
                </td>
                <td width="50%">
                    <strong style="color: #0284C7;">ORDER DETAILS:</strong><br>
                    Order Ref: {order['order_number']}<br>
                    Created: {inv['created_at'][:10]}
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
                <td><strong>Rs. {order['subtotal']:,.2f}</strong></td>
            </tr>
            <tr>
                <td>GST ({order['gst_rate']}%):</td>
                <td><strong>Rs. {order['gst_amount']:,.2f}</strong></td>
            </tr>
            <tr class="total-row">
                <td>Grand Total:</td>
                <td>Rs. {order['grand_total']:,.2f}</td>
            </tr>
        </table>
        
        <div style="clear: both;"></div>
        
        <div class="footer">
            Thank you for your business! | Pioneer Automation Corp<br>
            This is a computer generated invoice and does not require physical signature.
        </div>
    </body>
    </html>
    """
    return html
