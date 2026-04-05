use std::fs::OpenOptions;
use std::io::Write;
use std::sync::mpsc::{self, Sender};
use std::thread;
use chrono::Utc;
use serde::Serialize;
use crate::models::Decision;

#[derive(Serialize)]
pub struct AuditEntry {
    pub timestamp: String,
    pub tool: String,
    pub risk: f32,
    pub decision: String,
    pub policy_id: String,
    pub latency_ns: u64,
}

pub fn start_logger() -> Sender<AuditEntry> {
    let (tx, rx) = mpsc::channel::<AuditEntry>();

    thread::spawn(move || {
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open("sentinel_audit.log")
            .unwrap();

        while let Ok(entry) = rx.recv() {
            if let Ok(json) = serde_json::to_string(&entry) {
                writeln!(file, "{}", json).unwrap();
            }
        }
    });

    tx
}
