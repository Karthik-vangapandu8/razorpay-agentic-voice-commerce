import os
import json
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

BILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bills")
os.makedirs(BILLS_DIR, exist_ok=True)

class BillItem(BaseModel):
    item_name: str
    quantity: int = 1
    unit_price: float
    total_price: float

class BillInvoice(BaseModel):
    invoice_id: str = Field(default_factory=lambda: f"MB-INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}")
    title: str = "MuscleBlaze Official Store Invoice"
    customer_name: str = "Guest Customer"
    items: List[BillItem]
    subtotal: float
    discount_code: Optional[str] = "FIT10"
    discount_percent: float = 10.0
    discount_amount: float
    free_gifts: List[str] = Field(default_factory=lambda: ["MuscleBlaze Premium Shaker Bottle"])
    final_total: float
    payment_method: str = "Pending"
    order_status: str = "Order Confirmed & Locked"
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def create_and_save_bill(
    customer_name: str,
    item_name: str,
    quantity: int = 1,
    unit_price: float = 4499.0,
    discount_code: str = "FIT10",
    free_gift: str = "MuscleBlaze Premium Shaker Bottle"
) -> str:
    """Generate and save a validated Pydantic Bill Invoice."""
    subtotal = round(float(unit_price * quantity), 2)
    discount_percent = 10.0 if "FIT" in discount_code.upper() or "10" in discount_code else 0.0
    discount_amount = round((subtotal * discount_percent) / 100.0, 2)
    final_total = round(subtotal - discount_amount, 2)
    
    item = BillItem(
        item_name=item_name,
        quantity=quantity,
        unit_price=unit_price,
        total_price=subtotal
    )
    
    invoice = BillInvoice(
        title=f"MuscleBlaze Invoice for {customer_name}",
        customer_name=customer_name,
        items=[item],
        subtotal=subtotal,
        discount_code=discount_code if discount_percent > 0 else "None",
        discount_percent=discount_percent,
        discount_amount=discount_amount,
        free_gifts=[free_gift] if free_gift else [],
        final_total=final_total
    )
    
    json_path = os.path.join(BILLS_DIR, f"{invoice.invoice_id}.json")
    txt_path = os.path.join(BILLS_DIR, f"{invoice.invoice_id}.txt")
    
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(invoice.model_dump_json(indent=2))
        
    receipt_text = f"""
============================================================
🏋️‍♂️  MUSCLEBLAZE OFFICIAL STORE INVOICE
============================================================
Invoice ID    : {invoice.invoice_id}
Date & Time   : {invoice.created_at}
Customer Name : {invoice.customer_name}
Order Status  : {invoice.order_status}
------------------------------------------------------------
ITEMS ORDERED:
  • {item.item_name}
    Qty: {item.quantity} x ₹{item.unit_price:,.2f} = ₹{item.total_price:,.2f}

------------------------------------------------------------
Subtotal            : ₹{invoice.subtotal:,.2f}
Discount ({invoice.discount_code} - {invoice.discount_percent}%): -₹{invoice.discount_amount:,.2f}
FREE Perks Included : {', '.join(invoice.free_gifts) if invoice.free_gifts else 'None'}
------------------------------------------------------------
GRAND TOTAL PAYABLE : ₹{invoice.final_total:,.2f}
============================================================
"""
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(receipt_text.strip())
        
    print(f"\n🧾 [BILL GENERATED] Saved to {txt_path}")
    print(receipt_text)
    
    return json.dumps({
        "status": "success",
        "invoice_id": invoice.invoice_id,
        "customer": invoice.customer_name,
        "item": item_name,
        "subtotal": f"₹{subtotal}",
        "discount": f"₹{discount_amount} ({discount_code})",
        "final_amount": f"₹{final_total}",
        "free_gift": free_gift
    }, ensure_ascii=False)

BILLING_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_bill_invoice",
        "description": "Generate Pydantic store invoice when customer locks order.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "item_name": {"type": "string"},
                "unit_price": {"type": "number"},
                "quantity": {"type": "integer"},
                "discount_code": {"type": "string"}
            },
            "required": ["customer_name", "item_name", "unit_price"]
        }
    }
}
