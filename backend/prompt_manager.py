import os
import requests
from typing import Optional
import jinja2

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(PROMPTS_DIR),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True
)

class SalesPromptManager:
    """
    Centralized Prompt Management Library with modular Jinja2 templates:
    prompts/
    ├── base_sales_agent.j2
    ├── stages/
    │   ├── greeting.j2
    │   ├── discovery.j2
    │   ├── recommendation.j2
    │   ├── objection.j2
    │   └── checkout.j2
    └── languages/
        └── indian_language_rules.j2
    """
    
    VALID_STAGES = ["greeting", "discovery", "recommendation", "objection", "checkout"]
    
    def __init__(self, agent_name: str = "Rohan", store_name: str = "MuscleBlaze Fitness Store"):
        self.agent_name = agent_name
        self.store_name = store_name
        self.customer_name = "Guest Customer"
        self.fitness_goal = "Muscle Building / Fitness"
        self.current_stage = "greeting"
        self.active_offers = [
            "Coupon Code 'FIT10': Instant 10% discount on all orders above ₹1,999",
            "Free premium MuscleBlaze Shaker bottle with every Biozyme Whey purchase",
            "Combo Deal: Buy Whey Protein + Creatine together and save ₹300"
        ]

    def set_customer_info(self, name: str = None, goal: str = None):
        if name:
            self.customer_name = name
        if goal:
            self.fitness_goal = goal

    def set_stage(self, stage: str):
        if stage.lower() in self.VALID_STAGES:
            self.current_stage = stage.lower()
        else:
            self.current_stage = "recommendation"

    def detect_intent_sarvam(self, transcript: str) -> Optional[str]:
        """Use Sarvam AI LLM (sarvam-105b-conversations) to understand customer speech intent across Indian languages."""
        sarvam_key = os.getenv("SARVAM_API_KEY", "")
        if not sarvam_key:
            return None

        url = "https://api.sarvam.ai/v1/chat/completions"
        headers = {"api-subscription-key": sarvam_key, "Content-Type": "application/json"}
        system_prompt = """You are an expert sales conversation stage classifier for a supplement store (MuscleBlaze).
Analyze the customer's input and output ONLY ONE word from:
- recommendation: Customer provides ANY qualification detail (such as age e.g. 'मेरा एज 22 है', '20 years old', workout days, gym frequency, health issues, lactose sensitivity, veg/non-veg).
- discovery: Customer asks about products, protein, mass gainers, weight gain, fat loss, needs help selecting, asks recommendations, or expresses any fitness goal.
- objection: Customer asks for discount, coupon, price drop, or complains about price.
- checkout: Customer expresses intent to buy, order, place order, pay, or add to cart.
- greeting: Customer ONLY says hello/hi/namaste with NO age, NO numbers, NO goal, and NO product mention.

Output strictly ONE word: discovery, recommendation, objection, checkout, or greeting."""

        payload = {
            "model": "sarvam-105b-conversations",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=4)
            if res.status_code == 200:
                out = res.json()["choices"][0]["message"]["content"].strip().lower()
                for stage in self.VALID_STAGES:
                    if stage in out:
                        print(f"🤖 Sarvam LLM Classified Intent: '{stage}' for input: '{transcript[:40]}...'")
                        return stage
        except Exception as e:
            print(f"Sarvam LLM intent classification fallback to rules: {e}")
        return None

    def auto_detect_stage(self, transcript: str, turn: int):
        """Intelligently switch conversation stage using Sarvam LLM primary intent classification with keyword fallback."""
        sarvam_stage = self.detect_intent_sarvam(transcript)
        
        # If in an active consultative stage (discovery/recommendation), never downgrade to greeting unless user explicitly says hi/hello
        if sarvam_stage == "greeting" and self.current_stage in ["discovery", "recommendation"]:
            t_lower = transcript.lower()
            if not any(w in t_lower for w in ["hi", "hello", "namaste", "నమస్తే", "नमस्ते"]):
                sarvam_stage = "discovery"

        if sarvam_stage and sarvam_stage in self.VALID_STAGES:
            self.set_stage(sarvam_stage)
            return

        t = transcript.lower()
        
        # Objection & Discount Negotiation
        if any(w in t for w in [
            "discount", "offer", "coupon", "code", "rate ekkuva", "price high", "too expensive",
            "taggichu", "kam karo", "kam kijiye", "డిస్కౌంట్", "ఆఫర్", "కూపన్", "రేటు", "తగ్గించు",
            "తక్కువ", "கார்ட்", "ஆர்டர்", "கூப்பன்"
        ]):
            self.set_stage("objection")
        # Checkout & Buy Intent
        elif any(w in t for w in [
            "buy", "order", "book", "cart", "payment", "konali", "teesukunta", "khareedna", "pack kar do",
            "కార్ట్", "ఆర్డర్", "కూపన్", "కొనుక్కుంటా", "పేమెంట్", "ఆర్డర్ పెట్టేయ్", "ఆర్డర్ ప్లేస్",
            "ఆర్డర్ చెయ్యి", "కార్ట్ లో", "కొనాలి", "வாங்க", "கட்டணம்", "कार्ट", "ऑर्डर", "कूपन", "खरीदना"
        ]):
            self.set_stage("checkout")
        # Qualification Response (customer provided age/workout/health/diet details)
        elif any(w in t for w in [
            "year", "yrs", "din", "days", "gym", "health", "issue", "veg", "non-veg", "nonveg",
            "age", "saal", "lactose", "sensitivity", "brother", "సంవత్సరాలు", "జిమ్", "వయస్సు", "సమస్య", "ఏజ్",
            "लैकोस्ट", "सेंसिविटी", "लैक्टोज", "भाई", "ऐज", "बार"
        ]) or any(c.isdigit() for c in t):
            self.set_stage("recommendation")
        # Goal / Product Inquiry (Initial Discovery phase)
        elif any(w in t for w in [
            "goal", "fat loss", "muscle gain", "muscle increase", "mass gainer", "mass gainers", "weight loss",
            "beginner", "suggest", "which one", "edhi better", "whey", "protein", "creatine", "peanut butter",
            "pre workout", "biozyme", "gainer", "లీన్ బాడీ", "వెయిట్ గెయిన్", "మజిల్", "గోల్", "బరువు",
            "ఫ్యాట్ లాస్", "మాస్ గేనర్", "ప్రోటీన్", "వే", "బయోజైమ్", "మాస్ గేనర్స్", "मास गेनर", "मसल इनक्रीस", "प्रोटीन"
        ]):
            self.set_stage("discovery")
        elif turn == 1:
            self.set_stage("greeting")
        else:
            self.set_stage("discovery")

    def render_system_prompt(self, **kwargs) -> str:
        """Render the master modular base_sales_agent.j2 prompt with all sub-templates and merchant knowledge."""
        try:
            from tools.merchant_service import get_store_config
            cfg = get_store_config()
            agent_name = cfg.agent_name or self.agent_name
            store_name = cfg.store_name or self.store_name
            knowledge_specs = cfg.knowledge_specs or ""
            active_offers = cfg.active_offers or self.active_offers
        except Exception:
            agent_name = self.agent_name
            store_name = self.store_name
            knowledge_specs = ""
            active_offers = self.active_offers

        template = jinja_env.get_template("base_sales_agent.j2")
        context = {
            "agent_name": agent_name,
            "store_name": store_name,
            "knowledge_specs": knowledge_specs,
            "customer_name": self.customer_name,
            "fitness_goal": self.fitness_goal,
            "stage": self.current_stage,
            "active_offers": active_offers,
            **kwargs
        }
        return template.render(context)

# Singleton Instance
prompt_manager = SalesPromptManager()
