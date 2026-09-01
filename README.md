# 🏋️‍♂️ MuscleBlaze Agentic Voice Commerce Platform
### *AI Growth & Autonomous Commerce Engine Powered by Sarvam AI, Groq LPU & Razorpay Test APIs*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Razorpay](https://img.shields.io/badge/Razorpay-Test%20Mode-blue)](https://razorpay.com/)
[![Groq LPU](https://img.shields.io/badge/Groq%20LPU-Qwen%203.6%2027B-orange)](https://groq.com/)
[![Sarvam AI](https://img.shields.io/badge/Sarvam%20AI-Multilingual%20Speech-green)](https://sarvam.ai/)
[![Tests](https://img.shields.io/badge/Tests-7%2F7%20Passed-brightgreen)](test_failure_scenarios.py)

---

## 🌟 Key Features

1. **🎙️ Multilingual Voice AI (Sarvam STT/TTS + Groq LPU)**:
   - Proactive conversational sales persona (Rohan) greeting in Hindi, Telugu, and English.
   - Real-time Voice Activity Detection (VAD) with auto-silence cutoff.
   - Ultra-fast inference (~1.5s - 2.5s) on Groq Cloud LPUs (`qwen/qwen3.6-27b`).

2. **🧮 100% Deterministic Financial Air-Gap**:
   - LLM **never calculates prices, taxes, or discounts**.
   - Deterministic backend verifies live inventory, combo savings (-₹300), and bounded `FIT10` coupon codes.

3. **🔄 Formal Order State Machine**:
   ```text
   CART_CREATED
     └──► PRICE_CONFIRMED
            └──► CUSTOMER_APPROVED
                   └──► PAYMENT_PENDING
                          ├──► PARTIALLY_PAID (Wallet partial + Razorpay link)
                          └──► PAID ──► ORDER_CONFIRMED
   ```

4. **💳 Programmable Agentic Wallet & Razorpay Split-Payment**:
   - Customer Wallet with daily spend rails (Max ₹15,000 cap).
   - Instant 1-click voice wallet deduction.
   - Automatic live Razorpay Smart Payment Link generation (`https://rzp.io/rzp/...`) for any remaining balance.

5. **🛡️ "The Bar" Safety & Audit Compliance**:
   - Bounded spend rails & single-order caps.
   - Full Know Your Agent (KYA) audit trails saved to `bills/`.
   - Idempotent Razorpay webhook ingestion.

---

## 📁 Repository Structure

```
razorpay-agentic-voice-commerce/
├── backend/                           # 🐍 FastAPI Python Backend Server
│   ├── api_server.py                  # REST & Voice Streaming Endpoints (Port 8000)
│   ├── commerce/                      # 🧮 Deterministic Commerce Engine
│   │   ├── models.py                  # Pydantic models & OrderStatus enum
│   │   ├── engine.py                  # Pricing, spend rails, and state machine
│   │   └── webhook.py                 # Idempotent Razorpay webhook handler
│   ├── prompts/                       # 📁 Modular Jinja2 Prompt Library
│   ├── tools/                         # 🛠️ Modular AI Tools Package
│   ├── bills/                         # 🧾 Generated Store Invoices & Receipts
│   ├── gym_store.db                   # 📦 SQLite Product & Wallet Database
│   ├── experiment_poc.py              # 🎙️ End-to-End CLI Voice Assistant Engine
│   └── test_failure_scenarios.py      # 🧪 Automated CLI Failure Test Suite (7/7 Passed)
│
└── frontend/                          # ⚛️ Next.js Web UI App (Coming Next)
```

---

## 🚀 Quickstart

### 1. Install Dependencies
```bash
pip install sounddevice soundfile requests numpy pydantic jinja2
```

### 2. Run the Failure Test Suite
```bash
python3 test_failure_scenarios.py
```

### 3. Run the Live Voice Assistant
```bash
python3 experiment_poc.py
```
