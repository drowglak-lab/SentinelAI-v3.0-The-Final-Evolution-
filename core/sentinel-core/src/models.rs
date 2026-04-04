use pyo3::prelude::*;

#[pyclass]
#[derive(Clone, Debug)]
pub enum Decision {
    Allow,
    Deny,
    Abstain,
}

#[pyclass]
pub struct EvaluationResult {
    #[pyo3(get)]
    pub decision: Decision,
    #[pyo3(get)]
    pub policy_id: String,
    #[pyo3(get)]
    pub reason: String,
}

// We include support for methods so that objects are useful in Python
#[pymethods]
impl EvaluationResult {
    #[new]
    fn new(decision: Decision, policy_id: String, reason: String) -> Self {
        EvaluationResult { decision, policy_id, reason }
    }
}
