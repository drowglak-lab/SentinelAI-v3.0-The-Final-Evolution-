import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

app = FastAPI(title="SentinelAI: External SIEM Witness")

class RootHashPayload(BaseModel):
    root_hash: str
    prev_hash: str
    timestamp: str
    signature: str

CHAIN_STORAGE = []
PROCESSED_BATCHES = set()

# Загружаем публичный ключ шлюза
with open("core/public.pem", "rb") as key_file:
    PUBLIC_KEY = serialization.load_pem_public_key(key_file.read())

@app.post("/ingest")
async def ingest_root(data: RootHashPayload):
    # Защита от дублей
    if data.root_hash in PROCESSED_BATCHES:
        return {"status": "ignored", "reason": "replay_protection"}

    # Проверка подписи (SIEM валидирует SentinelAI)
    try:
        PUBLIC_KEY.verify(
            bytes.fromhex(data.signature),
            data.root_hash.encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
    except InvalidSignature:
        print(f"[SECURITY ALERT] Invalid signature for hash: {data.root_hash[:8]}")
        raise HTTPException(status_code=403, detail="Signature verification failed")

    # Проверка целостности цепи
    if CHAIN_STORAGE and data.prev_hash != CHAIN_STORAGE[-1]['root_hash']:
        raise HTTPException(status_code=409, detail="Hash chain broken")

    CHAIN_STORAGE.append(data.model_dump())
    PROCESSED_BATCHES.add(data.root_hash)
    print(f"[+] Verified Root: {data.root_hash[:12]} | Index: {len(CHAIN_STORAGE)}")
    return {"status": "accepted"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)
