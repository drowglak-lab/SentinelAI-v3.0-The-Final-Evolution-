import random
import asyncio
import redis.asyncio as async_redis
from enum import Enum
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from sentinel_core import SentinelCore
from execution.policy_engine import PolicyEngine

# 💥 ИМПОРТИРУЕМ НАШ НОВЫЙ FINTECH MIDDLEWARE
from core.idempotency import FinTechIdempotencyMiddleware

# ==========================================
# 1. КОНФИГУРАЦИЯ И СТРОГИЕ ТИПЫ
# ==========================================
class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379"
    rocksdb_path: str = "/app/data/rocksdb"

settings = Settings()

class SystemMode(str, Enum):
    NORMAL = "NORMAL"
    FROZEN = "FROZEN"
    READ_ONLY = "READ_ONLY"
    RAMP_UP = "RAMP_UP"

class RecoveryState:
    def __init__(self):
        self.mode = SystemMode.NORMAL
        self.rate_limit = 1.0

class TransferRequest(BaseModel):
    tx_id: str = Field(..., description="Уникальный ID транзакции")
    tx_hash: str = Field(..., description="Хэш данных для проверки в Rust")
    role: str = Field(default="USER", description="Роль инициатора")
    amount: float = Field(..., gt=0, description="Сумма перевода")
    target: str = Field(..., description="Счет назначения")

# ==========================================
# 2. ФОНОВЫЕ ПРОЦЕССЫ
# ==========================================
async def sync_with_redis(redis_client: async_redis.Redis, state: RecoveryState):
    print("📡 Sentinel Sync: Connected to Redis Control Plane")
    while True:
        try:
            mode_val = await redis_client.get("sentinel:mode")
            rate_val = await redis_client.get("sentinel:rate_limit")
            
            if mode_val: 
                try:
                    state.mode = SystemMode(mode_val)
                except ValueError:
                    pass 
            if rate_val: 
                state.rate_limit = float(rate_val)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"⚠️ Redis Sync Error: {e}")
        await asyncio.sleep(1)

# ==========================================
# 3. GLOBAL CONNECTIONS & LIFECYCLE
# ==========================================
# Создаем глобальный пул соединений Redis ДО старта приложения
shared_redis_client = async_redis.from_url(settings.redis_url, decode_responses=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.core = SentinelCore(settings.rocksdb_path, settings.redis_url)
    app.state.redis = shared_redis_client # Используем уже созданный пул
    app.state.recovery = RecoveryState()
    
    app.state.policy_engine = PolicyEngine("config/policies.yaml")
    
    app.state.sync_task = asyncio.create_task(
        sync_with_redis(app.state.redis, app.state.recovery)
    )
    yield
    
    app.state.sync_task.cancel()
    try:
        await app.state.sync_task
    except asyncio.CancelledError:
        pass
    await app.state.redis.close()

app = FastAPI(title="SentinelAI v3.0 - Enterprise Edition", lifespan=lifespan)

# ==========================================
# 4. MIDDLEWARE CHAIN (Порядок имеет значение!)
# ==========================================

# Сначала проверяем идемпотентность (защита от двойных трат)
# strict_mode=False позволяет пропускать запросы без ключа во время тестов, 
# в реальном проде ставится True
app.add_middleware(
    FinTechIdempotencyMiddleware, 
    redis_client=shared_redis_client, 
    strict_mode=False 
)

# Затем наша самописная L1 защита (Ramp-Up, Frozen)
@app.middleware("http")
async def security_gate(request: Request, call_next):
    # Пропускаем запросы без состояния (на случай если идемпотентность отбила их раньше)
    if not hasattr(request.app.state, "recovery"):
         return await call_next(request)

    core: SentinelCore = request.app.state.core
    state: RecoveryState = request.app.state.recovery

    if core.is_frozen() or state.mode == SystemMode.FROZEN:
        return JSONResponse(status_code=503, content={"detail": "SYSTEM_FROZEN"})

    if state.mode == SystemMode.READ_ONLY and request.method != "GET":
        return JSONResponse(status_code=403, content={"detail": "SYSTEM_READ_ONLY"})

    if state.mode == SystemMode.RAMP_UP:
        if random.random() > state.rate_limit:
            return JSONResponse(status_code=429, content={"detail": "RECOVERY_RAMP_UP"})

    return await call_next(request)

# ==========================================
# 5. DEPENDENCY INJECTION & ENDPOINTS
# ==========================================
def get_sentinel_core(request: Request) -> SentinelCore:
    return request.app.state.core

def get_policy_engine(request: Request) -> PolicyEngine:
    return request.app.state.policy_engine

@app.post("/v1/banking/transfer")
async def handle_transfer(
    req: TransferRequest, 
    core: SentinelCore = Depends(get_sentinel_core),
    policy_engine: PolicyEngine = Depends(get_policy_engine)
):
    is_allowed, reason = policy_engine.evaluate(
        action="transfer_funds",
        role=req.role,
        context={"amount": req.amount, "target": req.target}
    )
    
    if not is_allowed:
        return JSONResponse(status_code=403, content={"status": "error", "detail": "POLICY_DENIED", "reason": reason})

    is_valid = core.audit_and_verify(req.tx_id, req.tx_hash)

    if not is_valid:
        return JSONResponse(status_code=400, content={"status": "error", "detail": "INTEGRITY_MISMATCH"})

    # Добавляем небольшую задержку, чтобы в тестах было легче поймать гонку данных
    await asyncio.sleep(0.5)

    return {
        "status": "success", 
        "tx_id": req.tx_id,
        "audit_hash": req.tx_hash,
        "engine": "Dynamic-Policy + Rust-RocksDB-Enforcer"
    }
