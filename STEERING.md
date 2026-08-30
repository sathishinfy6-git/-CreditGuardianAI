# CreditGuardian AI – Steering File
## Credit Risk & Regulatory Intelligence Copilot for Corporate Lending

---

## 1. Project Overview

**CreditGuardian AI** is a Snowflake-native application that analyzes borrower financial statements, account transactions, loan exposures, and regulatory policies to:

- Identify credit risk signals (early warning indicators)
- Provide explainable lending recommendations (approve/reject/conditions)
- Answer compliance and regulatory questions via natural language
- Generate audit-ready credit assessment reports

**Target Users:** Credit analysts, risk officers, compliance teams, lending managers.

---

## 2. Architecture (Snowflake-Native)

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│   Streamlit-in-Snowflake (SiS) Dashboard / Cortex Agent     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   INTELLIGENCE LAYER                         │
│  Cortex AI Functions: AI_COMPLETE, AI_EXTRACT, AI_CLASSIFY  │
│  Cortex Agent (RAG over regulatory docs)                    │
│  Semantic View (analyst-friendly query surface)             │
│  Cortex Search (regulatory policy lookup)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     DATA LAYER                               │
│  Borrower Financials │ Loan Exposures │ Transactions        │
│  Regulatory Docs (PDF/stage) │ Credit Ratings History       │
│  Risk Scoring Models │ Audit Logs                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Data Model (Core Tables)

