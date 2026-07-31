import os
import pandas as pd
import sqlite3
from datetime import datetime
from app.models.database import get_db_connection, execute_db, query_db

class ImportService:
    @staticmethod
    def detect_headers_and_df(file_path, sheet_name, mandatory_synonym_groups):
        """Scans the first 30 rows of a sheet to locate the header row matching at least one synonym from each group."""
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=30)
        
        header_row_idx = None
        for i, row in df_raw.iterrows():
            row_str = [str(val).strip().lower() for val in row.values if pd.notna(val)]
            
            matched_groups = 0
            for group in mandatory_synonym_groups:
                if any(any(syn in cell_str for cell_str in row_str) for syn in group):
                    matched_groups += 1
            
            if matched_groups >= len(mandatory_synonym_groups):
                header_row_idx = i
                break
                
        if header_row_idx is None:
            raise ValueError(f"Could not find a valid header row containing part numbers in sheet '{sheet_name}'.")
            
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row_idx)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    @classmethod
    def import_inventory(cls, file_path, sheet_name='Stock Group Reorder Status', filename='uploaded_file.xlsx', imported_by=None):
        """Imports inventory quantities into the SQLite database with robust upserts and logging."""
        item_groups = [['item code', 'part number', 'part no', 'partno', 'code', 'item_code', 'part_no']]
        try:
            df = cls.detect_headers_and_df(file_path, sheet_name, item_groups)
        except Exception as e:
            try:
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

        # Resolve columns
        item_code_col = None
        for c in df.columns:
            c_lower = c.lower()
            if any(syn in c_lower for syn in ['item code', 'part number', 'part no', 'partno', 'code', 'item_code', 'part_no']):
                item_code_col = c
                break
        
        if not item_code_col:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": ["Could not locate an Item Code / Part Number column in inventory sheet."]
            }

        stock_col = None
        for c in df.columns:
            c_lower = c.lower()
            if any(syn in c_lower for syn in ['closing stock', 'current stock', 'stock', 'qty', 'quantity', 'closing', 'stock qty', 'available', 'inventory']):
                stock_col = c
                break

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
                
            savepoint_name = f"sp_inv_{idx}"
            try:
                cur.execute(f"SAVEPOINT {savepoint_name};")
                
                # Check for stock quantity
                stock_val = 0.0
                if stock_col:
                    raw_stock = row.get(stock_col)
                    if pd.notna(raw_stock):
                        try:
                            cleaned_stock = str(raw_stock).replace(',', '').strip()
                            stock_val = float(cleaned_stock)
                        except ValueError:
                            raise ValueError(f"Invalid stock numeric value '{raw_stock}'")
                
                # 1. Check if product exists
                cur.execute("SELECT id FROM PRODUCTS WHERE part_number = ?", (item_code,))
                prod = cur.fetchone()
                
                if prod is None:
                    series = item_code.split('-')[0] if '-' in item_code else None
                    cur.execute(
                        "INSERT INTO PRODUCTS (part_number, part_name, series, make) VALUES (?, ?, ?, ?)",
                        (item_code, item_code, series, 'WAGO')
                    )
                    product_id = cur.lastrowid
                else:
                    product_id = prod['id']
                
                # 2. Upsert inventory record
                cur.execute("SELECT id FROM INVENTORY WHERE product_id = ?", (product_id,))
                inv = cur.fetchone()
                if inv is None:
                    cur.execute(
                        "INSERT INTO INVENTORY (product_id, current_stock, last_updated) VALUES (?, ?, ?)",
                        (product_id, stock_val, datetime.now().isoformat())
                    )
                else:
                    cur.execute(
                        "UPDATE INVENTORY SET current_stock = ?, last_updated = ? WHERE product_id = ?",
                        (stock_val, datetime.now().isoformat(), product_id)
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
        
        # Log this import
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
    def import_costs(cls, file_path, sheet_name='PRICE LIST', filename='uploaded_file.xlsx', imported_by=None):
        """Imports product cost prices into the SQLite database, managing is_current historical tags."""
        item_groups = [['item code', 'part number', 'part no', 'partno', 'code', 'item_code', 'part_no']]
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

        # Resolve columns
        item_code_col = None
        for c in df.columns:
            c_lower = c.lower()
            if any(syn in c_lower for syn in ['item code', 'part number', 'part no', 'partno', 'code', 'item_code', 'part_no']):
                item_code_col = c
                break
        
        if not item_code_col:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": ["Could not locate an Item Code / Part Number column in price sheet."]
            }
        
        # Prioritize 'decimal converted' or 'converted' or 'price/rate'
        price_col = None
        for search_syns in [['decimal converted', 'converted rate'], ['price', 'rate', 'mrp', 'cost']]:
            for c in df.columns:
                c_lower = c.lower()
                if any(syn in c_lower for syn in search_syns):
                    price_col = c
                    break
            if price_col:
                break

        if not price_col:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [f"Could not identify a price column in the sheet. Columns: {df.columns.tolist()}"]
            }

        packing_col = None
        for c in df.columns:
            c_lower = c.lower()
            if any(syn in c_lower for syn in ['packing', 'quantity pcs', 'pack qty', 'packing quantity']):
                packing_col = c
                break

        series_col = None
        for c in df.columns:
            c_lower = c.lower()
            if any(syn in c_lower for syn in ['series', 'group', 'category']):
                series_col = c
                break

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
                
                # Resolve Price value
                raw_price = row.get(price_col)
                if pd.isna(raw_price):
                    raise ValueError("Price value is empty")
                
                try:
                    cleaned_price = str(raw_price).replace(',', '').strip()
                    price_val = float(cleaned_price)
                except ValueError:
                    raise ValueError(f"Invalid price numeric value '{raw_price}'")
                
                # Standardize pricing unit (INR per 100 pcs)
                if 'decimal' not in price_col.lower() and price_val > 100000 and int(price_val) == price_val:
                    price_val = price_val / 100.0
                
                # Resolve packing quantity
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
                
                # 1. Create or update product definition
                cur.execute("SELECT id, packing_quantity FROM PRODUCTS WHERE part_number = ?", (item_code,))
                prod = cur.fetchone()
                if prod is None:
                    cur.execute(
                        "INSERT INTO PRODUCTS (part_number, part_name, series, make, packing_quantity) VALUES (?, ?, ?, ?, ?)",
                        (item_code, item_code, series_val, 'WAGO', packing_qty)
                    )
                    product_id = cur.lastrowid
                else:
                    product_id = prod['id']
                    cur.execute(
                        "UPDATE PRODUCTS SET packing_quantity = ?, series = ? WHERE id = ?",
                        (packing_qty, series_val, product_id)
                    )
                
                # 2. Check current active price
                cur.execute(
                    "SELECT id, price_per_100_pcs FROM PRODUCT_COSTS WHERE product_id = ? AND is_current = 1",
                    (product_id,)
                )
                active_cost = cur.fetchone()
                
                price_changed = True
                if active_cost:
                    if abs(active_cost['price_per_100_pcs'] - price_val) < 0.001:
                        price_changed = False  # No change
                
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
        
        # Log this import
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
