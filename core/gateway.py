import sentinel_core  # Our new Rust engine
from fastapi import FastAPI, Header, HTTPException
from security.pii_scrub import scrub_pii # Leaving the quick version
from typing import Dict

app = FastAPI(title="SentinelAI v3.0: Control Plane (Rust Powered)")

# Initialize the context (in reality, this will come from the DB/Redis)
# At the current stage, we use a cached dictionary
GLOBAL_CONTEXT = {
    "risk_score": 0.4,
    "environment": "production"
}

@app.post("/v1/agent/execute")
async def handle_agent_request(payload: dict, x_agent_token: str = Header(None)):
    # 1. Identity Layer: Token verification (simplified)
    if x_agent_token != "valid_secret_token":
        raise HTTPException(status_code=401, detail="Invalid Agent Token")

    # 2. Shield Layer (Input): Cleaning PII
    # Now we're doing it directly in the main thread, because it's fast, 
    # the Rust engine freed up our CPU resources by removing the load from GIL.
    clean_prompt = scrub_pii(payload.get('prompt', ''))

    # 3. Execution Layer (Rust Action Firewall): The judge steps in
    # We check every tool call through our ultra-fast pipeline
    for tool_call in payload.get("tool_calls", []):
        tool_name = tool_call.get("name")
        
        # Calling the Rust core (fast_evaluate)
        # We pass the instrument name and risk level from our Context Builder
        result = sentinel_core.fast_evaluate(
            tool_name=tool_name,
            risk=GLOBAL_CONTEXT["risk_score"]
        )

        # If Rust-The judge said DENY — we block it instantly
        if result.decision == sentinel_core.Decision.Deny:
            return {
                "status": "DENIED",
                "policy_id": result.policy_id,
                "reason": result.reason,
                "scrubbed_content": clean_prompt
            }

    # 4. Success Path
    return {
        "status": "SUCCESS",
        "message": "Authorized by Sentinel Rust Core",
        "scrubbed_content": clean_prompt,
        "metrics": {
            "engine": "rust-v1",
            "latency_status": "sub-1ms-eval"
        }
    }
