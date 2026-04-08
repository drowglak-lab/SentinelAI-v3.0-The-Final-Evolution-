import random
import asyncio
import redis.asyncio as async_redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings
from sentinel_core import SentinelCore

# 1. КОНФИГУРАЦИЯ: Убираем хардкод
class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379"
    rocksdb_path: str = "/app/data/rocksdb"

settings = Settings()

# 2. ИНКАПСУЛЯЦИЯ СТЕЙТА: Никаких глобальных классов
class RecoveryState:
    def __init__(self):
        self.mode = "NORMAL"
        self.rate_limit = 1.0

async def sync_with_redis(redis_client: async_redis.Redis, state: RecoveryState):
    """Синхронизация теперь работает с переданными инстансами, а не глобальными переменными"""
    print("📡 Sentinel Sync: Connected to Redis Control Plane")
    while True:
        try:
            mode = await redis_client.get("sentinel:mode")
            rate = await redis_client.get("sentinel:rate_limit")
            
            if mode: state.mode = mode
            if rate: state.rate_limit = float(rate)
        except asyncio.CancelledError:
            # Корректное завершение задачи
            break
        except Exception as e:
            print(f"⚠️ Redis Sync Error: {e}")
        
        await asyncio.sleep(1)

# 3. УПРАВЛЕНИЕ ЖИЗНЕННЫМ ЦИКЛОМ (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте приложения создаем ресурсы и кладем в app.state
    app.state.core = SentinelCore(settings.rocksdb_path, settings.redis_url)
    app.state.redis = async_redis.from_url(settings.redis_url, decode_responses=True)
    app.state.recovery = RecoveryState()
    
    # Запускаем фоновую задачу
    app.state.sync_task = asyncio.create_task(
        sync_with_redis(app.state.redis, app.state.recovery)
    )
    yield  # Здесь приложение работает
    
    # При остановке (graceful shutdown) всё корректно закрываем
    app.state.sync_task.cancel()
    await app.state.redis.close()

app = FastAPI(title="SentinelAI v3.0 - Enterprise Edition", lifespan=lifespan)

# 4. MIDDLEWARE
@app.middleware("http")
async def security_gate(request: Request, call_next):
    # Получаем доступ к стейту через объект запроса
    core: SentinelCore = request.app.state.core
    state: RecoveryState = request.app.state.recovery

    if core.is_frozen() or state.mode == "FROZEN":
        return JSONResponse(
            status_code=503,
            content={"detail": "SYSTEM_FROZEN", "reason": "Integrity Breach or Manual Emergency"}
        )

    if state.mode == "READ_ONLY" and request.method != "GET":
        return JSONResponse(
            status_code=403,
            content={"detail": "SYSTEM_READ_ONLY", "message": "Write operations are disabled"}
        )

    if state.mode == "RAMP_UP":
        if random.random() > state.rate_limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "RECOVERY_RAMP_UP", "allowed_rate": f"{state.rate_limit * 100}%"}
            )

    return await call_next(request)

# 5. DEPENDENCY INJECTION
def get_sentinel_core(request: Request) -> SentinelCore:
    """Провайдер зависимости для маршрутов"""
    return request.app.state.core

@app.post("/v1/banking/transfer")
async def handle_transfer(data: dict, core: SentinelCore = Depends(get_sentinel_core)):
    # Теперь мы получаем core из параметров функции, а не из воздуха!
    tx_id = data.get("tx_id", "default_id")
    tx_hash = data.get("tx_hash", "default_hash")

    is_valid = core.audit_and_verify(tx_id, tx_hash)

    if not is_valid:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": "INTEGRITY_MISMATCH", "action": "LOCAL_FREEZE_TRIGGERED"}
        )

    return {
        "status": "success", 
        "tx_id": tx_id,
        "audit_hash": tx_hash,
        "engine": "Rust-RocksDB-Enforcer"
    }
