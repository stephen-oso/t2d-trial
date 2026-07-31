# T2D Trial Pre-Screener — Design Spec
**Date:** 2026-07-30
**Status:** Approved for implementation

---

## Problem

Nurse practitioners at community health clinics serving underinsured populations see 15–20 Type 2 Diabetes patients daily. Some patients qualify for clinical trials (free medication, closer monitoring) but manual eligibility screening takes 2 hours per patient. Most never get referred.

This tool reduces that to 30 seconds: paste a patient note, get back a ranked list of trials with pass/fail per criterion and a list of missing information needed to confirm eligibility.

---

## Scope

- **Condition:** Type 2 Diabetes, pre-insulin patients only (on oral medications or diet-controlled)
- **Trials:** 10 manually curated trials from ClinicalTrials.gov with lab-value-based eligibility criteria only (HbA1c, BMI, eGFR, months since diagnosis). No complex temporal or boolean exclusion logic.
- **User:** Nurse practitioners at community health clinics
- **Input:** SOAP note or brief patient summary (unstructured text)
- **Output:** Ranked trial matches with per-criterion pass/fail/unknown + list of missing info needed

---

## What This Is Not

This is a scoped learning demo, not a production clinical decision tool. It does not handle:
- Conditions other than Type 2 Diabetes
- Insulin-dependent patients
- Trials with complex nested exclusion logic
- Real patient data (all test cases are synthetic)

---

## Architecture

### Phase 1 — RAG + Structured Extraction
Two independent pieces that connect at the end.

**Trial Ingestion (RAG side):**
- Fetch 10 curated T2D trials from ClinicalTrials.gov API
- Extract eligibility criteria text per trial
- Chunk and embed using HuggingFace sentence-transformers (all-MiniLM-L6-v2)
- Store in ChromaDB locally (Phase 1–3), Qdrant Cloud for deployment (Phase 4)

**Patient Profile Extraction (Structured Extraction side):**
- Input: unstructured SOAP note or patient summary
- Use direct Groq API (llama3-8b-8192) + Pydantic to extract:
  - `age: int`
  - `sex: str`
  - `months_since_diagnosis: int | None`
  - `hba1c: float | None`
  - `bmi: float | None`
  - `egfr: float | None`
  - `current_medications: list[str]`
  - `on_insulin: bool`
  - `exclusion_flags: list[str]`
- No LangChain in Phase 1 — raw API calls only so the mechanics are understood first

### Phase 2 — Tool-Calling Agent
ReAct agent (Groq + LangGraph) with 3 tools:

| Tool | Purpose |
|---|---|
| `search_trials(query)` | Semantic search against ChromaDB/Qdrant, returns relevant trial criteria chunks |
| `check_eligibility(patient, trial_criteria)` | Field-by-field comparison, returns PASS / FAIL / UNKNOWN per criterion |
| `score_match(results)` | Aggregates criterion results into an overall match score (0–1) |

Agent reasoning pattern (ReAct):
1. Extract search query from patient profile
2. Call `search_trials` → retrieve top 5 relevant trial chunks
3. For each trial: call `check_eligibility` → per-criterion verdict
4. Call `score_match` → rank all trials
5. Return ranked list with verdicts and missing info

LangGraph and LangChain introduced here once raw Groq API is understood from Phase 1.

### Phase 3 — Evaluation Pipeline

**Ground truth:**
- 20 synthetic patient notes manually written
- Each manually cross-referenced against actual trial PDFs to establish correct matches
- Stored in `data/test_cases/` as JSON

**Metrics:**
- **Precision:** of trials returned as matches, how many are correct
- **Recall:** of all trials a patient qualifies for, how many did we find
- **Hallucination test:** agent should return FAIL when patient meets an exclusion criterion — not MATCH

**Tooling:** DeepEval integrated with pytest. CI-ready (can be added to GitHub Actions).

**Target baseline to beat:**
- Precision > 85%
- Recall > 80%
- Zero hallucinated matches on exclusion criteria

### Phase 4 — Deployment

