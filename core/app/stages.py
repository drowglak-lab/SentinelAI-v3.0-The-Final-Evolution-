import sentinel_core
import json
import logging

logger = logging.getLogger("sentinel-ai")

# ⚡ НОВОЕ: Этап обогащения. Лезем в "базу данных" за скрытым профилем
class EnrichmentStage:
    async def process(self, ctx):
        # Имитация быстрого кэша (например, Redis)
        mock_db = {
            "standard": {"kyc_status": "verified", "account_age_days": 365.0},
            "unverified": {"kyc_status": "pending", "account_age_days": 2.0},
        }

        # Берем уровень пользователя из запроса
        user_tier = ctx.raw_payload.get("user_tier", "unverified")
        
        # Достаем его скрытый профиль (если не найден - считаем подозрительным)
        profile = mock_db.get(user_tier, {"kyc_status": "none", "account_age_days": 0.0})

        # Вшиваем секретные данные в доменные данные для Rust
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
                    
                    # ⚡ НОВОЕ: Объяснение для теневой блокировки
                    elif trace.policy_id == "hidden_kyc_block":
                        status = ctx.domain_data.get('kyc_status')
                        reason = f"Теневая блокировка: ваш скрытый статус KYC '{status}' не позволяет совершать переводы на такую сумму. Пройдите верификацию."
                    
                    ctx.reasons.append(reason)
        return ctx

class ForensicAuditStage:
    async def process(self, ctx):
        for t in ctx.traces:
            logger.info(json.dumps({
                "tx_id": ctx.tx_id,
                "event": "policy_match",
                "policy_id": t.policy_id,
                "matched": t.matched,
                "mode": "enforce" if "Enforce" in str(t.mode) else "shadow"
            }))
        return ctx
