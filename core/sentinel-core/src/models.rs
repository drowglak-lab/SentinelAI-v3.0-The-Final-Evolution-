use pyo3::prelude::*;

#[pyclass]
#[derive(Clone, Debug, PartialEq, Eq)] // PartialEq обязателен для сравнения в engine.rs
pub enum Decision {
    Allow,
    Deny,
    Abstain,
}

#[pyclass]
#[derive(Clone)]
pub struct EvaluationResult {
    #[pyo3(get)]
    pub decision: Decision,
    #[pyo3(get)]
    pub policy_id: String,
    #[pyo3(get)]
    pub reason: String,
}

#[pymethods]
impl EvaluationResult {
    #[new]
    pub fn new(decision: Decision, policy_id: String, reason: String) -> Self {
        EvaluationResult { decision, policy_id, reason }
    }
}

// Общая структура политики, которую будут использовать все модули
pub struct Policy {
    pub id: String,
    pub tool_name: String,
    pub priority: u32,
}
