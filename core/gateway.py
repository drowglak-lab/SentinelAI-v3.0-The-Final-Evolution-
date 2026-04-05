import sentinel_core
from fastapi import FastAPI, Header, HTTPException, Body
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Начальный прогрев системы
    try:
        sentinel_core.load_policies("core/policies.yaml")
        print("🛡️ [Sentinel] Engine warming complete. Policies loaded.")
    except Exception as e:
        print(f"❌ [Sentinel] Startup failure: {e}")
    yield

app = FastAPI(title="SentinelAI v3.0: Control Plane", lifespan=lifespan)

# ЭНДПОИНТ ДЛЯ HOT RELOAD ⚡
@app.post("/v1/system/reload")
async def reload_config(x_admin_token: str = Header(None)):
    if x_admin_token != "admin_secret_reload_token":
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    try:
        # Прямой вызов Rust-функции обновления
        msg = sentinel_core.load_policies("core/policies.yaml")
        return {"status": "ok", "detail": msg}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401)

    # Собираем контекст (можешь добавлять сюда любые поля)
    context = {
        "risk_score": float(payload.get("risk", 0.6)),
        "amount": float(payload.get("amount", 0.0)),
        "is_new": payload.get("user_tier") == "new"
    }

    result = sentinel_core.fast_evaluate(tool_name="transfer_funds", context=context)

    if result.decision != result.shadow_decision:
        print(f"⚠️ [DRIFT] {result.shadow_policy_id} triggered. Check YAML version.")

    return {
        "status": "SUCCESS" if result.decision == sentinel_core.Decision.Allow else "DENIED",
        "shadow": str(result.shadow_decision),
        "policy": result.policy_id
    }
