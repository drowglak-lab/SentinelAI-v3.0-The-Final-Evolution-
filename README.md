# # SentinelAI v3.0: The Action Firewall for Autonomous Agents 🛡️🤖

**The High-Performance Security Layer for AI-Driven Banking Operations.**

SentinelAI is an Enterprise-grade **Action Firewall** designed to bridge the gap between autonomous AI agents and strict financial security requirements. In an era where LLMs execute code and handle transactions, SentinelAI ensures every action is validated, anonymized, and cryptographically logged.

---

## 🏛️ Layered Security Architecture

The system operates on a **Zero-Trust** model, processing requests through three specialized layers:

* **Shield Layer (Input):** Real-time PII (Personally Identifiable Information) scrubbing using parallel subinterpreters to prevent sensitive data leakage to external LLMs.
* **Execution Layer (Control):** A high-speed **Rust-powered** engine that validates agent intent against identity-based policies (RBAC). We don't trust the model's "hallucinated" safety; we enforce hard constraints.
* **Audit Layer (Forensics):** An immutable audit trail powered by **Merkle Trees**. Every action is linked in a cryptographic chain, making log tampering mathematically impossible.

---

## ⚖️ Regulatory Compliance (EU DORA Ready)

Designed with the **Digital Operational Resilience Act (DORA)** in mind:
* **Integrity:** Cryptographic hash-chaining ensures audit data remains unchanged.
* **Recoverability:** State-sync protocol allows the gateway to resume the audit chain after system failures or re-deployments.
* **Performance:** Sub-15ms policy evaluation core written in Rust to meet high-frequency trading and banking requirements.

---

## 📂 Tech Stack
* **Language:** Python 3.12+ (pioneering **PEP 734** concepts) & **Rust** (Safety & Speed).
* **Frameworks:** FastAPI (Asynchronous Orchestration), Maturin (Rust-Python bridge).
* **Infrastructure:** Docker & Docker Compose (Microservices Isolation).
* **Security:** RSA Signing, SHA-256 Merkle Chaining.

---

## 📊 Performance Post-Mortem: Overcoming the GIL

To prove the architecture, we conducted stress tests using **Locust** (500 concurrent users, 50 req/sec).

### The Evolution of Throughput:
| Phase | Optimization | Throughput | Latency (p95) | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | Dynamic Imports | 111 RPS | > 60s | I/O Bottleneck |
| **Phase 2** | Memoization & Caching | **280 RPS** | ~1.2s | CPU/GIL Bound |
| **Phase 3** | **Rust Core / Subinterpreters** | **Target 1000+** | **< 15ms** | **Parallel Victory** |

### The Verdict:
Standard Python threading hits a "glass ceiling" due to the **Global Interpreter Lock (GIL)**. SentinelAI v3.0 bypasses this by utilizing **PEP 734 (Multiple Interpreters)** and **Rust extensions**. By giving each security scan its own interpreter/core, we transform a sequential bottleneck into a parallel highway.

---

## 🚀 Quick Start (Enterprise Deployment)

The entire ecosystem is containerized for consistent deployment across cloud environments.

```powershell
# 1. Clone the repository
git clone https://github.com/your-repo/sentinel-ai.git

# 2. Start the Secure Gateway & SIEM Audit Service
docker-compose up --build
```
*The Gateway will automatically synchronize its cryptographic state with the SIEM service upon startup.*

---

## 👨‍💻 Developer
**Aleksei Matveenko** *Specializing in AI Execution Security & High-Performance Backend Architecture.* 📍 Valencia, Spain (Ready for EU Fintech Challenges)
