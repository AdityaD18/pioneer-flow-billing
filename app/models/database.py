import os
import sqlite3
from flask import g

DATABASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'db'))
DATABASE_PATH = os.path.join(DATABASE_DIR, 'database.db')
SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql'))

def init_db():
    """Initializes the database using the schema.sql script."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs(os.path.abspath(os.path.join(DATABASE_DIR, '..', 'uploads')), exist_ok=True)
    os.makedirs(os.path.abspath(os.path.join(DATABASE_DIR, '..', 'exports')), exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

import threading
local_storage = threading.local()

def get_db_connection():
    """Gets a raw sqlite3 connection with standard settings."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def get_db():
    """Gets database connection, using Flask g context if available, otherwise thread-local storage."""
    try:
        from flask import has_app_context, g
        if has_app_context():
            db = getattr(g, '_database', None)
            if db is None:
                db = g._database = get_db_connection()
            return db
    except ImportError:
        pass
        
    # Thread-local storage fallback (for Streamlit, unit tests, etc.)
    db = getattr(local_storage, 'database', None)
    if db is None:
        db = local_storage.database = get_db_connection()
    return db

def close_connection(exception):
    """Closes the context connection if active."""
    # Close flask context connection
    try:
        from flask import has_app_context, g
        if has_app_context():
            db = getattr(g, '_database', None)
            if db is not None:
                db.close()
                return
    except ImportError:
        pass

    # Close thread-local connection if it exists
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
