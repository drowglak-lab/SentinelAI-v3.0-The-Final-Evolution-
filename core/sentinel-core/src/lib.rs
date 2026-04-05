use pyo3::prelude::*;
use std::sync::Arc;
use std::collections::HashMap;
use std::fs;
use chrono::Utc;

mod models;
mod store;
mod engine;
mod logger;

lazy_static::lazy_static! {
    static ref GLOBAL_STORE: store::PolicyStore = store::PolicyStore::new_empty();
    static ref LOGGER_TX: std::sync::mpsc::Sender<logger::AuditEntry> = logger::start_logger();
}

#[pyfunction]
fn load_policies(path: String) -> PyResult<String> {
    // 1. Читаем файл (если файла нет - падаем с ошибкой, не трогая память)
    let content = fs::read_to_string(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Read error: {}", e)))?;

    // 2. Валидация (Fail-safe): если YAML кривой, возвращаем ошибку Python
    let config: models::PolicyConfig = serde_yaml::from_str(&content)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("YAML Error: {}", e)))?;
    
    // 3. Обновление (Atomic-like update)
    GLOBAL_STORE.raw_store.clear();
    for policy in config.policies {
        GLOBAL_STORE.raw_store.insert(policy.id.clone(), Arc::new(policy));
    }

    // 4. Пересборка снимка памяти для быстрых вычислений
    GLOBAL_STORE.rebuild_snapshot();

    Ok(format!("SUCCESS: {} policies reloaded. Current version: {}", GLOBAL_STORE.raw_store.len(), config.version))
}

#[pyfunction]
#[pyo3(signature = (tool_name, context))]
fn fast_evaluate(tool_name: String, context: HashMap<String, models::AttrValue>) -> PyResult<models::EvaluationResult> {
    let start_time = std::time::Instant::now();
    let snapshot = GLOBAL_STORE.snapshot.load_full();
    let engine = engine::EvaluationEngine { snapshot };
    let result = engine.evaluate(&tool_name, &context);

    let risk_log = if let Some(models::AttrValue::Float(r)) = context.get("risk_score") { *r } else { 0.0 };

    let entry = logger::AuditEntry {
        timestamp: Utc::now().to_rfc3339(),
        tool: tool_name,
        risk: risk_log,
        decision: format!("{:?}", result.decision),
        shadow_decision: format!("{:?}", result.shadow_decision),
        is_diff: result.decision != result.shadow_decision,
        policy_id: result.policy_id.clone(),
        latency_ns: start_time.elapsed().as_nanos() as u64,
    };

    let _ = LOGGER_TX.send(entry);
    Ok(result)
}

#[pymodule]
fn sentinel_core(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<models::Decision>()?;
    m.add_class::<models::ExecutionMode>()?;
    m.add_class::<models::EvaluationResult>()?;
    m.add_function(wrap_pyfunction!(load_policies, m)?)?;
    m.add_function(wrap_pyfunction!(fast_evaluate, m)?)?;
    Ok(())
}
