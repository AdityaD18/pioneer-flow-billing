import os
import sqlite3
import threading
from datetime import datetime
from app.core.config import Config

DATABASE_DIR = Config.DATABASE_DIR
DATABASE_PATH = Config.DATABASE_PATH
SCHEMA_PATH = Config.SCHEMA_PATH

local_storage = threading.local()

def init_db():
    """Initializes the database using the schema.sql script and seeds default customer data if empty."""
    os.makedirs(Config.DATABASE_DIR, exist_ok=True)
    os.makedirs(Config.UPLOADS_DIR, exist_ok=True)
    os.makedirs(Config.EXPORTS_DIR, exist_ok=True)
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    with open(Config.SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    conn.executescript(schema_sql)
    
    # Run migrations for INVENTORY table if new columns are missing
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(INVENTORY)")
    columns = [col[1] for col in cursor.fetchall()]
    
    new_cols = {
        "purc_orders_pending": "REAL DEFAULT 0",
        "sale_orders_due": "REAL DEFAULT 0",
        "nett_available": "REAL DEFAULT 0",
        "reorder_level": "REAL DEFAULT 0",
        "short_fall": "REAL DEFAULT 0",
        "min_reorder_qty": "REAL DEFAULT 0",
        "order_to_be_placed": "REAL DEFAULT 0"
    }
    
    for col_name, col_type in new_cols.items():
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE INVENTORY ADD COLUMN {col_name} {col_type};")
    
    # Seed 1 Demo Customer
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM CUSTOMERS")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO CUSTOMERS (name, discount_percentage, gst_number, payment_terms, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("Demo1", 10.0, "27DEMO11234A1Z1", Config.DEFAULT_PAYMENT_TERMS, now_str, now_str)
        )
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Gets a raw sqlite3 connection with standard settings."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def get_db():
    """Gets database connection using thread-local storage."""
    db = getattr(local_storage, 'database', None)
    if db is None:
        db = local_storage.database = get_db_connection()
    return db

def close_connection(exception=None):
    """Closes the context connection if active."""
    db = getattr(local_storage, 'database', None)
    if db is not None:
        db.close()
        local_storage.database = None

def query_db(query, args=(), one=False):
    """Utility to query the database and return dictionary rows."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Utility to execute a modifying command and commit it, returns lastrowid."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id

def execute_transaction(queries_with_args):
    """Executes a list of (query, args) tuples inside a single transaction."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE TRANSACTION;")
        for query, args in queries_with_args:
            cur.execute(query, args)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
