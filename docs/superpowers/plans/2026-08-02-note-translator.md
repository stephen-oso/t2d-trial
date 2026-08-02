# Note Translator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a note translator that rewrites incomplete SOAP notes with gap placeholders, reducing UNKNOWN verdicts in trial eligibility matching.

**Architecture:** New `POST /optimize` endpoint calls Claude Haiku to rewrite a note as clean SOAP with `[not found — add if available]` placeholders for missing clinical fields. Frontend gains a two-tab layout (Optimize Note / Find Trials) where the optimized note transfers to the matcher with one click.

**Tech Stack:** FastAPI, Pydantic v2, Anthropic SDK (`claude-haiku-4-5-20251001`), React, plain CSS.

## Global Constraints

- LLM model: `claude-haiku-4-5-20251001` — matches rest of codebase, do not change
- Anthropic SDK: `anthropic>=0.40.0`
- Pydantic v2 for all models
- No changes to `matching/`, `extraction/extract.py`, `extraction/models.py`, `PatientCard.jsx`, `TrialCard.jsx`, `HistoryDrawer.jsx`
- Frontend: no component libraries — plain CSS with BEM naming
- Optimizer failure must never raise a 500 — return original note unchanged with empty `missing_fields`
- Placeholder text verbatim: `[not found — add if available]`

---

### Task 1: optimize_note() function

**Files:**
- Create: `extraction/optimize.py`
- Create: `tests/test_optimize.py`

**Interfaces:**
- Consumes: `anthropic.Anthropic` client, `os.environ["ANTHROPIC_API_KEY"]`
- Produces: `optimize_note(note: str) -> dict` — returns `{"optimized_note": str, "missing_fields": list[str]}`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_optimize.py`:

```python
from unittest.mock import MagicMock, patch
from extraction.optimize import optimize_note


