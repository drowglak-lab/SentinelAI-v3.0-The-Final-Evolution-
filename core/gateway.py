import random
from fastapi import FastAPI, HTTPException, Request
from sentinel_core import SentinelCore

app = FastAPI(title="SentinelAI v3.0")

# Инициализируем ядро (RocksDB будет лежать в /app/data/rocksdb)
core = SentinelCore("/app/data/rocksdb", "redis://redis:6379")

class RecoveryState:
    MODE = "NORMAL"  # NORMAL, FROZEN, READ_ONLY, RAMP_UP
    RATE_LIMIT = 1.0

@app.middleware("http")
async def security_gate(request: Request, call_next):
    # L0 Check
    if core.is_frozen() or RecoveryState.MODE == "FROZEN":
        raise HTTPException(status_code=503, detail="SYSTEM_FROZEN")

    # Read-Only phase
    if RecoveryState.MODE == "READ_ONLY" and request.method != "GET":
        raise HTTPException(status_code=403, detail="READ_ONLY_MODE")

    # Ramp-Up control
    if RecoveryState.MODE == "RAMP_UP" and random.random() > RecoveryState.RATE_LIMIT:
        raise HTTPException(status_code=429, detail="THROTTLED")

    return await call_next(request)

@app.post("/v1/banking/transfer")
async def handle_transfer(data: dict):
    return {"status": "success", "audit_hash": "verified"}
