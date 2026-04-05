from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Dict
import uuid

@dataclass
class Context:
    # Identity
    tx_id: str
    timestamp: datetime
    
    # Data Layers
    raw_payload: Dict[str, Any]
    domain_data: Dict[str, Any] = field(default_factory=dict)
    
    # Engine Results
    decision: Optional[str] = None
    policy_id: Optional[str] = None
    traces: list = field(default_factory=list)
    version: str = "unknown"
    
    # Control & Errors
    errors: list[str] = field(default_factory=list)

class ContextFactory:
    @staticmethod
    def from_http(payload: Dict[str, Any]) -> Context:
        # Здесь мы превращаем "грязный" JSON в чистый объект
        return Context(
            tx_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            raw_payload=payload,
            domain_data={
                "amount": float(payload.get("amount", 0.0)),
                "country": str(payload.get("country", "unknown")),
                "risk_score": float(payload.get("risk", 0.6)),
                "user_tier": str(payload.get("user_tier", "standard"))
            }
        )