| Component | Service | Cost |
|---|---|---|
| FastAPI backend | Render.com | Free |
| Vector DB | Qdrant Cloud | Free |
| LLM | Groq API | Free |
| Keep-warm cron | Render cron job (pings /health every 14 min) | Free |
| Frontend (optional) | Netlify | Free |

**API Endpoints:**

```
POST /match
  Input:  { "note": "unstructured patient text..." }
  Output: {
    "patient": { ...extracted PatientProfile... },
    "matches": [
      {
        "trial_id": "NCT04821",
        "trial_name": "...",
        "score": 0.91,
        "criteria": [
          { "criterion": "HbA1c 7.5–10%", "status": "PASS", "patient_value": "8.2%" },
          { "criterion": "eGFR > 60", "status": "UNKNOWN", "patient_value": null }
        ],
        "missing_info": ["eGFR not provided in note"]
      }
    ]
  }

GET /trials       → list of all 10 curated trials
GET /health       → { "status": "healthy", "model": "llama3-8b-8192" }
GET /metrics      → request count, avg latency, error rate
```

---

## Data

### Trial Data (`data/trials/`)
10 manually curated ClinicalTrials.gov trials:
- Fetched via ClinicalTrials.gov v2 API (no auth required)
- Selection criteria: active/recently completed, T2D, pre-insulin, lab-value-only eligibility
- Stored as JSON: `{ trial_id, title, eligibility_criteria_text, inclusion, exclusion }`

### Test Cases (`data/test_cases/`)
20 synthetic patient notes:
- 10 patients who clearly qualify for at least one trial
- 5 patients who are disqualified by a specific criterion (exclusion test)
- 5 edge cases (missing info, borderline values)
- Each includes `correct_matches: [trial_id, ...]` verified manually against trial PDFs

---

## Stack

```
Language:      Python 3.11+
LLM:           Groq API (llama3-8b-8192) — free tier
Embeddings:    sentence-transformers/all-MiniLM-L6-v2 (local, free)
Vector DB:     ChromaDB (Phase 1–3 local) → Qdrant Cloud (Phase 4)
Agent:         LangGraph (introduced Phase 2)
Evaluation:    DeepEval + pytest
API:           FastAPI + uvicorn
Deployment:    Render.com (backend) + Netlify (optional frontend)
```

---

## Folder Structure

```
t2d-trial-screener/
├── data/
│   ├── trials/               ← 10 curated trial JSONs
│   └── test_cases/           ← 20 verified synthetic patient notes
├── ingestion/
│   └── load_trials.py        ← fetch from ClinicalTrials.gov, embed, store
├── extraction/
│   └── patient_profile.py    ← raw Groq API + Pydantic extraction
├── matching/
│   └── agent.py              ← LangGraph ReAct agent + 3 tools
├── evaluation/
│   └── test_screener.py      ← DeepEval tests + precision/recall reporting
├── api/
│   ├── main.py               ← FastAPI endpoints
│   └── keepwarm.py           ← cron ping to prevent Render cold starts
├── docs/
│   └── superpowers/specs/    ← this file
├── .env.example              ← required env vars (no secrets)
├── requirements.txt
└── README.md
```

---

## Case Study Framing

> "Built a clinical trial pre-screener for nurse practitioners at community health clinics. Scoped to 10 curated Type 2 Diabetes trials targeting pre-insulin patients. Manually verified 20 test cases against trial PDFs to establish ground truth. System achieved [X]% precision and [Y]% recall on the test set. Demonstrates RAG, structured extraction, agentic reasoning, LLM evaluation, and production API deployment on a zero-cost stack."

Metrics filled in after Phase 3 evaluation runs.

---

## Known Limitations (to state honestly)

- Scoped to 10 trials and one condition — not a general-purpose matcher
- Groq free tier has rate limits — acceptable for demo, would need paid tier for production load
- Render free tier cold starts (~30–60s) mitigated by keep-warm cron
- Synthetic test cases — real-world performance may differ
- Not a medical device — output is a suggestion for a nurse to investigate, not a clinical decision
