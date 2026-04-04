use std::collections::HashMap;
use std::sync::Arc;
use arc_swap::ArcSwap;
use dashmap::DashMap; // Adding DashMap for thread-safe recording

// Policy description
pub struct Policy {
    pub id: String,
    pub tool_name: String,
    pub priority: u32,
}

// A snapshot of reality for quick reading (O(1))
pub struct PolicySnapshot {
    pub by_tool: HashMap<String, Vec<Arc<Policy>>>,
    pub version: u64,
}

// Main storage
pub struct PolicyStore {
    // Record layer: this is where we make changes from Python
    pub raw_store: DashMap<String, Arc<Policy>>,
    // Reading layer: this is where the engine gets data without locks
    pub snapshot: ArcSwap<PolicySnapshot>,
}

impl PolicyStore {
    // Creating an empty storage at startup
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

    // The "bridge" that turns raw data into a fast index
    pub fn rebuild_snapshot(&self) {
        let mut new_map: HashMap<String, Vec<Arc<Policy>>> = HashMap::new();
        
        // Group all policies by tool name
        for entry in self.raw_store.iter() {
            let policy = entry.value();
            new_map.entry(policy.tool_name.clone())
                   .or_insert_with(Vec::new)
                   .push(Arc::clone(policy));
        }

        // We atomically replace the old reality with a new one
        let new_snapshot = PolicySnapshot {
            by_tool: new_map,
            version: self.snapshot.load().version + 1,
        };
        
        self.snapshot.store(Arc::new(new_snapshot));
    }
}
