import os
import pandas as pd
import sqlite3
from datetime import datetime
from app.models.database import get_db, execute_db, query_db

class ImportService:
    @staticmethod
    def detect_headers_and_df(file_path, sheet_name, mandatory_columns):
        """Scans the first 20 rows of a sheet to locate the header row matching mandatory columns."""
        # Read without headers initially to find the header row
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=30)
        
        header_row_idx = None
        for i, row in df_raw.iterrows():
            row_str = [str(val).strip().lower() for val in row.values if pd.notna(val)]
            # Check if all mandatory column sub-words or exact names match
            matched = 0
            for col in mandatory_columns:
                col_lower = col.lower()
                if any(col_lower in cell_str for cell_str in row_str):
                    matched += 1
            if matched >= len(mandatory_columns):
                header_row_idx = i
                break
        
        if header_row_idx is None:
            raise ValueError(f"Could not find a row containing columns {mandatory_columns} in sheet '{sheet_name}'.")
        
        # Load the full sheet using the detected header row
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row_idx)
        # Strip string spaces from column headers
        df.columns = [str(c).strip() for c in df.columns]
        return df

    @classmethod
    def import_inventory(cls, file_path, sheet_name='Stock Group Reorder Status', filename='uploaded_file.xlsx', imported_by=None):
        """Imports inventory quantities into the SQLite database with robust upserts and logging."""
        try:
            # We look for "Item Code" and "Closing Stock" or similar
            df = cls.detect_headers_and_df(file_path, sheet_name, ['Item Code'])
        except Exception as e:
            # Fallback: try active sheet or find sheet that has matching columns
            try:
                xls = pd.ExcelFile(file_path)
                matching_sheets = [s for s in xls.sheet_names if 'stock' in s.lower() or 'group' in s.lower()]
                if not matching_sheets:
                    matching_sheets = xls.sheet_names
                df = cls.detect_headers_and_df(file_path, matching_sheets[0], ['Item Code'])
                sheet_name = matching_sheets[0]
            except Exception as ex:
                return {
                    "status": "failed",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": [f"Header detection failed: {str(ex)}"]
                }

        # Resolve column names
        item_code_col = [c for c in df.columns if 'item code' in c.lower() or 'part number' in c.lower()][0]
        stock_cols = [c for c in df.columns if 'closing stock' in c.lower() or 'current stock' in c.lower() or 'stock' in c.lower()]
        stock_col = stock_cols[0] if stock_cols else None

        total_records = len(df)
        successful_records = 0
        failed_records = 0
        errors = []
        
        conn = get_db()
        
        for idx, row in df.iterrows():
            try:
                item_code = str(row.get(item_code_col, '')).strip()
                if not item_code or item_code.lower() == 'nan' or item_code.lower() == 'total':
                    continue  # skip totals or empty lines silently
                
                # Check for stock quantity
                stock_val = 0
                if stock_col:
                    raw_stock = row.get(stock_col)
                    if pd.notna(raw_stock):
                        try:
                            stock_val = float(raw_stock)
                        except ValueError:
                            errors.append(f"Row {idx + 2}: Invalid stock numeric value '{raw_stock}' for item '{item_code}'. Skiped.")
                            failed_records += 1
                            continue
                
                # Begin Transactional Upsert for this row
                cur = conn.cursor()
                
                # 1. Check if product exists
                cur.execute("SELECT id FROM PRODUCTS WHERE part_number = ?", (item_code,))
                prod = cur.fetchone()
                
                new_product = False
                if prod is None:
                    # Create product
                    series = item_code.split('-')[0] if '-' in item_code else None
                    cur.execute(
                        "INSERT INTO PRODUCTS (part_number, part_name, series, make) VALUES (?, ?, ?, ?)",
                        (item_code, item_code, series, 'WAGO')
                    )
                    product_id = cur.lastrowid
                    new_product = True
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
                
                conn.commit()
                successful_records += 1
            except Exception as row_error:
                conn.rollback()
                failed_records += 1
                errors.append(f"Row {idx + 2}: Exception during upsert: {str(row_error)}")
        
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
            "errors": errors[:50]  # Limit to first 50 errors for display
        }

    @classmethod
    def import_costs(cls, file_path, sheet_name='PRICE LIST', filename='uploaded_file.xlsx', imported_by=None):
        """Imports product cost prices into the SQLite database, managing is_current historical tags."""
        try:
            # We look for "Item Code" and some price column
            df = cls.detect_headers_and_df(file_path, sheet_name, ['Item Code'])
        except Exception as e:
            try:
                xls = pd.ExcelFile(file_path)
                matching_sheets = [s for s in xls.sheet_names if 'price' in s.lower() or 'cost' in s.lower() or 'rate' in s.lower()]
                if not matching_sheets:
                    matching_sheets = xls.sheet_names
                df = cls.detect_headers_and_df(file_path, matching_sheets[0], ['Item Code'])
                sheet_name = matching_sheets[0]
            except Exception as ex:
                return {
                    "status": "failed",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": [f"Header detection failed: {str(ex)}"]
                }

        # Resolve columns
        item_code_col = [c for c in df.columns if 'item code' in c.lower() or 'part number' in c.lower()][0]
        
        price_cols = [c for c in df.columns if 'decimal converted' in c.lower() or 'price' in c.lower() or 'rate' in c.lower()]
        if not price_cols:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [f"Could not identify a price column in the sheet. Available: {df.columns.tolist()}"]
            }
        # Prioritize decimal converted price if available
        decimal_cols = [c for c in price_cols if 'decimal converted' in c.lower()]
        price_col = decimal_cols[0] if decimal_cols else price_cols[0]

        packing_cols = [c for c in df.columns if 'packing' in c.lower() or 'quantity pcs' in c.lower()]
        packing_col = packing_cols[0] if packing_cols else None

        series_cols = [c for c in df.columns if 'series' in c.lower() or 'group' in c.lower()]
        series_col = series_cols[0] if series_cols else None

        total_records = len(df)
        successful_records = 0
        failed_records = 0
        errors = []
        
        conn = get_db()
        
        for idx, row in df.iterrows():
            try:
                item_code = str(row.get(item_code_col, '')).strip()
                if not item_code or item_code.lower() == 'nan' or item_code.lower() == 'total':
                    continue
                
                # Resolve Price value
                raw_price = row.get(price_col)
                if pd.isna(raw_price):
                    errors.append(f"Row {idx + 2}: Price value is empty for item '{item_code}'. Skipped.")
                    failed_records += 1
                    continue
                
                try:
                    price_val = float(raw_price)
                except ValueError:
                    errors.append(f"Row {idx + 2}: Invalid price numeric value '{raw_price}' for item '{item_code}'. Skipped.")
                    failed_records += 1
                    continue
                
                # Standardize pricing unit. In WAGO, Price is per 100 pcs.
                # If the column does not have "decimal converted" or "100pcs" but is a large integer like 720035 (should be 7200.35)
                # let's check: if column name is 'Price in " Per 100pcs' (no decimal converted) and the price > 5000 and has no decimals,
                # it might need division. In the provided PRICE LIST, we have 'Price in " Per 100pcs decimal converted' which is float.
                # If we read the integer column, it is stored as '720035'. We'll prioritize the decimal converted column.
                # If the value is a large integer, let's divide it if we detect it's the non-decimal column.
                if 'decimal' not in price_col.lower() and price_val > 100000 and int(price_val) == price_val:
                    # Heuristic for non-decimal converted integer columns in this specific dataset
                    price_val = price_val / 100.0
                
                # Resolve packing quantity
                packing_qty = 1
                if packing_col:
                    raw_packing = row.get(packing_col)
                    if pd.notna(raw_packing):
                        try:
                            # Might be string like 'TBC' or number
                            packing_qty = int(float(str(raw_packing).replace('TBC', '1').strip()))
                        except ValueError:
                            packing_qty = 1

                series_val = str(row.get(series_col, '')).strip() if series_col else (item_code.split('-')[0] if '-' in item_code else None)
                if series_val == 'nan':
                    series_val = item_code.split('-')[0] if '-' in item_code else None
                
                cur = conn.cursor()
                
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
                    # Update packing quantity and series
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
                    # Compare
                    if abs(active_cost['price_per_100_pcs'] - price_val) < 0.001:
                        price_changed = False  # No change
                
                if price_changed:
                    # Expire old price
                    if active_cost:
                        cur.execute(
                            "UPDATE PRODUCT_COSTS SET is_current = 0, effective_to = ? WHERE id = ?",
                            (datetime.now().isoformat(), active_cost['id'])
                        )
                    # Insert new price
                    price_per_unit = price_val / 100.0
                    cur.execute(
                        "INSERT INTO PRODUCT_COSTS (product_id, price_per_100_pcs, price_per_unit, effective_from, is_current) VALUES (?, ?, ?, ?, ?)",
                        (product_id, price_val, price_per_unit, datetime.now().isoformat(), 1)
                    )
                
                conn.commit()
                successful_records += 1
            except Exception as row_error:
                conn.rollback()
                failed_records += 1
                errors.append(f"Row {idx + 2}: Exception during cost upsert: {str(row_error)}")
        
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
