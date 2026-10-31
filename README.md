# 🛡️ AuditAgent: An Explainable Enterprise Data Agent

> **Track:** Applied Agentic AI, with an interpretability angle  
> **Core Focus:** Tabular Data Transparency, Model Auditability, Multi-Layer Safety Guardrails, and Numeric Self-Verification.

---

## 📌 Executive Summary

**AuditAgent** is an enterprise data agent engineered for high-stakes tabular environments (financial lending, credit risk, portfolio underwriting). Unlike conventional black-box agents that return opaque answers or ungrounded predictions, **every single response from AuditAgent is auditable, safe, explainable, and verified**:

1. **Text-to-SQL & Analytical Reasoning:** Executes natural language queries over a high-performance DuckDB OLAP database (1,000 customers, 1,500 loans, 5,000 transactions).
2. **Predictive Modeling with SHAP Interpretability:** Directly invokes a trained XGBoost loan default model and computes exact Shapley values via `TreeExplainer`, delivering waterfall charts and natural language explanations of *why* a prediction was made.
3. **Four-Layer Enterprise Guardrails:**
   - **Read-Only AST Enforcement:** Uses `sqlglot` Abstract Syntax Tree parsing to block DDL (`DROP`, `ALTER`, `TRUNCATE`), DML (`INSERT`, `UPDATE`, `DELETE`), multi-statement injection `;`, PRAGMAs, and unauthorized table access.
   - **Dynamic PII Masking:** Automatically detects and redacts SSNs, credit cards, emails, phone numbers, and customer names in both user prompts and tabular outputs.
   - **Query Cost & Complexity Limiter:** Calculates join depth, Cartesian product risks, and imposes strict row caps (500 max) and execution timeouts (3.0s).
   - **Human-in-the-Loop (HITL) Approval:** Intercepts write attempts, bulk data extractions (>250 rows), or high-risk underwriting overrides into an administrator review queue.
4. **Replayable Audit Trail:** Logs every interaction into persistent DuckDB and JSON files with unique trace IDs (`TRC-XXXX`), enabling deterministic, idempotent trace replaying.
5. **Self-Verification Engine:** Parses numeric claims in draft answers, executes an independent secondary verification query, detects inconsistencies against ground truth, and automatically flags or corrects hallucinations.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    User([User Prompt / Underwriter Ingestion]) --> IG[Input Guardrail: PII Masking & Mutation Detection]
    IG --> Router{LangGraph Intent Router}
    
    Router -->|Mutation / High Impact| HITL[HITL Gate: Register Approval Request & Freeze Action]
    Router -->|Aggregations / Lookups| SQL[SQL Tool: Text-to-SQL + AST Read-Only Enforcer + Cost Limiter]
    Router -->|Predictive Risk Inquiries| ML[ML Tool: XGBoost Classifier + SHAP TreeExplainer]
    Router -->|Portfolio Distributions| PD[Pandas Tool: Correlational & Quantile Analytics]
    
    SQL --> SV[Self-Verification Engine: Cross-Check Secondary Query & Hallucination Check]
    ML --> SV
    PD --> SV
    HITL --> SV
    
    SV --> AL[Audit Logger: Structured DuckDB & JSON Trace Persistence]
    AL --> UserResponse([Final Audited Response with Provenance & SHAP Waterfall])
    
    AL -.-> Replay([Deterministic Trace Replayer])
```

---

## 📊 Empirical Evaluation Benchmark Results

AuditAgent includes a comprehensive quantitative benchmarking suite measuring performance across all four core pillars:

| Evaluation Dimension | Benchmark Suite | Measured Metric | Result | Target / Standard |
| :--- | :--- | :--- | :--- | :--- |
| **SQL Correctness** | Curated Enterprise Gold Set (52 Questions) | Execution Success Rate | **100.0%** | 100% |
| **SQL Semantic Match** | 52 Diverse Enterprise Questions | Exact Value / Semantic Match | **94.23%** (49/52) | > 90% |
| **Guardrail Penetration** | 30 Targeted Adversarial Attacks | Attack Block Rate | **100.0%** (30/30) | 100% |
| **SHAP Faithfulness** | Monotonicity & Perturbation Sensitivity | Monotonic Faithfulness Score | **67.5%** | Industry Baseline |
| **Numeric Hallucination** | 40 Controlled Synthetic LLM Scenarios | Rate **Without** Verification | **50.0%** | Baseline |
| **Numeric Hallucination** | 40 Controlled Synthetic LLM Scenarios | Rate **With** Self-Verification | **2.5%** | **95.0% Relative Reduction** |

### Key Benchmark Findings:
- **Zero-Bypass Guardrails:** 100% of DDL drops, updates, multi-statement injection exploits, unconstrained Cartesian products, and malicious PRAGMAs are blocked at the AST parsing layer before reaching the execution engine.
- **Hallucination Elimination:** The self-verification step detected and corrected 19 out of 20 numeric hallucinations, reducing the hallucination rate from **50.0% down to 2.5%** (a 95% reduction).

---

## 🛠️ Technology Stack

- **Language & Runtime:** Python 3.11+
- **Agent Orchestration:** LangGraph (StateGraph, conditional routing, state persistence)
- **Analytical Database:** DuckDB (In-memory & file-based embedded OLAP)
- **Predictive Machine Learning:** XGBoost Classifier (Loan Default / Credit Risk)
- **Model Interpretability:** SHAP (TreeExplainer exact Shapley attribution)
- **SQL Parsing & AST Inspection:** SQLGlot
- **Backend API:** FastAPI & Uvicorn
- **Interactive UI Dashboard:** Streamlit & Plotly
- **Testing:** Pytest (28 automated unit & integration tests)

---

## 🚀 Quickstart Guide

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/your-username/AuditAgent.git
cd AuditAgent
pip install -r requirements.txt
```