| Table | Purpose |
|-------|---------|
| `CUSTOMERS` | Borrower master (company info, sector, industry, risk tier) |
| `COMPANY_FINANCIALS` | Annual/quarterly P&L, balance sheet, cash flow, ratios |
| `LOAN_HISTORY` | Loan facility history – sanctions, drawdowns, status |
| `LOAN_REPAYMENT` | Loan EMI repayment schedule and actuals |
| `BANK_TRANSACTIONS` | Monthly account debit/credit transaction summaries |
| `CREDIT_RATINGS` | External credit ratings from agencies (S&P, Moody's, CRISIL) |
| `INDUSTRY_TRENDS` | Macro-level industry trend analytics (joins on SECTOR/INDUSTRY) |
| `LOAN_APPLICATIONS` | Loan application intake pipeline with AI-assisted decisioning |
| `MACRO_ECONOMIC_RAW` | Raw JSON landing table for external macro-economic data feeds |
| `MACRO_ECONOMIC_INDICATORS` | Structured macro indicators: CPI, repo rate, GDP, NPA ratio, FX, commodities |
| `REGULATORY_POLICIES` | 29 regulatory policy sections (6 RBI/Basel/IBC PDFs) parsed via AI pipeline |
| `RISK_SCORES` | **Dynamic Table** – 7-component composite credit risk score (Financial + Repayment + Cashflow + Collateral + Rating + Industry + Macro) |

### Streaming Pipeline Objects

| Object | Type | Purpose |
|--------|------|---------|
| `MACRO_FEED_STAGE` | Stage | Internal stage for external JSON feeds |
| `REGULATORY_DOCS_STAGE` | Stage | Storage for regulatory policy documents (legacy, CSE-encrypted) |
| `REGULATORY_PDF_STAGE` | Stage | SSE-encrypted stage for regulatory PDFs (used by PARSE_DOCUMENT) |
| `REGULATORY_DOCS_RAW` | Table | Raw parsed text from PDFs with tracking metadata (hash, page count, status, errors) |
| `PDF_PROCESSING_LOG` | Table | Audit log for every PDF ingestion run (run_id, file counts, status, errors) |
| `MACRO_ECONOMIC_STREAM` | Stream | Append-only CDC on MACRO_ECONOMIC_RAW |
| `PROCESS_MACRO_DATA_TASK` | Task | Triggered by stream; parses JSON → structured; refreshes RISK_SCORES |
| `REGULATORY_PDF_LOAD_TASK` | Task | Daily (6AM IST) — parses PDFs → AI_EXTRACT → REGULATORY_POLICIES |
| `LOAD_REGULATORY_PDFS` | Procedure | Production-grade pipeline: incremental PARSE_DOCUMENT (page-chunked) + AI_EXTRACT + FLATTEN + MERGE with per-file error isolation |
| `REGULATORY_SEARCH_SERVICE` | Cortex Search | Semantic search over regulatory policies (29 sections from 6 PDFs) |

### Streaming Data Flow
```
External Feed (JSON) → @MACRO_FEED_STAGE → COPY INTO MACRO_ECONOMIC_RAW
    → MACRO_ECONOMIC_STREAM (CDC) → PROCESS_MACRO_DATA_TASK (daily, WHEN stream has data)
        → INSERT INTO MACRO_ECONOMIC_INDICATORS (structured)
        → ALTER DYNAMIC TABLE RISK_SCORES REFRESH
```

### Regulatory PDF Ingestion Pipeline (Production-Grade)
```
Upload PDF → @REGULATORY_PDF_STAGE/policies/
    → LOAD_REGULATORY_PDFS() procedure (or REGULATORY_PDF_LOAD_TASK daily 6AM IST)
        Step 0: Initialize run in PDF_PROCESSING_LOG, refresh stage directory
        Step 1: Per-file loop with MD5-based idempotency (skip unchanged files)
                → Get page count (cheap 1-page metadata call)
                → If ≤500 pages: single PARSE_DOCUMENT call (LAYOUT mode)
                → If >500 pages: chunked parsing via page_filter (500-page batches)
                → Per-file TRY/CATCH: failures logged, processing continues
                → INSERT into REGULATORY_DOCS_RAW with hash, page count, status
        Step 2: AI_EXTRACT on newly parsed docs (title, authority, date, category)
        Step 3: Split parsed text on markdown ## headers → MERGE into REGULATORY_POLICIES
        Step 4: Finalize PDF_PROCESSING_LOG (file counts, status, error summary)
    → REGULATORY_SEARCH_SERVICE auto-refreshes (1hr lag) for RAG queries
```

---

## 4. Implementation Phases

### Phase 1: Foundation – Data Layer ✓
- [x] Create database and schema (`CREDITGUARDIAN_AI.CORE`)
- [x] Design and create all core tables with sample data
- [x] Load regulatory documents to a Snowflake stage
- [x] Set up Cortex Search service over regulatory docs

### Phase 2: Risk Intelligence – AI Functions ✓
- [x] Build early-warning indicator computation (Dynamic Tables) — RISK_SCORES with 7-component formula
- [x] Build risk signal extraction (AI_EXTRACT on financials) — CREDIT_RISK_SIGNALS view
- [x] Build credit risk classifier (AI_CLASSIFY on borrower profiles) — BORROWER_RISK_CLASSIFICATION view (SMA + lending rec)
- [x] Build explainable recommendation generator (AI_COMPLETE) — GENERATE_CREDIT_ASSESSMENT procedure + CREDIT_ASSESSMENTS table

### Phase 3: Query & Compliance Layer ✓
- [x] Create Semantic Model YAML (deployed to @REGULATORY_DOCS_STAGE/semantic/credit_risk_sv.yaml)
- [x] Build Cortex Agent for regulatory Q&A + data queries (CREDITGUARDIAN_AGENT)
- [x] Create stored procedures for credit assessment generation (GENERATE_CREDIT_ASSESSMENT — done in Phase 2)

### Phase 4: Presentation & Reporting ✓
- [x] Build Streamlit dashboard (CREDITGUARDIAN_DASHBOARD — 5 pages: Portfolio Overview, Borrower Deep Dive, Loan Applications, Macro Monitor, Compliance Copilot)
- [x] Generate audit-ready credit reports (via GENERATE_CREDIT_ASSESSMENT in Borrower Deep Dive page)
- [x] Drill-down into risk signals and recommendations (score component bar chart + AI narrative)

### Phase 5: Operationalization
- [x] Schedule periodic risk signal refresh (Tasks + Streams) — PROCESS_MACRO_DATA_TASK (daily, stream-triggered)
- [x] Production-grade PDF ingestion pipeline — incremental, idempotent, error-resilient, chunked for large docs
- [x] PDF processing audit log — PDF_PROCESSING_LOG table with run-level metrics
- [ ] Set up alerts for critical risk threshold breaches
- [ ] Implement RBAC (analyst vs. officer vs. auditor roles)
- [ ] Audit logging for all AI-generated recommendations

---

## 5. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Compute | Snowflake serverless (tasks, dynamic tables) | No infra management |
| AI Models | Cortex AI built-in functions | Native, no external API keys |
| Regulatory RAG | Cortex Search + Cortex Agent | Grounded answers with citations |
| Reporting | Semantic View + Streamlit | Self-serve + governed |
| Audit | Every AI call logged with inputs/outputs | Regulatory requirement |

---

## 6. Snowflake Services Used

- **Cortex AI Functions**: AI_COMPLETE, AI_EXTRACT, AI_CLASSIFY, AI_SUMMARIZE_AGG
- **Cortex PARSE_DOCUMENT**: PDF text/layout extraction (regulatory document ingestion)
- **Cortex Search**: Regulatory policy retrieval (semantic vector search)
- **Cortex Agent**: Natural-language copilot (RAG + Analyst combined)
- **Semantic Views**: Governed query interface
- **Dynamic Tables**: Incremental risk signal computation
- **Tasks & Streams**: Scheduled refresh, CDC, and PDF ingestion pipeline
- **Streamlit-in-Snowflake**: Interactive dashboard
- **Stages**: Document storage (regulatory PDFs — SSE-encrypted for PARSE_DOCUMENT compatibility)

---

## 7. Connection & Environment

- **Connection**: GK87106 (`lu90241.ap-southeast-7.aws`)
- **User**: SATHISHINFY.T01
- **Target Database**: CREDITGUARDIAN_AI
- **Target Schema**: CORE (data), ANALYTICS (views/models), APP (streamlit/agents)

---

## 8. Conventions

- All table names: UPPER_SNAKE_CASE
- All AI outputs stored with timestamp + model version for reproducibility
- Every credit assessment gets a unique `ASSESSMENT_ID` (UUID)
- Regulatory references cite source document + section
- Sample data uses realistic but synthetic corporate lending scenarios

---

## 9. Current Status

**Phase**: Phase 1-4 ✓ COMPLETE. Phase 5 partial (streaming done, PDF ingestion pipeline upgraded to production-grade). Remaining: alerts, RBAC, audit logging. Dashboard live at Snowsight (URL ID: f5tu7tt7njlpiyokohpp).

### Recently Added (Aug 30, 2026)
- Upgraded `LOAD_REGULATORY_PDFS` SP to production-grade:
  - **Incremental processing**: MD5 hash-based idempotency — skips unchanged files
  - **Page chunking**: Detects page count first, then processes large docs (>500 pages) in batches via `page_filter` — supports up to 100MB / 2000 pages per PDF
  - **Per-file error isolation**: TRY/CATCH per file — one failure doesn't kill the batch
  - **MERGE instead of TRUNCATE**: Incremental upsert preserves existing policies
  - **Markdown header splitting**: Deterministic section extraction from PARSE_DOCUMENT LAYOUT output (replaces fragile pipe-delimited AI_EXTRACT approach)
  - **Auto-incrementing POLICY_IDs**: New IDs start after existing MAX
- Added tracking columns to `REGULATORY_DOCS_RAW`: FILE_SIZE, FILE_HASH, PAGE_COUNT, PROCESSING_STATUS, ERROR_MESSAGE, PROCESSED_AT
- Created `PDF_PROCESSING_LOG` table — full audit trail per run (run_id, timestamps, file counts, success/failure/partial status, error summaries)
- Widened `REGULATORY_POLICIES.SECTION` column to VARCHAR(1000) for real-world section names
- Successfully tested: 6 files detected, 6 processed, 0 failed, 38 policy sections loaded

### Previously Added (Aug 26, 2026)
- Created 6 realistic RBI/Basel/IBC regulatory PDFs
- Built initial PDF → Table pipeline: `PARSE_DOCUMENT` → `AI_EXTRACT` → `REGULATORY_POLICIES`
- New stage: `REGULATORY_PDF_STAGE` (SSE-encrypted, compatible with PARSE_DOCUMENT)
- New scheduled task: `REGULATORY_PDF_LOAD_TASK` (daily 6AM IST)
- REGULATORY_POLICIES now has 38 structured sections extracted from 6 PDFs
