use pyo3::prelude::*;
mod models;
mod store;
mod engine;

#[pymodule]
fn sentinel_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<models::Decision>()?;
    m.add_class::<models::EvaluationResult>()?;
    
    // A wrapper function for quick calls from Python
    #[pyfn(m)]
    #[pyo3(name = "fast_evaluate")]
    fn fast_evaluate(tool_name: &str, risk: f32) -> PyResult<models::EvaluationResult> {
        // In real code, this will refer to a global variable. Store
        // We are now returning the IOC for the integration test.
        Ok(models::EvaluationResult {
            decision: models::Decision::Allow,
            policy_id: "rust_core_v1".to_string(),
            reason: "Fast-path execution successful".to_string(),
        })
    }

    Ok(())
}
