import os
import sys
import json
import base64
import time
import re
import sqlite3
import requests
import numpy as np
import sounddevice as sd
import soundfile as sf
from prompt_manager import prompt_manager

# Load .env if present
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# API Keys & Endpoints
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "qwen/qwen3.6-27b"
DB_PATH = "gym_store.db"

# Mapping of detected language codes to Sarvam TTS bulbul:v3 speakers
SPEAKER_MAP = {
    "te-IN": "gokul",    # Telugu
    "hi-IN": "shubh",    # Hindi
    "en-IN": "rohan",    # English (Sales Executive persona)
    "ta-IN": "vijay",    # Tamil
    "kn-IN": "gokul",    # Kannada
    "ml-IN": "gokul",    # Malayalam
    "mr-IN": "shubh",    # Marathi
    "bn-IN": "shubh",    # Bengali
    "gu-IN": "shubh",    # Gujarati
    "pa-IN": "shubh",    # Punjabi
    "od-IN": "shubh",    # Odia
}

from tools import ALL_TOOLS, TOOL_FUNCTION_MAP

# =====================================================================
# 🎙️ AUDIO RECORDING (VAD) & SARVAM STT/TTS
# =====================================================================

def record_microphone_vad(output_path: str = "input_mic.wav", sample_rate: int = 16000, max_duration: float = 30.0) -> str:
    """Dynamic VAD Recording: Auto-starts on speech, auto-stops 1.2s after silence."""
    print("\n🎙️  [LISTENING] Speak into your microphone now...")
    print("   (Recording stops automatically when you stop speaking)")
    
    chunk_size = 800
    silence_limit_chunks = int(1.2 * (sample_rate / chunk_size))
    speech_threshold = 250
    
    audio_frames = []
    speech_started = False
    silent_chunks = 0
    start_time = time.time()
    
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=chunk_size) as stream:
        while True:
            chunk, overflowed = stream.read(chunk_size)
            chunk_flat = chunk.flatten()
            
            rms = np.sqrt(np.mean(chunk_flat.astype(np.float32) ** 2))
            
            if not speech_started:
                if rms > speech_threshold:
                    speech_started = True
                    print("\n   🔴 [SPEAKING] Recording voice...", end="", flush=True)
                    audio_frames.append(chunk_flat)
            else:
                audio_frames.append(chunk_flat)
                print(".", end="", flush=True)
                
                if rms < speech_threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0
                    
                if silent_chunks >= silence_limit_chunks:
                    print("\n   ✅ Silence detected. Finished recording!")
                    break
                    
            if time.time() - start_time > max_duration:
                print("\n   ⏱️ Max duration reached. Stopping recording.")
                break

    if audio_frames:
        full_audio = np.concatenate(audio_frames, axis=0)
        sf.write(output_path, full_audio, sample_rate)
        return output_path
    else:
        print("\n⚠️ No speech detected.")
        return ""

def transcribe_audio_sarvam_autodetect(audio_path: str) -> tuple[str, str]:
    """Transcribe audio using Sarvam STT with auto-language detection."""
    if not audio_path or not os.path.exists(audio_path):
        return "", "te-IN"
        
    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"api-subscription-key": SARVAM_API_KEY}
    
    print(f"\n[1/3] 🎙️  Transcribing audio with Sarvam STT (Auto-detect)...")
    start_time = time.time()
    
    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
        payload = {"model": "saaras:v3", "language_code": "unknown"}
        response = requests.post(url, headers=headers, files=files, data=payload)
        
    duration = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        transcript = data.get("transcript", "").strip()
        detected_lang = data.get("language_code", "te-IN")
        if not detected_lang or detected_lang == "unknown":
            detected_lang = "te-IN"
            
        print(f"✅ STT Complete ({duration:.2f}s): \"{transcript}\"")
        print(f"🌐 Auto-detected Language: {detected_lang}")
        return transcript, detected_lang
    else:
        print(f"❌ Sarvam STT Error ({response.status_code}): {response.text}")
        return "", "te-IN"

# =====================================================================
# 🧠 GROQ API CLIENT WITH RESILIENT RETRY & CONTEXT PRUNING
# =====================================================================

def prune_message_history(messages: list, max_recent_turns: int = 4) -> list:
    """Sliding Window: Keep system prompt + last N dialogue turns to stay well within TPM limits."""
    if len(messages) <= (max_recent_turns * 2 + 1):
        return messages
    system_msg = messages[0]
    recent_messages = messages[-(max_recent_turns * 2):]
    return [system_msg] + recent_messages

