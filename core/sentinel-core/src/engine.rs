impl EvaluationEngine {
    pub fn evaluate(&self, tool_name: &str, context_risk: f32) -> EvaluationResult {
        let policies = match self.snapshot.by_tool.get(tool_name) {
            Some(p) => p,
            None => return self.default_deny("No policies"),
        };

        let mut enforce_dec = (Decision::Abstain, "default".to_string());
        let mut shadow_dec = (Decision::Abstain, "default".to_string());

        for policy in policies {
            let decision = if context_risk > 0.8 { Decision::Deny } else { Decision::Allow };

            match policy.mode {
                ExecutionMode::Enforce => {
                    // Логика Deny-Overrides для реального потока
                    if enforce_dec.0 != Decision::Deny {
                        enforce_dec = (decision, policy.id.clone());
                    }
                }
                ExecutionMode::Shadow => {
                    // Логика для теневого потока
                    if shadow_dec.0 != Decision::Deny {
                        shadow_dec = (decision, policy.id.clone());
                    }
                }
            }
            
            // Оптимизация: если в Enforce уже Deny, можно было бы выйти, 
            // но нам нужно докрутить Shadow до конца для чистоты лога.
        }

        EvaluationResult {
            decision: enforce_dec.0,
            policy_id: enforce_dec.1,
            shadow_decision: shadow_dec.0,
            shadow_policy_id: shadow_dec.1,
            reason: "Multi-pass evaluation complete".to_string(),
        }
    }
}
