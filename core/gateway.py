import random
import asyncio
import redis.asyncio as async_redis
from fastapi import FastAPI, HTTPException, Request
from sentinel_core import SentinelCore

app = FastAPI(title="SentinelAI v3.0")

# Инициализируем ядро
core = SentinelCore("/app/data/rocksdb", "redis://redis:6379")

class RecoveryState:
    MODE = "NORMAL"  # Динамически меняется из Redis
    RATE_LIMIT = 1.0

async def sync_with_redis():
    """Фоновая задача: синхронизация состояния L1 (Redis) -> L0 (Локально)"""
    # Подключаемся к Redis внутри сети Docker
    r = async_redis.from_url("redis://redis:6379", decode_responses=True)
    print("📡 Sentinel Sync: Connected to Redis")
    
    while True:
        try:
            # Читаем режим и лимит
            mode = await r.get("sentinel:mode")
            rate = await r.get("sentinel:rate_limit")
            
            if mode:
                RecoveryState.MODE = mode
            if rate:
                RecoveryState.RATE_LIMIT = float(rate)
                
        except Exception as e:
            print(f"⚠️ Redis Sync Error: {e}")
        
        await asyncio.sleep(1)  # Проверка каждую секунду

@app.on_event("startup")
async def startup_event():
    # Запускаем синхронизацию как фоновую задачу при старте шлюза
    asyncio.create_task(sync_with_redis())

@app.middleware("http")
async def security_gate(request: Request, call_next):
    # 1. Мгновенный Kill-Switch (L0 из Rust + L1 из нашего стейта)
    if core.is_frozen() or RecoveryState.MODE == "FROZEN":
        raise HTTPException(status_code=503, detail="SYSTEM_FROZEN: Integrity Breach")

    # 2. Режим Read-Only
    if RecoveryState.MODE == "READ_ONLY" and request.method != "GET":
        raise HTTPException(status_code=403, detail="SYSTEM_READ_ONLY: Maintenance")

    # 3. Ramp-Up (Адаптивный пропуск трафика)
    if RecoveryState.MODE == "RAMP_UP":
        if random.random() > RecoveryState.RATE_LIMIT:
            raise HTTPException(status_code=429, detail="RECOVERY_RAMP_UP: Limited Capacity")

    return await call_next(request)

@app.post("/v1/banking/transfer")
async def handle_transfer(data: dict):
    return {"status": "success", "audit_hash": "verified"}
