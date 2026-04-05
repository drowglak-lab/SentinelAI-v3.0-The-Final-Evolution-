import sentinel_core
from fastapi import FastAPI, Header, HTTPException, Body
from security.pii_scrub import scrub_pii 
from contextlib import asynccontextmanager

def build_financial_risk(amount: float, user_tier: str) -> float:
    base_risk = 0.2
    if amount > 1000:
        base_risk += 0.4
    if amount > 5000:
        base_risk += 0.3
    if user_tier == "new":
        base_risk += 0.2
    return min(base_risk, 1.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        sentinel_core.add_policy("fin_limit_standard", "transfer_funds", 100)
        sentinel_core.add_policy("fin_limit_high", "transfer_funds", 500)
        print("🛡️ [Sentinel] Financial Shield active. Policies synchronized.")
    except Exception as e:
        print(f"❌ [Sentinel] Failed to initialize Rust Core: {e}")
    yield

app = FastAPI(title="SentinelAI v3.0: Financial Guard", lifespan=lifespan)

@app.post("/v1/banking/transfer")
async def handle_transfer(
    payload: dict = Body(...), 
    x_agent_token: str = Header(None)
):
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401, detail="Invalid Security Token")

    amount = payload.get("amount", 0.0)
    recipient = payload.get("recipient", "unknown")
    user_tier = payload.get("user_tier", "standard")
    prompt = payload.get("prompt", "")

    # Очистка PII
    clean_prompt = scrub_pii(prompt)

    # Вычисление риска
    current_risk = build_financial_risk(amount, user_tier)

    # Вызов Rust-ядра
    result = sentinel_core.fast_evaluate(
        tool_name="transfer_funds",
        risk=current_risk
    )

    if result.decision == sentinel_core.Decision.Deny:
        return {
            "status": "DENIED",
            "security_event": {
                "policy_id": result.policy_id,
                "calculated_risk": current_risk,
                "reason": result.reason,
                "action": "BLOCKED"
            },
            "scrubbed_prompt": clean_prompt
        }

    return {
        "status": "SUCCESS",
        "transaction": {"id": "tx_2026_0504", "amount": amount, "recipient": recipient},
        "metrics": {"risk_score": current_risk, "engine": "rust-core-v1"}
    }
