from enum import Enum
from typing import List, Set

class AgentScope(str, Enum):
    """
    Granular permissions (Scopes) for AI Agents.
    Using Enums prevents typo-related security breaches.
    """
    # Read-only scopes (Low risk)
    READ_BALANCE = "account:read_balance"
    READ_HISTORY = "account:read_history"
    READ_MARKET_DATA = "market:read_data"
    
    # Mutating scopes (High risk)
    TRANSFER_FUNDS = "payment:transfer_funds"
    ISSUE_CARD = "card:issue"
    
    # Administrative/System scopes
    AUDIT_LOGS = "system:audit"

class AgentRole(str, Enum):
    """
    Predefined roles that group multiple scopes together.
    """
    BASIC_ASSISTANT = "role:basic_assistant"
    WEALTH_MANAGER = "role:wealth_manager"
    ADMIN_BOT = "role:admin_bot"

# Role-to-Scope Mapping
# This is our source of truth for what a role can actually do.
ROLE_PERMISSIONS = {
    AgentRole.BASIC_ASSISTANT: {
        AgentScope.READ_BALANCE,
        AgentScope.READ_HISTORY,
        AgentScope.READ_MARKET_DATA
    },
    AgentRole.WEALTH_MANAGER: {
        AgentScope.READ_BALANCE,
        AgentScope.READ_HISTORY,
        AgentScope.READ_MARKET_DATA,
        AgentScope.TRANSFER_FUNDS  # Requires additional ABAC checks in the firewall
    },
    AgentRole.ADMIN_BOT: {
        AgentScope.AUDIT_LOGS
    }
}

def resolve_agent_scopes(roles: List[str], custom_scopes: List[str] = None) -> Set[str]:
    """
    Compiles a final set of allowed scopes based on the agent's assigned roles 
    and any directly assigned custom scopes.
    """
    allowed_scopes = set()
    
    # Unpack permissions from assigned roles
    for role_str in roles:
        try:
            role = AgentRole(role_str)
            allowed_scopes.update(ROLE_PERMISSIONS.get(role, set()))
        except ValueError:
            # Log invalid role attempt but do not crash
            import logging
            logging.getLogger("sentinel_ai.identity").warning(f"Attempted to resolve invalid role: {role_str}")
            
    # Add any specific custom scopes (if applicable)
    if custom_scopes:
        for scope_str in custom_scopes:
            try:
                scope = AgentScope(scope_str)
                allowed_scopes.add(scope)
            except ValueError:
                pass # Ignore invalid scopes
                
    # Return as a set of string values for fast O(1) lookup in the Action Firewall
    return {scope.value for scope in allowed_scopes}
