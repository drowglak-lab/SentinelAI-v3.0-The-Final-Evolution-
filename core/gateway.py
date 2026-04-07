import sentinel_core
import logging
import sys
import json
import asyncio
from fastapi import FastAPI, Header, HTTPException, Body
from contextlib import asynccontextmanager

from core.app.context import ContextFactory
from core.app.stages import EnrichmentStage, RustEvaluationStage, ExplainStage, ForensicAuditStage, periodic_flush, retry_worker
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
        policy_hash = verify_policy_integrity()
        logger.info(json.dumps({"event": "security_check", "status": "passed", "policy_hash": policy_hash[:12]}))
        sentinel_core.load_policies("core/policies.yaml")
        
        # Запуск воркеров
        tasks = [asyncio.create_task(periodic_flush()), asyncio.create_task(retry_worker())]
        yield
        for t in tasks: t.cancel()
    except SecurityTamperingException as e:
        logger.error(json.dumps({"event": "FATAL_ERROR", "reason": str(e)}))
        raise RuntimeError("System halted.")

app = FastAPI(title="SentinelAI v3.0", lifespan=lifespan)

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token": raise HTTPException(status_code=401)
    ctx = await pipeline.execute(ContextFactory.from_http(payload))
    return {"status": ctx.decision, "tx_id": ctx.tx_id, "policy": ctx.policy_id, "reasons": ctx.reasons}
