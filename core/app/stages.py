import sentinel_core
import json
import logging

logger = logging.getLogger("sentinel-ai")

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

# ⚡ НОВОЕ: XAI (Explainable AI) Stage
class ExplainStage:
    async def process(self, ctx):
        # Генерируем объяснение только если транзакция заблокирована
        if ctx.decision == "DENIED":
            for trace in ctx.traces:
                # Ищем сработавшее правило в режиме Enforce (боевом)
                if trace.matched and "Enforce" in str(trace.mode):
                    reason = f"Сработало базовое правило блокировки: {trace.policy_id}"
                    
                    # Кастомный маппинг для сложных правил (в будущем тут будет вызов LLM)
                    if trace.policy_id == "high_risk_block" or trace.policy_id == "spanish_high_risk_block":
                        country = ctx.domain_data.get('country')
                        amount = ctx.domain_data.get('amount')
                        reason = f"Высокий риск. Транзакция из региона '{country}' на сумму {amount} превышает допустимые лимиты дерева безопасности."
                    
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
