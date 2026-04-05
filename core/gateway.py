import sentinel_core
from fastapi import FastAPI, Header, HTTPException, Body
from security.pii_scrub import scrub_pii 
from contextlib import asynccontextmanager

def build_financial_risk(amount: float, user_tier: str) -> float:
    base_risk = 0.2
    if amount > 1000: base_risk += 0.4
    if amount > 5000: base_risk += 0.3
    if user_tier == "new": base_risk += 0.2
    return min(base_risk, 1.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Основная политика (Enforce)
    sentinel_core.add_policy("fin_limit_high", "transfer_funds", 500, sentinel_core.ExecutionMode.Enforce)
    
    # Теневая экспериментальная политика 🚩
    # Мы тестируем ее в Shadow Mode, чтобы не мешать бизнесу
    sentinel_core.add_policy("exp_v2_rules", "transfer_funds", 999, sentinel_core.ExecutionMode.Shadow)
    
    print("🛡️ [Sentinel] Hybrid Mode active: Enforce + Shadow.")
    yield

app = FastAPI(title="SentinelAI v3.0: Financial Guard", lifespan=lifespan)

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401, detail="Invalid Security Token")

    amount = payload.get("amount", 0.0)
    user_tier = payload.get("user_tier", "standard")
    
    clean_prompt = scrub_pii(payload.get("prompt", ""))
    current_risk = build_financial_risk(amount, user_tier)

    # Вызов Rust-ядра (двойной проход внутри)
    result = sentinel_core.fast_evaluate(tool_name="transfer_funds", risk=current_risk)

    # Детектор Policy Drift (Дрейфа политик)
    if result.decision != result.shadow_decision:
        print(f"⚠️ [DRIFT] Shadow logic disagreed! Policy: {result.shadow_policy_id}")

    if result.decision == sentinel_core.Decision.Deny:
        return {"status": "DENIED", "policy_id": result.policy_id}

    return {
        "status": "SUCCESS",
        "metrics": {"risk": current_risk},
        "shadow_report": {"verdict": str(result.shadow_decision)}
    }
