# main.py
import interpreters # High-performance Python 3.14 feature
from fastapi import FastAPI, Header, HTTPException
from core.sub_manager import SubinterpreterManager
from execution.policy_engine import ActionFirewall

app = FastAPI(title="SentinelAI v3.0: Control Plane")

@app.post("/v1/agent/execute")
async def handle_agent_request(payload: dict, x_agent_token: str = Header("default_token")):
    """
    Main entry point for AI Agent Governance.
    Orchestrates identity, parallel scrubbing, and action firewall.
    """
    
    # 1. Identity Layer (Simulation of JWT/RBAC)
    # In a real bank, this would be a verified identity from a secure token.
    agent_identity = {
        "id": "bot_01", 
        "permissions": ["read_balance", "summarize", "get_history"]
    } 
    
    # 2. Shield Layer (Input): High-Performance Parallel Scrubbing
    # GENIUS MOVE: We use the 3.14 SubinterpreterManager to run PII 
    # detection on a separate CPU core to keep the main API thread fast.
    clean_prompt = SubinterpreterManager.run_task(
        module_path="security.pii_scrub", 
        function_name="scrub_pii", 
        data=payload.get('prompt', '')
    )

    # 3. Execution Layer (Action Firewall): Intent Validation
    # We don't trust the LLM's output; we validate its intent against the policy.
    firewall = ActionFirewall(agent_identity)
    
    tool_calls = payload.get("tool_calls", [])
    for tool_call in tool_calls:
        auth_status = firewall.validate_action(tool_call)
        if auth_status["decision"] == "DENIED":
            # Log the violation and block immediately.
            return {
                "status": "BLOCKED", 
                "error": auth_status["reason"],
                "security_layer": "SentinelAI Action Firewall"
            }

    # 4. Success Path
    return {
        "status": "SUCCESS",
        "scrubbed_content": clean_prompt,
        "authorized_actions": [t.get("name") for t in tool_calls],
        "engine_metrics": {
            "parallel_processing": "Enabled (Python 3.14)",
            "security_check": "Passed",
            "timestamp": "2026-04-01"
        }
    }
