use crate::models::{Decision, EvaluationResult, ExecutionMode, PolicyValue, EvaluationTrace};
use std::collections::HashMap;
use std::sync::Arc;

pub struct EvaluationEngine {
    pub snapshot: Arc<crate::store::PolicySnapshot>,
    pub version: String,
}

impl EvaluationEngine {
    pub fn evaluate(&self, tool_name: &str, context: &HashMap<String, PolicyValue>) -> EvaluationResult {
        let policies = match self.snapshot.by_tool.get(tool_name) {
            Some(p) => p,
            None => return self.default_deny("No policies found"),
        };

        let mut enforce_state = (Decision::Abstain, "default".to_string());
        let mut shadow_state = (Decision::Abstain, "default".to_string());
        let mut traces = Vec::new();

        for policy in policies {
            let actual_val = context.get(&policy.attr_key);
            
            let is_match = match (actual_val, &policy.value, policy.operator.as_str()) {
                (Some(PolicyValue::Float(a)), PolicyValue::Float(b), "gt") => a > b,
                (Some(PolicyValue::Float(a)), PolicyValue::Float(b), "lt") => a < b,
                (Some(PolicyValue::Str(a)), PolicyValue::Str(b), "eq") => a == b,
                (Some(PolicyValue::Str(a)), PolicyValue::Str(b), "contains") => a.contains(b),
                (Some(val), PolicyValue::List(list), "in") => list.contains(val),
                (Some(val), PolicyValue::List(list), "not_in") => !list.contains(val),
                _ => false, 
            };

            traces.push(EvaluationTrace {
                policy_id: policy.id.clone(),
                matched: is_match,
                attr_key: policy.attr_key.clone(),
                expected: policy.value.clone(),
                actual: actual_val.cloned(),
                mode: policy.mode,
            });

            let current_decision = if is_match { Decision::Deny } else { Decision::Allow };

            match policy.mode {
                ExecutionMode::Enforce => {
                    if enforce_state.0 != Decision::Deny {
                        enforce_state = (current_decision, policy.id.clone());
                    }
                }
                ExecutionMode::Shadow => {
                    if shadow_state.0 != Decision::Deny {
                        shadow_state = (current_decision, policy.id.clone());
                    }
                }
            }
        }

        EvaluationResult {
            decision: enforce_state.0,
            policy_id: enforce_state.1,
            shadow_decision: shadow_state.0,
            shadow_policy_id: shadow_state.1,
            reason: "Multi-type evaluation complete".to_string(),
            version: self.version.clone(),
            traces,
        }
    }

    fn default_deny(&self, reason: &str) -> EvaluationResult {
        EvaluationResult {
            decision: Decision::Deny,
            policy_id: "system".to_string(),
            shadow_decision: Decision::Deny,
            shadow_policy_id: "system".to_string(),
            reason: reason.to_string(),
            version: self.version.clone(),
            traces: Vec::new(),
        }
    }
}
