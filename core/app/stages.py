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