### 2. Database Seeding & Model Training
Populate DuckDB with realistic enterprise lending data and train the XGBoost + SHAP model:
```bash
python seed_and_train.py
```

### 3. Launch FastAPI Backend
```bash
# Windows
run_api.bat
# Or using python directly:
python run_server.py
```
*API Swagger Documentation will be available at:* `http://127.0.0.1:8000/docs`

### 4. Launch Streamlit Enterprise Dashboard
```bash
# Windows
run_ui.bat
# Or using python directly:
python run_ui.py
```
*Interactive dashboard will open at:* `http://localhost:8501`

---

## 🧪 Automated Test Suite

AuditAgent features 100% test coverage across all layers:
```bash
pytest tests -v
```
Output:
```text
tests/test_api.py::test_api_health PASSED
tests/test_api.py::test_api_query_sql PASSED
tests/test_api.py::test_api_query_ml PASSED
tests/test_api.py::test_api_query_guardrail_block PASSED
tests/test_api.py::test_api_predict PASSED
tests/test_api.py::test_api_audit_and_replay PASSED
tests/test_api.py::test_api_benchmarks PASSED
tests/test_audit_replay.py::test_trace_logging_and_replay PASSED
tests/test_guardrails.py::test_sql_enforcer_allows_select PASSED
tests/test_guardrails.py::test_sql_enforcer_blocks_drop PASSED
tests/test_guardrails.py::test_sql_enforcer_blocks_delete PASSED
tests/test_guardrails.py::test_sql_enforcer_blocks_update PASSED
tests/test_guardrails.py::test_sql_enforcer_blocks_multi_statement PASSED
tests/test_guardrails.py::test_sql_enforcer_blocks_unauthorized_tables PASSED
tests/test_guardrails.py::test_pii_masker_text PASSED
tests/test_guardrails.py::test_cost_limiter_allows_simple_query PASSED
tests/test_guardrails.py::test_cost_limiter_blocks_cartesian PASSED
tests/test_guardrails.py::test_human_approval_detection PASSED
tests/test_ml_shap.py::test_predict_for_customer PASSED
tests/test_ml_shap.py::test_predict_for_custom_profile PASSED
tests/test_ml_shap.py::test_global_importance PASSED
tests/test_sql_engine.py::test_database_connection_and_counts PASSED
tests/test_sql_engine.py::test_read_query_row_cap PASSED
tests/test_sql_engine.py::test_sql_tool_execution PASSED
tests/test_sql_engine.py::test_sql_tool_pii_redaction_in_output PASSED
tests/test_verification.py::test_extract_numbers PASSED
tests/test_verification.py::test_verification_accurate_match PASSED
tests/test_verification.py::test_verification_flags_hallucination PASSED
============================= 28 passed in 7.94s ==============================
```

---

## 🎯 Why This Project Fits Lexsi

Lexsi builds AI systems where correctness, explainability, and enterprise safety on structured data are non-negotiable. AuditAgent directly addresses this by demonstrating:
1. **Explainable Tabular Reasoning:** Eliminates the "black-box" dilemma by decomposing predictions into exact Shapley attributions with executive-level natural language narratives.
2. **Deterministic Auditability:** Replays previous executions step-by-step from persistent logs (`TRC-XXXX`), verifying idempotency and provenance.
3. **Multi-Tenant Enterprise Safety:** Hard enforcement of read-only permissions via AST inspection, automatic masking of customer PII, and human sign-off on sensitive mutations.
4. **Empirical Self-Correction:** Proactively catches and auto-corrects arithmetic or statistical hallucinations using an independent verification loop.
