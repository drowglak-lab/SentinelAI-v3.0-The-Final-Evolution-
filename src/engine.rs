use crate::models::{Decision, EvaluationResult, Policy};
use std::sync::Arc;
use std::time::Instant;

pub struct EvaluationEngine {
    // Link to the current snapshot of reality
    pub snapshot: Arc<crate::store::PolicySnapshot>,
}

impl EvaluationEngine {
    pub fn evaluate(&self, tool_name: &str, context_risk: f32) -> EvaluationResult {
        let start = Instant::now();
        
        // 1. Looking for a policy tool (O(1))
        let policies = match self.snapshot.by_tool.get(tool_name) {
            Some(p) => p,
            None => return EvaluationResult {
                decision: Decision::Deny,
                policy_id: "system".to_string(),
                reason: "No policies found for this tool".to_string(),
            },
        };

        let mut final_decision = Decision::Abstain;
        let mut best_policy_id = "default".to_string();

        // 2. Running through the policies (Deny-Overrides)
        for policy in policies {
            // Imitation of logic: if the risk of context > the policy threshold - Deny
            if context_risk > 0.8 { // Hardcod for example, in the future DSL
                return EvaluationResult {
                    decision: Decision::Deny,
                    policy_id: policy.id.clone(),
                    reason: "Context risk threshold exceeded (Global Deny)".to_string(),
                };
            }

            // Priority logic
            if final_decision != Decision::Allow {
                final_decision = Decision::Allow;
                best_policy_id = policy.id.clone();
            }
        }

        let duration = start.elapsed().as_nanos();
        // In the Python logs, we will use this duration for the formula E
        
        EvaluationResult {
            decision: final_decision,
            policy_id: best_policy_id,
            reason: format!("Approved in {}ns", duration),
        }
    }
}
