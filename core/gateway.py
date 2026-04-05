import sentinel_core
from fastapi import FastAPI, Header, HTTPException, Body
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Загружаем политики из YAML файла
        sentinel_core.load_policies("core/policies.yaml")
        print("🛡️ [Sentinel] Policies loaded from YAML. Engine ready.")
    except Exception as e:
        print(f"❌ [Sentinel] Failed to load policies: {e}")
    yield

app = FastAPI(title="SentinelAI v3.0: Policy Platform", lifespan=lifespan)

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401)

    # Собираем контекст из запроса
    amount = payload.get("amount", 0.0)
    risk = 0.6 # Здесь может быть логика build_financial_risk

    context = {
        "risk_score": risk,
        "amount": float(amount),
        "is_new": payload.get("user_tier") == "new"
    }

    # Оценка
    result = sentinel_core.fast_evaluate(tool_name="transfer_funds", context=context)

    if result.decision != result.shadow_decision:
        print(f"⚠️ [DRIFT] Policy {result.shadow_policy_id} disagreed in Shadow Mode")

    return {
        "status": "SUCCESS" if result.decision == sentinel_core.Decision.Allow else "DENIED",
        "policy": result.policy_id,
        "shadow_report": {"verdict": str(result.shadow_decision)}
    }
