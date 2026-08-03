import os
import re
import pandas as pd
import sqlite3
from datetime import datetime
from app.models.database import get_db_connection, execute_db, query_db
from app.services.excel_header_detector import ExcelHeaderDetector
from app.core.config import Config
from app.core.constants import (
    EXCEL_STOCK_SHEET_NAME, EXCEL_COST_SHEET_NAME,
    ITEM_CODE_SYNONYMS, CLOSING_STOCK_SYNONYMS, PURC_PENDING_SYNONYMS,
    SALE_DUE_SYNONYMS, NETT_AVAILABLE_SYNONYMS, REORDER_LEVEL_SYNONYMS,
    SHORTFALL_SYNONYMS, MIN_REORDER_SYNONYMS, ORDER_TO_PLACE_SYNONYMS,
    PRICE_SYNONYMS, PACKING_QTY_SYNONYMS, SERIES_SYNONYMS
)

class ImportService:
    @staticmethod
    def detect_headers_and_df(file_path, sheet_name, mandatory_synonym_groups):
        """Delegates header detection to ExcelHeaderDetector for backward compatibility."""
        return ExcelHeaderDetector.detect_headers_and_df(file_path, sheet_name, mandatory_synonym_groups)

    @classmethod
    def import_inventory(cls, file_path, sheet_name=EXCEL_STOCK_SHEET_NAME, filename='uploaded_file.xlsx', imported_by=None):
        """Imports inventory quantities into the SQLite database with robust upserts and logging."""
        item_groups = [ITEM_CODE_SYNONYMS]
        try:
            df = cls.detect_headers_and_df(file_path, sheet_name, item_groups)
        except Exception as e:
            try:
                if hasattr(file_path, 'seek'):
                    file_path.seek(0)
                xls = pd.ExcelFile(file_path)
                matching_sheets = [s for s in xls.sheet_names if 'stock' in s.lower() or 'group' in s.lower() or 'reorder' in s.lower()]
                if not matching_sheets:
                    matching_sheets = xls.sheet_names
                df = cls.detect_headers_and_df(file_path, matching_sheets[0], item_groups)
                sheet_name = matching_sheets[0]
            except Exception as ex:
                return {
                    "status": "failed",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": [f"Header detection failed for stock sheet: {str(ex)}"]
                }

        find_col = ExcelHeaderDetector.find_matching_column

        # Resolve columns using centralized constants
        item_code_col = find_col(df.columns, ITEM_CODE_SYNONYMS)
        if not item_code_col:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": ["Could not locate an Item Code / Part Number column in inventory sheet."]
            }

        stock_col = find_col(df.columns, CLOSING_STOCK_SYNONYMS)
        purc_col = find_col(df.columns, PURC_PENDING_SYNONYMS)
        sales_col = find_col(df.columns, SALE_DUE_SYNONYMS)
        nett_col = find_col(df.columns, NETT_AVAILABLE_SYNONYMS)
        reorder_col = find_col(df.columns, REORDER_LEVEL_SYNONYMS)
        shortfall_col = find_col(df.columns, SHORTFALL_SYNONYMS)
        min_reorder_col = find_col(df.columns, MIN_REORDER_SYNONYMS)
        order_to_place_col = find_col(df.columns, ORDER_TO_PLACE_SYNONYMS)

        def parse_float_or_none(row, col_name):
            if not col_name:
                return None
            val = row.get(col_name)
            if pd.isna(val):
                return None
            try:
                cleaned = str(val).replace(',', '').strip()
                match = re.search(r'[-+]?\d*\.?\d+', cleaned)
                if match:
                    return float(match.group(0))
                return None
            except Exception:
                return None

        total_records = len(df)
        successful_records = 0
        failed_records = 0
        errors = []
        
        conn = get_db_connection()
        conn.isolation_level = None
        cur = conn.cursor()
        cur.execute("BEGIN TRANSACTION;")
        
        for idx, row in df.iterrows():
            item_code = str(row.get(item_code_col, '')).strip()
            if item_code.endswith('.0'):
                item_code = item_code[:-2]
            if not item_code or item_code.lower() == 'nan' or item_code.lower() == 'total':
                continue
                
            savepoint_name = f"sp_inv_{idx}"
            try:
                cur.execute(f"SAVEPOINT {savepoint_name};")
                
                stock_val = parse_float_or_none(row, stock_col) or 0.0
                purc_val = parse_float_or_none(row, purc_col) or 0.0
                sales_val = parse_float_or_none(row, sales_col) or 0.0
                
                nett_raw = parse_float_or_none(row, nett_col)
                if nett_raw is not None:
                    nett_val = nett_raw
                else:
                    nett_val = stock_val + purc_val - sales_val
                    
                reorder_raw = parse_float_or_none(row, reorder_col)
                reorder_val = reorder_raw if reorder_raw is not None else 0.0
                
                shortfall_raw = parse_float_or_none(row, shortfall_col)
                if shortfall_raw is not None:
                    shortfall_val = shortfall_raw
                else:
                    shortfall_val = max(0.0, reorder_val - nett_val)
                    
                min_reorder_raw = parse_float_or_none(row, min_reorder_col)
                min_reorder_val = min_reorder_raw if min_reorder_raw is not None else 0.0
                
                order_to_place_raw = parse_float_or_none(row, order_to_place_col)
                if order_to_place_raw is not None:
                    order_to_place_val = order_to_place_raw
                else:
                    order_to_place_val = max(shortfall_val, min_reorder_val) if shortfall_val > 0 else 0.0
                
                # 1. Check if product exists
                cur.execute("SELECT id FROM PRODUCTS WHERE part_number = ?", (item_code,))
                prod = cur.fetchone()
                
                if prod is None:
                    series = item_code.split('-')[0] if '-' in item_code else None
                    cur.execute(
                        "INSERT INTO PRODUCTS (part_number, part_name, series, make) VALUES (?, ?, ?, ?)",
                        (item_code, item_code, series, Config.DEFAULT_MAKE)
                    )
                    product_id = cur.lastrowid
                else:
                    product_id = prod['id']
                
                # 2. Upsert inventory record
                cur.execute("SELECT id FROM INVENTORY WHERE product_id = ?", (product_id,))
                inv = cur.fetchone()
                if inv is None:
                    cur.execute(
                        """INSERT INTO INVENTORY (
                            product_id, current_stock, purc_orders_pending, sale_orders_due,
                            nett_available, reorder_level, short_fall, min_reorder_qty,
                            order_to_be_placed, last_updated
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            product_id, stock_val, purc_val, sales_val,
                            nett_val, reorder_val, shortfall_val, min_reorder_val,
                            order_to_place_val, datetime.now().isoformat()
                        )
                    )
                else:
                    cur.execute(
                        """UPDATE INVENTORY SET 
                            current_stock = ?, purc_orders_pending = ?, sale_orders_due = ?,
                            nett_available = ?, reorder_level = ?, short_fall = ?, min_reorder_qty = ?,
                            order_to_be_placed = ?, last_updated = ? 
                           WHERE product_id = ?""",
                        (
                            stock_val, purc_val, sales_val,
                            nett_val, reorder_val, shortfall_val, min_reorder_val,
                            order_to_place_val, datetime.now().isoformat(), product_id
                        )
                    )
                
                cur.execute(f"RELEASE SAVEPOINT {savepoint_name};")
                successful_records += 1
            except Exception as row_error:
                try: cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                except: pass
                failed_records += 1
                errors.append(f"Row {idx + 2}: {str(row_error)}")
        
        cur.execute("COMMIT;")
        conn.close()
        
        status = 'success'
        if failed_records > 0:
            status = 'partial_success' if successful_records > 0 else 'failed'
            
        execute_db(
            "INSERT INTO IMPORT_LOG (import_type, filename, total_records, successful_records, failed_records, imported_by, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('inventory', filename, total_records, successful_records, failed_records, imported_by, status)
        )
        
        return {
            "status": status,
            "total_records": total_records,
            "successful_records": successful_records,
            "failed_records": failed_records,
            "errors": errors[:50]
        }

    @classmethod
    def sync_from_web_url(cls, url, imported_by='Auto Sync'):
        """Downloads an Excel spreadsheet from a remote web URL and imports it in-memory."""
        import urllib.request
        from io import BytesIO
        
        url_clean = url.strip()
        if "docs.google.com/spreadsheets" in url_clean and "/edit" in url_clean:
            url_clean = url_clean.split("/edit")[0] + "/export?format=xlsx"
            
        try:
            req = urllib.request.Request(
                url_clean, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()
                
            file_stream = BytesIO(content)
            result = cls.import_inventory(
                file_stream, 
                sheet_name=EXCEL_STOCK_SHEET_NAME, 
                filename='google_sheets.xlsx', 
                imported_by=imported_by
            )
            return result
        except Exception as e:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [f"Web fetch failed: {str(e)}"]
            }

    @classmethod
    def import_costs(cls, file_path, sheet_name=EXCEL_COST_SHEET_NAME, filename='uploaded_file.xlsx', imported_by=None):
        """Imports product cost prices into the SQLite database, managing is_current historical tags."""
        item_groups = [ITEM_CODE_SYNONYMS]
        try:
            df = cls.detect_headers_and_df(file_path, sheet_name, item_groups)
        except Exception as e:
            try:
                xls = pd.ExcelFile(file_path)
                matching_sheets = [s for s in xls.sheet_names if 'price' in s.lower() or 'cost' in s.lower() or 'rate' in s.lower()]
                if not matching_sheets:
                    matching_sheets = xls.sheet_names
                df = cls.detect_headers_and_df(file_path, matching_sheets[0], item_groups)
                sheet_name = matching_sheets[0]
            except Exception as ex:
                return {
                    "status": "failed",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": [f"Header detection failed for cost list: {str(ex)}"]
                }

        find_col = ExcelHeaderDetector.find_matching_column

        # Resolve columns using centralized constants
        item_code_col = find_col(df.columns, ITEM_CODE_SYNONYMS)
        if not item_code_col:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": ["Could not locate an Item Code / Part Number column in price sheet."]
            }
        
        price_col = find_col(df.columns, PRICE_SYNONYMS)
        if not price_col:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [f"Could not identify a price column in the sheet. Columns: {df.columns.tolist()}"]
            }

        packing_col = find_col(df.columns, PACKING_QTY_SYNONYMS)
        series_col = find_col(df.columns, SERIES_SYNONYMS)

        total_records = len(df)
        successful_records = 0
        failed_records = 0
        errors = []
        
        conn = get_db_connection()
        conn.isolation_level = None
        cur = conn.cursor()
        cur.execute("BEGIN TRANSACTION;")
        
        for idx, row in df.iterrows():
            item_code = str(row.get(item_code_col, '')).strip()
            if not item_code or item_code.lower() == 'nan' or item_code.lower() == 'total':
                continue
                
            savepoint_name = f"sp_cost_{idx}"
            try:
                cur.execute(f"SAVEPOINT {savepoint_name};")
                
                raw_price = row.get(price_col)
                if pd.isna(raw_price):
                    raise ValueError("Price value is empty")
                
                try:
                    cleaned_price = str(raw_price).replace(',', '').strip()
                    price_val = float(cleaned_price)
                except ValueError:
                    raise ValueError(f"Invalid price numeric value '{raw_price}'")
                
                if 'decimal' not in price_col.lower() and price_val > 100000 and int(price_val) == price_val:
                    price_val = price_val / 100.0
                
                packing_qty = 1
                if packing_col:
                    raw_packing = row.get(packing_col)
                    if pd.notna(raw_packing):
                        try:
                            packing_qty = int(float(str(raw_packing).replace('TBC', '1').replace(',', '').strip()))
                        except ValueError:
                            packing_qty = 1

                series_val = str(row.get(series_col, '')).strip() if series_col else (item_code.split('-')[0] if '-' in item_code else None)
                if series_val == 'nan' or not series_val:
                    series_val = item_code.split('-')[0] if '-' in item_code else None
                
                cur.execute("SELECT id, packing_quantity FROM PRODUCTS WHERE part_number = ?", (item_code,))
                prod = cur.fetchone()
                if prod is None:
                    cur.execute(
                        "INSERT INTO PRODUCTS (part_number, part_name, series, make, packing_quantity) VALUES (?, ?, ?, ?, ?)",
                        (item_code, item_code, series_val, Config.DEFAULT_MAKE, packing_qty)
                    )
                    product_id = cur.lastrowid
                else:
                    product_id = prod['id']
                    cur.execute(
                        "UPDATE PRODUCTS SET packing_quantity = ?, series = ? WHERE id = ?",
                        (packing_qty, series_val, product_id)
                    )
                
                cur.execute(
                    "SELECT id, price_per_100_pcs FROM PRODUCT_COSTS WHERE product_id = ? AND is_current = 1",
                    (product_id,)
                )
                active_cost = cur.fetchone()
                
                price_changed = True
                if active_cost:
                    if abs(active_cost['price_per_100_pcs'] - price_val) < 0.001:
                        price_changed = False
                
                if price_changed:
                    if active_cost:
                        cur.execute(
                            "UPDATE PRODUCT_COSTS SET is_current = 0, effective_to = ? WHERE id = ?",
                            (datetime.now().isoformat(), active_cost['id'])
                        )
                    price_per_unit = price_val / 100.0
                    cur.execute(
                        "INSERT INTO PRODUCT_COSTS (product_id, price_per_100_pcs, price_per_unit, effective_from, is_current) VALUES (?, ?, ?, ?, ?)",
                        (product_id, price_val, price_per_unit, datetime.now().isoformat(), 1)
                    )
                
                cur.execute(f"RELEASE SAVEPOINT {savepoint_name};")
                successful_records += 1
            except Exception as row_error:
                try: cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                except: pass
                failed_records += 1
                errors.append(f"Row {idx + 2}: {str(row_error)}")
        
        cur.execute("COMMIT;")
        conn.close()
        
        status = 'success'
        if failed_records > 0:
            status = 'partial_success' if successful_records > 0 else 'failed'
            
        execute_db(
            "INSERT INTO IMPORT_LOG (import_type, filename, total_records, successful_records, failed_records, imported_by, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('cost', filename, total_records, successful_records, failed_records, imported_by, status)
        )
        
        return {
            "status": status,
            "total_records": total_records,
            "successful_records": successful_records,
            "failed_records": failed_records,
            "errors": errors[:50]
        }
