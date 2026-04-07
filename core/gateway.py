import sentinel_core
import logging
import sys
import json
import asyncio
import httpx  # Добавили для общения с SIEM
from fastapi import FastAPI, Header, HTTPException, Body
from contextlib import asynccontextmanager

from core.app.context import ContextFactory
# Добавили merkle_manager в импорт
from core.app.stages import (
    EnrichmentStage, RustEvaluationStage, ExplainStage, 
    ForensicAuditStage, periodic_flush, retry_worker, merkle_manager
)
from core.app.pipeline import SentinelPipeline
from core.trust import verify_policy_integrity, SecurityTamperingException

logger = logging.getLogger("sentinel-ai")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler("audit.log", encoding="utf-8")]
    for h in handlers:
        h.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(h)

pipeline = SentinelPipeline([EnrichmentStage(), RustEvaluationStage(), ExplainStage(), ForensicAuditStage()])

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # 1. Проверка целостности политик
        policy_hash = verify_policy_integrity()
        logger.info(json.dumps({"event": "security_check", "status": "passed", "policy_hash": policy_hash[:12]}))
        sentinel_core.load_policies("core/policies.yaml")
        
        # 2. ⚡ Синхронизация цепочки хэшей с SIEM
        async with httpx.AsyncClient() as client:
            try:
                # Спрашиваем у базы SIEM последний записанный корень
                response = await client.get("http://127.0.0.1:9000/latest", timeout=2.0)
                if response.status_code == 200:
                    latest_root = response.json().get("latest_root")
                    if latest_root and latest_root != "0" * 64:
                        # Устанавливаем хэш в менеджер, чтобы продолжить цепь
                        merkle_manager.prev_root = latest_root
                        logger.info(f"[SYNC] Chain resumed from SIEM state: {latest_root[:12]}")
                    else:
                        logger.info("[SYNC] SIEM is empty. Starting a new chain.")
            except Exception as e:
                logger.warning(f"[SYNC_FAILED] SIEM unreachable for sync: {e}. Starting from zero.")

        # 3. Запуск фоновых воркеров
        tasks = [
            asyncio.create_task(periodic_flush()), 
            asyncio.create_task(retry_worker())
        ]
        
        yield
        
        for t in tasks: 
            t.cancel()
            
    except SecurityTamperingException as e:
        logger.error(json.dumps({"event": "FATAL_ERROR", "reason": str(e)}))
        # Важно: система не должна запускаться при нарушении подписи
        raise RuntimeError("System halted due to integrity failure.")

app = FastAPI(title="SentinelAI v3.0", lifespan=lifespan)

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token": 
        raise HTTPException(status_code=401, detail="Unauthorized Agent")
    
    ctx = await pipeline.execute(ContextFactory.from_http(payload))
    return {
        "status": ctx.decision, 
        "tx_id": ctx.tx_id, 
        "policy": ctx.policy_id, 
        "reasons": ctx.reasons
    }
