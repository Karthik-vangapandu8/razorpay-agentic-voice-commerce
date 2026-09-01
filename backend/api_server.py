import os
import sys
import json
import base64
import time
import re
import sqlite3
import uuid
import requests
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load .env
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from prompt_manager import prompt_manager
from tools import ALL_TOOLS, TOOL_FUNCTION_MAP
from commerce.engine import calculate_deterministic_quote, execute_order_checkout, DB_PATH
from commerce.models import OrderStatus
from commerce.webhook import handle_razorpay_webhook
from tools.wallet_service import get_or_create_wallet, WALLET_DB_PATH

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "qwen/qwen3.6-27b"

# Product Image Mapping (High-res MuscleBlaze supplement images)
PRODUCT_IMAGES = {
    1: "https://images.unsplash.com/photo-1579722821273-0f6c7d44362f?auto=format&fit=crop&w=600&q=80", # Biozyme Whey
    2: "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?auto=format&fit=crop&w=600&q=80", # Raw Whey Isolate
    3: "https://images.unsplash.com/photo-1546483875-ad9014c88eba?auto=format&fit=crop&w=600&q=80", # Creatine
    4: "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=600&q=80", # WrathX Preworkout
    5: "https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?auto=format&fit=crop&w=600&q=80", # Super Gainer
    6: "https://images.unsplash.com/photo-1527661591475-527312dd65f5?auto=format&fit=crop&w=600&q=80", # Peanut Butter
    7: "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80", # Fish Oil
    8: "https://images.unsplash.com/photo-1550572017-edd951aa8f72?auto=format&fit=crop&w=600&q=80"  # Multivitamin
}

app = FastAPI(title="MuscleBlaze Agentic Voice Commerce API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session dialogue history
SESSION_HISTORIES: Dict[str, List[Dict[str, Any]]] = {}

def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    if session_id not in SESSION_HISTORIES:
        SESSION_HISTORIES[session_id] = []
    return SESSION_HISTORIES[session_id]

def prune_messages(messages: List[Dict[str, Any]], max_turns: int = 4) -> List[Dict[str, Any]]:
    if len(messages) <= (1 + max_turns * 2):
        return messages
    system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
    recent = messages[-(max_turns * 2):]
    return [system_msg] + recent if system_msg else recent

def transcribe_audio_sarvam(audio_bytes: bytes) -> Dict[str, str]:
    """Transcribe audio with Sarvam AI saaras:v3."""
    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"api-subscription-key": SARVAM_API_KEY}
    files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
    data = {"model": "saaras:v3", "language_code": "unknown"}
    
    try:
        res = requests.post(url, headers=headers, files=files, data=data, timeout=10)
        if res.status_code in [200, 201]:
            d = res.json()
            return {
                "transcript": d.get("transcript", "").strip(),
                "language_code": d.get("language_code", "hi-IN")
            }
        else:
            print(f"⚠️ Sarvam STT Error ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"⚠️ Sarvam STT Exception: {e}")
    return {"transcript": "", "language_code": "hi-IN"}

def synthesize_speech_sarvam(text: str, lang_code: str) -> str:
    """Synthesize speech with Sarvam AI bulbul:v3 and return base64 WAV."""
    speaker_map = {
        "hi-IN": "shubh",
        "te-IN": "gokul",
        "en-IN": "rohan",
        "ta-IN": "vijay"
    }
    speaker = speaker_map.get(lang_code, "shubh")
    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": [text[:500]],
        "target_language_code": lang_code,
        "speaker": speaker,
        "model": "bulbul:v3"
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=12)
        if res.status_code in [200, 201]:
            data = res.json()
            audios = data.get("audios", [])
            if audios:
                return audios[0] # base64 WAV
    except Exception as e:
        print(f"⚠️ Sarvam TTS Exception: {e}")
    return ""

def clean_speech_text(text: str) -> str:
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'<tool_call>.*?</tool_call>', '', cleaned, flags=re.DOTALL)
    cleaned = cleaned.replace("*", "").replace("`", "").replace("#", "").strip()
    return cleaned

# =========================================================================
# API ENDPOINTS
# =========================================================================

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "MuscleBlaze Agentic Voice Commerce API"}

