import sentinel_core
import json
import logging

logger = logging.getLogger("sentinel-ai")

class RustEvaluationStage:
    """Этап вызова высокоскоростного Rust-ядра"""
    async def process(self, ctx):
        # Передаём только то, что нужно Rust
        result = sentinel_core.fast_evaluate(
            tool_name="transfer_funds", 
            context=ctx.domain_data
        )
        
        ctx.decision = "SUCCESS" if result.decision == sentinel_core.Decision.Allow else "DENIED"
        ctx.policy_id = result.policy_id
        ctx.traces = result.traces
        ctx.version = result.version
        return ctx

class ForensicAuditStage:
    """Этап записи 'чёрного ящика' в audit.log"""
    async def process(self, ctx):
        for t in ctx.traces:
            logger.info(json.dumps({
                "tx_id": ctx.tx_id,
                "event": "policy_match",
                "policy_id": t.policy_id,
                "matched": t.matched,
                "field": t.attr_key,
                "actual": str(t.actual) if t.actual else None,
                "expected": str(t.expected)
            }))
        return ctx
