from flask import Blueprint, jsonify
from app.models.database import query_db

dashboard_bp = Blueprint('dashboard_bp', __name__)

@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Retrieves simple statistics for the MVP dashboard."""
    # 1. Total Products
    prod_count = query_db("SELECT COUNT(*) as c FROM PRODUCTS", one=True)['c']
    
    # 2. Total Customers
    cust_count = query_db("SELECT COUNT(*) as c FROM CUSTOMERS", one=True)['c']
    
    # 3. Total Invoices
    inv_count = query_db("SELECT COUNT(*) as c FROM INVOICES", one=True)['c']
    
    # 4. Last Inventory Import
    inv_import = query_db(
        "SELECT imported_at FROM IMPORT_LOG WHERE import_type='inventory' ORDER BY imported_at DESC LIMIT 1",
        one=True
    )
    last_inventory_import = inv_import['imported_at'] if inv_import else None
    
    # 5. Last Price Import
    price_import = query_db(
        "SELECT imported_at FROM IMPORT_LOG WHERE import_type='cost' ORDER BY imported_at DESC LIMIT 1",
        one=True
    )
    last_price_import = price_import['imported_at'] if price_import else None
    
    return jsonify({
        "total_products": prod_count,
        "total_customers": cust_count,
        "total_invoices": inv_count,
        "last_inventory_import": last_inventory_import,
        "last_price_import": last_price_import
    })
