use std::collections::HashMap;
use std::sync::Arc;
use arc_swap::ArcSwap;

pub struct Policy {
    pub id: String,
    pub tool_name: String,
    pub priority: u32,
}

pub struct PolicySnapshot {
    pub by_tool: HashMap<String, Vec<Arc<Policy>>>,
}

pub struct PolicyStore {
    pub snapshot: ArcSwap<PolicySnapshot>,
}
