import os
import re
import pandas as pd
import sqlite3
from datetime import datetime
from app.models.database import get_db_connection, execute_db, query_db

class ImportService:
    @staticmethod
    def detect_headers_and_df(file_path, sheet_name, mandatory_synonym_groups):
        """Scans the first 30 rows of a sheet to locate the header row matching at least one synonym from each group."""
        if hasattr(file_path, 'seek'):
            file_path.seek(0)
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
            
        if hasattr(file_path, 'seek'):
            file_path.seek(0)
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

        # Helper to find column key by exact match first, then substring match
        def find_col(df_cols, syns):
            # Exact match (case insensitive)
            for c in df_cols:
                c_clean = str(c).lower().strip()
                if c_clean in syns:
                    return c
            # Substring match
            for c in df_cols:
                c_clean = str(c).lower().strip()
                if any(syn in c_clean for syn in syns):
                    return c
            return None

        # Resolve columns
        item_code_col = find_col(df.columns, ['item code', 'part number', 'part no', 'partno', 'code', 'item_code', 'part_no'])
        if not item_code_col:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": ["Could not locate an Item Code / Part Number column in inventory sheet."]
            }

        stock_col = find_col(df.columns, ['closing stock', 'current stock', 'closing stock (pcs)', 'closing stock(pcs)', 'available stock', 'current stock (pcs)', 'stock'])
        purc_col = find_col(df.columns, ['purc orders pending', 'purchase orders pending', 'purc orders', 'purchase pending', 'pending purchase', 'incoming stock', 'pending orders'])
        sales_col = find_col(df.columns, ['sale orders due', 'sales orders due', 'sale orders', 'sales due', 'due sales', 'outgoing stock', 'reserved stock'])
        nett_col = find_col(df.columns, ['nett available', 'net available', 'nett qty', 'net qty', 'available qty'])
        reorder_col = find_col(df.columns, ['re-order level', 'reorder level', 'reorder qty limit', 'reorder level (pcs)'])
        shortfall_col = find_col(df.columns, ['short fall', 'shortfall', 'short qty', 'shortage'])
        min_reorder_col = find_col(df.columns, ['min reorder qty', 'min reorder', 'minimum order qty', 'min reorder quantity'])
        order_to_place_col = find_col(df.columns, ['order to be placed', 'placed order', 'order to place', 'to be placed', 'order to be placed (pcs)'])

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
                
                # nett_available: if Excel cell has value, use it; otherwise compute: stock + purc - sales
                nett_raw = parse_float_or_none(row, nett_col)
                if nett_raw is not None:
                    nett_val = nett_raw
                else:
                    nett_val = stock_val + purc_val - sales_val
                    
                reorder_raw = parse_float_or_none(row, reorder_col)
                reorder_val = reorder_raw if reorder_raw is not None else 0.0
                
                # short_fall: if Excel cell has value, use it; otherwise compute: max(0, reorder - nett)
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
    def import_customers_excel(cls, file_path_or_bytes, filename='customers.xlsx', imported_by='Admin'):
        """Import customers from Excel or CSV file."""
        import pandas as pd
        from app.models.database import get_db_connection
        
        try:
            if isinstance(file_path_or_bytes, bytes):
                df = pd.read_excel(BytesIO(file_path_or_bytes)) if filename.endswith(('.xlsx', '.xls')) else pd.read_csv(BytesIO(file_path_or_bytes))
            elif hasattr(file_path_or_bytes, 'read'):
                file_path_or_bytes.seek(0)
                b_content = file_path_or_bytes.read()
                df = pd.read_excel(BytesIO(b_content)) if filename.endswith(('.xlsx', '.xls')) else pd.read_csv(BytesIO(b_content))
            else:
                df = pd.read_excel(file_path_or_bytes) if filename.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path_or_bytes)
        except Exception as e:
            return {"status": "failed", "total_records": 0, "successful_records": 0, "failed_records": 0, "errors": [f"Failed to read customer file: {str(e)}"]}
            
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("BEGIN TRANSACTION;")
        
        total_records = len(df)
        successful_records = 0
        failed_records = 0
        errors = []
        
        col_map = {}
        for col in df.columns:
            c_low = str(col).strip().lower()
            if any(k in c_low for k in ['customer', 'party', 'client', 'name', 'company']):
                if 'name' not in col_map: col_map['name'] = col
            elif any(k in c_low for k in ['disc', 'discount', 'dis %', 'margin']):
                col_map['discount'] = col
            elif 'phone' in c_low or 'mobile' in c_low or 'contact' in c_low:
                col_map['phone'] = col
            elif 'email' in c_low:
                col_map['email'] = col
            elif 'gst' in c_low:
                col_map['gstin'] = col
            elif 'address' in c_low or 'location' in c_low:
                col_map['address'] = col
                
        name_col = col_map.get('name')
        if not name_col:
            conn.close()
            return {"status": "failed", "total_records": 0, "successful_records": 0, "failed_records": 0, "errors": ["Could not identify Customer Name column in file."]}
            
        for idx, row in df.iterrows():
            savepoint_name = f"sp_cust_{idx}"
            try:
                cur.execute(f"SAVEPOINT {savepoint_name};")
                c_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
                if not c_name or c_name.lower() in ('nan', 'total', 'grand total'):
                    cur.execute(f"RELEASE SAVEPOINT {savepoint_name};")
                    continue
                    
                disc_val = 0.0
                if 'discount' in col_map and pd.notna(row[col_map['discount']]):
                    disc_val = parse_float_or_none(row[col_map['discount']]) or 0.0
                    
                phone_val = str(row[col_map['phone']]).strip() if 'phone' in col_map and pd.notna(row[col_map['phone']]) else ""
                email_val = str(row[col_map['email']]).strip() if 'email' in col_map and pd.notna(row[col_map['email']]) else ""
                gstin_val = str(row[col_map['gstin']]).strip() if 'gstin' in col_map and pd.notna(row[col_map['gstin']]) else ""
                addr_val = str(row[col_map['address']]).strip() if 'address' in col_map and pd.notna(row[col_map['address']]) else ""
                
                cur.execute("SELECT id FROM CUSTOMERS WHERE LOWER(name) = LOWER(?)", (c_name,))
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        "UPDATE CUSTOMERS SET discount_percent = ?, phone = ?, email = ?, gstin = ?, address = ? WHERE id = ?",
                        (disc_val, phone_val, email_val, gstin_val, addr_val, existing['id'])
                    )
                else:
                    cur.execute(
                        "INSERT INTO CUSTOMERS (name, discount_percent, phone, email, gstin, address) VALUES (?, ?, ?, ?, ?, ?)",
                        (c_name, disc_val, phone_val, email_val, gstin_val, addr_val)
                    )
                cur.execute(f"RELEASE SAVEPOINT {savepoint_name};")
                successful_records += 1
            except Exception as r_err:
                try: cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                except: pass
                failed_records += 1
                errors.append(f"Row {idx+2}: {str(r_err)}")
                
        cur.execute("COMMIT;")
        conn.close()
        
        status = 'success' if failed_records == 0 else ('partial_success' if successful_records > 0 else 'failed')
        execute_db(
            "INSERT INTO IMPORT_LOG (import_type, filename, total_records, successful_records, failed_records, imported_by, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('customers', filename, total_records, successful_records, failed_records, imported_by, status)
        )
        return {"status": status, "total_records": total_records, "successful_records": successful_records, "failed_records": failed_records, "errors": errors[:50]}

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
                sheet_name='Stock Group Reorder Status', 
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

    @classmethod
    def import_from_tally_xml(cls, xml_data, filename='tally_live.xml', imported_by='Tally Live Sync'):
        """Parses Tally Prime Stock Summary XML and imports stock levels and rates into SQLite."""
        import xml.etree.ElementTree as ET
        
        if isinstance(xml_data, bytes):
            xml_str = xml_data.decode('utf-8', errors='ignore')
        else:
            xml_str = str(xml_data)
            
        xml_clean = re.sub(r'&(?!amp;|lt;|gt;|apos;|quot;)', '&amp;', xml_str)
        
        try:
            root = ET.fromstring(xml_clean)
        except Exception as ex:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [f"Invalid Tally XML structure: {str(ex)}"]
            }
            
        acc_names = root.findall('.//DSPACCNAME')
        stk_infos = root.findall('.//DSPSTKINFO')
        
        tally_ledgers = root.findall('.//LEDGER')
        if not acc_names and not tally_ledgers:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": ["No Stock Summary or Ledger blocks found in Tally XML response."]
            }
            
        total_records = min(len(acc_names), len(stk_infos)) if (acc_names and stk_infos) else 0
        successful_records = 0
        failed_records = 0
        errors = []
        
        conn = get_db_connection()
        conn.isolation_level = None
        cur = conn.cursor()
        cur.execute("BEGIN TRANSACTION;")
        
        for idx in range(total_records):
            a_el = acc_names[idx]
            s_el = stk_infos[idx]
            
            name_el = a_el.find('.//DSPDISPNAME')
            qty_el = s_el.find('.//DSPCLQTY')
            rate_el = s_el.find('.//DSPCLRATE')
            
            if name_el is None or not name_el.text:
                continue
                
            item_code = name_el.text.strip()
            if not item_code or item_code.lower() == 'nan' or item_code.lower() == 'total':
                continue
                
            qty_str = qty_el.text.strip() if qty_el is not None and qty_el.text else '0'
            rate_str = rate_el.text.strip() if rate_el is not None and rate_el.text else '0'
            
            # parse numeric stock
            m_qty = re.search(r'[-+]?\d*\.?\d+', qty_str.replace(',', ''))
            stock_val = float(m_qty.group(0)) if m_qty else 0.0
            
            # parse numeric rate
            m_rate = re.search(r'[-+]?\d*\.?\d+', rate_str.replace(',', ''))
            rate_val = float(m_rate.group(0)) if m_rate else 0.0
            
            savepoint_name = f"sp_tally_{idx}"
            try:
                cur.execute(f"SAVEPOINT {savepoint_name};")
                
                # 1. Upsert product
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
                    
                # 2. Upsert inventory stock level
                cur.execute("SELECT purc_orders_pending, sale_orders_due, reorder_level, min_reorder_qty FROM INVENTORY WHERE product_id = ?", (product_id,))
                inv = cur.fetchone()
                
                purc_val = inv['purc_orders_pending'] if inv and inv['purc_orders_pending'] else 0.0
                sales_val = inv['sale_orders_due'] if inv and inv['sale_orders_due'] else 0.0
                reorder_val = inv['reorder_level'] if inv and inv['reorder_level'] else 0.0
                min_reorder_val = inv['min_reorder_qty'] if inv and inv['min_reorder_qty'] else 0.0
                
                nett_val = stock_val + purc_val - sales_val
                shortfall_val = max(0.0, reorder_val - nett_val)
                order_to_place_val = max(shortfall_val, min_reorder_val) if shortfall_val > 0 else 0.0
                
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
                            current_stock = ?, nett_available = ?, short_fall = ?, 
                            order_to_be_placed = ?, last_updated = ? 
                           WHERE product_id = ?""",
                        (
                            stock_val, nett_val, shortfall_val, 
                            order_to_place_val, datetime.now().isoformat(), product_id
                        )
                    )
                    
                # 3. Update cost rate if present in Tally
                if rate_val > 0:
                    price_per_100 = rate_val
                    price_per_unit = rate_val / 100.0
                    
                    cur.execute("SELECT id, price_per_100_pcs FROM PRODUCT_COSTS WHERE product_id = ? AND is_current = 1", (product_id,))
                    active_cost = cur.fetchone()
                    
                    price_changed = True
                    if active_cost and abs(active_cost['price_per_100_pcs'] - price_per_100) < 0.001:
                        price_changed = False
                        
                    if price_changed:
                        if active_cost:
                            cur.execute(
                                "UPDATE PRODUCT_COSTS SET is_current = 0, effective_to = ? WHERE id = ?",
                                (datetime.now().isoformat(), active_cost['id'])
                            )
                        cur.execute(
                            "INSERT INTO PRODUCT_COSTS (product_id, price_per_100_pcs, price_per_unit, effective_from, is_current) VALUES (?, ?, ?, ?, ?)",
                            (product_id, price_per_100, price_per_unit, datetime.now().isoformat(), 1)
                        )
                
                cur.execute(f"RELEASE SAVEPOINT {savepoint_name};")
                successful_records += 1
            except Exception as row_error:
                try: cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                except: pass
                failed_records += 1
                errors.append(f"Item {item_code}: {str(row_error)}")
                
        # Also parse LEDGER elements if present in Tally XML (Master Export)
        tally_ledgers = root.findall('.//LEDGER')
        for idx_l, leg in enumerate(tally_ledgers):
            c_name = leg.attrib.get('NAME') or leg.findtext('NAME')
            if not c_name:
                nl = leg.find('.//LANGUAGENAME.LIST/NAME.LIST/NAME')
                if nl is not None: c_name = nl.text
            if not c_name: continue
            c_name = c_name.strip()
            if not c_name or c_name.lower() in ('nan', 'total'): continue
            
            parent_grp = (leg.findtext('PARENT') or "").strip().lower()
            # Filter to only customer/debtor ledgers
            if parent_grp and not any(kw in parent_grp for kw in ['debtor', 'customer']):
                continue
            
            gstin = leg.findtext('PARTYGSTIN') or leg.findtext('GSTIN') or ""
            phone = leg.findtext('LEDGERPHONE') or leg.findtext('MOBILE') or ""
            email = leg.findtext('EMAIL') or ""
            addr_list = [a.text for a in leg.findall('.//ADDRESS') if a is not None and a.text]
            address = "\n".join(addr_list) if addr_list else ""
            
            sp_leg = f"sp_leg_{idx_l}"
            try:
                cur.execute(f"SAVEPOINT {sp_leg};")
                cur.execute("SELECT id FROM CUSTOMERS WHERE LOWER(name) = LOWER(?)", (c_name,))
                ex = cur.fetchone()
                if ex:
                    if gstin:
                        cur.execute("UPDATE CUSTOMERS SET gst_number = ? WHERE id = ?", (gstin, ex['id']))
                else:
                    cur.execute("INSERT INTO CUSTOMERS (name, discount_percentage, gst_number) VALUES (?, ?, ?)", (c_name, 0.0, gstin))
                cur.execute(f"RELEASE SAVEPOINT {sp_leg};")
                successful_records += 1
            except Exception:
                try: cur.execute(f"ROLLBACK TO SAVEPOINT {sp_leg};")
                except: pass
                
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
    def sync_from_tally_port(cls, tally_url='http://localhost:9000', imported_by='Tally Live Sync'):
        """Connects directly to Tally Prime XML HTTP Server and imports live Stock Summary & Customers."""
        import urllib.request
        
        tdl_stock_query = b"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Stock Summary</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <ISITEMWISE>Yes</ISITEMWISE>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

        tdl_ledger_query = b"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>LedgerColl</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="LedgerColl" ISINITIALIZE="Yes">
            <TYPE>Ledger</TYPE>
            <NATIVEMETHOD>Name</NATIVEMETHOD>
            <NATIVEMETHOD>Parent</NATIVEMETHOD>
            <NATIVEMETHOD>PartyGSTIN</NATIVEMETHOD>
            <NATIVEMETHOD>LedgerPhone</NATIVEMETHOD>
            <NATIVEMETHOD>Email</NATIVEMETHOD>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""
        try:
            # 1. Fetch Stock Summary
            req_stock = urllib.request.Request(tally_url.strip(), data=tdl_stock_query, headers={'Content-Type': 'text/xml'})
            with urllib.request.urlopen(req_stock, timeout=15) as resp:
                xml_stock_data = resp.read()
                
            res_stock = cls.import_from_tally_xml(xml_stock_data, filename='tally_stock_9000.xml', imported_by=imported_by)
            
            # 2. Fetch Customer Ledgers
            try:
                req_ledger = urllib.request.Request(tally_url.strip(), data=tdl_ledger_query, headers={'Content-Type': 'text/xml'})
                with urllib.request.urlopen(req_ledger, timeout=15) as resp:
                    xml_ledger_data = resp.read()
                cls.import_from_tally_xml(xml_ledger_data, filename='tally_ledgers_9000.xml', imported_by=imported_by)
            except Exception:
                pass
                
            return res_stock
        except Exception as ex:
            return {
                "status": "failed",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [f"Failed to connect to Tally Prime on {tally_url}: {str(ex)}"]
            }
