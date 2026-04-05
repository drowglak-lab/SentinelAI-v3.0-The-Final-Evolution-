import sentinel_core
import logging
import sys
import json
from fastapi import FastAPI, Header, HTTPException, Body
from contextlib import asynccontextmanager

# Импортируем нашу новую архитектуру
from core.app.context import ContextFactory
from core.app.stages import EnrichmentStage, RustEvaluationStage, ExplainStage, ForensicAuditStage
from core.app.pipeline import SentinelPipeline

# ⚡ НОВОЕ: Импортируем наш модуль доверия
from core.trust import verify_policy_integrity, SecurityTamperingException

# Настройка логирования
logger = logging.getLogger("sentinel-ai")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler("audit.log")]
    for h in handlers:
        h.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(h)

# Встраиваем EnrichmentStage ПЕРЕД Rust-ядром
pipeline = SentinelPipeline([
    EnrichmentStage(),      # 1. Обогащаем скрытыми данными
    RustEvaluationStage(),  # 2. Вычисляем
    ExplainStage(),         # 3. Объясняем
    ForensicAuditStage()    # 4. Логируем
])

# ⚡ НОВОЕ: Жесткая проверка безопасности при старте
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # 1. Проверяем криптографическую подпись политик
        policy_hash = verify_policy_integrity()
        logger.info(json.dumps({"event": "security_check", "status": "passed", "policy_hash": policy_hash[:12]}))
        
        # 2. Только если проверка пройдена, грузим их в ядро
        sentinel_core.load_policies("core/policies.yaml")
        logger.info(json.dumps({"event": "startup", "status": "ready"}))
        yield
    except SecurityTamperingException as e:
        # HARD FAIL: убиваем процесс, если конфигурация скомпрометирована
        logger.error(json.dumps({"event": "FATAL_ERROR", "reason": str(e)}))
        raise RuntimeError("System halted due to security violation.")

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
        "reasons": ctx.reasons,
        "audit": [{"id": t.policy_id, "matched": t.matched} for t in ctx.traces if t.matched]
    }
