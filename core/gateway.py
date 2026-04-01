# core/gateway.py
import interpreters # New in 3.14
from fastapi import FastAPI, Header
from execution.policy_engine import ActionFirewall

app = FastAPI(title="SentinelAI Control Plane")

@app.post("/v1/agent/execute")
async def handle_agent_request(payload: dict, x_agent_token: str = Header(None)):
    # 1. Identity Layer: Checking who it is (Scopes)
    # There will be a check in a real bank here JWT
    agent_identity = {"id": "bot_01", "permissions": ["read_db", "summarize"]} 
    
    # 2. Shield Layer (Input): Running the PII scrubber in a parallel kernel
    shield_interp = interpreters.create()
    shield_interp.run("from security.pii_scrub import scrub; scrub(data)", config={"data": payload['prompt']})
    clean_prompt = interpreters.get_main_channel().recv()

    # 3. Execution Layer (Action Firewall): Checking Intentions
    firewall = ActionFirewall(agent_identity)
    for tool_call in payload.get("tool_calls", []):
        auth_status = firewall.validate_action(tool_call)
        if auth_status["decision"] == "DENIED":
            return auth_status # We block immediately!

    # 4. If everything is clean, we send it to LLM
    return {"status": "SUCCESS", "message": "Action authorized and data secured."}
