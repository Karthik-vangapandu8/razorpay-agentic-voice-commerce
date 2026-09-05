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

def reload_env():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "=" in line:
                    k, v = line.strip().split("=", 1)
                    os.environ[k.strip()] = v.strip()

reload_env()

from prompt_manager import prompt_manager
from tools import ALL_TOOLS, TOOL_FUNCTION_MAP
from commerce.engine import calculate_deterministic_quote, execute_order_checkout, DB_PATH
from commerce.models import OrderStatus
from commerce.webhook import handle_razorpay_webhook
from tools.wallet_service import get_or_create_wallet, WALLET_DB_PATH

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "qwen/qwen3.8-27b"

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

# In-memory session dialogue history & customer names
SESSION_HISTORIES: Dict[str, List[Dict[str, Any]]] = {}
SESSION_NAMES: Dict[str, str] = {}

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

def transcribe_audio_sarvam(audio_bytes: bytes, filename: str = "audio.webm", content_type: str = "audio/webm") -> Dict[str, str]:
    """Transcribe audio with Sarvam AI saaras:v3."""
    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"api-subscription-key": SARVAM_API_KEY}
    
    # Infer mime and filename extension
    ext = "webm"
    if "wav" in filename.lower() or "wav" in content_type.lower():
        ext = "wav"
        mime = "audio/wav"
    elif "mp4" in filename.lower() or "m4a" in filename.lower():
        ext = "mp4"
        mime = "audio/mp4"
    else:
        ext = "webm"
        mime = "audio/webm"

    files = {"file": (f"voice_input.{ext}", audio_bytes, mime)}
    data = {"model": "saaras:v3", "language_code": "unknown"}
    
    try:
        print(f"🎙️ Sending {len(audio_bytes)} bytes audio ({mime}) to Sarvam STT...")
        res = requests.post(url, headers=headers, files=files, data=data, timeout=12)
        if res.status_code in [200, 201]:
            d = res.json()
            t = d.get("transcript", "").strip()
            l = d.get("language_code", "hi-IN")
            print(f"✅ Sarvam STT Transcript: '{t}' (Lang: {l})")
            return {
                "transcript": t,
                "language_code": l
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
    if not text:
        return ""

    # Step 0: Remove raw internal Order IDs, transaction IDs, invoice IDs, wallet IDs & labels
    text = re.sub(r'(?:order|invoice|transaction|wallet)\s*id[:\s]*[A-Z0-9_-]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(MB-ORD-[A-Z0-9-]+|ORD-MB-[A-Z0-9-]+|TXN-[A-Z0-9-]+|INV-[A-Z0-9-]+|WALLET-[A-Z0-9-]+)\b', '', text, flags=re.IGNORECASE)

    # Step 1: Remove full <think>...</think> and <tool_call>...</tool_call> blocks FIRST
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)

    # Step 2: Handle unclosed <think> tag
    if "<think>" in text:
        parts = text.split("<think>")
        prefix = parts[0].strip()
        body = parts[-1].strip()
        text = prefix if prefix else body

    # Step 3: Find the LAST valid quoted spoken text block in double quotes
    all_quotes = re.findall(r'"([^"\n\r]{20,})"', text)
    if all_quotes:
        for q in reversed(all_quotes):
            q_strip = q.strip()
            q_lower = q_strip.lower()
            if not any(w in q_lower for w in [
                "the search", "refining for", "language:", "tone:", "draft",
                "constraints", "i need to", "respectful", "product:", "features:",
                "price:", "discount:", "call to action:", "let's check", "output only 1 to 2",
                "spoken audio constraints", "short, crisp", "recommend only", "confidently pitch",
                "quote the exact", "ask the customer if"
            ]):
                return q_strip.replace("*", "").replace("`", "").replace("#", "").strip()

    # Step 4: Check for explicit refined/condensed/final markers
    condensed_markers = [
        "Refining for spoken audio constraints", "Refining for length:", "Condensed:",
        "Condensed Response:", "Refined Response:", "Shortened Response:", "Refined:",
        "Shortened:", "Final Output:", "Final Spoken Text:", "Spoken Response:",
        "Spoken Text:", "Final Polish:", "Final Draft:", "Telugu Response:", "Tamil Response:",
        "Hindi Response:", "English Response:", "Final Answer:"
    ]
    for marker in condensed_markers:
        if marker in text:
            after_marker = text.split(marker)[-1].strip()
            if ":" in after_marker:
                after_colon = after_marker.split(":", 1)[1].strip()
                if len(after_colon) >= 15:
                    after_marker = after_colon
            if after_marker:
                text = after_marker
                break

    # Step 5: Trim off trailing self-refinement / self-assessment notes
    trim_markers = [
        "Let's check the constraints", "The draft looks good", "This looks good",
        "It covers", "This meets all constraints", "Final check", "Check constraints:",
        "My draft is", "Let's condense", "Let's refine", "I should address", "The draft is 2 sentences"
    ]
    for trim_m in trim_markers:
        if trim_m in text:
            before_trim = text.split(trim_m)[0].strip()
            if len(before_trim) >= 15:
                text = before_trim

    # Step 6: Line by line filtering for reasoning / planning prefixes
    lines = text.split("\n")
    cleaned_lines = []
    
    bad_prefixes = (
        "the search returned", "i need to", "let's check", "the draft looks good",
        "the draft is", "refining for", "draft in", "draft:", "mental draft",
        "language:", "tone:", "response plan:", "constraints:", "thinking process:",
        "reasoning:", "analysis:", "user switched", "user is speaking", "user introduced",
        "customer introduced", "i will respond", "final check", "switching language",
        "refining for length", "formulate response", "check constraints:", "wait,",
        "i should", "let's refine", "mental sandbox", "language switching", "the user wants",
        "the search results", "since the goal", "given the strict", "i will pitch",
        "i will recommend", "actually,", "looking at the", "my draft is", "let's condense",
        "this looks good", "it covers", "recommend only", "confidently pitch", "quote the exact",
        "ask the customer if"
    )

    for l in lines:
        l_trim = l.strip()
        l_lower = l_trim.lower()
        if not l_trim:
            continue
        
        if l_lower.startswith(bad_prefixes):
            if (l_lower.startswith("draft in") or l_lower.startswith("draft:")) and ":" in l_trim:
                content_after = l_trim.split(":", 1)[1].strip()
                if content_after and not content_after.lower().startswith(bad_prefixes):
                    cleaned_lines.append(content_after)
            continue
        
        if ":" in l_trim:
            key = l_trim.split(":", 1)[0].strip().lower()
            if key in ["language", "tone", "constraints", "stage", "customer name", "fitness goal", "response plan"]:
                continue
                
        cleaned_lines.append(l_trim)

    text = " ".join(cleaned_lines)
    
    # Step 7: Strip quotes and markdown
    cleaned = text.replace('"', '').replace("*", "").replace("`", "").replace("#", "").strip()
    
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
    """Get Sauda AI's initial proactive greeting text & synthesized audio."""
    greeting_text = "Welcome to Sauda AI. A merchant can upload their products and product knowledge, and Sauda turns that information into a conversational AI sales executive."
    if "hi" in lang_code:
        greeting_text = "Sauda AI में आपका स्वागत है। कोई भी मर्चेंट अपने प्रोडक्ट्स और नॉलेज अपलोड कर सकता है, और सौदा AI उसे एक कन्वर्सेशनल AI सेल्स एग्जीक्यूटिव में बदल देता है।"
    elif "te" in lang_code:
        greeting_text = "Sauda AI కి స్వాగతం. ఏ మర్చంట్ అయినా తమ ప్రొడక్ట్స్ మరియు నాలెడ్జ్ అప్‌లోడ్ చేయవచ్చు, మరియు सौदा AI దానిని కాన్వర్సేషనల్ AI సేల్స్ ఎగ్జిక్యూటివ్‌గా మారుస్తుంది."
        
    audio_base64 = synthesize_speech_sarvam(greeting_text, lang_code)
    return {
        "greeting_text": greeting_text,
        "language_code": lang_code,
        "audio_base64": audio_base64,
        "speaker": "Rohan (Sauda AI Sales Executive)"
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
    stt_res = transcribe_audio_sarvam(
        audio_bytes,
        filename=file.filename or "voice_input.webm",
        content_type=file.content_type or "audio/webm"
    )
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

_key_counter = 0

def groq_post_with_retry(payload: dict, max_retries: int = 3) -> dict:
    """Send requests to Groq with round-robin key rotation & instant fallback on 429 rate limits."""
    global _key_counter
    reload_env()
    groq_keys = [k for k in [os.getenv("GROQ_API_KEY", ""), os.getenv("GROQ_API_KEY_2", "")] if k]
    payload["max_tokens"] = payload.get("max_tokens", 2500)

    num_keys = len(groq_keys) if groq_keys else 1
    for attempt in range(max_retries * num_keys):
        current_key = groq_keys[_key_counter % num_keys] if groq_keys else os.getenv("GROQ_API_KEY", "")
        _key_counter += 1
        headers = {
            "Authorization": f"Bearer {current_key}",
            "Content-Type": "application/json"
        }
        try:
            res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                res_json = res.json()
                # Check if choice content was truncated due to length or empty
                if res_json and "choices" in res_json and res_json["choices"]:
                    choice = res_json["choices"][0]
                    msg_content = choice.get("message", {}).get("content", "") or ""
                    finish_reason = choice.get("finish_reason")
                    # If empty content because of length limits, retry with bumped tokens
                    if not msg_content and finish_reason == "length" and attempt < (max_retries * num_keys - 1):
                        print("⚠️ [EMPTY CONTENT / LENGTH LIMIT] Groq response was truncated. Retrying request...")
                        payload["max_tokens"] = 3000
                        time.sleep(0.3)
                        continue
                return res_json
            elif res.status_code == 429:
                print(f"⏳ [429 RATE LIMIT] Key ending in ...{current_key[-6:]} rate limited. Waiting 1.5s and rotating to next Groq API key...")
                time.sleep(1.5)
                continue
            else:
                print(f"⚠️ Groq API Error ({res.status_code}): {res.text}")
                time.sleep(0.5)
        except Exception as e:
            print(f"⚠️ Groq Connection Error: {e}")
            time.sleep(0.5)
    return {}

def process_turn(session_id: str, customer_name: str, user_text: str, lang_code: str) -> Dict[str, Any]:
    """Core dialogue processing function."""
    history = get_session_history(session_id)
    
    # Check session memory for previously introduced name
    if session_id in SESSION_NAMES:
        customer_name = SESSION_NAMES[session_id]
        
    # Dynamic Customer Name extraction if introduced in speech
    name_match = re.search(r'(?:mera naam|my name is|main|i am)\s+([A-Za-z\u0900-\u097F]+(?:\s+[A-Za-z\u0900-\u097F]+)?)', user_text, re.IGNORECASE)
    if name_match:
        extracted = name_match.group(1).strip()
        if len(extracted) >= 3 and not any(w in extracted.lower() for w in ["whey", "protein", "creatine", "order", "shaker", "buy", "kya", "batao"]):
            customer_name = extracted
            SESSION_NAMES[session_id] = customer_name

    display_name = customer_name if customer_name and customer_name not in ["Kartik", "Guest Customer", "Guest"] else "Sir"
    prompt_manager.set_customer_info(name=display_name)
    prompt_manager.auto_detect_stage(user_text, turn=len(history))
    system_prompt = prompt_manager.render_system_prompt()
    
    # Refresh/initialize system prompt with updated stage instructions
    if not history:
        history.append({"role": "system", "content": system_prompt})
    else:
        history[0] = {"role": "system", "content": system_prompt}
        
    history.append({"role": "user", "content": user_text})
    pruned = prune_messages(history, max_turns=4)
    
    payload = {
        "model": GROQ_MODEL,
        "messages": pruned,
        "tools": ALL_TOOLS,
        "tool_choice": "auto",
        "temperature": 0.3,
        "max_tokens": 2500
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
                    print(f"🔧 Executing Tool: {fn_name} with args: {fn_args}")
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
                "temperature": 0.3,
                "max_tokens": 2500
            }
            data2 = groq_post_with_retry(payload2)
            if data2 and "choices" in data2:
                assistant_reply = data2["choices"][0]["message"].get("content", "")
        else:
            assistant_reply = content
            
    cleaned_reply = clean_speech_text(assistant_reply)
    
    # Auto-run product search if stage is recommendation but LLM did not invoke search_gym_products tool
    if not highlighted_products and prompt_manager.current_stage in ["discovery", "recommendation"]:
        try:
            search_query = user_text
            # Map common Hindi/transcribed product keywords
            if any(w in user_text.lower() for w in ["मिसेली", "ओट्स", "ब्रेकफास्ट", "oats", "breakfast", "muesli"]):
                search_query = "oats"
            elif any(w in user_text.lower() for w in ["प्रोटीन", "व्हे", "protein", "whey", "biozyme"]):
                search_query = "whey protein"
            elif any(w in user_text.lower() for w in ["क्रिएटिन", "creatine"]):
                search_query = "creatine"
            elif any(w in user_text.lower() for w in ["गेनर", "gainer"]):
                search_query = "mass gainer"

            tool_out = TOOL_FUNCTION_MAP["search_gym_products"](query=search_query)
            if tool_out and not tool_out.startswith("No matching"):
                p_data = json.loads(tool_out)
                if isinstance(p_data, list):
                    highlighted_products.extend(p_data)
        except Exception as e:
            print(f"Auto product search fallback error: {e}")

    # Automatic Checkout Execution Fallback if stage is checkout and LLM was rate-limited or didn't invoke tool
    if not order_result and prompt_manager.current_stage == "checkout":
        try:
            pay_method = "COD" if any(w in user_text.lower() for w in ["cod", "cash", "कैश", "सीओडी", "कैश ऑन डिलीवरी"]) else "ONLINE"
            addr = user_text if len(user_text) > 10 else "Visakhapatnam, Andhra Pradesh"
            # Determine order item from history or default to Biozyme Whey
            order_item_name = "MuscleBlaze Biozyme Performance Whey 2kg"
            for m in reversed(history):
                if m.get("role") == "user" and any(w in m.get("content", "").lower() for w in ["oats", "ओट्स", "creatine", "gainer"]):
                    if "oats" in m.get("content", "").lower() or "ओट्स" in m.get("content", "").lower():
                        order_item_name = "MuscleBlaze High Protein Oats Chocolate 1kg"
                    break
            
            tool_res = TOOL_FUNCTION_MAP["process_order_checkout"](
                items=[{"product_name": order_item_name, "quantity": 1}],
                customer_name=display_name,
                payment_method=pay_method,
                delivery_address=addr
            )
            if tool_res and isinstance(tool_res, str) and tool_res.startswith("{"):
                order_result = json.loads(tool_res)
                print(f"✅ [AUTO CHECKOUT FALLBACK EXECUTED] Order #{order_result.get('order_id')} created!")
        except Exception as e:
            print(f"Auto checkout fallback error: {e}")

    # Deterministic Tool-Aware Fallback if Qwen text output was empty or invalid
    if not cleaned_reply:
        if active_quote and active_quote.get("items"):
            item_names = ", ".join([i.get("name", "") for i in active_quote.get("items", [])])
            total = active_quote.get("final_total", 0)
            if "te" in lang_code:
                cleaned_reply = f"నమస్తే {display_name} గారు! మీ కార్ట్ అప్‌డేట్ చేసాము: {item_names}. FIT10 కూపన్‌తో ఫైనల్ టోటల్ ₹{total:,.2f}."
            else:
                cleaned_reply = f"Namaste {display_name} ji! Aapka cart update kar diya hai: {item_names}. Final Total FIT10 coupon discount ke saath ₹{total:,.2f} hai."
        elif order_result:
            status = order_result.get("order_status", "CONFIRMED")
            if "te" in lang_code:
                cleaned_reply = f"మీ ఆర్డర్ విజయవంతంగా {status} అయ్యింది! మస్కిల్‌బ్లేజ్‌లో కొనుగోలు చేసినందుకు ధన్యవాదాలు."
            else:
                cleaned_reply = f"Aapka order successfully {status} ho gaya hai! MuscleBlaze se khareedne ke liye dhanyawad."
        elif highlighted_products:
            p = highlighted_products[0]
            pname = p.get("name", "")
            price = p.get("price_inr", 0)
            disc_price = round(price * 0.9, 2) if price else price
            if "te" in lang_code:
                cleaned_reply = f"నమస్తే {display_name} గారు! మీ గోల్ కోసం {pname} అత్యుత్తమమైనది. 'FIT10' కూపన్‌తో ₹{disc_price:,.2f} కి లభిస్తుంది. దీన్ని లాక్ ఇన్‌ చేద్దామా?"
            elif "ta" in lang_code:
                cleaned_reply = f"Vanakkam {display_name} ji! Ungal goal kaga {pname} சிறந்த தேர்வு. 'FIT10' coupon oda price ₹{disc_price:,.2f}. Confirm pannalamama?"
            elif "en" in lang_code:
                cleaned_reply = f"Hello {display_name}, {pname} is the perfect recommendation. With the 'FIT10' coupon code, the price is ₹{disc_price:,.2f}. Shall we lock this in?"
            else:
                cleaned_reply = f"कार्तिक जी, आपके लिए {pname} सबसे बेस्ट ऑप्शन है। 'FIT10' कूपन के साथ इसका प्राइस ₹{disc_price:,.2f} होगा। क्या हम इसे अभी लॉक इन कर लें?"
        else:
            if "te" in lang_code:
                cleaned_reply = f"క్షమించండి {display_name} గారు, మీ స్వరం సరిగ్గా వినిపించలేదు. దయచేసి ఒకసారి మళ్ళీ చెప్పగలరా?"
            elif "ta" in lang_code:
                cleaned_reply = f"Mannikkavum {display_name} ji, ungal kural saraiya ketkala. Marubadiyum solla mudiyuma?"
            elif "en" in lang_code:
                cleaned_reply = f"Sorry {display_name}, I couldn't hear that clearly. Could you please repeat that?"
            else:
                cleaned_reply = f"माफ़ कीजिएगा {display_name} जी, आपकी आवाज़ थोड़ी साफ़ नहीं आ पाई। क्या आप एक बार फिर से बताएंगे?"

    history.append({"role": "assistant", "content": cleaned_reply})
    
    # Synthesize audio
    audio_b64 = synthesize_speech_sarvam(cleaned_reply, lang_code)
    
    return {
        "transcript": user_text,
        "language_code": lang_code,
        "stage": prompt_manager.current_stage,
        "assistant_text": cleaned_reply,
        "audio_base64": audio_b64,
        "highlighted_products": highlighted_products,
        "active_quote": active_quote,
        "order_result": order_result
    }

class CheckoutApiRequest(BaseModel):
    customer_name: Optional[str] = "Kartik"
    items: List[Dict[str, Any]] = []
    coupon_code: Optional[str] = "FIT10"
    pay_via_wallet: Optional[bool] = True
    payment_method: Optional[str] = "ONLINE"
    delivery_address: Optional[str] = ""

@app.post("/api/checkout")
def direct_checkout(req: CheckoutApiRequest):
    """Direct API checkout invocation."""
    return execute_order_checkout(req.customer_name, req.items, req.coupon_code, req.pay_via_wallet, req.payment_method, req.delivery_address)

class TopUpApiRequest(BaseModel):
    customer_name: Optional[str] = "Kartik"
    amount: float = 1000.0

@app.post("/api/wallet/topup")
def topup_wallet_endpoint(req: TopUpApiRequest):
    """API endpoint to add money / top up customer wallet balance."""
    from tools.wallet_service import topup_wallet_balance
    res = json.loads(topup_wallet_balance(req.customer_name, req.amount))
    return res

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

# =========================================================================
# MERCHANT DASHBOARD API ENDPOINTS
# =========================================================================

from tools.merchant_service import (
    get_store_config, save_store_config, StoreConfig,
    get_all_merchant_products, add_merchant_product, update_merchant_product, delete_merchant_product,
    get_merchant_orders_ledger
)

@app.get("/api/merchant/config")
def merchant_get_config():
    """Fetch merchant store & agent configuration."""
    return get_store_config().model_dump()

@app.post("/api/merchant/config")
def merchant_update_config(config: StoreConfig):
    """Update merchant store & agent configuration."""
    save_store_config(config)
    return {"status": "success", "config": config.model_dump()}

@app.get("/api/merchant/products")
def merchant_get_products():
    """Fetch complete product list for merchant CRUD view."""
    return {"products": get_all_merchant_products()}

class MerchantProductInput(BaseModel):
    name: str
    category: str = "Protein"
    flavour: str = "Standard"
    price_inr: float
    stock_count: int = 50
    rating: float = 4.8
    description: str = ""
    image_url: str = ""

@app.post("/api/merchant/products")
def merchant_add_product(req: MerchantProductInput):
    """Add a new product to SQLite catalog."""
    return add_merchant_product(
        name=req.name,
        category=req.category,
        flavour=req.flavour,
        price_inr=req.price_inr,
        stock_count=req.stock_count,
        rating=req.rating,
        description=req.description,
        image_url=req.image_url
    )

@app.put("/api/merchant/products/{product_id}")
def merchant_update_product(product_id: int, req: MerchantProductInput):
    """Update an existing product in SQLite catalog."""
    return update_merchant_product(
        product_id=product_id,
        name=req.name,
        category=req.category,
        flavour=req.flavour,
        price_inr=req.price_inr,
        stock_count=req.stock_count,
        rating=req.rating,
        description=req.description,
        image_url=req.image_url
    )

@app.delete("/api/merchant/products/{product_id}")
def merchant_delete_product(product_id: int):
    """Delete a product from SQLite catalog."""
    return delete_merchant_product(product_id)

@app.get("/api/merchant/orders")
def merchant_get_orders():
    """Fetch live merchant orders ledger."""
    return {"orders": get_merchant_orders_ledger()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
