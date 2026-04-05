use crate::models::{Decision, EvaluationResult, Policy, ExecutionMode};
use std::sync::Arc;

pub struct EvaluationEngine {
    pub snapshot: Arc<crate::store::PolicySnapshot>,
}

impl EvaluationEngine {
    pub fn evaluate(&self, tool_name: &str, context_risk: f32) -> EvaluationResult {
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
            // Имитация логики DSL (риск > 0.8 => Deny)
            let current_decision = if context_risk > 0.8 { Decision::Deny } else { Decision::Allow };

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
            reason: "Dual-mode evaluation complete".to_string(),
        }
    }
}
