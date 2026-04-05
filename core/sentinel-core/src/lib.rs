use pyo3::prelude::*;
use std::sync::Arc;
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
#[pyo3(signature = (id, tool_name, priority, mode = models::ExecutionMode::Enforce))]
fn add_policy(id: String, tool_name: String, priority: u32, mode: models::ExecutionMode) -> PyResult<()> {
    let policy = Arc::new(models::Policy { id, tool_name, priority, mode });
    GLOBAL_STORE.raw_store.insert(policy.id.clone(), policy);
    GLOBAL_STORE.rebuild_snapshot();
    Ok(())
}

#[pyfunction]
#[pyo3(signature = (tool_name, risk))]
fn fast_evaluate(tool_name: String, risk: f32) -> PyResult<models::EvaluationResult> {
    let start_time = std::time::Instant::now();
    let snapshot = GLOBAL_STORE.snapshot.load_full();
    let engine = engine::EvaluationEngine { snapshot };
    let result = engine.evaluate(&tool_name, risk);
    let duration = start_time.elapsed().as_nanos() as u64;

    let entry = logger::AuditEntry {
        timestamp: Utc::now().to_rfc3339(),
        tool: tool_name,
        risk,
        decision: format!("{:?}", result.decision),
        shadow_decision: format!("{:?}", result.shadow_decision),
        is_diff: result.decision != result.shadow_decision,
        policy_id: result.policy_id.clone(),
        latency_ns: duration,
    };

    let _ = LOGGER_TX.send(entry);
    Ok(result)
}

#[pymodule]
fn sentinel_core(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<models::Decision>()?;
    m.add_class::<models::ExecutionMode>()?;
    m.add_class::<models::EvaluationResult>()?;
    m.add_function(wrap_pyfunction!(add_policy, m)?)?;
    m.add_function(wrap_pyfunction!(fast_evaluate, m)?)?;
    Ok(())
}
