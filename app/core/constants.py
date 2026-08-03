"""
Immutable Domain & System Constants for Pioneer Flow Billing ERP.
"""

# Numbering System Sequence Prefixes
INVOICE_SEQ_PREFIX = "INV"
QUOTATION_SEQ_PREFIX = "QTN"
DEFAULT_START_SEQ = 1001

# Excel Sheet Names & Column Synonym Definitions
EXCEL_STOCK_SHEET_NAME = "Stock Group Reorder Status"
EXCEL_COST_SHEET_NAME = "PRICE LIST"

ITEM_CODE_SYNONYMS = ['item code', 'part number', 'part no', 'partno', 'code', 'item_code', 'part_no']
CLOSING_STOCK_SYNONYMS = ['closing stock', 'current stock', 'closing stock (pcs)', 'closing stock(pcs)', 'available stock', 'current stock (pcs)', 'stock']
PURC_PENDING_SYNONYMS = ['purc orders pending', 'purchase orders pending', 'purc orders', 'purchase pending', 'pending purchase', 'incoming stock', 'pending orders']
SALE_DUE_SYNONYMS = ['sale orders due', 'sales orders due', 'sale orders', 'sales due', 'due sales', 'outgoing stock', 'reserved stock']
NETT_AVAILABLE_SYNONYMS = ['nett available', 'net available', 'nett qty', 'net qty', 'available qty']
REORDER_LEVEL_SYNONYMS = ['re-order level', 'reorder level', 'reorder qty limit', 'reorder level (pcs)']
SHORTFALL_SYNONYMS = ['short fall', 'shortfall', 'short qty', 'shortage']
MIN_REORDER_SYNONYMS = ['min reorder qty', 'min reorder', 'minimum order qty', 'min reorder quantity']
ORDER_TO_PLACE_SYNONYMS = ['order to be placed', 'placed order', 'order to place', 'to be placed', 'order to be placed (pcs)']

PRICE_SYNONYMS = ['decimal converted', 'converted rate', 'price', 'rate', 'mrp', 'cost']
PACKING_QTY_SYNONYMS = ['packing', 'quantity pcs', 'pack qty', 'packing quantity']
SERIES_SYNONYMS = ['series', 'group', 'category']
