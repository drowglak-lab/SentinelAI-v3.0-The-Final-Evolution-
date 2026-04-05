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
    # Теперь при добавлении политики указываем, какой атрибут проверять
    # Напр: проверяем "risk_score" с порогом 0.8
    sentinel_core.add_policy("fin_limit_high", "transfer_funds", "risk_score", 0.8, sentinel_core.ExecutionMode.Enforce)
    
    # Теневая политика: проверяет тот же "risk_score", но с порогом 0.5
    sentinel_core.add_policy("exp_v2_rules", "transfer_funds", "risk_score", 0.5, sentinel_core.ExecutionMode.Shadow)
    
    print("🛡️ [Sentinel] Context-aware Hybrid Mode active.")
    yield

app = FastAPI(title="SentinelAI v3.0", lifespan=lifespan)

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401, detail="Invalid Security Token")

    amount = payload.get("amount", 0.0)
    user_tier = payload.get("user_tier", "standard")
    current_risk = build_financial_risk(amount, user_tier)

    # СОБИРАЕМ КОНТЕКСТ 🧠
    context = {
        "risk_score": current_risk,
        "amount": float(amount),
        "is_new_user": user_tier == "new"
    }

    # Передаем словарь в Rust
    result = sentinel_core.fast_evaluate(tool_name="transfer_funds", context=context)

    if result.decision != result.shadow_decision:
        print(f"⚠️ [DRIFT] Shadow logic disagreed! Policy: {result.shadow_policy_id}")

    if result.decision == sentinel_core.Decision.Deny:
        return {"status": "DENIED", "policy_id": result.policy_id}

    return {
        "status": "SUCCESS",
        "metrics": {"risk": current_risk},
        "shadow_report": {"verdict": str(result.shadow_decision)}
    }
