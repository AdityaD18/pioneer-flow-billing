import os
import re
import pandas as pd
import sqlite3
from datetime import datetime
from app.repositories.base_repository import BaseRepository
from app.repositories.import_log_repository import ImportLogRepository
from app.services.inventory_service import InventoryService
from app.services.excel_header_detector import ExcelHeaderDetector
from app.core.config import Config
from app.core.logger import import_logger
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
        import_logger.info(f"Starting inventory import from file '{filename}', sheet '{sheet_name}'.")
        item_groups = [ITEM_CODE_SYNONYMS]
        try:
            df = cls.detect_headers_and_df(file_path, sheet_name, item_groups)
        except Exception as e:
            import_logger.warning(f"Header detection failed on sheet '{sheet_name}': {e}. Attempting matching sheet search...")
            try:
                if hasattr(file_path, 'seek'):
                    file_path.seek(0)
                xls = pd.ExcelFile(file_path)
                matching_sheets = [s for s in xls.sheet_names if 'stock' in s.lower() or 'group' in s.lower() or 'reorder' in s.lower()]
                if not matching_sheets:
                    matching_sheets = xls.sheet_names
                df = cls.detect_headers_and_df(file_path, matching_sheets[0], item_groups)
                sheet_name = matching_sheets[0]
                import_logger.info(f"Successfully matched fallback stock sheet '{sheet_name}'.")
            except Exception as ex:
                err_msg = f"Header detection failed for stock sheet: {str(ex)}"
                import_logger.error(err_msg, exc_info=True)
                return {
                    "status": "failed",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": [err_msg]
                }

        find_col = ExcelHeaderDetector.find_matching_column

        # Resolve columns using centralized constants
        item_code_col = find_col(df.columns, ITEM_CODE_SYNONYMS)
        if not item_code_col:
            err_msg = "Could not locate an Item Code / Part Number column in inventory sheet."
            import_logger.error(err_msg)
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [err_msg]
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
        
        conn = BaseRepository.get_connection()
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
                reorder_val = parse_float_or_none(row, reorder_col) or 0.0
                shortfall_raw = parse_float_or_none(row, shortfall_col)
                min_reorder_val = parse_float_or_none(row, min_reorder_col) or 0.0
                order_to_place_raw = parse_float_or_none(row, order_to_place_col)
                
                # Delegate calculation to InventoryService
                metrics = InventoryService.calculate_reorder_metrics(
                    stock_val, purc_val, sales_val, reorder_val, min_reorder_val,
                    nett_raw, shortfall_raw, order_to_place_raw
                )
                nett_val = metrics['nett_available']
                shortfall_val = metrics['shortfall']
                order_to_place_val = metrics['order_to_place']
                
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
                try:
                    cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                except Exception as rollback_err:
                    import_logger.warning(f"Rollback to savepoint {savepoint_name} failed: {rollback_err}")
                failed_records += 1
                err_text = f"Row {idx + 2}: {str(row_error)}"
                errors.append(err_text)
                import_logger.warning(f"Inventory row processing error - {err_text}")
        
        cur.execute("COMMIT;")
        conn.close()
        
        status = 'success'
        if failed_records > 0:
            status = 'partial_success' if successful_records > 0 else 'failed'
            
        ImportLogRepository.log_import('inventory', filename, total_records, successful_records, failed_records, imported_by, status)
        import_logger.info(f"Inventory import finished ({status}): {successful_records}/{total_records} successful, {failed_records} failed.")
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
        import_logger.info(f"Initiating remote web spreadsheet sync from URL: {url_clean}")
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
            import_logger.info(f"Web spreadsheet sync completed successfully: {result['successful_records']} records processed.")
            return result
        except Exception as e:
            err_msg = f"Web fetch failed: {str(e)}"
            import_logger.error(err_msg, exc_info=True)
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [err_msg]
            }

    @classmethod
    def import_costs(cls, file_path, sheet_name=EXCEL_COST_SHEET_NAME, filename='uploaded_file.xlsx', imported_by=None):
        """Imports product cost prices into the SQLite database, managing is_current historical tags."""
        import_logger.info(f"Starting cost list import from file '{filename}', sheet '{sheet_name}'.")
        item_groups = [ITEM_CODE_SYNONYMS]
        try:
            df = cls.detect_headers_and_df(file_path, sheet_name, item_groups)
        except Exception as e:
            import_logger.warning(f"Header detection failed on cost sheet '{sheet_name}': {e}. Searching fallback sheets...")
            try:
                xls = pd.ExcelFile(file_path)
                matching_sheets = [s for s in xls.sheet_names if 'price' in s.lower() or 'cost' in s.lower() or 'rate' in s.lower()]
                if not matching_sheets:
                    matching_sheets = xls.sheet_names
                df = cls.detect_headers_and_df(file_path, matching_sheets[0], item_groups)
                sheet_name = matching_sheets[0]
                import_logger.info(f"Matched fallback cost sheet '{sheet_name}'.")
            except Exception as ex:
                err_msg = f"Header detection failed for cost list: {str(ex)}"
                import_logger.error(err_msg, exc_info=True)
                return {
                    "status": "failed",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": [err_msg]
                }

        find_col = ExcelHeaderDetector.find_matching_column

        # Resolve columns using centralized constants
        item_code_col = find_col(df.columns, ITEM_CODE_SYNONYMS)
        if not item_code_col:
            err_msg = "Could not locate an Item Code / Part Number column in price sheet."
            import_logger.error(err_msg)
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [err_msg]
            }
        
        price_col = find_col(df.columns, PRICE_SYNONYMS)
        if not price_col:
            err_msg = f"Could not identify a price column in the sheet. Columns: {df.columns.tolist()}"
            import_logger.error(err_msg)
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [err_msg]
            }

        packing_col = find_col(df.columns, PACKING_QTY_SYNONYMS)
        series_col = find_col(df.columns, SERIES_SYNONYMS)

        total_records = len(df)
        successful_records = 0
        failed_records = 0
        errors = []
        
        conn = BaseRepository.get_connection()
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
                try:
                    cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                except Exception as rollback_err:
                    import_logger.warning(f"Rollback to savepoint {savepoint_name} failed: {rollback_err}")
                failed_records += 1
                err_text = f"Row {idx + 2}: {str(row_error)}"
                errors.append(err_text)
                import_logger.warning(f"Cost row processing error - {err_text}")
        
        cur.execute("COMMIT;")
        conn.close()
        
        status = 'success'
        if failed_records > 0:
            status = 'partial_success' if successful_records > 0 else 'failed'
            
        ImportLogRepository.log_import('cost', filename, total_records, successful_records, failed_records, imported_by, status)
        import_logger.info(f"Cost list import finished ({status}): {successful_records}/{total_records} successful, {failed_records} failed.")
        return {
            "status": status,
            "total_records": total_records,
            "successful_records": successful_records,
            "failed_records": failed_records,
            "errors": errors[:50]
        }
