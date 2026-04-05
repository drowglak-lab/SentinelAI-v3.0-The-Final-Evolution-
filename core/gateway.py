import sentinel_core
import logging
import sys
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, Header, HTTPException, Body, Request
from contextlib import asynccontextmanager

# Настройка профессионального логирования
logger = logging.getLogger("sentinel-ai")
logger.setLevel(logging.INFO)

# 1. Вывод в консоль (для разработки)
stream_handler = logging.StreamHandler(sys.stdout)
# 2. Сохранение в файл (для аудита и форензики)
file_handler = logging.FileHandler("audit.log")

formatter = logging.Formatter('%(message)s')
stream_handler.set_formatter(formatter)
file_handler.set_formatter(formatter)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        msg = sentinel_core.load_policies("core/policies.yaml")
        logger.info(json.dumps({
            "event": "system_startup",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "msg": msg
        }))
    except Exception as e:
        logger.error(json.dumps({"event": "system_failure", "error": str(e)}))
    yield

app = FastAPI(title="SentinelAI v3.0: Forensic Platform", lifespan=lifespan)

@app.post("/v1/system/reload")
async def reload_config(x_admin_token: str = Header(None)):
    if x_admin_token != "admin_secret_reload_token":
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    reload_id = str(uuid.uuid4())
    try:
        msg = sentinel_core.load_policies("core/policies.yaml")
        logger.info(json.dumps({
            "event": "policy_reload",
            "reload_id": reload_id,
            "timestamp": datetime.utcnow().isoformat(),
            "detail": msg
        }))
        return {"status": "ok", "reload_id": reload_id}
    except Exception as e:
        logger.error(json.dumps({"event": "reload_error", "reload_id": reload_id, "error": str(e)}))
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401)

    # Генерируем уникальный ID транзакции для связи всех логов
    tx_id = str(uuid.uuid4())
    
    context = {
        "risk_score": float(payload.get("risk", 0.6)),
        "amount": float(payload.get("amount", 0.0)),
        "is_new": payload.get("user_tier") == "new"
    }

    result = sentinel_core.fast_evaluate(tool_name="transfer_funds", context=context)

    # --- СТРУКТУРИРОВАННЫЙ АУДИТ В ФАЙЛ ---
    for t in result.traces:
        log_entry = {
            "tx_id": tx_id, # Тот самый паспорт транзакции
            "event": "policy_match",
            "timestamp": datetime.utcnow().isoformat(),
            "policy_id": t.policy_id,
            "version": result.version,
            "mode": "enforce" if "Enforce" in str(t.mode) else "shadow",
            "matched": t.matched,
            "evidence": {
                "field": t.attr_key,
                "actual": t.actual_value,
                "threshold": t.threshold
            }
        }
        logger.info(json.dumps(log_entry))

    # Логируем дрейф с полным контекстом
    if result.decision != result.shadow_decision:
        logger.warning(json.dumps({
            "tx_id": tx_id,
            "event": "logic_drift",
            "enforce": str(result.decision),
            "shadow": str(result.shadow_decision),
            "policy_id": result.shadow_policy_id,
            "context": context
        }))

    return {
        "status": "SUCCESS" if result.decision == sentinel_core.Decision.Allow else "DENIED",
        "tx_id": tx_id,
        "audit": [
            {
                "id": t.policy_id,
                "field": t.attr_key,
                "actual": t.actual_value,
                "expected": t.threshold
            } for t in result.traces if t.matched
        ]
    }
