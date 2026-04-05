import sentinel_core  # Our jet engine is on Rust
from fastapi import FastAPI, Header, HTTPException
from security.pii_scrub import scrub_pii 
from contextlib import asynccontextmanager
from typing import Dict

# --- Policy Initialization (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This block is executed ONCE when the server starts.
Here, we synchronize our Rust core with the current rules.
    """
    try:
        # We fill the storage with policies (in the future, this will be a load from the database)
        sentinel_core.add_policy(id="pol_db_01", tool_name="db_write", priority=100)
        sentinel_core.add_policy(id="pol_api_01", tool_name="api_call", priority=50)
        sentinel_core.add_policy(id="pol_shell_01", tool_name="shell_exec", priority=1000)
        
        print("🛡️ [Sentinel] Rust Action Firewall initialized with active policies.")
    except Exception as e:
        print(f"❌ [Sentinel] Failed to initialize Rust Core: {e}")
    
    yield
    # Here you can specify the cleanup logic when the server is turned off

# --- Application ---
app = FastAPI(
    title="SentinelAI v3.0: Control Plane (Rust Powered)",
    lifespan=lifespan
)

# The global context (simulation of data from Redis/Auth Context)
GLOBAL_CONTEXT = {
    "risk_score": 0.4,
    "environment": "production"
}

@app.post("/v1/agent/execute")
async def handle_agent_request(payload: dict, x_agent_token: str = Header(None)):
    # 1. Identity Layer: Simple token verification
    if x_agent_token != "valid_secret_token":
        raise HTTPException(status_code=401, detail="Invalid Agent Token")

    # 2. Shield Layer (Input): Clearing personal data (PII)
    # Thanks to Rust, we save CPU resources and can do this in the main thread
    prompt = payload.get('prompt', '')
    clean_prompt = scrub_pii(prompt)

    # 3. Execution Layer (Rust Action Firewall): Работает «судья»
    tool_calls = payload.get("tool_calls", [])
    
    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        
        # Calling the Rust core (fast_evaluate method)
        # It runs in nanoseconds and does not block the GIL
        result = sentinel_core.fast_evaluate(
            tool_name=tool_name,
            risk=GLOBAL_CONTEXT["risk_score"]
        )

        # If the Rust verdict is DENY (Forbidden), we block the entire request instantly
        if result.decision == sentinel_core.Decision.Deny:
            return {
                "status": "DENIED",
                "policy_id": result.policy_id,
                "reason": result.reason,  # This will display the reason and processing time in ns
                "scrubbed_content": clean_prompt
            }

    # 4. Success Path: If all the checks are passed
    return {
        "status": "SUCCESS",
        "message": "Authorized by Sentinel Rust Core",
        "scrubbed_content": clean_prompt,
        "metrics": {
            "engine": "rust-core-v1",
            "eval_count": len(tool_calls),
            "latency_tier": "ultra-low-nanos"
        }
    }
