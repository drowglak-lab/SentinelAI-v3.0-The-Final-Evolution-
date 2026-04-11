from typing import Dict, Any, Tuple
from security.opa_client import ResilientOPAClient

class DeterministicEnforcer:
    # 💥 Внедряем OPA клиент через Dependency Injection
    def __init__(self, db_conn, opa_client: ResilientOPAClient):
        self.db = db_conn
        self.opa = opa_client

    async def _get_trusted_beneficiary(self, user_id: str, beneficiary_uuid: str) -> dict:
        cursor = await self.db.execute("""
            SELECT account_iban, is_active, aml_risk_score, country_code 
            FROM approved_beneficiaries 
            WHERE id = ? AND owner_user_id = ?
        """, (beneficiary_uuid, user_id))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def validate_transfer_intent(self, user_id: str, ai_payload: Dict[str, Any]) -> Tuple[bool, str, dict]:
        target_uuid = ai_payload.get("target_beneficiary_id")
        amount = ai_payload.get("amount")

        if not target_uuid or not amount:
            return False, "MALFORMED_INTENT: Missing required fields", {}

        try:
            amount = float(amount)
        except ValueError:
            return False, "MALFORMED_INTENT: Invalid amount format", {}

        # 1. Достаем НАСТОЯЩИЕ данные о получателе из БД (защита от Semantic Gap)
        beneficiary = await self._get_trusted_beneficiary(user_id, target_uuid)
        
        if not beneficiary:
            return False, "SEMANTIC_VIOLATION: Unknown or unauthorized beneficiary ID", {}

        # 2. 💥 ГОТОВИМ КОНТЕКСТ ДЛЯ OPA (Policy-as-Code)
        opa_payload = {
            "action": "transfer_funds",
            "amount": amount,
            "beneficiary": {
                "is_active": beneficiary["is_active"],
                "aml_risk_score": beneficiary["aml_risk_score"],
                "country_code": beneficiary["country_code"]
            }
        }

        # 3. 🛡️ СПРАШИВАЕМ ОРАКУЛА (Через отказоустойчивый Circuit Breaker)
        is_allowed = await self.opa.evaluate_policy(opa_payload)

        if not is_allowed:
            return False, "POLICY_DENIED: OPA rejected the transaction or is unreachable", {}

        # 4. Формируем безопасный контекст для выполнения транзакции
        safe_execution_context = {
            "user_id": user_id,
            "amount": amount,
            "target_iban": beneficiary["account_iban"] 
        }

        return True, "INTENT_APPROVED", safe_execution_context
