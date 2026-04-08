import random
import asyncio
import redis.asyncio as async_redis
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse  # Импортируем для ручного формирования ответов
from sentinel_core import SentinelCore

app = FastAPI(title="SentinelAI v3.0")

# Инициализируем ядро (RocksDB)
core = SentinelCore("/app/data/rocksdb", "redis://redis:6379")

class RecoveryState:
    MODE = "NORMAL"
    RATE_LIMIT = 1.0

async def sync_with_redis():
    """Фоновая задача: синхронизация L1 (Redis) -> L0 (Локально)"""
    r = async_redis.from_url("redis://redis:6379", decode_responses=True)
    print("📡 Sentinel Sync: Connected to Redis")
    
    while True:
        try:
            mode = await r.get("sentinel:mode")
            rate = await r.get("sentinel:rate_limit")
            
            if mode:
                RecoveryState.MODE = mode
            if rate:
                RecoveryState.RATE_LIMIT = float(rate)
                
        except Exception as e:
            print(f"⚠️ Redis Sync Error: {e}")
        
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(sync_with_redis())

@app.middleware("http")
async def security_gate(request: Request, call_next):
    # 1. Мгновенный Kill-Switch (L0 + L1)
    # Используем JSONResponse вместо raise HTTPException для корректной работы в мидлвари
    if core.is_frozen() or RecoveryState.MODE == "FROZEN":
        return JSONResponse(
            status_code=503,
            content={"detail": "SYSTEM_FROZEN", "reason": "Integrity Breach Detected"}
        )

    # 2. Режим Read-Only
    if RecoveryState.MODE == "READ_ONLY" and request.method != "GET":
        return JSONResponse(
            status_code=403,
            content={"detail": "SYSTEM_READ_ONLY", "message": "Write operations are disabled"}
        )

    # 3. Ramp-Up (Адаптивный пропуск трафика)
    if RecoveryState.MODE == "RAMP_UP":
        if random.random() > RecoveryState.RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "RECOVERY_RAMP_UP", 
                    "message": "Request throttled due to system recovery",
                    "allowed_rate": f"{RecoveryState.RATE_LIMIT * 100}%"
                }
            )

    return await call_next(request)

@app.post("/v1/banking/transfer")
async def handle_transfer(data: dict):
    return {"status": "success", "audit_hash": "verified"}