def _mock_response(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


def test_optimize_note_returns_structure():
    optimized = (
        "S: 48-year-old male, T2D 4 years.\n\n"
        "O: HbA1c 7.6%, Fasting Plasma Glucose (FPG): [not found — add if available], "
        "OGTT 2-hour glucose: [not found — add if available], BMI 27.1, eGFR 91 mL/min, "
        "AST: [not found — add if available], ALT: [not found — add if available], "
        "ALP: [not found — add if available], Total Bilirubin: [not found — add if available]. "
        "Metformin 500mg BID.\n\nA: T2DM near target.\n\nP: Continue current regimen."
    )
    with patch("extraction.optimize._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(optimized)
        result = optimize_note("Patient has diabetes. HbA1c 7.6%. On metformin.")

    assert "optimized_note" in result
    assert "missing_fields" in result
    assert isinstance(result["optimized_note"], str)
    assert isinstance(result["missing_fields"], list)
    assert "FPG" in result["missing_fields"]
    assert "OGTT" in result["missing_fields"]


def test_optimize_note_no_missing_fields():
    full_note = (
        "S: 48M, T2D 4 years.\n\n"
        "O: HbA1c 7.6%, FPG 148 mg/dL, OGTT 2-hour glucose 218 mg/dL, BMI 27.1, "
        "eGFR 91 mL/min, AST 22 U/L, ALT 28 U/L, ALP 74 U/L, Total Bilirubin 0.8 mg/dL. "
        "Metformin 500mg BID.\n\nA: Near target.\n\nP: Continue."
    )
    with patch("extraction.optimize._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(full_note)
        result = optimize_note("Patient has full labs.")

    assert result["missing_fields"] == []


def test_optimize_note_on_api_failure_returns_original():
    with patch("extraction.optimize._client") as mock_client:
        mock_client.messages.create.side_effect = Exception("API error")
        result = optimize_note("Original note text.")

    assert result["optimized_note"] == "Original note text."
    assert result["missing_fields"] == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_optimize.py -v
```
Expected: `ImportError` — `extraction.optimize` does not exist yet.

- [ ] **Step 3: Implement extraction/optimize.py**

```python
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_PLACEHOLDER = "[not found — add if available]"

# (keyword in original note, short display name for missing_fields list)
_FIELDS = [
    ("hba1c",           "HbA1c"),
    ("fasting",         "FPG"),
    ("ogtt",            "OGTT"),
    ("bmi",             "BMI"),
    ("egfr",            "eGFR"),
    ("ast",             "AST"),
    ("alt",             "ALT"),
    ("alp",             "ALP"),
    ("bilirubin",       "Bilirubin"),
    ("age",             "Age"),
    ("sex",             "Sex"),
    ("diagnosis",       "Diagnosis Duration"),
    ("medication",      "Medications"),
    ("insulin",         "Insulin Use"),
]

_SYSTEM = f"""You are a clinical documentation assistant for a T2D clinical trial pre-screener.

Rewrite the provided clinical note as a clean, well-structured SOAP note (S, O, A, P sections).

Rules:
1. Preserve ALL existing clinical values exactly — never change numbers or facts.
2. In the O (Objective) section, add the placeholder "{_PLACEHOLDER}" for each of these fields if they are NOT mentioned anywhere in the original note:
   - HbA1c (%)
   - Fasting Plasma Glucose / FPG (mg/dL)
   - OGTT 2-hour glucose (mg/dL)
   - BMI (kg/m²)
   - eGFR (mL/min/1.73m²)
   - AST (U/L)
   - ALT (U/L)
   - ALP (U/L)
   - Total Bilirubin (mg/dL)
   - Patient age
   - Patient sex
   - Duration since T2D diagnosis
   - Current medications (full list)
   - Insulin use (yes/no)
3. Do NOT invent or estimate any clinical values.
4. Return ONLY the rewritten SOAP note — no explanation, no preamble."""


def optimize_note(note: str) -> dict:
    try:
        response = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": f"Rewrite this note:\n\n{note}"}],
        )
        optimized = response.content[0].text.strip()
        note_lower = note.lower()
        missing = [
            display
            for keyword, display in _FIELDS
            if keyword not in note_lower and _PLACEHOLDER in optimized
        ]
        return {"optimized_note": optimized, "missing_fields": missing}
    except Exception:
        return {"optimized_note": note, "missing_fields": []}
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_optimize.py -v
```
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add extraction/optimize.py tests/test_optimize.py
git commit -m "feat: add optimize_note() — SOAP rewrite with gap placeholders"
```

---

### Task 2: POST /optimize endpoint

**Files:**
- Modify: `api/models.py` — add `OptimizeRequest`, `OptimizeResponse`
- Modify: `api/main.py` — add `POST /optimize`, import `optimize_note`
- Modify: `tests/test_api.py` — add two endpoint tests

**Interfaces:**
- Consumes: `optimize_note(note: str) -> dict` from `extraction.optimize`
- Produces: `POST /optimize` — accepts `{"note": str}`, returns `{"optimized_note": str, "missing_fields": list[str]}`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_api.py`:

```python
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_optimize_endpoint_returns_optimized_note():
    with patch("api.main.optimize_note") as mock_opt:
        mock_opt.return_value = {
            "optimized_note": "S: Patient...\nO: HbA1c 7.6%...",
            "missing_fields": ["FPG", "OGTT"],
        }
        resp = client.post("/optimize", json={"note": "Patient has T2D. HbA1c 7.6%."})

    assert resp.status_code == 200
    data = resp.json()
    assert data["optimized_note"] == "S: Patient...\nO: HbA1c 7.6%..."
    assert data["missing_fields"] == ["FPG", "OGTT"]


def test_optimize_endpoint_rejects_short_note():
    resp = client.post("/optimize", json={"note": "hi"})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_api.py -v -k "optimize"
```
Expected: FAIL — `/optimize` route does not exist.

- [ ] **Step 3: Add models to api/models.py**

Add after the existing `MatchRequest` class:

```python
class OptimizeRequest(BaseModel):
    note: str = Field(min_length=10, description="Raw clinical note to optimize")


class OptimizeResponse(BaseModel):
    optimized_note: str
    missing_fields: list[str]
```

Also add to the imports at the top of `api/models.py` if not already present — `OptimizeRequest` and `OptimizeResponse` use `Field` which is already imported.

- [ ] **Step 4: Add endpoint to api/main.py**

Add to the imports block at the top:
```python
from extraction.optimize import optimize_note
```

Add after the existing `/match` endpoint:
```python
@app.post("/optimize", response_model=OptimizeResponse)
def optimize(request: OptimizeRequest):
    result = optimize_note(request.note)
    return OptimizeResponse(**result)
```

Also add `OptimizeRequest, OptimizeResponse` to the import from `api.models`.

- [ ] **Step 5: Run tests to confirm they pass**

```
pytest tests/test_api.py -v -k "optimize"
```
Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add api/models.py api/main.py tests/test_api.py
git commit -m "feat: add POST /optimize endpoint for note translation"
```

---

### Task 3: Frontend — tabs + Optimize Note UI

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/App.css`

**Interfaces:**
- Consumes: `POST /optimize` at `${API_URL}/optimize`
- Produces: Two-tab input screen. Optimized note pre-fills the existing `note` state consumed by `handleSubmit`.

- [ ] **Step 1: Add new state variables inside App()**

Add after the existing state declarations (after `const intervalRef = useRef(null);`):

```jsx
const [tab, setTab] = useState('optimize');
const [rawNote, setRawNote] = useState('');
const [optimizedNote, setOptimizedNote] = useState('');
const [missingFields, setMissingFields] = useState([]);
const [optimizing, setOptimizing] = useState(false);
```

- [ ] **Step 2: Add handleOptimize and useOptimizedNote functions**

Add after the existing `handleSubmit` function:

```jsx
async function handleOptimize() {
  setOptimizing(true);
  setOptimizedNote('');
  setMissingFields([]);
  try {
    const res = await fetch(`${API_URL}/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: rawNote }),
    });
    if (!res.ok) throw new Error(`API error ${res.status}`);
    const data = await res.json();
    setOptimizedNote(data.optimized_note);
    setMissingFields(data.missing_fields);
  } catch {
    setOptimizedNote(rawNote);
    setMissingFields([]);
  } finally {
    setOptimizing(false);
  }
}

function useOptimizedNote() {
  setNote(optimizedNote);
  setTab('find');
}
```

- [ ] **Step 3: Add tab reset to the reset() function**

Update the existing `reset()` function to also clear optimize state:

```jsx
function reset() {
  setView('input');
  setNote('');
  setLocation('');
  setResult(null);
  setError(null);
  setTab('optimize');
  setRawNote('');
  setOptimizedNote('');
  setMissingFields([]);
}
```

- [ ] **Step 4: Replace input-section JSX with tabbed layout**

Replace the entire `{(view === 'input' || view === 'loading') && (...)}` block with:

```jsx
{(view === 'input' || view === 'loading') && (
  <div className="input-section">
    <div className="tabs">
      <button
        className={`tabs__tab${tab === 'optimize' ? ' tabs__tab--active' : ''}`}
        onClick={() => setTab('optimize')}
        disabled={view === 'loading'}
      >
        Optimize Note
      </button>
      <button
        className={`tabs__tab${tab === 'find' ? ' tabs__tab--active' : ''}`}
        onClick={() => setTab('find')}
        disabled={view === 'loading'}
      >
        Find Trials
      </button>
    </div>

    {tab === 'optimize' && view === 'input' && (
      <div className="optimize-tab">
        <textarea
          className="input-section__textarea"
          value={rawNote}
          onChange={e => setRawNote(e.target.value)}
          placeholder="Paste your note here — we'll clean it up and flag any missing clinical values..."
          rows={10}
        />
        <button
          className="btn btn--secondary"
          onClick={handleOptimize}
          disabled={rawNote.trim().length === 0 || optimizing}
        >
          {optimizing ? 'Optimizing...' : 'Optimize Note'}
        </button>

        {optimizedNote && (
          <>
            {missingFields.length > 0 && (
              <div className="missing-banner">
                <span className="missing-banner__label">Missing:</span>{' '}
                {missingFields.join(', ')} — fill in what you have
              </div>
            )}
            <textarea
              className="input-section__textarea"
              value={optimizedNote}
              onChange={e => setOptimizedNote(e.target.value)}
              rows={14}
            />
            <button className="btn btn--primary" onClick={useOptimizedNote}>
              Use This Note →
            </button>
          </>
        )}
      </div>
    )}

    {(tab === 'find' || view === 'loading') && (
      <>
        <textarea
          className="input-section__textarea"
          value={note}
          onChange={e => setNote(e.target.value)}
          placeholder="Paste a SOAP note or patient summary..."
          disabled={view === 'loading'}
          rows={10}
        />
        {view === 'input' && (
          <>
            <input
              className="input-section__location"
              type="text"
              value={location}
              onChange={e => setLocation(e.target.value)}
              placeholder="Patient location (optional) — e.g. Toronto, ON"
            />
            <div className="input-section__footer">
              <button
                className="input-section__sample-link"
                onClick={() => setNote(SAMPLE_NOTE)}
              >
                Load sample note
              </button>
              <p className="input-section__hint">Analysis takes ~30 seconds</p>
            </div>
            <button
              className="btn btn--primary"
              onClick={handleSubmit}
              disabled={note.trim().length === 0}
            >
              Find Matching Trials
            </button>
          </>
        )}
        {view === 'loading' && (
          <div className="loading">
            <div className="loading__steps">
              {LOADING_STEPS.map((step, i) => (
                <div
                  key={i}
                  className={`loading__step${
                    i < loadingStep
                      ? ' loading__step--done'
                      : i === loadingStep
                      ? ' loading__step--active'
                      : ''
                  }`}
                >
                  <div className="loading__step-dot" />
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </>
    )}
  </div>
)}
```

- [ ] **Step 5: Add CSS to App.css**

Add after the `.input-section__location` block:

```css
.tabs {
  display: flex;
  gap: 0.25rem;
  border-bottom: 2px solid #e2e8f0;
  margin-bottom: 1rem;
}

.tabs__tab {
  padding: 0.5rem 1.25rem;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 150ms, border-color 150ms;
}

.tabs__tab:hover { color: #1e293b; }

.tabs__tab--active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}

.tabs__tab:disabled { opacity: 0.4; cursor: not-allowed; }

.optimize-tab {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.missing-banner {
  padding: 0.625rem 1rem;
  background: #fef9c3;
  border: 1px solid #fde047;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #713f12;
}

.missing-banner__label { font-weight: 600; }
```

- [ ] **Step 6: Manual verification**

```
cd frontend && npm run dev
```

Check:
1. App loads with two tabs — "Optimize Note" active, "Find Trials" inactive
2. Switching to "Find Trials" shows existing note input, location, and submit button
3. "Load sample note" still works on Find Trials tab
4. On Optimize tab: paste a short partial note (e.g. "58M T2D 12 years HbA1c 8.2%"), click "Optimize Note" — spinner appears then optimized SOAP note renders with placeholders and yellow missing-fields banner
5. Editing the optimized textarea works inline
6. "Use This Note →" switches to Find Trials tab with note pre-filled
7. Full match submit still works end to end
8. "New Search" resets all state including tabs

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.jsx frontend/src/App.css
git commit -m "feat: add Optimize Note tab with two-tab layout and note translator UI"
```

---

### Task 4: Deploy

- [ ] **Step 1: Push backend to Railway**

```bash
git push origin master
```

Watch Railway dashboard for "Deploy succeeded" before proceeding.

- [ ] **Step 2: Deploy frontend to Vercel**

```
cd frontend
npx vercel --prod
```

- [ ] **Step 3: Smoke test on production**

1. Open the live Vercel URL
2. On Optimize tab: paste `"58M, T2D 12 years, HbA1c 8.2%, on metformin"` and click "Optimize Note"
3. Verify: optimized SOAP note appears with placeholders for FPG, OGTT, liver values; yellow banner lists missing fields
4. Click "Use This Note →" — switches to Find Trials tab with note pre-filled
5. Add location `"Toronto, ON"` and click "Find Matching Trials"
6. Verify: results return with fewer UNKNOWN verdicts for liver/glucose criteria than the original short note would have produced
