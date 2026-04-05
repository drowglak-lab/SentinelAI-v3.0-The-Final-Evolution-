use std::collections::HashMap;
use std::sync::Arc;
use arc_swap::ArcSwap;
use dashmap::DashMap;
use crate::models::Policy; // Importing from a neighboring module

pub struct PolicySnapshot {
    pub by_tool: HashMap<String, Vec<Arc<Policy>>>,
    pub version: u64,
}

pub struct PolicyStore {
    pub raw_store: DashMap<String, Arc<Policy>>,
    pub snapshot: ArcSwap<PolicySnapshot>,
}

impl PolicyStore {
    pub fn new_empty() -> Self {
        let empty_snapshot = Arc::new(PolicySnapshot {
            by_tool: HashMap::new(),
            version: 0,
        });
        Self {
            raw_store: DashMap::new(),
            snapshot: ArcSwap::new(empty_snapshot),
        }
    }

    pub fn rebuild_snapshot(&self) {
        let mut new_map: HashMap<String, Vec<Arc<Policy>>> = HashMap::new();
        
        for entry in self.raw_store.iter() {
            let policy = entry.value();
            new_map.entry(policy.tool_name.clone())
                   .or_insert_with(Vec::new)
                   .push(Arc::clone(policy));
        }

        let new_snapshot = PolicySnapshot {
            by_tool: new_map,
            version: self.snapshot.load().version + 1,
        };
        
        self.snapshot.store(Arc::new(new_snapshot));
    }
}
