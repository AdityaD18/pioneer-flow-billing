import os
import sqlite3
from datetime import datetime
from .logger import tally_logger

CACHE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'db', 'cache.db'))
PROD_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'db', 'database.db'))

class TallyCacheManager:
    """Manages local cache database (cache.db), sync manifests, deletion detection, and production DB sync."""

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
                alias TEXT,
                parent TEXT,
                category TEXT,
                description TEXT,
                base_units TEXT,
                hsn_code TEXT,
                closing_stock REAL DEFAULT 0.0,
                closing_rate REAL DEFAULT 0.0,
                closing_value REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS CACHE_LEDGERS (
                guid TEXT PRIMARY KEY,
                master_id INTEGER,
                alter_id INTEGER,
                name TEXT UNIQUE NOT NULL,
                alias TEXT,
                parent TEXT,
                gstin TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                pincode TEXT,
                state TEXT,
                country TEXT,
                is_active INTEGER DEFAULT 1,
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

            CREATE TABLE IF NOT EXISTS CACHE_SYNC_MANIFESTS (
                sync_id TEXT PRIMARY KEY,
                sync_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_sec REAL DEFAULT 0.0,
                expected_records INTEGER DEFAULT 0,
                received_records INTEGER DEFAULT 0,
                inserted_records INTEGER DEFAULT 0,
                updated_records INTEGER DEFAULT 0,
                deleted_records INTEGER DEFAULT 0,
                skipped_records INTEGER DEFAULT 0,
                failed_records INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                validation_result TEXT NOT NULL,
                checksum TEXT
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

    def update_cache_stock_items(self, stock_items, detect_deletions=False):
        """Atomic transaction staging for stock items with optional deletion detection."""
        conn = self._get_cache_conn()
        conn.isolation_level = None
        cur = conn.cursor()
        cur.execute("BEGIN TRANSACTION;")
        
        inserted = 0
        updated = 0
        active_guids = set()
        
        try:
            for item in stock_items:
                guid = item.get('guid') or f"GUID_STOCK_{hash(item['name'])}"
                active_guids.add(guid)
                
                cur.execute("SELECT alter_id FROM CACHE_STOCK_ITEMS WHERE name = ?", (item['name'],))
                existing = cur.fetchone()
                
                if not existing:
                    inserted += 1
                else:
                    updated += 1
                    
                cur.execute("""
                    INSERT INTO CACHE_STOCK_ITEMS (
                        guid, master_id, alter_id, name, alias, parent, category, description,
                        base_units, hsn_code, closing_stock, closing_rate, closing_value, is_active, last_synced
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
                    ON CONFLICT(name) DO UPDATE SET
                        alter_id=excluded.alter_id,
                        alias=excluded.alias,
                        parent=excluded.parent,
                        category=excluded.category,
                        description=excluded.description,
                        base_units=excluded.base_units,
                        hsn_code=excluded.hsn_code,
                        closing_stock=excluded.closing_stock,
                        closing_rate=excluded.closing_rate,
                        closing_value=excluded.closing_value,
                        is_active=1,
                        last_synced=datetime('now')
                """, (
                    guid, item.get('master_id', 0), item.get('alter_id', 0), item['name'],
                    item.get('alias', ''), item.get('parent', 'WAGO'), item.get('category', ''),
                    item.get('description', ''), item.get('base_units', 'PCS'), item.get('hsn_code', ''),
                    item.get('closing_stock', 0.0), item.get('closing_rate', 0.0), item.get('closing_value', 0.0)
                ))

            deleted = 0
            if detect_deletions and active_guids:
                # Mark items not in Tally active set as inactive
                cur.execute("SELECT guid FROM CACHE_STOCK_ITEMS WHERE is_active = 1")
                cached_guids = {r['guid'] for r in cur.fetchall()}
                missing_guids = cached_guids - active_guids
                if missing_guids:
                    deleted = len(missing_guids)
                    cur.executemany("UPDATE CACHE_STOCK_ITEMS SET is_active = 0 WHERE guid = ?", [(g,) for g in missing_guids])
                    tally_logger.info(f"🗑️ Deletion Detection: Marked {deleted:,} missing stock items inactive.")

            cur.execute("COMMIT;")
            conn.close()
            tally_logger.info(f"💾 Cache Stock Items Transacted: {inserted:,} Inserted, {updated:,} Updated, {deleted:,} Deleted.")
            return {"inserted": inserted, "updated": updated, "deleted": deleted}
        except Exception as ex:
            cur.execute("ROLLBACK;")
            conn.close()
            tally_logger.error(f"❌ Cache Stock Items Transaction Failed: {ex}")
            raise ex

    def update_cache_ledgers(self, ledgers, detect_deletions=False):
        """Atomic transaction staging for ledgers with optional deletion detection."""
        conn = self._get_cache_conn()
        conn.isolation_level = None
        cur = conn.cursor()
        cur.execute("BEGIN TRANSACTION;")
        
        inserted = 0
        updated = 0
        active_guids = set()
        
        try:
            for leg in ledgers:
                guid = leg.get('guid') or f"GUID_LEDGER_{hash(leg['name'])}"
                active_guids.add(guid)
                
                cur.execute("SELECT alter_id FROM CACHE_LEDGERS WHERE name = ?", (leg['name'],))
                existing = cur.fetchone()
                
                if not existing:
                    inserted += 1
                else:
                    updated += 1
                    
                cur.execute("""
                    INSERT INTO CACHE_LEDGERS (
                        guid, master_id, alter_id, name, alias, parent, gstin, phone, email,
                        address, pincode, state, country, is_active, last_synced
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
                    ON CONFLICT(name) DO UPDATE SET
                        alter_id=excluded.alter_id,
                        alias=excluded.alias,
                        parent=excluded.parent,
                        gstin=excluded.gstin,
                        phone=excluded.phone,
                        email=excluded.email,
                        address=excluded.address,
                        pincode=excluded.pincode,
                        state=excluded.state,
                        country=excluded.country,
                        is_active=1,
                        last_synced=datetime('now')
                """, (
                    guid, leg.get('master_id', 0), leg.get('alter_id', 0), leg['name'],
                    leg.get('alias', ''), leg.get('parent', ''), leg.get('gstin', ''),
                    leg.get('phone', ''), leg.get('email', ''), leg.get('address', ''),
                    leg.get('pincode', ''), leg.get('state', ''), leg.get('country', '')
                ))

            deleted = 0
            if detect_deletions and active_guids:
                cur.execute("SELECT guid FROM CACHE_LEDGERS WHERE is_active = 1")
                cached_guids = {r['guid'] for r in cur.fetchall()}
                missing_guids = cached_guids - active_guids
                if missing_guids:
                    deleted = len(missing_guids)
                    cur.executemany("UPDATE CACHE_LEDGERS SET is_active = 0 WHERE guid = ?", [(g,) for g in missing_guids])
                    tally_logger.info(f"🗑️ Deletion Detection: Marked {deleted:,} missing ledgers inactive.")

            cur.execute("COMMIT;")
            conn.close()
            tally_logger.info(f"💾 Cache Ledgers Transacted: {inserted:,} Inserted, {updated:,} Updated, {deleted:,} Deleted.")
            return {"inserted": inserted, "updated": updated, "deleted": deleted}
        except Exception as ex:
            cur.execute("ROLLBACK;")
            conn.close()
            tally_logger.error(f"❌ Cache Ledgers Transaction Failed: {ex}")
            raise ex

    def sync_cache_to_prod_database(self):
        """Pushes validated cached records from cache.db to production database.db inside an atomic transaction."""
        c_conn = self._get_cache_conn()
        p_conn = self._get_prod_conn()
        
        c_cur = c_conn.cursor()
        p_cur = p_conn.cursor()
        p_cur.execute("BEGIN TRANSACTION;")
        
        try:
            # 1. Sync Products & Inventory
            c_cur.execute("SELECT * FROM CACHE_STOCK_ITEMS WHERE is_active = 1")
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
            c_cur.execute("SELECT * FROM CACHE_LEDGERS WHERE is_active = 1")
            cached_ledgers = c_cur.fetchall()
            
            cust_count = 0
            for leg in cached_ledgers:
                c_name = leg['name']
                parent_grp = (leg['parent'] or "").strip().lower()
                
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
        except Exception as ex:
            p_cur.execute("ROLLBACK;")
            c_conn.close()
            p_conn.close()
            tally_logger.error(f"❌ Production DB Sync Failed: {ex}")
            raise ex

    def save_sync_manifest(self, manifest):
        """Saves a structured sync manifest to CACHE_SYNC_MANIFESTS."""
        conn = self._get_cache_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO CACHE_SYNC_MANIFESTS (
                sync_id, sync_type, timestamp, duration_sec, expected_records,
                received_records, inserted_records, updated_records, deleted_records,
                skipped_records, failed_records, retry_count, validation_result, checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sync_id) DO UPDATE SET
                validation_result=excluded.validation_result,
                duration_sec=excluded.duration_sec
        """, (
            manifest.get('sync_id'), manifest.get('sync_type'), manifest.get('timestamp', datetime.now().isoformat()),
            manifest.get('duration_sec', 0.0), manifest.get('expected_records', 0), manifest.get('received_records', 0),
            manifest.get('inserted_records', 0), manifest.get('updated_records', 0), manifest.get('deleted_records', 0),
            manifest.get('skipped_records', 0), manifest.get('failed_records', 0), manifest.get('retry_count', 0),
            manifest.get('validation_result', 'UNKNOWN'), manifest.get('checksum', '')
        ))
        conn.commit()
        conn.close()

    def get_latest_sync_manifests(self, limit=15):
        conn = self._get_cache_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM CACHE_SYNC_MANIFESTS ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

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
