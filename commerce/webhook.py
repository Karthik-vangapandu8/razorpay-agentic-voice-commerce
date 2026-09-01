import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any
from .models import OrderStatus, Order
from .engine import _load_orders, _save_orders, DB_PATH, BILLS_DIR

PROCESSED_WEBHOOKS_FILE = os.path.join(BILLS_DIR, "processed_webhooks.json")

def _load_processed_webhooks() -> list:
    if os.path.exists(PROCESSED_WEBHOOKS_FILE):
        try:
            with open(PROCESSED_WEBHOOKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _save_processed_webhooks(webhooks: list):
    with open(PROCESSED_WEBHOOKS_FILE, "w", encoding="utf-8") as f:
        json.dump(webhooks, f, indent=2)

def handle_razorpay_webhook(
    event: str,
    payment_id: str,
    order_id: str,
    amount_paid_inr: float,
    event_id: str = None
) -> Dict[str, Any]:
    """
    IDEMPOTENT RAZORPAY WEBHOOK HANDLER:
    - Protects against duplicate webhook deliveries (idempotency).
    - Verifies order state transitions to PAID -> ORDER_CONFIRMED.
    - Decrements stock in SQLite.
    """
    if not event_id:
        event_id = f"evt_{payment_id}_{order_id}"
        
    processed = _load_processed_webhooks()
    if event_id in processed:
        print(f"\n⚠️ [WEBHOOK IDEMPOTENT] Event {event_id} already processed. Skipping duplicate.")
        return {
            "status": "ignored_duplicate",
            "message": f"Webhook event {event_id} was already processed."
        }
        
    orders = _load_orders()
    order_dict = orders.get(order_id)
    if not order_dict:
        return {
            "status": "failed",
            "message": f"Order {order_id} not found."
        }
        
    order = Order(**order_dict)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Update payment amounts
    order.razorpay_paid += amount_paid_inr
    order.razorpay_pending = max(0.0, round(order.razorpay_pending - amount_paid_inr, 2))
    order.razorpay_payment_id = payment_id
    
    # State Machine Transition
    if order.razorpay_pending == 0.0:
        order.status = OrderStatus.ORDER_CONFIRMED
        order.audit.state_history.append({"state": OrderStatus.PAID.value, "timestamp": now_str})
        order.audit.state_history.append({"state": OrderStatus.ORDER_CONFIRMED.value, "timestamp": now_str, "razorpay_payment_id": payment_id})
        
        # Decrement Inventory in SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for item in order.items:
            cursor.execute("UPDATE products SET stock_count = stock_count - ? WHERE id = ?", (item.quantity, item.product_id))
        conn.commit()
        conn.close()
        print(f"\n📦 [INVENTORY DECREMENTED] Deducted purchased items from SQLite store.")
    else:
        order.status = OrderStatus.PARTIALLY_PAID
        order.audit.state_history.append({"state": OrderStatus.PARTIALLY_PAID.value, "timestamp": now_str, "amount": amount_paid_inr})
        
    order.updated_at = now_str
    orders[order.order_id] = order.model_dump()
    _save_orders(orders)
    
    # Record webhook as processed (Idempotency)
    processed.append(event_id)
    _save_processed_webhooks(processed)
    
    # Rewrite receipt with ORDER_CONFIRMED status
    receipt_txt_path = os.path.join(BILLS_DIR, f"{order.order_id}.txt")
    receipt_json_path = os.path.join(BILLS_DIR, f"{order.order_id}.json")
    with open(receipt_json_path, "w", encoding="utf-8") as f:
        f.write(order.model_dump_json(indent=2))
        
    print(f"\n✅ [WEBHOOK PROCESSED] Order {order.order_id} is now: {order.status.value}!")
    return {
        "status": "success",
        "order_id": order.order_id,
        "new_order_status": order.status.value,
        "total_paid": f"₹{order.wallet_paid + order.razorpay_paid:,.2f}",
        "razorpay_payment_id": payment_id
    }
