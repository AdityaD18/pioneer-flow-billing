from dataclasses import dataclass, field, asdict
from typing import List, Optional

@dataclass
class StockItem:
    product_id: int
    part_number: str
    part_name: Optional[str] = None
    series: Optional[str] = None
    make: Optional[str] = "WAGO"
    packing_quantity: int = 1
    current_stock: float = 0.0
    cost_price_100: float = 0.0
    rate_per_unit: float = 0.0

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "Part Number": self.part_number,
            "Series": self.series or "",
            "Make": self.make or "",
            "Packing Qty": self.packing_quantity,
            "Current Stock (PCS)": self.current_stock,
            "Cost / 100 Pcs (INR)": self.cost_price_100,
            "Rate / Pc (INR)": self.rate_per_unit
        }

@dataclass
class StockGroup:
    name: str
    series_code: Optional[str] = None

@dataclass
class Customer:
    id: Optional[int]
    name: str
    discount_percentage: float = 0.0
    gst_number: Optional[str] = None
    payment_terms: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)

@dataclass
class Ledger:
    id: Optional[int]
    name: str
    reference_number: str
    customer_name: str
    date: str
    grand_total: float
    type: str = "Invoice"

    def to_dict(self):
        return asdict(self)

@dataclass
class PurchaseOrder:
    part_number: str
    make: str
    purc_orders_pending: float
    current_stock: float
    nett_available: float

    def to_dict(self):
        return asdict(self)

@dataclass
class SalesOrder:
    part_number: str
    make: str
    sale_orders_due: float
    current_stock: float
    nett_available: float

    def to_dict(self):
        return asdict(self)

@dataclass
class InvoiceItem:
    product_id: int
    part_number: str
    part_name: Optional[str]
    quantity: float
    unit_price: float
    discount_percentage: float
    gst_percentage: float
    line_total: float

    def to_dict(self):
        return asdict(self)

@dataclass
class Invoice:
    id: int
    invoice_number: str
    order_id: int
    order_number: str
    customer_name: str
    invoice_date: str
    grand_total: float
    created_at: str
    items: List[InvoiceItem] = field(default_factory=list)

    def to_dict(self):
        res = asdict(self)
        res['items'] = [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.items]
        return res

@dataclass
class Quotation:
    id: int
    quotation_number: str
    customer_name: str
    created_at: str
    grand_total: float
    items: List[InvoiceItem] = field(default_factory=list)

    def to_dict(self):
        res = asdict(self)
        res['items'] = [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.items]
        return res

@dataclass
class Company:
    company_name: str
    company_subtitle: str
    company_footer: str
    default_gst_rate: float
    default_payment_terms: str

    def to_dict(self):
        return asdict(self)
