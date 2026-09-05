from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class OrderStatus(str, Enum):
    CART_CREATED = "CART_CREATED"
    PRICE_CONFIRMED = "PRICE_CONFIRMED"
    CUSTOMER_APPROVED = "CUSTOMER_APPROVED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class CartItemInput(BaseModel):
    product_name_or_keyword: str
    quantity: int = Field(default=1, ge=1, le=10)

class PricingLineItem(BaseModel):
    product_id: int
    name: str
    unit_price: float
    quantity: int
    line_total: float
    flavour: Optional[str] = "Standard"

class CartQuote(BaseModel):
    items: List[PricingLineItem]
    subtotal: float
    combo_discount: float = 0.0
    coupon_code: Optional[str] = None
    coupon_discount: float = 0.0
    total_discount: float = 0.0
    free_gifts: List[str] = []
    final_total: float
    is_valid: bool = True
    error_message: Optional[str] = None

class OrderAuditTrail(BaseModel):
    agent_id: str = "AGENT-MB-ROHAN-01"
    kya_verified: bool = True
    channel: str = "VOICE_AI_SARVAM_GROQ"
    spend_rails_passed: bool = True
    state_history: List[Dict[str, Any]] = []
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: f"MB-ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}")
    customer_name: str
    delivery_address: Optional[str] = ""
    payment_method: Optional[str] = "ONLINE"
    items: List[PricingLineItem]
    quote: CartQuote
    status: OrderStatus = OrderStatus.CART_CREATED
    wallet_paid: float = 0.0
    razorpay_paid: float = 0.0
    razorpay_pending: float = 0.0
    razorpay_payment_link: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    audit: OrderAuditTrail = Field(default_factory=OrderAuditTrail)
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
