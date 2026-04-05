import sentinel_core
import json
import logging
import asyncio
import httpx
import hashlib
from datetime import datetime

# ⚡ НОВОЕ: Импортируем крипто-движок
from core.crypto_audit import MerkleManager

logger = logging.getLogger("sentinel-ai")

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ АУДИТА ---
AUDIT_BUFFER = []
AUDIT_LOCK = asyncio.Lock()
MAX_BUFFER_SIZE = 10000
FLUSH_THRESHOLD = 5

merkle_manager = MerkleManager()

async def flush_batch(batch: list):
    """Отправка цепочки в SIEM"""
    current_root = merkle_manager.build_merkle_root(batch)
    # Связываем текущий корень с предыдущим (Hash Chain)
    chain_hash = hashlib.sha256((merkle_manager.prev_root + current_root).encode()).hexdigest()
    
    payload = {
        "root_hash": chain_hash,
        "prev_hash": merkle_manager.prev_root,
        "timestamp": datetime.utcnow().isoformat(),
        "signature": merkle_manager.sign_hash(chain_hash)
    }
    
    merkle_manager.prev_root = chain_hash # Двигаем цепь вперед

    async with httpx.AsyncClient() as client:
        try:
            await client.post("http://127.0.0.1:9000/ingest", json=payload, timeout=2.0)
        except Exception as e:
            logger.error(f"❌ СБОЙ ДОСТАВКИ В SIEM: {e}. Переход в локальный WAL.")

async def periodic_flush():
    """Таймер: сбрасывает логи, если трафик редкий"""
    while True:
        await asyncio.sleep(3.0)
        async with AUDIT_LOCK:
            if AUDIT_BUFFER:
                batch = list(AUDIT_BUFFER)
                AUDIT_BUFFER.clear()
                asyncio.create_task(flush_batch(batch))


# --- СТАДИИ КОНВЕЙЕРА ---

class EnrichmentStage:
    async def process(self, ctx):
        mock_db = {
            "standard": {"kyc_status": "verified", "account_age_days": 365.0},
            "unverified": {"kyc_status": "pending", "account_age_days": 2.0},
        }
        user_tier = ctx.raw_payload.get("user_tier", "unverified")
        profile = mock_db.get(user_tier, {"kyc_status": "none", "account_age_days": 0.0})

        ctx.domain_data["kyc_status"] = profile["kyc_status"]
        ctx.domain_data["account_age_days"] = profile["account_age_days"]
        return ctx

class RustEvaluationStage:
    async def process(self, ctx):
        result = sentinel_core.fast_evaluate(
            tool_name="transfer_funds", 
            context=ctx.domain_data
        )
        ctx.decision = "SUCCESS" if result.decision == sentinel_core.Decision.Allow else "DENIED"
        ctx.policy_id = result.policy_id
        ctx.version = result.version
        ctx.traces = result.traces
        return ctx

class ExplainStage:
    async def process(self, ctx):
        if ctx.decision == "DENIED":
            for trace in ctx.traces:
                if trace.matched and "Enforce" in str(trace.mode):
                    reason = f"Сработало базовое правило блокировки: {trace.policy_id}"
                    
                    if trace.policy_id == "high_risk_block" or trace.policy_id == "spanish_high_risk_block":
                        country = ctx.domain_data.get('country')
                        amount = ctx.domain_data.get('amount')
                        reason = f"Высокий риск. Транзакция из региона '{country}' на сумму {amount} превышает допустимые лимиты дерева безопасности."
                    
                    elif trace.policy_id == "hidden_kyc_block":
                        status = ctx.domain_data.get('kyc_status')
                        reason = f"Теневая блокировка: ваш скрытый статус KYC '{status}' не позволяет совершать переводы на такую сумму. Пройдите верификацию."
                    
                    ctx.reasons.append(reason)
        return ctx

# ⚡ НОВОЕ: Полностью переписанный этап форензики
class ForensicAuditStage:
    async def process(self, ctx):
        event = {"tx_id": ctx.tx_id, "decision": ctx.decision, "policy": ctx.policy_id}
        event_hash = hashlib.sha256(json.dumps(event).encode()).hexdigest()
        
        async with AUDIT_LOCK: # Thread-safe операция
            if len(AUDIT_BUFFER) >= MAX_BUFFER_SIZE:
                # Backpressure: убиваем транзакцию, если буфер переполнен
                raise RuntimeError("Audit overflow! System fail-closed.")
                
            AUDIT_BUFFER.append(event_hash)
            
            if len(AUDIT_BUFFER) >= FLUSH_THRESHOLD:
                batch = list(AUDIT_BUFFER)
                AUDIT_BUFFER.clear()
                asyncio.create_task(flush_batch(batch))
                
        return ctx
