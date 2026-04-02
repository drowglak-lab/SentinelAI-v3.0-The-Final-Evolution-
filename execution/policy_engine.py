import logging
from typing import Dict, Any

logger = logging.getLogger("sentinel_ai.firewall")

class ActionFirewall:
    """
    Action Firewall (Policy Engine) for AI Agents.
    Validates RBAC and ABAC constraints.
    """
    
    def __init__(self, agent_identity: Dict[str, Any]):
        self.agent_id = agent_identity.get("id", "unknown_agent")
        self.allowed_tools = set(agent_identity.get("permissions", []))
        
        self.policies = {
            "transfer_funds": {
                "max_amount_usd": 5000, 
                "blocked_prefixes": ["CRYPTO_", "DARK_"]
            }
        }

    def validate_action(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})

        # Layer 1: RBAC
        if tool_name not in self.allowed_tools:
            return {
                "decision": "DENIED", 
                "reason": f"Permission denied: Tool '{tool_name}' is unauthorized."
            }

        # Layer 2: ABAC (Dynamic Dispatch)
        validation_method = getattr(self, f"_validate_{tool_name}", self._default_validator)
        return validation_method(arguments)

    def _validate_transfer_funds(self, args: Dict[str, Any]) -> Dict[str, Any]:
        amount = args.get("amount", 0.0)
        target_account = args.get("target_account", "")

        max_allowed = self.policies["transfer_funds"]["max_amount_usd"]
        if amount > max_allowed:
            return {"decision": "DENIED", "reason": "Amount exceeds hard limit."}

        blocked_prefixes = self.policies["transfer_funds"]["blocked_prefixes"]
        if any(target_account.startswith(p) for p in blocked_prefixes):
            return {"decision": "DENIED", "reason": "Target account is blacklisted."}

        return {"decision": "ALLOWED"}

    def _default_validator(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"decision": "ALLOWED"}
