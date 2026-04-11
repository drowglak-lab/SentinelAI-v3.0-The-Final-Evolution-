import httpx
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger("OPA_Client")

class CircuitBreakerOpenException(Exception):
    pass

class ResilientOPAClient:
    def __init__(self, opa_url: str):
        self.opa_url = opa_url
        self.client = httpx.AsyncClient(timeout=2.0) # Жесткий таймаут: финтех не ждет вечно
        
        # Состояние Circuit Breaker (Предохранитель)
        self.failure_count = 0
        self.failure_threshold = 3
        self.is_open = False
        self.recovery_timeout = 10 # Секунд до попытки "пропинговать" снова

    async def _trip_breaker(self):
        self.is_open = True
        logger.error("🚨 [Circuit Breaker] OPENED! OPA is unreachable. Failing fast.")
        await asyncio.sleep(self.recovery_timeout)
        logger.info("🔄 [Circuit Breaker] HALF-OPEN. Testing OPA availability...")
        self.is_open = False
        self.failure_count = 0

    async def evaluate_policy(self, payload: Dict[str, Any]) -> bool:
        if self.is_open:
            # Предохранитель сработал. Мы сразу отказываем (Fail-safe: deny by default),
            # не тратя время на ожидание мертвого сервиса.
            logger.warning("⛔ OPA request blocked by Circuit Breaker.")
            return False 

        try:
            # Делаем запрос к сайдкару OPA
            response = await self.client.post(
                f"{self.opa_url}/v1/data/sentinel/fintech/allow",
                json={"input": payload}
            )
            response.raise_for_status()
            
            result = response.json().get("result", False)
            self.failure_count = 0 # Сбрасываем счетчик ошибок при успехе
            return result

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            self.failure_count += 1
            logger.error(f"⚠️ OPA Communication Error ({self.failure_count}/{self.failure_threshold}): {e}")
            
            if self.failure_count >= self.failure_threshold:
                # Если ошибки повторяются, "размыкаем цепь" в фоновой задаче
                asyncio.create_task(self._trip_breaker())
            
            return False # Fail-safe: если движок политик недоступен, запрещаем транзакцию
