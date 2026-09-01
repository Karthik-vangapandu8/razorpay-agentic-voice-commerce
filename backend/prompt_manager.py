import os
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

    def auto_detect_stage(self, transcript: str, turn: int):
        """Intelligently switch conversation stage based on customer speech semantics."""
        t = transcript.lower()
        
        # Objection & Discount Negotiation
        if any(w in t for w in ["discount", "offer", "coupon", "code", "rate ekkuva", "price high", "too expensive", "taggichu", "kam karo", "kam kijiye"]):
            self.set_stage("objection")
        # Checkout & Buy Intent
        elif any(w in t for w in ["buy", "order", "book", "cart", "payment", "konali", "teesukunta", "khareedna", "pack kar do"]):
            self.set_stage("checkout")
        # Discovery / Goal Discussion
        elif any(w in t for w in ["goal", "fat loss", "muscle gain", "weight loss", "beginner", "suggest", "which one", "edhi better"]):
            self.set_stage("discovery")
        # Specific Product Recommendation & Pricing
        elif any(w in t for w in ["whey", "protein", "creatine", "peanut butter", "pre workout", "biozyme", "rate", "price", "stock"]):
            self.set_stage("recommendation")
        elif turn == 1:
            self.set_stage("greeting")
        else:
            self.set_stage("recommendation")

    def render_system_prompt(self, **kwargs) -> str:
        """Render the master modular base_sales_agent.j2 prompt with all sub-templates."""
        template = jinja_env.get_template("base_sales_agent.j2")
        context = {
            "agent_name": self.agent_name,
            "store_name": self.store_name,
            "customer_name": self.customer_name,
            "fitness_goal": self.fitness_goal,
            "stage": self.current_stage,
            "active_offers": self.active_offers,
            **kwargs
        }
        return template.render(context)

# Singleton Instance
prompt_manager = SalesPromptManager()
