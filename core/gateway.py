import sentinel_core
from fastapi import FastAPI, Header, HTTPException, Body
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Начальная загрузка при старте
    try:
        sentinel_core.load_policies("core/policies.yaml")
        print("🛡️ [Sentinel] Engine warmed up. Audit tracing: ENABLED.")
    except Exception as e:
        print(f"❌ [Sentinel] Startup failure: {e}")
    yield

app = FastAPI(title="SentinelAI v3.0: Policy Platform", lifespan=lifespan)

# ЭНДПОИНТ ДЛЯ HOT RELOAD ⚡
@app.post("/v1/system/reload")
async def reload_config(x_admin_token: str = Header(None)):
    if x_admin_token != "admin_secret_reload_token":
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    try:
        msg = sentinel_core.load_policies("core/policies.yaml")
        return {"status": "ok", "detail": msg}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401)

    # Собираем контекст из входящих данных
    context = {
        "risk_score": float(payload.get("risk", 0.6)),
        "amount": float(payload.get("amount", 0.0)),
        "is_new": payload.get("user_tier") == "new"
    }

    # Выполняем оценку в Rust
    result = sentinel_core.fast_evaluate(tool_name="transfer_funds", context=context)

    # --- BLOCK: EXPLAINABLE LOGGING 🏦 ---
    # Выводим в терминал "протокол допроса" каждой транзакции
    print(f"\n📝 [AUDIT TRACE] Config Version: {result.version}")
    for t in result.traces:
        # Превращаем Enum из Rust в читаемую строку режима
        mode_str = "ENFORCE" if "Enforce" in str(t.mode) else "SHADOW"
        status = "🚩 MATCHED" if t.matched else "✅ Passed"
        
        print(f"  └─ [{mode_str}] Policy: {t.policy_id:20} | "
              f"Rule: {t.attr_key} > {t.threshold} | "
              f"Actual: {t.actual_value} -> {status}")
    # -------------------------------------

    # Детекция дрейфа логики (Shadow vs Enforce)
    if result.decision != result.shadow_decision:
        print(f"⚠️ [DRIFT] Shadow logic disagreed. Shadow Policy: {result.shadow_policy_id}")

    # Финальный ответ клиенту
    if result.decision == sentinel_core.Decision.Deny:
        return {
            "status": "DENIED",
            "policy": result.policy_id,
            "version": result.version,
            "reason": "Security threshold violation"
        }

    return {
        "status": "SUCCESS",
        "version": result.version,
        "shadow_report": {"verdict": str(result.shadow_decision)},
        "audit_log": [
            {"id": t.policy_id, "matched": t.matched} 
            for t in result.traces if t.matched
        ]
    }
