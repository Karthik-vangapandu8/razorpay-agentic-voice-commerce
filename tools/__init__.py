"""
Centralized Tools Package
Deterministic Commerce Architecture:
- DB Tools: search_gym_products
- Commerce Intent Tools: get_cart_pricing_quote, process_order_checkout
- Wallet Tools: check_wallet_balance
"""

from .db_tools import search_gym_products, DB_TOOL_SCHEMA
from .wallet_service import check_wallet_balance, WALLET_TOOL_SCHEMAS
from .commerce_tools import get_cart_pricing_quote, process_order_checkout, COMMERCE_TOOL_SCHEMAS

# Complete list of tool schemas for LLM
ALL_TOOLS = [
    DB_TOOL_SCHEMA,
    WALLET_TOOL_SCHEMAS[0], # check_wallet_balance only
    *COMMERCE_TOOL_SCHEMAS
]

# Mapping tool names to Python callable functions
TOOL_FUNCTION_MAP = {
    "search_gym_products": search_gym_products,
    "check_wallet_balance": check_wallet_balance,
    "get_cart_pricing_quote": get_cart_pricing_quote,
    "process_order_checkout": process_order_checkout
}

__all__ = [
    "ALL_TOOLS",
    "TOOL_FUNCTION_MAP",
    "search_gym_products",
    "check_wallet_balance",
    "get_cart_pricing_quote",
    "process_order_checkout"
]