@app.get("/api/catalog")
def get_catalog():
    """Fetch all products with stock and images from SQLite store."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, category, flavour, price_inr, stock_count, rating, description FROM products")
    rows = cursor.fetchall()
    conn.close()
    
    catalog = []
    for r in rows:
        pid = r[0]
        catalog.append({
            "id": pid,
            "name": r[1],
            "category": r[2],
            "flavour": r[3],
            "price_inr": r[4],
            "stock_count": r[5],
            "rating": r[6],
            "description": r[7],
            "image_url": PRODUCT_IMAGES.get(pid, "https://images.unsplash.com/photo-1579722821273-0f6c7d44362f?auto=format&fit=crop&w=600&q=80"),
            "discount_price": round(r[4] * 0.9, 2) # FIT10 sample discounted rate
        })
    return {"catalog": catalog, "total": len(catalog)}

@app.get("/api/wallet")
def get_wallet_info(customer_name: str = "Kartik"):
    """Fetch live customer programmable wallet balance & ledger."""
    wallet = get_or_create_wallet(customer_name)
    available_limit = wallet.daily_spend_limit - wallet.daily_spent_today
    
    conn = sqlite3.connect(WALLET_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT tx_id, amount, tx_type, reference_id, description, timestamp FROM wallet_transactions WHERE wallet_id = ? ORDER BY timestamp DESC LIMIT 10", (wallet.wallet_id,))
    tx_rows = cursor.fetchall()
    conn.close()
    
    txs = []
    for t in tx_rows:
        txs.append({
            "tx_id": t[0],
            "amount": t[1],
            "tx_type": t[2],
            "reference_id": t[3],
            "description": t[4],
            "timestamp": t[5]
        })
        
    return {
        "wallet_id": wallet.wallet_id,
        "customer_name": wallet.customer_name,
        "balance": wallet.balance,
        "currency": wallet.currency,
        "daily_spend_limit": wallet.daily_spend_limit,
        "remaining_daily_limit": available_limit,
        "kya_verified": wallet.kya_verified,
        "transactions": txs
    }

@app.get("/api/greeting")
def get_initial_greeting(lang_code: str = "hi-IN"):
    """Get Rohan's initial proactive greeting text & synthesized audio."""
    greeting_text = "Namaste and Welcome to MuscleBlaze! Main hoon Rohan, aapka sales and fitness advisor. Aapka naam kya hai aur aaj aapka main fitness goal kya hai?"
    if "te" in lang_code:
        greeting_text = "నమస్తే! మస్కిల్‌బ్లేజ్ కి స్వాగతం! నేను రోహన్, మీ ఫిట్‌నెస్ అడ్వైజర్. మీ పేరు మరియు మీ గోల్ ఏంటో చెప్పండి!"
    elif "en" in lang_code:
        greeting_text = "Hello and welcome to MuscleBlaze! I'm Rohan, your personal fitness and supplement advisor. What is your name and fitness goal today?"
        
    audio_base64 = synthesize_speech_sarvam(greeting_text, lang_code)
    return {
        "greeting_text": greeting_text,
        "language_code": lang_code,
        "audio_base64": audio_base64,
        "speaker": "Rohan (AI Sales Advisor)"
    }

class TextChatRequest(BaseModel):
    session_id: str = "default_session"
    customer_name: str = "Kartik"
    text: str
    language_code: Optional[str] = "hi-IN"

@app.post("/api/chat")
def handle_text_chat(req: TextChatRequest):
    """Handle text dialogue turn with tool execution and voice generation."""
    return process_turn(req.session_id, req.customer_name, req.text, req.language_code)

@app.post("/api/voice-chat")
async def handle_voice_chat(
    file: UploadFile = File(...),
    session_id: str = Form("default_session"),
    customer_name: str = Form("Kartik")
):
    """Handle audio dialogue turn (WebM/WAV): Transcribe ➔ Tool Execution ➔ TTS."""
    audio_bytes = await file.read()
    stt_res = transcribe_audio_sarvam(audio_bytes)
    transcript = stt_res.get("transcript", "")
    lang_code = stt_res.get("language_code", "hi-IN")
    
    if not transcript:
        return {
            "transcript": "",
            "language_code": lang_code,
            "assistant_text": "Aapki aawaz theek se sunai nahi di, kripya dobara boliye.",
            "audio_base64": synthesize_speech_sarvam("Aapki aawaz theek se sunai nahi di, kripya dobara boliye.", lang_code),
            "highlighted_products": []
        }
        
    res = process_turn(session_id, customer_name, transcript, lang_code)
    res["transcript"] = transcript
    return res

