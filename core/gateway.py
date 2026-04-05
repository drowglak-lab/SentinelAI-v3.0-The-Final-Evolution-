import sentinel_core
import logging
import sys
import json
from fastapi import FastAPI, Header, HTTPException, Body
from contextlib import asynccontextmanager

# Настройка структурированного логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s', # В проде здесь будет JSON-форматтер
    stream=sys.stdout
)
logger = logging.getLogger("sentinel-ai")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        msg = sentinel_core.load_policies("core/policies.yaml")
        logger.info(json.dumps({
            "event": "engine_startup",
            "status": "success",
            "detail": msg
        }))
    except Exception as e:
        logger.error(json.dumps({"event": "startup_failure", "error": str(e)}))
    yield

app = FastAPI(title="SentinelAI v3.0: Observable Platform", lifespan=lifespan)

@app.post("/v1/system/reload")
async def reload_config(x_admin_token: str = Header(None)):
    if x_admin_token != "admin_secret_reload_token":
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    try:
        msg = sentinel_core.load_policies("core/policies.yaml")
        logger.info(json.dumps({"event": "policy_hot_reload", "status": "ok", "message": msg}))
        return {"status": "ok", "detail": msg}
    except Exception as e:
        logger.error(json.dumps({"event": "reload_failure", "error": str(e)}))
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401)

    context = {
        "risk_score": float(payload.get("risk", 0.6)),
        "amount": float(payload.get("amount", 0.0)),
        "is_new": payload.get("user_tier") == "new"
    }

    result = sentinel_core.fast_evaluate(tool_name="transfer_funds", context=context)

    # --- СТРУКТУРИРОВАННЫЙ АУДИТ ТРАССИРОВКИ ---
    for t in result.traces:
        log_payload = {
            "event": "policy_trace",
            "version": result.version,
            "policy_id": t.policy_id,
            "mode": "enforce" if "Enforce" in str(t.mode) else "shadow",
            "matched": t.matched,
            "field": t.attr_key,
            "actual": t.actual_value,
            "threshold": t.threshold,
            "recipient": payload.get("recipient", "unknown")
        }
        # В проде это уходит в Graylog/Datadog одним JSON-объектом
        logger.info(json.dumps(log_payload))

    # Детекция дрейфа логики (Drift Detection)
    if result.decision != result.shadow_decision:
        logger.warning(json.dumps({
            "event": "logic_drift",
            "enforce_decision": str(result.decision),
            "shadow_decision": str(result.shadow_decision),
            "shadow_policy": result.shadow_policy_id,
            "context_summary": context
        }))

    # Богатый API ответ для клиента
    return {
        "status": "SUCCESS" if result.decision == sentinel_core.Decision.Allow else "DENIED",
        "version": result.version,
        "policy_id": result.policy_id,
        "audit_evidence": [
            {
                "id": t.policy_id,
                "field": t.attr_key,
                "actual": t.actual_value,
                "expected": t.threshold,
                "matched": t.matched
            } for t in result.traces if t.matched
        ]
    }
