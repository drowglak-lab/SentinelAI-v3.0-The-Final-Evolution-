import sentinel_core
import logging
import sys
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, Header, HTTPException, Body
from contextlib import asynccontextmanager

# Настройка логирования: Консоль + Файл
logger = logging.getLogger("sentinel-ai")
logger.setLevel(logging.INFO)
handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler("audit.log")]
for h in handlers:
    h.set_formatter(logging.Formatter('%(message)s'))
    logger.addHandler(h)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        sentinel_core.load_policies("core/policies.yaml")
        logger.info(json.dumps({"event": "startup", "status": "ready"}))
    except Exception as e:
        logger.error(json.dumps({"event": "startup_error", "error": str(e)}))
    yield

app = FastAPI(title="SentinelAI v3.0: Forensic Platform", lifespan=lifespan)

@app.post("/v1/system/reload")
async def reload_config(x_admin_token: str = Header(None)):
    if x_admin_token != "admin_secret_reload_token":
        raise HTTPException(status_code=403, detail="Invalid token")
    msg = sentinel_core.load_policies("core/policies.yaml")
    logger.info(json.dumps({"event": "reload", "message": msg}))
    return {"status": "ok", "detail": msg}

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401)

    tx_id = str(uuid.uuid4())
    context = {
        "risk_score": float(payload.get("risk", 0.6)),
        "amount": float(payload.get("amount", 0.0)),
        "country": str(payload.get("country", "unknown")),
        "is_new": payload.get("user_tier") == "new"
    }

    result = sentinel_core.fast_evaluate(tool_name="transfer_funds", context=context)

    for t in result.traces:
        logger.info(json.dumps({
            "tx_id": tx_id,
            "event": "policy_match",
            "policy_id": t.policy_id,
            "matched": t.matched,
            "mode": "enforce" if "Enforce" in str(t.mode) else "shadow",
            "field": t.attr_key,
            "actual": str(t.actual) if t.actual else None
        }))

    return {
        "status": "SUCCESS" if result.decision == sentinel_core.Decision.Allow else "DENIED",
        "tx_id": tx_id,
        "version": result.version,
        "audit": [{"id": t.policy_id, "matched": t.matched} for t in result.traces if t.matched]
    }
