-- Mechanical Parts Invoice Automation System Schema

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- 1. PRODUCTS
CREATE TABLE IF NOT EXISTS PRODUCTS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number TEXT UNIQUE NOT NULL,
    part_name TEXT NULL,
    series TEXT NULL,
    make TEXT NULL,
    unit TEXT DEFAULT 'PCS',
    packing_quantity INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_products_part_number ON PRODUCTS(part_number);

-- 2. INVENTORY
CREATE TABLE IF NOT EXISTS INVENTORY (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER UNIQUE NOT NULL REFERENCES PRODUCTS(id) ON DELETE CASCADE,
    current_stock REAL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. PRODUCT_COSTS
CREATE TABLE IF NOT EXISTS PRODUCT_COSTS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES PRODUCTS(id) ON DELETE CASCADE,
    price_per_100_pcs REAL NOT NULL,
    price_per_unit REAL NOT NULL,
    effective_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    effective_to TIMESTAMP NULL,
    is_current BOOLEAN DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_product_costs_current ON PRODUCT_COSTS(product_id, is_current);

-- 4. CUSTOMERS
CREATE TABLE IF NOT EXISTS CUSTOMERS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    discount_percentage REAL DEFAULT 0,
    gst_number TEXT NULL,
    payment_terms TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. IMPORT_LOG
CREATE TABLE IF NOT EXISTS IMPORT_LOG (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_type TEXT NOT NULL, -- 'inventory' or 'cost'
    filename TEXT NOT NULL,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_records INTEGER DEFAULT 0,
    successful_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    imported_by TEXT NULL,
    status TEXT NOT NULL -- 'success', 'partial_success', 'failed'
);

-- 6. ORDERS
CREATE TABLE IF NOT EXISTS ORDERS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES CUSTOMERS(id) ON DELETE RESTRICT,
    customer_name_snapshot TEXT NOT NULL,
    customer_gst_snapshot TEXT NULL,
    customer_terms_snapshot TEXT NULL,
    discount_percentage REAL DEFAULT 0,
    subtotal REAL DEFAULT 0,
    discount_amount REAL DEFAULT 0,
    gst_amount REAL DEFAULT 0,
    grand_total REAL DEFAULT 0,
    gst_rate REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. ORDER_ITEMS
CREATE TABLE IF NOT EXISTS ORDER_ITEMS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES ORDERS(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES PRODUCTS(id) ON DELETE RESTRICT,
    part_number_snapshot TEXT NOT NULL,
    part_name_snapshot TEXT NULL,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL, -- price per 100 pcs
    discount_percentage REAL DEFAULT 0,
    gst_percentage REAL DEFAULT 0,
    line_total REAL NOT NULL
);

-- 8. INVOICES
CREATE TABLE IF NOT EXISTS INVOICES (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    order_id INTEGER UNIQUE NOT NULL REFERENCES ORDERS(id) ON DELETE RESTRICT,
    invoice_date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. INVOICE_SEQUENCE
CREATE TABLE IF NOT EXISTS INVOICE_SEQUENCE (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year TEXT NOT NULL,
    seq_number INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_invoice_seq ON INVOICE_SEQUENCE(year, seq_number);

-- 10. APP_SETTINGS
CREATE TABLE IF NOT EXISTS APP_SETTINGS (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Insert default configurations
INSERT OR IGNORE INTO APP_SETTINGS (key, value) VALUES ('gst_rate', '18.0');

-- 11. QUOTATIONS
CREATE TABLE IF NOT EXISTS QUOTATIONS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_number TEXT UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES CUSTOMERS(id) ON DELETE RESTRICT,
    customer_name_snapshot TEXT NOT NULL,
    customer_gst_snapshot TEXT NULL,
    customer_terms_snapshot TEXT NULL,
    discount_percentage REAL DEFAULT 0,
    subtotal REAL DEFAULT 0,
    discount_amount REAL DEFAULT 0,
    gst_amount REAL DEFAULT 0,
    grand_total REAL DEFAULT 0,
    gst_rate REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. QUOTATION_ITEMS
CREATE TABLE IF NOT EXISTS QUOTATION_ITEMS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_id INTEGER NOT NULL REFERENCES QUOTATIONS(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES PRODUCTS(id) ON DELETE RESTRICT,
    part_number_snapshot TEXT NOT NULL,
    part_name_snapshot TEXT NULL,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL, -- price per 100 pcs snapshot
    discount_percentage REAL DEFAULT 0,
    gst_percentage REAL DEFAULT 0,
    line_total REAL NOT NULL
);

-- 13. QUOTATION_SEQUENCE
CREATE TABLE IF NOT EXISTS QUOTATION_SEQUENCE (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year TEXT NOT NULL,
    seq_number INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_quotation_seq ON QUOTATION_SEQUENCE(year, seq_number);
