use pyo3::prelude::*;
use std::sync::Arc;
use arc_swap::ArcSwap;
use chrono::Utc;

mod models;
mod store;
mod engine;
mod logger; // Подключаем твой новый модуль

// Глобальные статические переменные
lazy_static::lazy_static! {
    // Хранилище политик
    static ref GLOBAL_STORE: store::PolicyStore = store::PolicyStore::new_empty();
    
    // Канал логгера. Запускается один раз и живет вечно.
    static ref LOGGER_TX: std::sync::mpsc::Sender<logger::AuditEntry> = logger::start_logger();
}

#[pymodule]
fn sentinel_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<models::Decision>()?;
    m.add_class::<models::EvaluationResult>()?;
    
    #[pyfn(m)]
    #[pyo3(name = "add_policy")]
    fn add_policy(id: String, tool_name: String, priority: u32) -> PyResult<()> {
        let policy = Arc::new(models::Policy { id, tool_name, priority });
        GLOBAL_STORE.raw_store.insert(policy.id.clone(), policy);
        GLOBAL_STORE.rebuild_snapshot();
        Ok(())
    }

    #[pyfn(m)]
    #[pyo3(name = "fast_evaluate")]
    fn fast_evaluate(tool_name: &str, risk: f32) -> PyResult<models::EvaluationResult> {
        let start_time = std::time::Instant::now();

        // 1. Получаем решение от движка
        let snapshot = GLOBAL_STORE.snapshot.load_full();
        let engine = engine::EvaluationEngine { snapshot };
        let result = engine.evaluate(tool_name, risk);

        let duration = start_time.elapsed().as_nanos() as u64;

        // 2. Asynchronous logging (Non-blocking)
        // Мы просто копируем данные и "бросаем" их в канал. 
        // Это занимает считанные наносекунды.
        let entry = logger::AuditEntry {
            timestamp: Utc::now().to_rfc3339(),
            tool: tool_name.to_string(),
            risk,
            decision: format!("{:?}", result.decision),
            policy_id: result.policy_id.clone(),
            latency_ns: duration,
        };

        // Игнорируем ошибку отправки, чтобы не уронить основной поток, 
        // если логгер вдруг перегружен (хотя mpsc::channel это проглотит)
        let _ = LOGGER_TX.send(entry);

        Ok(result)
    }

    Ok(())
}
