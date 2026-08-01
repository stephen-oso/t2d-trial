# T2D Trial Pre-Screener

Clinical trial matching assistant for nurse practitioners at community health clinics.
Paste a patient note, get back a ranked list of T2D trial matches with per-criterion pass/fail verdicts and a list of missing information.

## Live API

`https://t2d-trial-screener-production.up.railway.app/docs`

## What it does

Takes an unstructured SOAP note or patient summary and:

1. **Extracts** a structured patient profile (age, HbA1c, BMI, eGFR, medications) via Groq LLM
2. **Searches** 10 curated T2D trials semantically via sentence-transformers + Qdrant
3. **Checks** eligibility criterion-by-criterion via a LangGraph ReAct agent
4. **Scores** each trial and returns ranked matches with PASS / FAIL / UNKNOWN per criterion

## Endpoints

```
POST /match     → ranked trial matches for a patient note
GET  /trials    → list all 10 curated trials
GET  /health    → service health check
GET  /metrics   → request count, avg latency, error rate
```

## Stack

| Layer | Technology |
|---|---|
| LLM (extraction) | Groq API — llama-3.1-8b-instant |
| LLM (agent + eligibility) | Groq API — llama-3.1-8b-instant |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (local) |
| Vector DB | Qdrant Cloud (production) / ChromaDB (local) |
| Agent | LangGraph ReAct |
| API | FastAPI + uvicorn |
| Deployment | Railway |

## Evaluation Results

Tested against 20 synthetic patient cases (10 qualifying, 5 disqualified, 5 edge cases) using a threshold of 0.5.

| Metric | Score |
|---|---|
| Precision | 46.2% |
| Recall | 14.3% |
| True Positives | 6 |
| False Positives | 7 |
| False Negatives | 36 |

**Why these numbers:** The system uses `llama-3.1-8b-instant` on the Groq free tier (6,000 TPM limit), which constrains the agent to compact per-criterion verdicts rather than full reasoning chains. The small model is conservative — it marks many criteria UNKNOWN rather than PASS, which drives down recall. The tradeoff keeps the system runnable without paid API access while demonstrating the full RAG + agent + evaluation pipeline end-to-end.

## Local Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # add GROQ_API_KEY
python ingestion/fetch_trials.py        # fetch 10 trials from ClinicalTrials.gov
python ingestion/embed_trials.py        # embed into local ChromaDB
uvicorn api.main:app --reload           # start dev server
```

## Running Tests

```bash
pytest tests/ -v -m "not slow"          # fast tests, no API calls
pytest evaluation/test_screener.py      # hallucination tests (uses Groq — takes ~10 min)
python evaluation/test_screener.py      # full precision/recall evaluation
```

## Known Limitations

- Scoped to 10 curated T2D trials — not a general-purpose clinical trial matcher
- Groq free tier has rate limits; evaluation is rate-limited with 30s sleep between cases
- Render free tier has cold starts (~30–60s) mitigated by keep-warm cron
- All test cases are synthetic — real-world performance may differ
- Not a medical device — output is a suggestion for a nurse to investigate, not a clinical decision
