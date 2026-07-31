import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.services.import_service import ImportService
from app.models.database import query_db

import_bp = Blueprint('import_routes', __name__)

UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'uploads'))
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@import_bp.route('/api/import/inventory', methods=['POST'])
def import_inventory():
    if 'file' not in request.files:
        return jsonify({"status": "failed", "errors": ["No file part in the request"]}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "failed", "errors": ["No selected file"]}), 400
    
    if file and allowed_file(file.filename):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        sheet_name = request.form.get('sheet_name', 'Stock Group Reorder Status')
        
        result = ImportService.import_inventory(file_path, sheet_name=sheet_name, filename=filename)
        return jsonify(result)
    
    return jsonify({"status": "failed", "errors": ["Invalid file extension. Only Excel files are supported."]}), 400

@import_bp.route('/api/import/cost', methods=['POST'])
def import_cost():
    if 'file' not in request.files:
        return jsonify({"status": "failed", "errors": ["No file part in the request"]}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "failed", "errors": ["No selected file"]}), 400
    
    if file and allowed_file(file.filename):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        sheet_name = request.form.get('sheet_name', 'PRICE LIST')
        
        result = ImportService.import_costs(file_path, sheet_name=sheet_name, filename=filename)
        return jsonify(result)
    
    return jsonify({"status": "failed", "errors": ["Invalid file extension. Only Excel files are supported."]}), 400

@import_bp.route('/api/import/logs', methods=['GET'])
def get_import_logs():
    logs = query_db("SELECT * FROM IMPORT_LOG ORDER BY imported_at DESC LIMIT 50")
    # Convert Row objects to dict
    log_list = []
    for log in logs:
        log_list.append({
            "id": log["id"],
            "import_type": log["import_type"],
            "filename": log["filename"],
            "imported_at": log["imported_at"],
            "total_records": log["total_records"],
            "successful_records": log["successful_records"],
            "failed_records": log["failed_records"],
            "imported_by": log["imported_by"],
            "status": log["status"]
        })
    return jsonify(log_list)
