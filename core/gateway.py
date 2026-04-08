import time
import random
from fastapi import FastAPI, HTTPException, Request
from sentinel_core import SentinelCore

app = FastAPI(title="SentinelAI v3.0 - The Final Evolution")

# Инициализация ядра (Путь внутри контейнера)
core = SentinelCore("/app/data/rocksdb", "redis://redis:6379")

class RecoveryState:
    MODE = "NORMAL"  # NORMAL, FROZEN, READ_ONLY, RAMP_UP
    RATE_LIMIT = 1.0

@app.middleware("http")
async def security_gate(request: Request, call_next):
    # 1. Мгновенная проверка Kill-Switch
    if core.is_frozen() or RecoveryState.MODE == "FROZEN":
        raise HTTPException(status_code=503, detail="SYSTEM_FROZEN: Integrity Breach")

    # 2. Режим Read-Only (для фазы после разморозки)
    if RecoveryState.MODE == "READ_ONLY" and request.method != "GET":
        raise HTTPException(status_code=403, detail="READ_ONLY_MODE: Maintenance")

    # 3. Ramp-Up (Адаптивный пропуск трафика)
    if RecoveryState.MODE == "RAMP_UP" and random.random() > RecoveryState.RATE_LIMIT:
        raise HTTPException(status_code=429, detail="RECOVERY_RAMP_UP: Limited Capacity")

    return await call_next(request)

@app.post("/v1/banking/transfer")
async def handle_transfer(data: dict):
    # Твоя логика из старого файла
    return {"status": "success", "audit_hash": "verified"}
