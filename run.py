import os
from app.models.database import init_db, close_connection
from flask import Flask, render_template

def create_app():
    # Initialize SQLite database (folders, tables, indices) on application launch
    init_db()
    
    app = Flask(__name__, 
                static_folder='app/static', 
                template_folder='app/templates')
    
    # Configure secrets
    app.config['SECRET_KEY'] = 'dev-key-antigravity-mechanical-invoice'
    
    # Register blueprints
    from app.routes.import_routes import import_bp
    from app.routes.customer_routes import customer_bp
    from app.routes.invoice_routes import invoice_bp
    from app.routes.dashboard import dashboard_bp
    
    app.register_blueprint(import_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(invoice_bp)
    app.register_blueprint(dashboard_bp)
    
    # Teardown connection
    app.teardown_appcontext(close_connection)
    
    @app.route('/')
    def index():
        return render_template('index.html')
        
    return app

if __name__ == '__main__':
    app = create_app()
    # Run locally on port 5000
    app.run(host='127.0.0.1', port=5000, debug=True)
