import sentinel_core  # Наш реактивный движок на Rust
from fastapi import FastAPI, Header, HTTPException
from security.pii_scrub import scrub_pii 
from contextlib import asynccontextmanager
from typing import Dict

# --- Инициализация политик (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Этот блок выполняется ОДИН РАЗ при запуске сервера.
    Здесь мы синхронизируем наше Rust-ядро с актуальными правилами.
    """
    try:
        # Наполняем хранилище политиками (в будущем это будет загрузка из БД)
        sentinel_core.add_policy(id="pol_db_01", tool_name="db_write", priority=100)
        sentinel_core.add_policy(id="pol_api_01", tool_name="api_call", priority=50)
        sentinel_core.add_policy(id="pol_shell_01", tool_name="shell_exec", priority=1000)
        
        print("🛡️ [Sentinel] Rust Action Firewall initialized with active policies.")
    except Exception as e:
        print(f"❌ [Sentinel] Failed to initialize Rust Core: {e}")
    
    yield
    # Здесь можно прописать логику очистки при выключении сервера

# --- Приложение ---
app = FastAPI(
    title="SentinelAI v3.0: Control Plane (Rust Powered)",
    lifespan=lifespan
)

# Глобальный контекст (имитация данных из Redis/Auth Context)
GLOBAL_CONTEXT = {
    "risk_score": 0.4,
    "environment": "production"
}

@app.post("/v1/agent/execute")
async def handle_agent_request(payload: dict, x_agent_token: str = Header(None)):
    # 1. Identity Layer: Простая проверка токена
    if x_agent_token != "valid_secret_token":
        raise HTTPException(status_code=401, detail="Invalid Agent Token")

    # 2. Shield Layer (Input): Очистка персональных данных (PII)
    # Благодаря Rust мы экономим ресурсы CPU и можем делать это в основном потоке
    prompt = payload.get('prompt', '')
    clean_prompt = scrub_pii(prompt)

    # 3. Execution Layer (Rust Action Firewall): Работает «судья»
    tool_calls = payload.get("tool_calls", [])
    
    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        
        # Вызываем Rust-ядро (метод fast_evaluate)
        # Он работает за наносекунды и не блокирует GIL
        result = sentinel_core.fast_evaluate(
            tool_name=tool_name,
            risk=GLOBAL_CONTEXT["risk_score"]
        )

        # Если вердикт Rust — DENY (Запрещено), блокируем весь запрос мгновенно
        if result.decision == sentinel_core.Decision.Deny:
            return {
                "status": "DENIED",
                "policy_id": result.policy_id,
                "reason": result.reason,  # Здесь будет причина и время обработки в нс
                "scrubbed_content": clean_prompt
            }

    # 4. Success Path: Если все проверки пройдены
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
