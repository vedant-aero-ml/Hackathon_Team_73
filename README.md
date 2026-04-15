# AI Augmented Data Compliance Framework

A modular, multi-agent Python system for vendor master data governance and compliance.
Built on the **SAP AI SDK (gen_ai_hub)** with a **Streamlit** dashboard.

Two independent pipelines — an AI-powered risk engine (Flow A) and an intelligent compliance checker with chat-driven Q&A and updates (Flow B).

---

## What Has Been Built

### Flow B — Compliance Dashboard ✅ (fully functional)

Upload a vendor master `.xlsx` or `.csv` file and get an instant compliance report. Then query and update data directly from a chat bar powered by the LLM.

#### Report

| Output | Description |
|--------|-------------|
| **Summary metrics** | Total / Active / Pending / Inactive counts |
| **Issue rows table** | INACTIVE and PENDING vendors with blank GDPR/ECCN cells highlighted |
| **Reason breakdown** | Missing GDPR / Missing ECCN / Both missing counts |
| **Processed download** | Updated `.xlsx` with `Status` and `Reason` columns added |

**Status logic applied per row:**

| Status | Condition |
|--------|-----------|
| ✅ ACTIVE | Both GDPR **and** ECCN present |
| ⏳ PENDING | One of GDPR / ECCN missing |
| ❌ INACTIVE | Both GDPR **and** ECCN missing |

> A cell is treated as missing if it is `null`, `NaN`, empty (`""`), or whitespace-only.

#### Compliance Assistant (Chat)

After the report renders, a chat bar appears below. It uses a **two-step code-execution approach** — the LLM generates pandas expressions that are executed against the real DataFrame, making responses factually grounded with no hallucination.

**Query examples:**
- `what is the status of SUP022?`
- `how many vendors are INACTIVE?`
- `show all vendors with missing GDPR`

**Update examples:**
- `update GDPR of SUP087 to GDPR-2026-06`
- `set ECCN for SUP054 to EAR99`

After an update:
- The report (metrics, issues table) refreshes live to reflect the change
- A **Download updated CSV** button appears directly below the chat reply
- The main download button also reflects the updated data

---

### Flow A — Vendor Change Risk Pipeline 🔧 (requires AI Core credentials)

A 7-agent sequential pipeline that evaluates vendor master change requests for fraud and compliance risk:

| # | Agent | What it does |
|---|-------|-------------|
| 1 | **Ingestion Agent** | Normalises input, extracts email domain, attaches vendor history |
| 2 | **Rule-Based Risk Agent** | Flags free email domains, sensitive field changes, prior rejections |
| 3 | **Anomaly Detection Agent** | Z-score frequency analysis vs. vendor population |
| 4 | **NLP Context Agent** | Calls `gpt-4o-mini` via SAP AI SDK to detect social-engineering signals |
| 5 | **Risk Aggregation Agent** | Weighted combination → final score 0–100 |
| 6 | **Decision Agent** | LOW → APPROVE / MEDIUM → REVIEW / HIGH → ESCALATE |
| 7 | **Explanation Agent** | Generates a human-readable compliance audit narrative |

---

## Project Structure

```
Hackathon_Team_73/
├── app.py                        # Streamlit dashboard (Flow B + Chat)
├── requirements.txt
├── .env                          # SAP AI Core credentials (never committed)
│
├── config/
│   └── settings.py               # Model name, score weights, thresholds
│
├── data/
│   ├── mock_vendor_history.py    # In-memory vendor change history (Flow A)
│   └── sample_vendors.xlsx       # Demo Excel file
│
├── models/
│   └── schemas.py                # All dataclasses and enums
│
├── agents/
│   ├── ingestion_agent.py
│   ├── rule_based_risk_agent.py
│   ├── anomaly_detection_agent.py
│   ├── nlp_context_agent.py      # Uses SAP AI SDK (lazy import)
│   ├── risk_aggregation_agent.py
│   ├── decision_agent.py
│   ├── explanation_agent.py
│   ├── excel_processing_agent.py # Flow B: classifies vendor status
│   └── chat_agent.py             # Flow B: LLM-powered Q&A + updates
│
├── pipelines/
│   ├── flow_a.py                 # Orchestrates agents 1–7
│   └── flow_b.py                 # Orchestrates Excel agent
│
└── utils/
    ├── validators.py
    └── formatting.py
```

---

## Setup & Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

Open `.env` and fill in your SAP AI Core values:

```env
AICORE_AUTH_URL=https://<subaccount>.authentication.<region>.hana.ondemand.com
AICORE_CLIENT_ID=<your-client-id>
AICORE_CLIENT_SECRET=<your-client-secret>
AICORE_BASE_URL=https://api.ai.<region>.aws.ml.hana.ondemand.com/v2
AICORE_RESOURCE_GROUP=default
```

> The Excel compliance checker (Flow B) works without credentials. Credentials are only needed for the NLP agent (Flow A) and the Compliance Assistant chat.

### 3. Run the app

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### 4. Try the sample file

Click **"Download sample Excel file"** in the UI, then re-upload it to see the full system in action — report, metrics, and chat.

---

## Chat Agent — How It Works

The Compliance Assistant uses a **two-step execution pipeline** to prevent hallucination:

```
User question / update command
        ↓
Step 1 — Intent classification (READ or WRITE)
        ↓
Step 2 — LLM generates a pandas expression or statement
        ↓
Step 3 — Python executes it against the real DataFrame
        ↓
Step 4 — LLM formats the raw result into a natural language answer
```

For **updates**, the execution runs on a copy of the DataFrame. Only on success is the live DataFrame updated and the report refreshed. Status and Reason are automatically recomputed after every field change.

**Safe eval/exec:** Both `eval` and `exec` run with `__builtins__: {}` — no file system or network access is possible from generated code.

---

## Where to Find AI Core Credentials

1. Go to **BTP Cockpit** → your subaccount → **Instances and Subscriptions**
2. Find your **AI Core** service instance → **"..."** → **Create Service Key**
3. The downloaded JSON contains: `url` (→ `AICORE_BASE_URL`), `clientid`, `clientsecret`, `auth_url`
4. `AICORE_RESOURCE_GROUP` is typically `default` unless set otherwise by your admin
