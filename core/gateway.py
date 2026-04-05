import sentinel_core  # Our reactive core on Rust
from fastapi import FastAPI, Header, HTTPException, Body
from security.pii_scrub import scrub_pii 
from contextlib import asynccontextmanager
from typing import Dict

# --- 1. Context Builder (Logic of risk calculation) ---
def build_financial_risk(amount: float, user_tier: str) -> float:
    """
    We turn business parameters into a deterministic risk score.
    This is the 'brain' of our gateway before we give the decision to the judge (Rust).
    """
    base_risk = 0.2  # The basic risk of any transfer
    
    # 🚩 We increase the risk for large amounts
    if amount > 1000:
        base_risk += 0.4
    if amount > 5000:
        base_risk += 0.3
        
    # 🚩 We increase the risk for new users (Tier: New)
    if user_tier == "new":
        base_risk += 0.2
        
    return min(base_risk, 1.0) # Риск не может быть больше 1.0

# --- 2. Initialization (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # We customize policies specifically for a financial scenario
        # pol_id, tool_name, priority
        sentinel_core.add_policy("fin_limit_standard", "transfer_funds", 100)
        sentinel_core.add_policy("fin_limit_high", "transfer_funds", 500)
        
        print("🛡️ [Sentinel] Financial Shield active. Policies synchronized.")
    except Exception as e:
        print(f"❌ [Sentinel] Failed to initialize Rust Core: {e}")
    yield

# --- 3. Application ---
app = FastAPI(
    title="SentinelAI v3.0: Financial Guard",
    lifespan=lifespan
)

@app.post("/v1/banking/transfer")
async def handle_transfer(
    payload: dict = Body(...), 
    x_agent_token: str = Header(None)
):
    """
    Endpoint simulates a secure transfer of funds through an AI agent.
    """
    # 1. Identity Layer
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401, detail="Invalid Security Token")

    # 2. Request Data
    amount = payload.get("amount", 0.0)
    recipient = payload.get("recipient", "unknown")
    user_tier = payload.get("user_tier", "standard")
    prompt = payload.get("prompt", "")

    # 3. Shield Layer (Input Scrubbing)
    clean_
