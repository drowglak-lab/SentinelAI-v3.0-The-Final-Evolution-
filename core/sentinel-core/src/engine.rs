use crate::models::{Decision, EvaluationResult, Policy, ExecutionMode, AttrValue};
use std::collections::HashMap;
use std::sync::Arc;

pub struct EvaluationEngine {
    pub snapshot: Arc<crate::store::PolicySnapshot>,
}

impl EvaluationEngine {
    pub fn evaluate(&self, tool_name: &str, context: &HashMap<String, AttrValue>) -> EvaluationResult {
        let policies = match self.snapshot.by_tool.get(tool_name) {
            Some(p) => p,
            None => return EvaluationResult {
                decision: Decision::Deny,
                policy_id: "system".to_string(),
                shadow_decision: Decision::Deny,
                shadow_policy_id: "system".to_string(),
                reason: "No policies found".to_string(),
            },
        };

        let mut enforce_state = (Decision::Abstain, "default".to_string());
        let mut shadow_state = (Decision::Abstain, "default".to_string());

        for policy in policies {
            // Ищем значение в контексте. Если нашли Float — сравниваем.
            let is_match = if let Some(AttrValue::Float(val)) = context.get(&policy.attr_key) {
                *val > policy.threshold
            } else {
                false
            };

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
            reason: "Context-aware evaluation complete".to_string(),
        }
    }
}