def groq_post_with_retry(payload: dict, max_retries: int = 3) -> dict:
    """Send requests to Groq with automatic 429 exponential backoff retry."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                return res.json()
            elif res.status_code == 429:
                err_data = res.json().get("error", {})
                msg = err_data.get("message", "")
                wait_match = re.search(r'try again in ([\d\.]+)s', msg)
                wait_sec = float(wait_match.group(1)) + 0.5 if wait_match else (2 ** attempt)
                print(f"⏳ [RATE LIMIT 429] Auto-waiting {wait_sec:.1f}s before retry (Attempt {attempt}/{max_retries})...")
                time.sleep(wait_sec)
            else:
                print(f"⚠️ Groq API Error ({res.status_code}): {res.text}")
                time.sleep(1)
        except Exception as e:
            print(f"⚠️ Groq Connection Error: {e}")
            time.sleep(1)
    return {}

def process_turn(session_id: str, customer_name: str, user_text: str, lang_code: str) -> Dict[str, Any]:
    """Core dialogue processing function."""
    prompt_manager.set_customer_info(name=customer_name)
    history = get_session_history(session_id)
    
    # Initialize system prompt if fresh session
    if not history:
        system_prompt = prompt_manager.render_system_prompt()
        history.append({"role": "system", "content": system_prompt})
        
    history.append({"role": "user", "content": user_text})
    pruned = prune_messages(history, max_turns=4)
    
    payload = {
        "model": GROQ_MODEL,
        "messages": pruned,
        "tools": ALL_TOOLS,
        "tool_choice": "auto",
        "temperature": 0.3
    }
    
    highlighted_products = []
    active_quote = None
    order_result = None
    assistant_reply = ""
    
    data = groq_post_with_retry(payload)
    if data and "choices" in data:
        choice = data["choices"][0]
        msg = choice.get("message", {})
        tool_calls = msg.get("tool_calls", [])
        content = msg.get("content", "") or ""
        
        if tool_calls:
            pruned.append(msg)
            for call in tool_calls:
                fn_name = call.get("function", {}).get("name")
                raw_args = call.get("function", {}).get("arguments", "{}")
                fn_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                
                if fn_name in TOOL_FUNCTION_MAP:
                    tool_output = TOOL_FUNCTION_MAP[fn_name](**fn_args)
                    
                    if fn_name == "search_gym_products":
                        try:
                            p_data = json.loads(tool_output)
                            if isinstance(p_data, list):
                                highlighted_products.extend(p_data)
                        except Exception:
                            pass
                    elif fn_name == "get_cart_pricing_quote":
                        try:
                            active_quote = json.loads(tool_output)
                        except Exception:
                            pass
                    elif fn_name == "process_order_checkout":
                        try:
                            order_result = json.loads(tool_output)
                        except Exception:
                            pass
                            
                    pruned.append({
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "content": tool_output
                    })
                    
            payload2 = {
                "model": GROQ_MODEL,
                "messages": pruned,
                "temperature": 0.3
            }
            data2 = groq_post_with_retry(payload2)
            if data2 and "choices" in data2:
                assistant_reply = data2["choices"][0]["message"].get("content", "")
        else:
            assistant_reply = content
            
    if not assistant_reply:
        assistant_reply = "Namaste Kartik ji! Main aapka order confirm karne ke liye details check kar raha hoon."
        
    cleaned_reply = clean_speech_text(assistant_reply)
    history.append({"role": "assistant", "content": cleaned_reply})
    
    # Synthesize audio
    audio_b64 = synthesize_speech_sarvam(cleaned_reply, lang_code)
    
    return {
        "transcript": user_text,
        "language_code": lang_code,
        "assistant_text": cleaned_reply,
        "audio_base64": audio_b64,
        "highlighted_products": highlighted_products,
        "active_quote": active_quote,
        "order_result": order_result
    }

@app.post("/api/checkout")
def direct_checkout(
    customer_name: str = "Kartik",
    items: List[Dict[str, Any]] = [],
    coupon_code: str = "FIT10",
    pay_via_wallet: bool = True
):
    """Direct API checkout invocation."""
    return execute_order_checkout(customer_name, items, coupon_code, pay_via_wallet)

@app.post("/api/webhook/razorpay")
async def razorpay_webhook_endpoint(request: Request):
    """Live Razorpay webhook listener."""
    payload = await request.json()
    event = payload.get("event", "")
    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = payment.get("id", f"pay_{uuid.uuid4().hex[:8]}")
    order_id = payment.get("notes", {}).get("invoice_id") or payload.get("payload", {}).get("payment_link", {}).get("entity", {}).get("reference_id")
    amount_paid = float(payment.get("amount", 0)) / 100.0
    
    if not order_id:
        return {"status": "ignored", "reason": "No order_id in notes"}
        
    return handle_razorpay_webhook(event, payment_id, order_id, amount_paid)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
