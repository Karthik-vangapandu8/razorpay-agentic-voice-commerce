import json
from typing import List, Dict, Any, Union
from commerce.engine import calculate_deterministic_quote, execute_order_checkout

def get_cart_pricing_quote(items: Any, coupon_code: str = "FIT10") -> str:
    """
    Tool: Calculate 100% deterministic pricing, combo discounts, coupon validation,
    and free perks without trusting LLM calculations.
    """
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            items = [{"product_name": items, "quantity": 1}]
            
    quote = calculate_deterministic_quote(items, coupon_code)
    return quote.model_dump_json()

def process_order_checkout(
    customer_name: str,
    items: Any,
    coupon_code: str = "FIT10",
    pay_via_wallet: Any = "true"
) -> str:
    """
    Tool: Execute deterministic money workflow:
    Inventory check -> Pricing -> Bounding rails -> Wallet debit -> Razorpay link -> State Machine.
    """
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            items = [{"product_name": items, "quantity": 1}]
            
    # Coerce pay_via_wallet flexibly
    should_pay_wallet = True
    if isinstance(pay_via_wallet, bool):
        should_pay_wallet = pay_via_wallet
    elif isinstance(pay_via_wallet, str):
        should_pay_wallet = pay_via_wallet.lower() in ["true", "1", "yes", "y", "wallet"]
        
    res = execute_order_checkout(
        customer_name=customer_name,
        items_request=items,
        coupon_code=coupon_code,
        pay_via_wallet=should_pay_wallet
    )
    return json.dumps(res, ensure_ascii=False)

COMMERCE_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_cart_pricing_quote",
            "description": "Calculate exact store price, combo discounts, and free perks for a list of items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_name": {"type": "string"},
                                "quantity": {"type": "integer"}
                            },
                            "required": ["product_name"]
                        }
                    },
                    "coupon_code": {"type": "string", "description": "Optional coupon (e.g. 'FIT10')"}
                },
                "required": ["items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "process_order_checkout",
            "description": "Execute deterministic order checkout with wallet split-pay and Razorpay payment link.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Name of the customer"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_name": {"type": "string"},
                                "quantity": {"type": "integer"}
                            },
                            "required": ["product_name"]
                        }
                    },
                    "coupon_code": {"type": "string", "description": "Discount coupon code"},
                    "pay_via_wallet": {"type": "string", "description": "'true' to deduct available wallet funds, 'false' for full Razorpay link"}
                },
                "required": ["customer_name", "items"]
            }
        }
    }
]
