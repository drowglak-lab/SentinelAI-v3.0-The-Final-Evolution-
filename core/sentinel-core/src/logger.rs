#[derive(Serialize)]
pub struct AuditEntry {
    pub timestamp: String,
    pub tool: String,
    pub risk: f32,
    pub decision: String,
    pub shadow_decision: String,
    pub is_diff: bool, // Показывает разницу между Enforce и Shadow
    pub policy_id: String,
    pub shadow_policy_id: String,
    pub latency_ns: u64,
}
