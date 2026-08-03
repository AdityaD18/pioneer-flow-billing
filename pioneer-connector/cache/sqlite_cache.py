import os
import sqlite3
from datetime import datetime
from typing import List, Optional
from tally.models.stock import TallyStockItem, TallyStockGroup
from tally.models.ledger import TallyLedger

CACHE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "connector_cache.db"))

class ConnectorCacheDB:
    """SQLite cache database preserving Tally data for instant API serving and offline resilience."""
    db_path = CACHE_DB_PATH

    @classmethod
    def get_connection(cls) -> sqlite3.Connection:
        target_path = getattr(cls, 'db_path', CACHE_DB_PATH)
        conn = sqlite3.connect(target_path)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def clear_all(cls):
        """Clears all cached tables for testing isolation."""
        conn = cls.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM cached_stock_items;")
        cur.execute("DELETE FROM cached_stock_groups;")
        cur.execute("DELETE FROM cached_ledgers;")
        cur.execute("DELETE FROM sync_metadata;")
        conn.commit()
        cur.close()
        conn.close()

    @classmethod
    def init_cache_db(cls):
        """Initializes cache tables and indexes."""
        target_path = getattr(cls, 'db_path', CACHE_DB_PATH)
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        conn = cls.get_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cached_stock_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT,
                part_number TEXT UNIQUE,
                name TEXT,
                parent_group TEXT,
                closing_balance REAL,
                closing_rate REAL,
                closing_value REAL,
                purchase_pending REAL,
                sales_due REAL,
                nett_available REAL,
                reorder_level REAL,
                shortfall REAL,
                updated_at TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cached_stock_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT,
                name TEXT UNIQUE,
                parent_group TEXT,
                series_code TEXT,
                updated_at TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cached_ledgers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT,
                name TEXT UNIQUE,
                parent_group TEXT,
                ledger_type TEXT,
                closing_balance REAL,
                gstin TEXT,
                address TEXT,
                phone TEXT,
                email TEXT,
                state TEXT,
                pin_code TEXT,
                updated_at TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_metadata (
                entity_name TEXT PRIMARY KEY,
                last_sync_timestamp TEXT,
                record_count INTEGER,
                status TEXT
            );
        """)

        conn.commit()
        cur.close()
        conn.close()

    # --- Stock Items Cache Operations ---
    @classmethod
    def save_stock_items(cls, items: List[TallyStockItem]):
        """Atomic upsert of stock items into SQLite cache."""
        if not items:
            return
        conn = cls.get_connection()
        cur = conn.cursor()
        now_str = datetime.utcnow().isoformat() + "Z"
        try:
            cur.execute("BEGIN TRANSACTION;")
            for item in items:
                cur.execute("""
                    INSERT INTO cached_stock_items (
                        guid, part_number, name, parent_group, closing_balance, 
                        closing_rate, closing_value, purchase_pending, sales_due, 
                        nett_available, reorder_level, shortfall, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(part_number) DO UPDATE SET
                        guid=excluded.guid,
                        name=excluded.name,
                        parent_group=excluded.parent_group,
                        closing_balance=excluded.closing_balance,
                        closing_rate=excluded.closing_rate,
                        closing_value=excluded.closing_value,
                        purchase_pending=excluded.purchase_pending,
                        sales_due=excluded.sales_due,
                        nett_available=excluded.nett_available,
                        reorder_level=excluded.reorder_level,
                        shortfall=excluded.shortfall,
                        updated_at=excluded.updated_at
                """, (
                    item.guid, item.part_number, item.name, item.parent_group, item.closing_balance,
                    item.closing_rate, item.closing_value, item.purchase_pending, item.sales_due,
                    item.nett_available, item.reorder_level, item.shortfall, now_str
                ))

            cur.execute("""
                INSERT INTO sync_metadata (entity_name, last_sync_timestamp, record_count, status)
                VALUES ('stock_items', ?, ?, 'synced')
                ON CONFLICT(entity_name) DO UPDATE SET
                    last_sync_timestamp=excluded.last_sync_timestamp,
                    record_count=excluded.record_count,
                    status=excluded.status
            """, (now_str, len(items)))

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @classmethod
    def get_stock_items(cls) -> List[TallyStockItem]:
        """Reads cached stock items from SQLite."""
        conn = cls.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM cached_stock_items ORDER BY part_number ASC")
        rows = cur.fetchall()
        items = []
        for r in rows:
            items.append(TallyStockItem(
                guid=r["guid"],
                name=r["name"],
                parent_group=r["parent_group"],
                part_number=r["part_number"],
                closing_balance=r["closing_balance"],
                closing_rate=r["closing_rate"],
                closing_value=r["closing_value"],
                purchase_pending=r["purchase_pending"],
                sales_due=r["sales_due"],
                nett_available=r["nett_available"],
                reorder_level=r["reorder_level"],
                shortfall=r["shortfall"]
            ))
        cur.close()
        conn.close()
        return items

    # --- Stock Groups Cache Operations ---
    @classmethod
    def save_stock_groups(cls, groups: List[TallyStockGroup]):
        """Atomic upsert of stock groups into SQLite cache."""
        if not groups:
            return
        conn = cls.get_connection()
        cur = conn.cursor()
        now_str = datetime.utcnow().isoformat() + "Z"
        try:
            cur.execute("BEGIN TRANSACTION;")
            for g in groups:
                cur.execute("""
                    INSERT INTO cached_stock_groups (guid, name, parent_group, series_code, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        guid=excluded.guid,
                        parent_group=excluded.parent_group,
                        series_code=excluded.series_code,
                        updated_at=excluded.updated_at
                """, (g.guid, g.name, g.parent_group, g.series_code, now_str))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @classmethod
    def get_stock_groups(cls) -> List[TallyStockGroup]:
        """Reads cached stock groups from SQLite."""
        conn = cls.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM cached_stock_groups ORDER BY name ASC")
        rows = cur.fetchall()
        groups = []
        for r in rows:
            groups.append(TallyStockGroup(
                guid=r["guid"],
                name=r["name"],
                parent_group=r["parent_group"],
                series_code=r["series_code"]
            ))
        cur.close()
        conn.close()
        return groups

    # --- Ledgers Cache Operations ---
    @classmethod
    def save_ledgers(cls, ledgers: List[TallyLedger]):
        """Atomic upsert of ledgers into SQLite cache."""
        if not ledgers:
            return
        conn = cls.get_connection()
        cur = conn.cursor()
        now_str = datetime.utcnow().isoformat() + "Z"
        try:
            cur.execute("BEGIN TRANSACTION;")
            for l in ledgers:
                cur.execute("""
                    INSERT INTO cached_ledgers (
                        guid, name, parent_group, ledger_type, closing_balance, 
                        gstin, address, phone, email, state, pin_code, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        guid=excluded.guid,
                        parent_group=excluded.parent_group,
                        ledger_type=excluded.ledger_type,
                        closing_balance=excluded.closing_balance,
                        gstin=excluded.gstin,
                        address=excluded.address,
                        phone=excluded.phone,
                        email=excluded.email,
                        state=excluded.state,
                        pin_code=excluded.pin_code,
                        updated_at=excluded.updated_at
                """, (
                    l.guid, l.name, l.parent_group, l.ledger_type, l.closing_balance,
                    l.gstin, l.address, l.phone, l.email, l.state, l.pin_code, now_str
                ))

            cur.execute("""
                INSERT INTO sync_metadata (entity_name, last_sync_timestamp, record_count, status)
                VALUES ('ledgers', ?, ?, 'synced')
                ON CONFLICT(entity_name) DO UPDATE SET
                    last_sync_timestamp=excluded.last_sync_timestamp,
                    record_count=excluded.record_count,
                    status=excluded.status
            """, (now_str, len(ledgers)))

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @classmethod
    def get_ledgers(cls, ledger_type: Optional[str] = None) -> List[TallyLedger]:
        """Reads cached ledgers from SQLite."""
        conn = cls.get_connection()
        cur = conn.cursor()
        if ledger_type:
            cur.execute("SELECT * FROM cached_ledgers WHERE ledger_type = ? ORDER BY name ASC", (ledger_type,))
        else:
            cur.execute("SELECT * FROM cached_ledgers ORDER BY name ASC")
        rows = cur.fetchall()
        ledgers = []
        for r in rows:
            ledgers.append(TallyLedger(
                guid=r["guid"],
                name=r["name"],
                parent_group=r["parent_group"],
                ledger_type=r["ledger_type"],
                closing_balance=r["closing_balance"],
                gstin=r["gstin"],
                address=r["address"],
                phone=r["phone"],
                email=r["email"],
                state=r["state"],
                pin_code=r["pin_code"]
            ))
        cur.close()
        conn.close()
        return ledgers

    @classmethod
    def get_last_sync(cls, entity_name: str) -> Optional[dict]:
        """Gets last sync metadata for an entity."""
        conn = cls.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sync_metadata WHERE entity_name = ?", (entity_name,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return dict(row)
        return None

# Ensure SQLite cache tables exist on module load
ConnectorCacheDB.init_cache_db()
