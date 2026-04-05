use std::fs::OpenOptions;
use std::io::Write;
use std::sync::mpsc::{self, Sender};
use std::thread;
use serde::Serialize;

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
        // Пытаемся открыть файл, если не выходит - пишем ошибку в stderr, но не вешаем поток
        let file_result = OpenOptions::new()
            .create(true)
            .append(true)
            .open("sentinel_audit.log");

        match file_result {
            Ok(mut file) => {
                while let Ok(entry) = rx.recv() {
                    if let Ok(json) = serde_json::to_string(&entry) {
                        if let Err(e) = writeln!(file, "{}", json) {
                            eprintln!("❌ [Logger] Failed to write to file: {}", e);
                        }
                    }
                }
            }
            Err(e) => eprintln!("❌ [Logger] Could not open log file: {}", e),
        }
    });

    tx
}
