import os
import sqlite3
from datetime import datetime
from .logger import tally_logger

CACHE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'db', 'cache.db'))
PROD_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'db', 'database.db'))

class TallyCacheManager:
    """Manages local cache database (cache.db) and synchronizes with main SQLite database (database.db)."""

    def __init__(self, cache_db_path=CACHE_DB_PATH, prod_db_path=PROD_DB_PATH):
        self.cache_db_path = cache_db_path
        self.prod_db_path = prod_db_path
        self._init_cache_schema()

    def _get_cache_conn(self):
        conn = sqlite3.connect(self.cache_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_prod_conn(self):
        conn = sqlite3.connect(self.prod_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_cache_schema(self):
        os.makedirs(os.path.dirname(self.cache_db_path), exist_ok=True)
        conn = self._get_cache_conn()
        cur = conn.cursor()
        
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS CACHE_STOCK_ITEMS (
                guid TEXT PRIMARY KEY,
                master_id INTEGER,
                alter_id INTEGER,
                name TEXT UNIQUE NOT NULL,
                parent TEXT,
                category TEXT,
                base_units TEXT,
                closing_stock REAL DEFAULT 0.0,
                closing_rate REAL DEFAULT 0.0,
                closing_value REAL DEFAULT 0.0,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS CACHE_LEDGERS (
                guid TEXT PRIMARY KEY,
                master_id INTEGER,
                alter_id INTEGER,
                name TEXT UNIQUE NOT NULL,
                parent TEXT,
                gstin TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS CACHE_SYNC_METRICS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT NOT NULL,
                status TEXT NOT NULL,
                stock_count INTEGER DEFAULT 0,
                ledger_count INTEGER DEFAULT 0,
                duration_sec REAL DEFAULT 0.0,
                error_msg TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()

    def get_max_alter_id(self, table_name="CACHE_STOCK_ITEMS"):
        conn = self._get_cache_conn()
        cur = conn.cursor()
        cur.execute(f"SELECT MAX(alter_id) as max_id FROM {table_name}")
        row = cur.fetchone()
        conn.close()
        return row['max_id'] if row and row['max_id'] else 0

    def update_cache_stock_items(self, stock_items):
        """Updates local cache.db with fetched stock items."""
        conn = self._get_cache_conn()
        cur = conn.cursor()
        
        updated_count = 0
        for item in stock_items:
            guid = item.get('guid') or f"GUID_STOCK_{hash(item['name'])}"
            cur.execute("""
                INSERT INTO CACHE_STOCK_ITEMS (
                    guid, master_id, alter_id, name, parent, category, base_units,
                    closing_stock, closing_rate, closing_value, last_synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(name) DO UPDATE SET
                    alter_id=excluded.alter_id,
                    parent=excluded.parent,
                    category=excluded.category,
                    closing_stock=excluded.closing_stock,
                    closing_rate=excluded.closing_rate,
                    closing_value=excluded.closing_value,
                    last_synced=datetime('now')
            """, (
                guid, item.get('master_id', 0), item.get('alter_id', 0), item['name'],
                item.get('parent', 'WAGO'), item.get('category', ''), item.get('base_units', 'PCS'),
                item.get('closing_stock', 0.0), item.get('closing_rate', 0.0), item.get('closing_value', 0.0)
            ))
            updated_count += 1
            
        conn.commit()
        conn.close()
        tally_logger.info(f"💾 Updated {updated_count:,} stock items in local cache.db.")

    def update_cache_ledgers(self, ledgers):
        """Updates local cache.db with fetched ledgers."""
        conn = self._get_cache_conn()
        cur = conn.cursor()
        
        updated_count = 0
        for leg in ledgers:
            guid = leg.get('guid') or f"GUID_LEDGER_{hash(leg['name'])}"
            cur.execute("""
                INSERT INTO CACHE_LEDGERS (
                    guid, master_id, alter_id, name, parent, gstin, phone, email, address, last_synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(name) DO UPDATE SET
                    alter_id=excluded.alter_id,
                    gstin=excluded.gstin,
                    phone=excluded.phone,
                    email=excluded.email,
                    address=excluded.address,
                    last_synced=datetime('now')
            """, (
                guid, leg.get('master_id', 0), leg.get('alter_id', 0), leg['name'],
                leg.get('parent', ''), leg.get('gstin', ''), leg.get('phone', ''),
                leg.get('email', ''), leg.get('address', '')
            ))
            updated_count += 1
            
        conn.commit()
        conn.close()
        tally_logger.info(f"💾 Updated {updated_count:,} ledgers in local cache.db.")

    def sync_cache_to_prod_database(self):
        """Pushes validated cached records from cache.db to production database.db."""
        c_conn = self._get_cache_conn()
        p_conn = self._get_prod_conn()
        
        c_cur = c_conn.cursor()
        p_cur = p_conn.cursor()
        p_cur.execute("BEGIN TRANSACTION;")
        
        # 1. Sync Products & Inventory
        c_cur.execute("SELECT * FROM CACHE_STOCK_ITEMS")
        cached_stocks = c_cur.fetchall()
        
        prod_count = 0
        for row in cached_stocks:
            p_name = row['name']
            p_make = row['parent'] or 'WAGO'
            q_val = row['closing_stock']
            r_val = row['closing_rate']
            
            p_cur.execute("SELECT id FROM PRODUCTS WHERE part_number = ?", (p_name,))
            p_row = p_cur.fetchone()
            if not p_row:
                series = p_name.split('-')[0] if '-' in p_name else None
                p_cur.execute(
                    "INSERT INTO PRODUCTS (part_number, part_name, series, make) VALUES (?, ?, ?, ?)",
                    (p_name, p_name, series, p_make)
                )
                p_id = p_cur.lastrowid
            else:
                p_id = p_row['id']
                p_cur.execute("UPDATE PRODUCTS SET make = ? WHERE id = ?", (p_make, p_id))
                
            p_cur.execute("SELECT id FROM INVENTORY WHERE product_id = ?", (p_id,))
            inv_row = p_cur.fetchone()
            if not inv_row:
                p_cur.execute(
                    "INSERT INTO INVENTORY (product_id, current_stock, last_updated) VALUES (?, ?, datetime('now'))",
                    (p_id, q_val)
                )
            else:
                p_cur.execute(
                    "UPDATE INVENTORY SET current_stock = ?, last_updated = datetime('now') WHERE product_id = ?",
                    (q_val, p_id)
                )
                
            if r_val > 0:
                p_cur.execute("UPDATE PRODUCT_COSTS SET is_current = 0 WHERE product_id = ? AND is_current = 1", (p_id,))
                p_cur.execute(
                    "INSERT INTO PRODUCT_COSTS (product_id, price_per_100_pcs, price_per_unit, effective_from, is_current) VALUES (?, ?, ?, datetime('now'), 1)",
                    (p_id, r_val, r_val / 100.0)
                )
            prod_count += 1
            
        # 2. Sync Customers / Ledgers
        c_cur.execute("SELECT * FROM CACHE_LEDGERS")
        cached_ledgers = c_cur.fetchall()
        
        cust_count = 0
        for leg in cached_ledgers:
            c_name = leg['name']
            parent_grp = (leg['parent'] or "").strip().lower()
            
            # Filter Sundry Debtors
            if parent_grp and not any(kw in parent_grp for kw in ['debtor', 'customer']):
                continue
                
            gstin = leg['gstin'] or ""
            p_cur.execute("SELECT id FROM CUSTOMERS WHERE LOWER(name) = LOWER(?)", (c_name,))
            ex = p_cur.fetchone()
            if ex:
                if gstin:
                    p_cur.execute("UPDATE CUSTOMERS SET gst_number = ? WHERE id = ?", (gstin, ex['id']))
            else:
                p_cur.execute("INSERT INTO CUSTOMERS (name, discount_percentage, gst_number) VALUES (?, ?, ?)", (c_name, 0.0, gstin))
            cust_count += 1
            
        p_conn.commit()
        c_conn.close()
        p_conn.close()
        
        tally_logger.info(f"🔄 Production database.db updated: {prod_count:,} SKUs, {cust_count:,} Customers.")
        return {"products": prod_count, "customers": cust_count}

    def log_sync_metric(self, sync_type, status, stock_count, ledger_count, duration_sec, error_msg=None):
        conn = self._get_cache_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO CACHE_SYNC_METRICS (
                sync_type, status, stock_count, ledger_count, duration_sec, error_msg, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (sync_type, status, stock_count, ledger_count, duration_sec, error_msg))
        conn.commit()
        conn.close()

    def get_latest_sync_metrics(self):
        conn = self._get_cache_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM CACHE_SYNC_METRICS ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
