use pyo3::prelude::*;
use serde::{Serialize, Deserialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum AttrValue {
    Float(f32),
    Str(String),
    Bool(bool),
}

impl<'source> FromPyObject<'source> for AttrValue {
    fn extract_bound(ob: &Bound<'source, PyAny>) -> PyResult<Self> {
        if let Ok(val) = ob.extract::<f32>() {
            Ok(AttrValue::Float(val))
        } else if let Ok(val) = ob.extract::<String>() {
            Ok(AttrValue::Str(val))
        } else if let Ok(val) = ob.extract::<bool>() {
            Ok(AttrValue::Bool(val))
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>("Unsupported type"))
        }
    }
}

#[pyclass]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ExecutionMode { Enforce, Shadow }

#[pyclass]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub enum Decision { Allow, Deny, Abstain }

// НОВАЯ СТРУКТУРА: Трассировка конкретного правила
#[pyclass]
#[derive(Clone, Serialize, Debug)]
pub struct EvaluationTrace {
    #[pyo3(get)] pub policy_id: String,
    #[pyo3(get)] pub matched: bool,
    #[pyo3(get)] pub attr_key: String,
    #[pyo3(get)] pub threshold: f32,
    #[pyo3(get)] pub actual_value: f32,
    #[pyo3(get)] pub mode: ExecutionMode,
}

#[pyclass]
#[derive(Clone)]
pub struct EvaluationResult {
    #[pyo3(get)] pub decision: Decision,
    #[pyo3(get)] pub policy_id: String,
    #[pyo3(get)] pub shadow_decision: Decision,
    #[pyo3(get)] pub shadow_policy_id: String,
    #[pyo3(get)] pub reason: String,
    #[pyo3(get)] pub version: String,
    #[pyo3(get)] pub traces: Vec<EvaluationTrace>, // Список всех проверок
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Policy {
    pub id: String,
    #[serde(rename = "tool")]
    pub tool_name: String,
    pub mode: ExecutionMode,
    pub attr_key: String,
    pub operator: String, 
    pub threshold: f32,
}

#[derive(Debug, Deserialize)]
pub struct PolicyConfig {
    pub version: String,
    pub policies: Vec<Policy>,
}
