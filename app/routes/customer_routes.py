from flask import Blueprint, request, jsonify
from app.services.customer_service import CustomerService

customer_bp = Blueprint('customer_routes', __name__)

@customer_bp.route('/api/customers', methods=['GET'])
def list_customers():
    q = request.args.get('q')
    customers = CustomerService.get_customers(q)
    return jsonify(customers)

@customer_bp.route('/api/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    customer = CustomerService.get_customer_by_id(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    return jsonify(customer)

@customer_bp.route('/api/customers', methods=['POST'])
def create_customer():
    data = request.get_json() or {}
    name = data.get('name')
    discount_percentage = data.get('discount_percentage', 0)
    gst_number = data.get('gst_number')
    payment_terms = data.get('payment_terms')
    
    if not name:
        return jsonify({"error": "Customer name is required"}), 400
        
    try:
        new_cust = CustomerService.create_customer(name, discount_percentage, gst_number, payment_terms)
        return jsonify(new_cust), 210
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@customer_bp.route('/api/customers/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    data = request.get_json() or {}
    name = data.get('name')
    discount_percentage = data.get('discount_percentage', 0)
    gst_number = data.get('gst_number')
    payment_terms = data.get('payment_terms')
    
    if not name:
        return jsonify({"error": "Customer name is required"}), 400
        
    try:
        updated_cust = CustomerService.update_customer(customer_id, name, discount_percentage, gst_number, payment_terms)
        return jsonify(updated_cust)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@customer_bp.route('/api/customers/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    try:
        CustomerService.delete_customer(customer_id)
        return jsonify({"success": True, "message": "Customer deleted successfully"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