def groq_post_with_retry(payload: dict, max_retries: int = 3) -> requests.Response:
    """Execute Groq request with automatic 429 Rate Limit backoff and retry."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    for attempt in range(max_retries):
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)
        
        if response.status_code == 200:
            return response
            
        # Handle 429 Rate Limit
        if response.status_code == 429:
            err_msg = response.json().get("error", {}).get("message", "")
            # Extract suggested wait time (e.g., "Please try again in 3.03s")
            match = re.search(r'try again in ([0-9\.]+)s', err_msg)
            wait_sec = float(match.group(1)) + 0.5 if match else (attempt + 1) * 2.5
            
            print(f"   ⏳ [RATE LIMIT 429] Auto-waiting {wait_sec:.1f}s before retry (Attempt {attempt+1}/{max_retries})...")
            time.sleep(wait_sec)
            continue
        else:
            return response
            
    return response

def query_groq_with_tools(messages: list) -> str:
    """Send conversation + SQLite DB tools to Groq Cloud API with full retry & multi-tool support."""
    print(f"\n[2/3] ⚡ Querying Groq Cloud LPU ({GROQ_MODEL}) + Database Tools...")
    start_time = time.time()
    
    pruned_messages = prune_message_history(messages)
    
    max_tool_iterations = 4
    for iteration in range(max_tool_iterations):
        payload = {
            "model": GROQ_MODEL,
            "messages": pruned_messages,
            "tools": ALL_TOOLS,
            "tool_choice": "auto",
            "temperature": 0.3
        }
        
        response = groq_post_with_retry(payload)
        
        if response.status_code != 200:
            print(f"❌ Groq API Error ({response.status_code}): {response.text}")
            return ""
            
        res_data = response.json()
        choice = res_data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        tool_calls = msg.get("tool_calls", [])
        content = msg.get("content", "") or ""
        
        # If model returned tool calls via API
        if tool_calls:
            print(f"⚡ [TOOL CALL DETECTED] Executing {len(tool_calls)} database query(ies)...")
            pruned_messages.append(msg)
            
            for call in tool_calls:
                call_id = call.get("id")
                func_info = call.get("function", {})
                fn_name = func_info.get("name")
                raw_args = func_info.get("arguments", "{}")
                fn_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                
                print(f"   🛠️  Executing DB Tool: {fn_name}({json.dumps(fn_args)})")
                
                if fn_name in TOOL_FUNCTION_MAP:
                    tool_result = TOOL_FUNCTION_MAP[fn_name](**fn_args)
                    print(f"   📊 DB Result: {tool_result}")
                    
                    pruned_messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": tool_result
                    })
                else:
                    print(f"   ⚠️ Unknown tool: {fn_name}")
            continue
            
        # If Qwen returned raw XML tool call in content
        if "<tool_call>" in content:
            param_match = re.search(r'<parameter=query>\s*(.*?)\s*</parameter>', content)
            if not param_match:
                param_match = re.search(r'<parameter=category>\s*(.*?)\s*</parameter>', content)
            search_term = param_match.group(1).strip() if param_match else "Protein"
            
            print(f"   🛠️  Executing DB Tool (from raw call): search_gym_products(query='{search_term}')")
            tool_result = search_gym_products(query=search_term)
            print(f"   📊 DB Result: {tool_result}")
            
            pruned_messages.append({"role": "assistant", "content": content})
            pruned_messages.append({"role": "user", "content": f"Database search result for {search_term}: {tool_result}. Now give the final sales answer to the customer in the user's language."})
            continue
            
        duration = time.time() - start_time
        print(f"✅ Final Groq Answer ({duration:.2f}s):\n\"{content}\"")
        return content

    return "ధన్యవాదాలు! మీ ఆర్డర్ వివరాలు చూసి వెంటనే అప్‌డేట్ చేస్తాము."

def clean_speech_text(text: str) -> str:
    """Strip reasoning tags (<think>...</think>), tool tags, markdown, and format clean speech."""
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'<tool_call>.*?</tool_call>', '', cleaned, flags=re.DOTALL)
    cleaned = cleaned.replace("*", "").replace("`", "").replace("#", "").strip()
    return cleaned

def speak_text_sarvam(text: str, lang_code: str, output_path: str = "output_response.wav") -> str:
    """Synthesize text into speech audio using Sarvam AI TTS (bulbul:v3)."""
    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    
    clean_text = clean_speech_text(text)
    if not clean_text:
        clean_text = "మీకు ఏ విధంగా సహాయం చేయగలను?"
        
    speaker = SPEAKER_MAP.get(lang_code, "rohan" if lang_code == "en-IN" else "gokul")
    
    payload = {
        "inputs": [clean_text],
        "target_language_code": lang_code,
        "speaker": speaker,
        "model": "bulbul:v3"
    }
    
    print(f"\n[3/3] 🔊 Synthesizing spoken audio ({lang_code} - speaker '{speaker}') with Sarvam TTS...")
    start_time = time.time()
    
    response = requests.post(url, headers=headers, json=payload)
    duration = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        audios = data.get("audios", [])
        if audios:
            audio_bytes = base64.b64decode(audios[0])
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            print(f"✅ TTS Complete ({duration:.2f}s): Saved to {output_path}")
            return output_path
    print(f"❌ Sarvam TTS Error ({response.status_code}): {response.text}")
    return ""

def run_gym_voice_assistant():
    print("=" * 70)
    print("⚡ SARVAM AI + GROQ LPU + JINJA2 PROMPT RESILIENT SALES ASSISTANT")
    print("=" * 70)
    print(f"🧠 LLM Engine: Groq LPU ({GROQ_MODEL}) - Ultra-Fast Cloud Execution")
    print("📁 Prompts: Centralized Jinja2 Templates (`prompts/base_sales_agent.j2`)")
    print("🛡️  Resilience: Auto 429 Retry Backoff + Sliding Window Context Pruning")
    print("💡 Ask about proteins, prices, discounts, coupons ('FIT10'), or combos in any language!")
    print("💡 Type 'q' and ENTER anytime to exit.\n")
    
    prompt_manager.set_stage("greeting")
    system_prompt = prompt_manager.render_system_prompt()
    
    # 🎙️ PROACTIVE AGENT GREETING: Agent speaks first to welcome the customer!
    initial_greeting = (
        "Namaste and Welcome to MuscleBlaze! Main hoon Rohan, aapka sales and fitness advisor. "
        "Aapka naam kya hai aur aaj aapka main fitness goal kya hai?"
    )
    
    print("\n👋 [AGENT SPEAKS FIRST] Rohan is greeting you...")
    print(f"💬 Rohan: \"{initial_greeting}\"")
    greeting_audio = speak_text_sarvam(initial_greeting, lang_code="hi-IN")
    if greeting_audio and sys.platform == "darwin":
        os.system(f"afplay '{greeting_audio}'")
        
    messages_history = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "assistant",
            "content": initial_greeting
        }
    ]
    
    turn = 1
    while True:
        print("\n" + "─" * 55)
        print(f"🔄 --- VOICE STORE TURN #{turn} [Stage: {prompt_manager.current_stage.upper()}] ---")
        print("─" * 55)
        
        user_input = input("👉 Press ENTER to reply to Rohan (or 'q' to exit): ").strip()
        if user_input.lower() == 'q':
            print("👋 Thank you for visiting the Gym Store! Goodbye!")
            break
            
        # Step 1: Record & STT
        audio_file = record_microphone_vad()
        transcript, detected_lang = transcribe_audio_sarvam_autodetect(audio_file)
        
        if not transcript:
            print("⚠️ Could not detect speech clearly. Let's try again.")
            continue
            
        # Dynamic Stage Detection across all 5 sales stages
        prompt_manager.auto_detect_stage(transcript, turn)
            
        # Dynamically refresh system prompt for current stage
        messages_history[0]["content"] = prompt_manager.render_system_prompt()
        messages_history.append({"role": "user", "content": transcript})
        
        # Step 2: Groq LPU Reasoning + SQLite Database Tool Call (with 429 Retry Backoff)
        reply = query_groq_with_tools(messages_history)
        if not reply:
            print("⚠️ No response generated. Retrying turn...")
            messages_history.pop()
            continue
            
        messages_history.append({"role": "assistant", "content": reply})
        
        # Step 3: Sarvam TTS & Audio Output
        audio_out = speak_text_sarvam(reply, lang_code=detected_lang)
        if audio_out and sys.platform == "darwin":
            print(f"\n🔊 Playing audio response over speakers (afplay)...")
            os.system(f"afplay '{audio_out}'")
            
        turn += 1

if __name__ == "__main__":
    try:
        run_gym_voice_assistant()
    except KeyboardInterrupt:
        print("\n\n👋 Store assistant stopped by user. Goodbye!")
