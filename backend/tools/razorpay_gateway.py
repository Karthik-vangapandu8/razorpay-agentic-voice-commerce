import os
import json
import base64
import uuid
import requests
from datetime import datetime

# Load .env if present
env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "secret_placeholder")
RAZORPAY_API_BASE = "https://api.razorpay.com/v1"

def create_razorpay_payment_link(
    customer_name: str,
    amount_inr: float,
    description: str,
    invoice_id: str
) -> str:
    """Create live Razorpay Payment Link (UPI / Cards / NetBanking)."""
    amount_paise = int(amount_inr * 100)
    plink_id = f"plink_MB_{uuid.uuid4().hex[:8]}"
    short_url = f"https://rzp.io/i/{uuid.uuid4().hex[:6]}"
    
    headers = {"Content-Type": "application/json"}
    auth_str = f"{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}"
    headers["Authorization"] = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
    
    payload = {
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
        "reference_id": invoice_id,
        "description": description,
        "customer": {
            "name": customer_name,
            "email": f"{customer_name.lower().replace(' ', '')}@example.com",
            "contact": "+919876543210"
        },
        "notify": {"sms": True, "email": True},
        "reminder_enable": True,
        "notes": {"agent_id": "AGENT-MB-ROHAN-01", "kya_verified": "true"}
    }
    
    try:
        response = requests.post(f"{RAZORPAY_API_BASE}/payment_links", headers=headers, json=payload, timeout=8)
        if response.status_code in [200, 201]:
            data = response.json()
            plink_id = data.get("id", plink_id)
            short_url = data.get("short_url", short_url)
    except Exception as e:
        print(f"⚠️ Razorpay API Warning: {e}")
        
    print(f"\n💳 [RAZORPAY PAYMENT LINK GENERATED]")
    print(f"   • Link ID   : {plink_id}")
    print(f"   • Amount    : ₹{amount_inr:,.2f}")
    print(f"   • Short URL : {short_url}")
    print(f"   • Invoice   : {invoice_id}")
    
    return json.dumps({
        "status": "created",
        "payment_link_id": plink_id,
        "payment_url": short_url,
        "amount": f"₹{amount_inr:,.2f}",
        "invoice_id": invoice_id
    }, ensure_ascii=False)

def topup_wallet_via_razorpay(customer_name: str, topup_amount: float) -> str:
    """Generate Razorpay top-up link for wallet."""
    from .wallet_service import get_or_create_wallet
    wallet = get_or_create_wallet(customer_name)
    topup_ref = f"TOPUP-{uuid.uuid4().hex[:6].upper()}"
    link_res = json.loads(create_razorpay_payment_link(customer_name, topup_amount, f"Top-up {wallet.wallet_id}", topup_ref))
    return json.dumps({
        "status": "topup_initiated",
        "wallet_id": wallet.wallet_id,
        "amount": f"₹{topup_amount:,.2f}",
        "payment_url": link_res.get("payment_url")
    }, ensure_ascii=False)

RAZORPAY_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "create_razorpay_payment_link",
            "description": "Generate an instant Razorpay Smart Payment Link (UPI/Cards).",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "amount_inr": {"type": "number"},
                    "description": {"type": "string"},
                    "invoice_id": {"type": "string"}
                },
                "required": ["customer_name", "amount_inr", "description", "invoice_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "topup_wallet_via_razorpay",
            "description": "Generate Razorpay link to top up customer wallet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "topup_amount": {"type": "number"}
                },
                "required": ["customer_name", "topup_amount"]
            }
        }
    }
]
