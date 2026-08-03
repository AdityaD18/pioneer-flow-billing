# Sequence Prefixes & Numbering Rules
INVOICE_SEQ_PREFIX = "INV"
QUOTATION_SEQ_PREFIX = "QTN"
DEFAULT_START_SEQ = 1001

# Source Sheet Names & Column Synonym Definitions
DEFAULT_STOCK_SHEET_NAME = "Stock Group Reorder Status"
DEFAULT_COST_SHEET_NAME = "PRICE LIST"

# Aliases for backward compatibility
EXCEL_STOCK_SHEET_NAME = DEFAULT_STOCK_SHEET_NAME
EXCEL_COST_SHEET_NAME = DEFAULT_COST_SHEET_NAME

# Master Synonym Mapping Arrays for Header Auto-Detection
ITEM_CODE_SYNONYMS = ['item code', 'item_code', 'part number', 'part_number', 'part no', 'part_no', 'item', 'code', 'wago part no.', 'wago part no']
CLOSING_STOCK_SYNONYMS = ['closing stock', 'current stock', 'stock', 'qty', 'quantity', 'balance', 'closing_stock']
PURC_PENDING_SYNONYMS = ['purc. orders pending', 'purc orders pending', 'purc_orders_pending', 'purchase orders pending', 'po pending', 'pending purchase']
SALE_DUE_SYNONYMS = ['sale orders due', 'sale_orders_due', 'sales orders due', 'so due', 'due sales']
NETT_AVAILABLE_SYNONYMS = ['nett available', 'nett_available', 'net available', 'available stock']
REORDER_LEVEL_SYNONYMS = ['reorder level', 'reorder_level', 'reorder qty', 'min level']
SHORTFALL_SYNONYMS = ['short fall', 'shortfall', 'short_fall', 'shortage']
MIN_REORDER_SYNONYMS = ['min. reorder qty', 'min reorder qty', 'min_reorder_qty', 'minimum reorder']
ORDER_TO_PLACE_SYNONYMS = ['order to be placed', 'order_to_be_placed', 'order to place', 'suggested order']

# Cost Price List Synonym Mapping Arrays
PRICE_SYNONYMS = ['cat. price / 100 in rs.', 'cat. price / 100', 'price/100', 'price_100', 'price', 'rate', 'cost', 'list price', 'cat price']
PACKING_QTY_SYNONYMS = ['std. pkg. / unit qty', 'std pkg', 'packing', 'packing_qty', 'pkg qty', 'unit qty']
SERIES_SYNONYMS = ['series', 'category', 'group', 'item series']
