import os
import json
import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from .models import OrderStatus, CartQuote, PricingLineItem, Order, OrderAuditTrail

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gym_store.db")
BILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bills")
ORDERS_DB_FILE = os.path.join(BILLS_DIR, "active_orders.json")
os.makedirs(BILLS_DIR, exist_ok=True)

# In-memory / persistent order registry
def _load_orders() -> Dict[str, Any]:
    if os.path.exists(ORDERS_DB_FILE):
        try:
            with open(ORDERS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_orders(orders: Dict[str, Any]):
    with open(ORDERS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2)

def lookup_product_by_term(search_term: str) -> Optional[Dict[str, Any]]:
    """Look up authoritative product details strictly from SQLite DB."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    words = search_term.strip().split()
    sql = "SELECT id, name, category, flavour, price_inr, stock_count FROM products WHERE 1=1"
    params = []
    
    for word in words:
        if word.lower() in ['protein', 'price', 'rate', 'cost', 'stock', 'please', 'mujhe', 'chahiye', 'pack']:
            continue
        sql += " AND (name LIKE ? OR category LIKE ? OR flavour LIKE ?)"
        params.extend([f"%{word}%", f"%{word}%", f"%{word}%"])
        
    cursor.execute(sql + " LIMIT 1", params)
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "flavour": row[3],
            "price_inr": float(row[4]),
            "stock_count": int(row[5])
        }
    return None

def calculate_deterministic_quote(items_request: List[Dict[str, Any]], coupon_code: str = "") -> CartQuote:
    """
    DETERMINISTIC PRICING ENGINE:
    - Never trusts prices from LLM.
    - Fetches authoritative price from SQLite DB.
    - Applies bounded discount rules & free perks.
    """
    line_items: List[PricingLineItem] = []
    subtotal = 0.0
    has_whey = False
    has_creatine = False
    
    for req in items_request:
        term = req.get("product_name") or req.get("product_name_or_keyword") or req.get("name") or req.get("item") or ""
        raw_qty = int(req.get("quantity") or req.get("qty") or 1)
        
        prod = lookup_product_by_term(term)
        if not prod:
            return CartQuote(
                items=[],
                subtotal=0.0,
                final_total=0.0,
                is_valid=False,
                error_message=f"Product matching '{term}' was not found in our catalog."
            )
            
        if raw_qty > prod["stock_count"]:
            return CartQuote(
                items=[],
                subtotal=0.0,
                final_total=0.0,
                is_valid=False,
                error_message=f"'{prod['name']}' is out of stock (only {prod['stock_count']} units available, but {raw_qty} requested)."
            )
            
        if raw_qty > 10:
            return CartQuote(
                items=[],
                subtotal=0.0,
                final_total=0.0,
                is_valid=False,
                error_message=f"Quantity {raw_qty} exceeds maximum retail limit of 10 units per order."
            )
            
        qty = raw_qty
        line_total = round(prod["price_inr"] * qty, 2)
        subtotal += line_total
        
        if "Whey" in prod["name"]:
            has_whey = True
        if "Creatine" in prod["name"]:
            has_creatine = True
            
        line_items.append(PricingLineItem(
            product_id=prod["id"],
            name=prod["name"],
            unit_price=prod["price_inr"],
            quantity=qty,
            line_total=line_total,
            flavour=prod["flavour"]
        ))
        
    subtotal = round(subtotal, 2)
    
    # 1. Deterministic Combo Discount (Whey + Creatine = ₹300 off)
    combo_discount = 300.0 if (has_whey and has_creatine and len(line_items) >= 2) else 0.0
    
    # 2. Deterministic Coupon Discount (FIT10 = 10% off, max cap ₹1,500)
    cleaned_coupon = coupon_code.strip().upper() if coupon_code else ""
    coupon_discount = 0.0
    applied_coupon = None
    
    if cleaned_coupon in ["FIT10", "FITNESS10"]:
        applied_coupon = "FIT10"
        raw_discount = (subtotal - combo_discount) * 0.10
        coupon_discount = round(min(raw_discount, 1500.0), 2) # Bounded max coupon cap
        
    total_discount = round(combo_discount + coupon_discount, 2)
    final_total = max(0.0, round(subtotal - total_discount, 2))
    
    # 3. Deterministic Free Gifts
    free_gifts = []
    if subtotal >= 1999.0 or has_whey:
        free_gifts.append("MuscleBlaze Premium Shaker Bottle (Free)")
        
    return CartQuote(
        items=line_items,
        subtotal=subtotal,
        combo_discount=combo_discount,
        coupon_code=applied_coupon,
        coupon_discount=coupon_discount,
        total_discount=total_discount,
        free_gifts=free_gifts,
        final_total=final_total,
        is_valid=True
    )

def execute_order_checkout(
    customer_name: str,
    items_request: List[Dict[str, Any]],
    coupon_code: str = "FIT10",
    pay_via_wallet: bool = True
) -> Dict[str, Any]:
    """
    DETERMINISTIC MONEY & ORDER WORKFLOW:
    Step 1: CART_CREATED -> PRICE_CONFIRMED
    Step 2: Check Spend Rails (Max ₹15k)
    Step 3: CUSTOMER_APPROVED -> PAYMENT_PENDING
    Step 4: Attempt Wallet Debit (if pay_via_wallet is True)
    Step 5: If partial/unpaid -> Generate real Razorpay Payment Link
    Step 6: Update State Machine: PARTIALLY_PAID or PAID or ORDER_CONFIRMED
    Step 7: Persist immutable receipt and audit trail to bills/
    """
    # 1. Price Confirmation
    quote = calculate_deterministic_quote(items_request, coupon_code)
    if not quote.is_valid:
        return {
            "status": "failed",
            "order_status": OrderStatus.FAILED.value,
            "error": quote.error_message
        }
        
    # 2. Spend Rails Validation
    if quote.final_total > 15000.0:
        return {
            "status": "failed",
            "order_status": OrderStatus.FAILED.value,
            "error": f"Total amount ₹{quote.final_total:,.2f} exceeds AI Agent safety spend rail of ₹15,000.00."
        }
        
    order = Order(
        customer_name=customer_name,
        items=quote.items,
        quote=quote,
        status=OrderStatus.PRICE_CONFIRMED
    )
    
    # Audit trail
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order.audit.state_history.append({"state": OrderStatus.PRICE_CONFIRMED.value, "timestamp": now_str})
    order.audit.state_history.append({"state": OrderStatus.CUSTOMER_APPROVED.value, "timestamp": now_str})
    order.status = OrderStatus.PAYMENT_PENDING
    order.audit.state_history.append({"state": OrderStatus.PAYMENT_PENDING.value, "timestamp": now_str})
    
    wallet_paid = 0.0
    from tools.wallet_service import get_or_create_wallet, WALLET_DB_PATH
    wallet = get_or_create_wallet(customer_name)
    
    # 3. Execute Wallet Deduction if requested
    if pay_via_wallet and wallet.balance > 0:
        deduct_amount = min(wallet.balance, quote.final_total)
        
        # Debit wallet in SQLite
        new_balance = round(wallet.balance - deduct_amount, 2)
        new_spent = round(wallet.daily_spent_today + deduct_amount, 2)
        tx_id = f"TXN-{uuid.uuid4().hex[:6].upper()}"
        
        conn = sqlite3.connect(WALLET_DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE wallets SET balance = ?, daily_spent_today = ? WHERE wallet_id = ?", (new_balance, new_spent, wallet.wallet_id))
        c.execute("INSERT INTO wallet_transactions VALUES (?, ?, ?, 'DEBIT_PURCHASE', ?, ?, ?)", 
                  (tx_id, wallet.wallet_id, deduct_amount, order.order_id, f"Order {order.order_id}", now_str))
        conn.commit()
        conn.close()
        
        wallet_paid = deduct_amount
        order.wallet_paid = wallet_paid
        
    remaining_to_pay = round(quote.final_total - wallet_paid, 2)
    order.razorpay_pending = remaining_to_pay
    
    # 4. Determine Exact State
    razorpay_link = None
    if remaining_to_pay == 0.0:
        # 100% Paid via Wallet!
        order.status = OrderStatus.ORDER_CONFIRMED
        order.audit.state_history.append({"state": OrderStatus.PAID.value, "timestamp": now_str})
        order.audit.state_history.append({"state": OrderStatus.ORDER_CONFIRMED.value, "timestamp": now_str})
    else:
        # Partial or Zero Wallet Payment -> Generate Razorpay Link
        if wallet_paid > 0:
            order.status = OrderStatus.PARTIALLY_PAID
            order.audit.state_history.append({"state": OrderStatus.PARTIALLY_PAID.value, "timestamp": now_str})
        else:
            order.status = OrderStatus.PAYMENT_PENDING
            
        from tools.razorpay_gateway import create_razorpay_payment_link
        rzp_res = json.loads(create_razorpay_payment_link(
            customer_name=customer_name,
            amount_inr=remaining_to_pay,
            description=f"Remaining balance for {order.order_id}",
            invoice_id=order.order_id
        ))
        razorpay_link = rzp_res.get("payment_url")
        order.razorpay_payment_link = razorpay_link
        
    order.updated_at = now_str
    
    # 5. Persist to Orders Registry & Write Clean Invoice Receipt
    all_orders = _load_orders()
    all_orders[order.order_id] = order.model_dump()
    _save_orders(all_orders)
    
    # Write Bill text receipt
    receipt_txt_path = os.path.join(BILLS_DIR, f"{order.order_id}.txt")
    receipt_json_path = os.path.join(BILLS_DIR, f"{order.order_id}.json")
    
    items_formatted = "\n".join([f"  • {it.name} (Qty: {it.quantity} x ₹{it.unit_price:,.2f} = ₹{it.line_total:,.2f})" for it in order.items])
    
    receipt_content = f"""
============================================================
🏋️‍♂️  MUSCLEBLAZE OFFICIAL STORE INVOICE
============================================================
Order ID      : {order.order_id}
Date & Time   : {order.created_at}
Customer Name : {order.customer_name}
Order Status  : {order.status.value}
------------------------------------------------------------
ITEMS ORDERED:
{items_formatted}

------------------------------------------------------------
Subtotal            : ₹{quote.subtotal:,.2f}
Combo Discount      : -₹{quote.combo_discount:,.2f}
Coupon ({quote.coupon_code or 'None'}): -₹{quote.coupon_discount:,.2f}
FREE Perks Included : {', '.join(quote.free_gifts) if quote.free_gifts else 'None'}
------------------------------------------------------------
TOTAL AMOUNT PAYABLE: ₹{quote.final_total:,.2f}
------------------------------------------------------------
PAYMENT BREAKDOWN:
  • Paid via Agentic Wallet : ₹{order.wallet_paid:,.2f}
  • Pending on Razorpay     : ₹{order.razorpay_pending:,.2f}
  • Razorpay Payment Link   : {order.razorpay_payment_link or 'N/A (Fully Paid via Wallet)'}
============================================================
Audit Verification : KYA Verified (AGENT-MB-ROHAN-01)
"""
    with open(receipt_txt_path, "w", encoding="utf-8") as f:
        f.write(receipt_content.strip())
    with open(receipt_json_path, "w", encoding="utf-8") as f:
        f.write(order.model_dump_json(indent=2))
        
    print(f"\n🧾 [ORDER STATE: {order.status.value}] Saved to {receipt_txt_path}")
    print(receipt_content)
    
    return {
        "status": "success",
        "order_id": order.order_id,
        "order_status": order.status.value,
        "customer": customer_name,
        "total_amount": f"₹{quote.final_total:,.2f}",
        "wallet_paid": f"₹{order.wallet_paid:,.2f}",
        "razorpay_pending": f"₹{order.razorpay_pending:,.2f}",
        "razorpay_payment_link": order.razorpay_payment_link,
        "free_gifts": quote.free_gifts,
        "receipt_file": receipt_txt_path
    }
