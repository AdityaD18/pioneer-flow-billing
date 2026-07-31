from flask import Blueprint, request, jsonify
from app.services.order_service import OrderService
from app.services.invoice_service import InvoiceService
from app.models.database import query_db, execute_db

invoice_bp = Blueprint('invoice_routes', __name__)

@invoice_bp.route('/api/invoices/calculate', methods=['POST'])
def calculate_invoice():
    """Returns calculations for order preview without saving any records."""
    data = request.get_json() or {}
    customer_input = data.get('customer', {})
    items_input = data.get('items', [])
    
    if not items_input:
        return jsonify({"error": "At least one item is required for calculations."}), 400
        
    try:
        calc = OrderService.calculate_order(customer_input, items_input)
        return jsonify(calc)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@invoice_bp.route('/api/invoices', methods=['POST'])
def create_invoice():
    """Saves the Order (and customer inline if needed) and creates the Invoice."""
    data = request.get_json() or {}
    customer_input = data.get('customer', {})
    items_input = data.get('items', [])
    invoice_date = data.get('invoice_date')
    
    if not items_input:
        return jsonify({"error": "At least one item is required to create an invoice."}), 400
        
    try:
        # 1. Create order
        order_id = OrderService.create_order(customer_input, items_input)
        # 2. Generate invoice for the order
        invoice_id = InvoiceService.generate_invoice_for_order(order_id, invoice_date)
        # 3. Retrieve and return invoice details
        invoice_details = InvoiceService.get_invoice_by_id(invoice_id)
        return jsonify(invoice_details), 210
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@invoice_bp.route('/api/invoices', methods=['GET'])
def list_invoices():
    q = request.args.get('q')
    invoices = InvoiceService.get_invoices(q)
    return jsonify(invoices)

@invoice_bp.route('/api/invoices/<int:invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    invoice = InvoiceService.get_invoice_by_id(invoice_id)
    if not invoice:
        return jsonify({"error": "Invoice not found."}), 404
    return jsonify(invoice)

@invoice_bp.route('/api/products/search', methods=['GET'])
def search_products():
    """Searches products by Item Code, Part Name, Make, or Series."""
    q = request.args.get('q', '').strip()
    if not q:
        # Return top 50 products by default
        rows = query_db(
            """SELECT p.*, i.current_stock, c.price_per_100_pcs 
               FROM PRODUCTS p
               LEFT JOIN INVENTORY i ON p.id = i.product_id
               LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
               ORDER BY p.part_number ASC LIMIT 50"""
        )
    else:
        search_str = f"%{q}%"
        rows = query_db(
            """SELECT p.*, i.current_stock, c.price_per_100_pcs 
               FROM PRODUCTS p
               LEFT JOIN INVENTORY i ON p.id = i.product_id
               LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
               WHERE p.part_number LIKE ? OR p.part_name LIKE ? OR p.make LIKE ? OR p.series LIKE ?
               ORDER BY p.part_number ASC LIMIT 50""",
            (search_str, search_str, search_str, search_str)
        )
    
    products = []
    for r in rows:
        products.append({
            "id": r["id"],
            "part_number": r["part_number"],
            "part_name": r["part_name"] or r["part_number"],
            "series": r["series"],
            "make": r["make"],
            "unit": r["unit"],
            "packing_quantity": r["packing_quantity"],
            "current_stock": r["current_stock"] if r["current_stock"] is not None else 0.0,
            "price_per_100_pcs": r["price_per_100_pcs"] if r["price_per_100_pcs"] is not None else 0.0
        })
    return jsonify(products)

@invoice_bp.route('/api/settings', methods=['GET'])
def get_settings():
    settings = OrderService.get_settings()
    return jsonify(settings)

@invoice_bp.route('/api/settings', methods=['POST'])
def update_settings():
    data = request.get_json() or {}
    gst_rate = data.get('gst_rate')
    if gst_rate is not None:
        try:
            # Validate numeric
            float(gst_rate)
            execute_db("INSERT OR REPLACE INTO APP_SETTINGS (key, value) VALUES ('gst_rate', ?)", (str(gst_rate),))
            return jsonify({"success": True, "message": "Settings updated successfully."})
        except ValueError:
            return jsonify({"error": "GST rate must be a valid numeric percentage."}), 400
            
    return jsonify({"error": "Invalid settings payload."}), 400
