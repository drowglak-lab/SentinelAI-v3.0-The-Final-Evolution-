use pyo3::prelude::*;
use serde::Serialize;

#[pyclass]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub enum ExecutionMode {
    Enforce,
    Shadow,
}

#[pyclass]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub enum Decision {
    Allow,
    Deny,
    Abstain,
}

#[pyclass]
#[derive(Clone)]
pub struct EvaluationResult {
    #[pyo3(get)] pub decision: Decision,
    #[pyo3(get)] pub policy_id: String,
    #[pyo3(get)] pub shadow_decision: Decision,
    #[pyo3(get)] pub shadow_policy_id: String,
    #[pyo3(get)] pub reason: String,
}

pub struct Policy {
    pub id: String,
    pub tool_name: String,
    pub priority: u32,
    pub mode: ExecutionMode,
}
