# T2D Trial Pre-Screener — Frontend Design

**Goal:** A React + Vite SPA that lets a user paste a patient note and see ranked T2D trial matches with per-criterion pass/fail verdicts.

**Architecture:** Static frontend in `frontend/` inside the existing repo, deployed to Vercel. Calls the live Railway API (`VITE_API_URL`) directly from the browser. No server-side code on Vercel.

**Tech stack:** React 18, Vite, plain CSS (no component library).

**Style:** Clean clinical / minimal — white cards, light grey background, muted palette.

---

## API Contract

`POST {VITE_API_URL}/match`
- Request body: `{ "note": "<string>" }`
- Response: `{ "patient": {...}, "matches": [...] }`

`matches` items:
```json
{
  "trial_id": "NCT04932928",
  "trial_name": "string",
  "score": 0.85,
  "criteria": [
    { "criterion": "string", "status": "PASS|FAIL|UNKNOWN", "patient_value": "string|null" }
  ],
  "missing_info": ["string"]
}
```

`patient` object keys: `age`, `hba1c`, `bmi`, `egfr`, `medications`, `diagnoses`, `systolic_bp`, `diastolic_bp`, `weight_kg` (any may be null).

**Latency:** The API takes 60–90 seconds. The UI must handle this with a staged loading message.

---

## File Structure

```
frontend/
  index.html
  vite.config.js
  package.json
  .env.example          # VITE_API_URL=https://...railway.app
  src/
    main.jsx
    App.jsx             # state machine + API call
    App.css             # all styles
    components/
      PatientCard.jsx   # extracted profile grid
      TrialCard.jsx     # single trial match (score bar + expandable criteria)
      StatusBadge.jsx   # PASS / FAIL / UNKNOWN colored pill
```

---

## UI States

### 1. Input state (initial)
- Header: "T2D Trial Pre-Screener" (h1) + subtitle: "Paste a patient note to find matching clinical trials."
- `<textarea>` placeholder: "Paste a SOAP note or patient summary..."
- "Find Matching Trials" button (primary, disabled when textarea is empty)
- Small helper text below button: "Analysis takes ~90 seconds"

### 2. Loading state
- Button replaced by a spinner + staged status message
- Message cycles every 20 seconds through:
  1. "Extracting patient profile..."
  2. "Searching clinical trials..."
  3. "Checking eligibility criteria..."
  4. "Scoring matches..."
- Textarea is disabled during loading
- No cancel button (API has no cancel endpoint)

### 3. Results state
- **"New Search" button** at top to reset to input state
- **PatientCard** — extracted profile fields in a 3-column grid:
  - Age, HbA1c, BMI, eGFR, Systolic BP, Diastolic BP, Weight
  - Medications (comma-joined list or "None recorded")
  - Diagnoses (comma-joined list or "None recorded")
  - Null values shown as "—"
- **TrialCard list** — one card per match, sorted by score descending (API already sorts)
  - Trial name (bold) + NCT ID (muted, smaller)
  - Score bar: filled rectangle, color-coded:
    - Green (`#2d7a4f`) if score ≥ 0.7
    - Amber (`#b45309`) if 0.3 ≤ score < 0.7
    - Red (`#b91c1c`) if score < 0.3
  - Score percentage label to the right of the bar (e.g. "85%")
  - "Show criteria" toggle (collapsed by default) → expands a table:
    - Columns: Criterion | Status | Patient Value
    - Status cell contains a `<StatusBadge>`
  - If `missing_info` is non-empty, show a grey "Missing info" section below the table listing the items

### Error state
- If the API returns a non-2xx response or the fetch throws, show an inline red error message: "Something went wrong. Please try again." with a retry button that resets to input state.

---

## Components

### `StatusBadge.jsx`
Props: `status: "PASS" | "FAIL" | "UNKNOWN"`
- PASS: green pill (`#dcfce7` bg, `#166534` text)
- FAIL: red pill (`#fee2e2` bg, `#991b1b` text)
- UNKNOWN: grey pill (`#f3f4f6` bg, `#6b7280` text)

### `PatientCard.jsx`
Props: `patient: object`
- Renders a white card with a 3-column CSS grid of labelled values.
- Medications and diagnoses are arrays; join with ", " or show "—" if null/empty.

### `TrialCard.jsx`
Props: `match: { trial_id, trial_name, score, criteria, missing_info }`
- Local state: `expanded: boolean` (default false)
- Score bar: `width: ${score * 100}%` on a grey track div
- Toggle button text: "Show criteria" / "Hide criteria"

### `App.jsx`
State:
- `view: "input" | "loading" | "results" | "error"`
- `note: string`
- `result: { patient, matches } | null`
- `error: string | null`
- `loadingStep: 0–3` (incremented every 20s while loading)

On submit: set `view = "loading"`, start 20s interval for `loadingStep`, `fetch(POST /match)`, on success set `result` and `view = "results"`, on failure set `error` and `view = "error"`.

---

## Deployment

- `frontend/` is a standalone Vite project with its own `package.json`.
- Vercel detects it as a Vite app when the Vercel project root is set to `frontend/`.
- Build command: `npm run build` | Output dir: `dist`
- Environment variable in Vercel dashboard: `VITE_API_URL=https://t2d-trial-screener-production.up.railway.app`
- `.env.example` committed; `.env` git-ignored.
- CORS: the Railway API already accepts all origins (FastAPI default).
