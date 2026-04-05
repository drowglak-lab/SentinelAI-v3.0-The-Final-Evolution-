use pyo3::prelude::*;
use std::collections::HashMap;

pub mod models;
pub mod engine;
pub mod store;

#[pyfunction]
fn load_policies(path: String) -> PyResult<String> {
    match store::POLICY_STORE.load_from_file(&path) {
        Ok(count) => Ok(format!("Loaded {} policies", count)),
        Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(e)),
    }
}

#[pyfunction]
fn fast_evaluate(tool_name: String, context: HashMap<String, models::PolicyValue>) -> PyResult<models::EvaluationResult> {
    let snapshot = store::POLICY_STORE.get_snapshot();
    
    let engine = engine::EvaluationEngine { 
        snapshot,
        version: "3.0".to_string() 
    };

    let _risk_log = if let Some(models::PolicyValue::Float(r)) = context.get("risk_score") { *r } else { 0.0 };

    Ok(engine.evaluate(&tool_name, &context))
}

#[pymodule]
fn sentinel_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<models::ExecutionMode>()?;
    m.add_class::<models::Decision>()?;
    m.add_class::<models::EvaluationTrace>()?;
    m.add_class::<models::EvaluationResult>()?;
    m.add_function(wrap_pyfunction!(load_policies, m)?)?;
    m.add_function(wrap_pyfunction!(fast_evaluate, m)?)?;
    Ok(())
}
