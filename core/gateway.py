import sentinel_core
import logging
import sys
import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, Protocol
from fastapi import FastAPI, Header, HTTPException, Body
from contextlib import asynccontextmanager

# --- 1. CONFIGURATION & LOGGING ---
logger = logging.getLogger("sentinel-ai")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler("audit.log")]
    for h in handlers:
        h.set_formatter(logging.Formatter('%(message)s'))
        logger.addHandler(h)

# --- 2. ARCHITECTURE: CONTEXT LAYER ---
@dataclass
class Context:
    """Паспорт транзакции: единственный источник правды в системе."""
    tx_id: str
    timestamp: datetime
    raw_payload: Dict[str, Any]
    
    # Domain Data (Очищенные данные для бизнеса)
    amount: float = 0.0
    country: str = "unknown"
    risk_score: float = 0.0
    user_tier: str = "standard"
    
    # Engine Results
    decision: Optional[str] = None
    policy_id: Optional[str] = None
    version: str = "unknown"
    traces: List[Any] = field(default_factory=list)
    
    # Control
    errors: List[str] = field(default_factory=list)

class ContextFactory:
    """Фабрика для создания контекста из входящего запроса."""
    @staticmethod
    def from_http(payload: Dict[str, Any]) -> Context:
        return Context(
            tx_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            raw_payload=payload,
            amount=float(payload.get("amount", 0.0)),
            country=str(payload.get("country", "unknown")),
            risk_score=float(payload.get("risk", 0.6)),
            user_tier=str(payload.get("user_tier", "standard"))
        )

# --- 3. ARCHITECTURE: PIPELINE STAGES ---
class PipelineStage(Protocol):
    async def process(self, ctx: Context) -> Context:
        ...

class RustEvaluationStage:
    """Этап вызова высокопроизводительного ядра Sentinel Core (Rust)."""
    async def process(self, ctx: Context) -> Context:
        # Маппинг контекста в формат, который ожидает Rust
        rust_ctx = {
            "amount": ctx.amount,
            "country": ctx.country,
            "risk_score": ctx.risk_score,
            "is_new": ctx.user_tier == "new"
        }
        
        result = sentinel_core.fast_evaluate(tool_name="transfer_funds", context=rust_ctx)
        
        # Обогащаем контекст результатами из ядра
        ctx.decision = "SUCCESS" if result.decision == sentinel_core.Decision.Allow else "DENIED"
        ctx.policy_id = result.policy_id
        ctx.version = result.version
        ctx.traces = result.traces
        return ctx

class ForensicAuditStage:
    """Этап записи доказательной базы в аудит-лог."""
    async def process(self, ctx: Context) -> Context:
        for t in ctx.traces:
            logger.info(json.dumps({
                "tx_id": ctx.tx_id,
                "event": "policy_match",
                "timestamp": ctx.timestamp.isoformat(),
                "policy_id": t.policy_id,
                "matched": t.matched,
                "mode": "enforce" if "Enforce" in str(t.mode) else "shadow",
                "field": t.attr_key,
                "actual": str(t.actual) if t.actual else None,
                "expected": str(t.expected)
            }))
        return ctx

# --- 4. ARCHITECTURE: PIPELINE ORCHESTRATOR ---
class SentinelPipeline:
    def __init__(self):
        self.stages: List[PipelineStage] = [
            RustEvaluationStage(),
            ForensicAuditStage()
        ]

    async def execute(self, ctx: Context) -> Context:
        for stage in self.stages:
            try:
                ctx = await stage.process(ctx)
            except Exception as e:
                ctx.errors.append(f"Error in stage {stage.__class__.__name__}: {str(e)}")
                break
        return ctx

# --- 5. API INTERFACE ---
pipeline = SentinelPipeline()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        sentinel_core.load_policies("core/policies.yaml")
        logger.info(json.dumps({"event": "startup", "status": "ready"}))
    except Exception as e:
        logger.error(json.dumps({"event": "startup_error", "error": str(e)}))
    yield

app = FastAPI(title="SentinelAI v3.0: Pipeline Edition", lifespan=lifespan)

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

    # 1. Инкапсуляция: создаем контекст через фабрику
    ctx = ContextFactory.from_http(payload)
    
    # 2. Оркестрация: запускаем pipeline
    ctx = await pipeline.execute(ctx)
    
    # 3. Обработка ошибок pipeline
    if ctx.errors:
        logger.error(json.dumps({"tx_id": ctx.tx_id, "errors": ctx.errors}))
        raise HTTPException(status_code=500, detail="Internal processing error")

    # 4. Ответ клиенту
    return {
        "status": ctx.decision,
        "tx_id": ctx.tx_id,
        "version": ctx.version,
        "policy": ctx.policy_id,
        "audit": [{"id": t.policy_id, "matched": t.matched} for t in ctx.traces if t.matched]
    }
