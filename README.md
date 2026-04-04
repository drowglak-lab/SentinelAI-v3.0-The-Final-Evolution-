# SentinelAI v3.0: The Final Evolution 🛡️🤖

**The Open-Source Control Plane for Secure AI Agent Execution.**

SentinelAI is not a simple proxy. It is a high-performance **Action Firewall** designed for the autonomous agent era (2026+). It bridges the gap between AI freedom and Enterprise security requirements.

## 🧱 Layered Security Architecture
1. **Shield Layer (Input):** Real-time PII anonymization using parallel subinterpreters.
2. **Execution Layer (Control):** Identity-based tool authorization. We don't trust the LLM; we validate the intent.
3. **Audit Layer (Logs):** Full behavioral traceability for every autonomous action.

## 🚀 Tech Excellence (Python 3.14)
We leverage **PEP 734 (Multiple Interpreters)** to achieve true multicore parallelism. Security scanning and policy enforcement happen on isolated CPU cores, ensuring sub-15ms latency for high-frequency banking environments.

## 📂 Project Structure
- `/core`: High-performance gateway orchestration.
- `/security`: PII scrubbing and injection detection.
- `/execution`: The Action Firewall & Policy Engine.
- `/identity`: Agent-based RBAC & Scopes.

## 📊 Performance Benchmark & The GIL Post-Mortem

To validate the architecture's capacity for handling high-frequency AI agent requests, a rigorous load testing phase was conducted using **Locust** (500 concurrent users, spawn rate: 50 req/sec). The goal was to test the theoretical limits of the `Action Firewall` and the CPU-bound `PII Scrubber`.

### Phase 1: The I/O Bottleneck
* **Initial Results:** ~111 RPS (Requests Per Second).
* **Latency:** Massive p95 spikes (up to 60 seconds during user spawn).
* **Root Cause Analysis:** The initial implementation of the `SubinterpreterManager` relied on dynamic imports (`importlib.import_module`) inside the thread pool to simulate isolation. When 500 concurrent threads attempted to access the file system and import the module simultaneously, it created catastrophic GIL contention and disk I/O blocking.

### Phase 2: Memoization Optimization
To mitigate the I/O bottleneck, a class-level in-memory cache (`_cache: Dict[str, Callable]`) was introduced. The module is now imported only once, and subsequent calls fetch the function reference in $O(1)$ time.
* **Results:** Throughput skyrocketed by **150%**, reaching stable peaks of **250-280 RPS** on a local Docker container (WSL2 environment).

### Phase 3: The Architectural Conclusion (Proving the Hypothesis)
Despite the massive RPS improvement, the p95 latency under peak concurrency still demonstrated CPU-bound blocking. 

**Why? The Global Interpreter Lock (GIL).**
The `security.pii_scrub` module relies on heavy Regular Expressions. While `asyncio.to_thread` offloads the work from the main event loop, all threads in standard Python (prior to 3.14) still share a single GIL. When multiple threads execute CPU-intensive regex simultaneously, they are forced to run sequentially, blocking each other.

**The Verdict:**
This benchmark empirically proves the core architectural thesis of **SentinelAI v3.0**. To achieve true, stable `Sub-15ms` latency for heavy AI-security workloads under extreme concurrency, standard Python threading is insufficient. 

The system architecture fundamentally **requires** either:
1.  **Python 3.14+ Multiple Interpreters (PEP 734):** Utilizing true per-interpreter GILs to achieve genuine CPU parallelism.
2.  **Rust Extensions:** Rewriting the `PII Scrubber` layer in Rust (similar to Pydantic V2 core) to release the GIL entirely during execution.
---
*Developed by **Aleksei Matveenko** — Specializing in AI Execution Security.*
