import sentinel_core
import logging
import sys
import json
from fastapi import FastAPI, Header, HTTPException, Body
from contextlib import asynccontextmanager

# Импортируем нашу новую архитектуру
from core.app.context import ContextFactory
from core.app.stages import RustEvaluationStage, ForensicAuditStage
from core.app.pipeline import SentinelPipeline

# Настройка логирования
logger = logging.getLogger("sentinel-ai")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler("audit.log")]
    for h in handlers:
        h.set_Formatter(logging.Formatter('%(message)s'))
        logger.addHandler(h)

# Инициализируем конвейер
pipeline = SentinelPipeline([
    RustEvaluationStage(),
    ForensicAuditStage()
])

@asynccontextmanager
async def lifespan(app: FastAPI):
    sentinel_core.load_policies("core/policies.yaml")
    logger.info(json.dumps({"event": "startup", "status": "ready"}))
    yield

app = FastAPI(title="SentinelAI v3.0: Enterprise Pipeline", lifespan=lifespan)

@app.post("/v1/banking/transfer")
async def handle_transfer(payload: dict = Body(...), x_agent_token: str = Header(None)):
    if x_agent_token != "bank_secret_token":
        raise HTTPException(status_code=401)

    # 1. Создаем паспорт транзакции
    ctx = ContextFactory.from_http(payload)
    
    # 2. Прогоняем через Pipeline
    ctx = await pipeline.execute(ctx)
    
    # 3. Ответ
    if ctx.errors:
        raise HTTPException(status_code=500, detail=str(ctx.errors))

    return {
        "status": ctx.decision,
        "tx_id": ctx.tx_id,
        "policy": ctx.policy_id,
        "audit": [{"id": t.policy_id, "matched": t.matched} for t in ctx.traces if t.matched]
    }
