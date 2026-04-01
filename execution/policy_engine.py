# execution/policy_engine.py
class ActionFirewall:
    def __init__(self, agent_identity: dict):
        self.identity = agent_identity # Из JWT токена
        self.allowed_tools = agent_identity.get("permissions", [])

    def validate_action(self, tool_call: dict):
        """
        Проверка: может ли агент вызвать этот конкретный инструмент?
        """
        requested_tool = tool_call.get("name")
        
        if requested_tool not in self.allowed_tools:
            return {
                "decision": "DENIED",
                "reason": f"Security Violation: Agent {self.identity['id']} is not authorized for {requested_tool}"
            }
            
        # Дополнительная проверка на лимиты (например, сумма транзакции)
        if requested_tool == "transfer_funds" and tool_call['args']['amount'] > 10000:
             return {"decision": "DENIED", "reason": "Amount exceeds single-transaction limit."}

        return {"decision": "ALLOWED"}
