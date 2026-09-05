import os
import json
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

WALLET_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gym_store.db")

class AgentWallet(BaseModel):
    wallet_id: str
    customer_name: str
    balance: float
    currency: str = "INR"
    daily_spend_limit: float = 15000.0
    daily_spent_today: float = 0.0
    kya_verified: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def init_wallet_tables():
    conn = sqlite3.connect(WALLET_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wallets (
        wallet_id TEXT PRIMARY KEY,
        customer_name TEXT UNIQUE NOT NULL,
        balance REAL NOT NULL,
        currency TEXT DEFAULT 'INR',
        daily_spend_limit REAL DEFAULT 15000.0,
        daily_spent_today REAL DEFAULT 0.0,
        kya_verified INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wallet_transactions (
        tx_id TEXT PRIMARY KEY,
        wallet_id TEXT NOT NULL,
        amount REAL NOT NULL,
        tx_type TEXT NOT NULL,
        reference_id TEXT,
        description TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)
    cursor.execute("SELECT wallet_id FROM wallets WHERE customer_name = 'Kartik'")
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO wallets (wallet_id, customer_name, balance, currency, daily_spend_limit, daily_spent_today, kya_verified, created_at)
        VALUES ('WALLET-MB-KARTIK-01', 'Kartik', 10000.0, 'INR', 15000.0, 0.0, 1, ?)
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    conn.commit()
    conn.close()

init_wallet_tables()

def get_or_create_wallet(customer_name: str = "Kartik") -> AgentWallet:
    conn = sqlite3.connect(WALLET_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT wallet_id, customer_name, balance, currency, daily_spend_limit, daily_spent_today, kya_verified, created_at FROM wallets WHERE customer_name LIKE ?", (f"%{customer_name}%",))
    row = cursor.fetchone()
    
    if not row:
        new_wallet_id = f"WALLET-MB-{uuid.uuid4().hex[:6].upper()}"
        initial_balance = 10000.0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO wallets (wallet_id, customer_name, balance, currency, daily_spend_limit, daily_spent_today, kya_verified, created_at)
        VALUES (?, ?, ?, 'INR', 15000.0, 0.0, 1, ?)
        """, (new_wallet_id, customer_name, initial_balance, now_str))
        conn.commit()
        wallet = AgentWallet(wallet_id=new_wallet_id, customer_name=customer_name, balance=initial_balance, created_at=now_str)
    else:
        wallet = AgentWallet(wallet_id=row[0], customer_name=row[1], balance=row[2], currency=row[3], daily_spend_limit=row[4], daily_spent_today=row[5], kya_verified=bool(row[6]), created_at=row[7])
    conn.close()
    return wallet

def check_wallet_balance(customer_name: str = "Kartik") -> str:
    """Check wallet balance and spend rails."""
    wallet = get_or_create_wallet(customer_name)
    available_limit = wallet.daily_spend_limit - wallet.daily_spent_today
    return json.dumps({
        "status": "active",
        "wallet_id": wallet.wallet_id,
        "balance": f"₹{wallet.balance:,.2f}",
        "daily_limit_left": f"₹{available_limit:,.2f}"
    }, ensure_ascii=False)

def pay_from_wallet(customer_name: str, amount: float, invoice_id: str, item_name: str) -> str:
    """Pay from customer wallet with spend rail check."""
    wallet = get_or_create_wallet(customer_name)
    if amount > 15000.0:
        return json.dumps({"status": "failed", "reason": "Spend limit exceeded (Max ₹15,000)"})
    if (wallet.daily_spent_today + amount) > wallet.daily_spend_limit:
        return json.dumps({"status": "failed", "reason": "Daily limit exceeded"})
    if wallet.balance < amount:
        return json.dumps({"status": "insufficient_balance", "balance": f"₹{wallet.balance:,.2f}", "amount_needed": f"₹{amount:,.2f}"})
        
    new_balance = round(wallet.balance - amount, 2)
    new_spent = round(wallet.daily_spent_today + amount, 2)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tx_id = f"TXN-{uuid.uuid4().hex[:6].upper()}"
    
    conn = sqlite3.connect(WALLET_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE wallets SET balance = ?, daily_spent_today = ? WHERE wallet_id = ?", (new_balance, new_spent, wallet.wallet_id))
    cursor.execute("INSERT INTO wallet_transactions VALUES (?, ?, ?, 'DEBIT_PURCHASE', ?, ?, ?)", (tx_id, wallet.wallet_id, amount, invoice_id, item_name, now_str))
    conn.commit()
    conn.close()
    
    print(f"\n💳 [WALLET DEBIT] Paid ₹{amount:,.2f} | Remaining: ₹{new_balance:,.2f} | TxID: {tx_id}")
    return json.dumps({
        "status": "success",
        "tx_id": tx_id,
        "paid": f"₹{amount:,.2f}",
        "remaining_balance": f"₹{new_balance:,.2f}",
        "invoice_id": invoice_id
    }, ensure_ascii=False)

def topup_wallet_balance(customer_name: str = "Kartik", amount: float = 1000.0) -> str:
    """Add money / top up customer's Programmable Wallet."""
    wallet = get_or_create_wallet(customer_name)
    new_balance = round(wallet.balance + amount, 2)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tx_id = f"TXN-TOPUP-{uuid.uuid4().hex[:6].upper()}"

    conn = sqlite3.connect(WALLET_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE wallets SET balance = ? WHERE wallet_id = ?", (new_balance, wallet.wallet_id))
    cursor.execute("INSERT INTO wallet_transactions VALUES (?, ?, ?, 'CREDIT_TOPUP', 'TOPUP', 'Wallet Top-Up', ?)", (tx_id, wallet.wallet_id, amount, now_str))
    conn.commit()
    conn.close()

    print(f"\n💳 [WALLET TOPUP] Added ₹{amount:,.2f} | New Balance: ₹{new_balance:,.2f} | TxID: {tx_id}")
    return json.dumps({
        "status": "success",
        "added_amount": f"₹{amount:,.2f}",
        "new_balance": f"₹{new_balance:,.2f}"
    }, ensure_ascii=False)

WALLET_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_wallet_balance",
            "description": "Check customer's available Programmable Wallet balance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"}
                },
                "required": ["customer_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "topup_wallet_balance",
            "description": "Add money / top up customer's Programmable Wallet balance when requested.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "amount": {"type": "number", "description": "Amount in INR to add to wallet"}
                },
                "required": ["customer_name", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pay_from_wallet",
            "description": "Pay directly from customer's Programmable Wallet when authorized.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "amount": {"type": "number"},
                    "invoice_id": {"type": "string"},
                    "item_name": {"type": "string"}
                },
                "required": ["customer_name", "amount", "invoice_id", "item_name"]
            }
        }
    }
]
