# T2D Frontend Redesign & Feature Completion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the T2D Trial Pre-Screener frontend to a modern clinical dashboard aesthetic and add sample note pre-fill, ClinicalTrials.gov links, clipboard copy, CSV export, and a search history drawer.

**Architecture:** Plain Vite + React, no new npm dependencies. All styles live in `src/App.css` (BEM). Features use browser APIs only (localStorage, navigator.clipboard, Blob). New `HistoryDrawer` component is the only new file.

**Tech Stack:** Vite 5, React 18, plain CSS, browser APIs (localStorage, Clipboard API, Blob/URL)

## Global Constraints
- No new npm dependencies
- All CSS in `src/App.css` (BEM naming convention)
- `localStorage` key: `t2d_history`
- Max history entries: 5
- History entry shape: `{ id: string, timestamp: string, snippet: string, matchCount: number, result: object }`
- CSV columns: `Trial Name, Trial ID, Score (%), Criterion, Status, Patient Value`
- NCT links: `https://clinicaltrials.gov/study/{trial_id}` — open in new tab

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `index.html` | Modify | Add Inter font `<link>` tags |
| `src/App.css` | Full rewrite | All styles — shell, buttons, input, loading, results, error, badges, cards, drawer |
| `src/App.jsx` | Modify | Add sample note, loading steps UI, history state/save/restore, copy handler, CSV handler |
| `src/components/HistoryDrawer.jsx` | Create | Slide-in drawer — renders history list, close/restore/clear actions |
| `src/components/TrialCard.jsx` | Modify | NCT ID becomes anchor, update `scoreColor` palette |
| `src/components/PatientCard.jsx` | No change | — |
| `src/components/StatusBadge.jsx` | No change | — |

---

### Task 1: Full CSS Rewrite + Inter Font

**Files:**
- Modify: `index.html`
- Modify: `src/App.css`

**Interfaces:**
- Produces: All CSS classes used by existing JSX and new tasks (see class list in step 2)

- [ ] **Step 1: Add Inter font to `index.html`**

Replace the entire `<head>` block with:

```html
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>T2D Trial Pre-Screener</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
</head>
```

- [ ] **Step 2: Replace `src/App.css` in full**

Overwrite the entire file with the following:

```css
/* ============================================================
   RESET & BASE
   ============================================================ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: #f1f5f9;
  color: #0f172a;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

/* ============================================================
   APP SHELL
   ============================================================ */
.app__header {
  background: #1e293b;
  position: sticky;
  top: 0;
  z-index: 10;
}

.app__header-inner {
  max-width: 720px;
  margin: 0 auto;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app__title {
  font-size: 1rem;
  font-weight: 600;
  color: #f8fafc;
  letter-spacing: -0.01em;
}

.app__subtitle {
  font-size: 0.72rem;
  color: #94a3b8;
  margin-top: 2px;
}

.app__main {
  max-width: 720px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* ============================================================
   BUTTONS
   ============================================================ */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: background 150ms, color 150ms, border-color 150ms;
  font-family: inherit;
  white-space: nowrap;
}

.btn--primary {
  background: #2563eb;
  color: #fff;
}
.btn--primary:hover:not(:disabled) { background: #1d4ed8; }
.btn--primary:disabled { background: #93c5fd; cursor: not-allowed; }

.btn--secondary {
  background: #fff;
  color: #374151;
  border: 1px solid #e2e8f0;
}
.btn--secondary:hover { background: #f8fafc; }

.btn--ghost {
  background: transparent;
  color: #94a3b8;
  border: 1px solid #334155;
  font-size: 0.8rem;
  padding: 0.375rem 0.75rem;
}
.btn--ghost:hover { background: #334155; color: #f8fafc; }

.btn--sm {
  padding: 0.3rem 0.7rem;
  font-size: 0.8rem;
}

/* ============================================================
   INPUT SECTION
   ============================================================ */
.input-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.input-section__textarea {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  font-family: inherit;
  font-size: 0.875rem;
  line-height: 1.6;
  color: #0f172a;
  background: #fff;
  resize: vertical;
  transition: border-color 150ms, box-shadow 150ms;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.input-section__textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
}
.input-section__textarea:disabled { background: #f8fafc; color: #94a3b8; }

.input-section__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.input-section__hint {
  font-size: 0.78rem;
  color: #94a3b8;
}

.input-section__sample-link {
  font-size: 0.78rem;
  color: #2563eb;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.input-section__sample-link:hover { color: #1d4ed8; }

/* ============================================================
   LOADING
   ============================================================ */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem 0;
}

.loading__steps {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
  max-width: 340px;
}

.loading__step {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.875rem;
  color: #cbd5e1;
  transition: color 300ms;
}

.loading__step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e2e8f0;
  flex-shrink: 0;
  transition: background 300ms, box-shadow 300ms;
}

.loading__step--done .loading__step-dot { background: #22c55e; }
.loading__step--done { color: #475569; }

.loading__step--active .loading__step-dot {
  background: #2563eb;
  box-shadow: 0 0 0 4px rgba(37,99,235,0.18);
  animation: pulse-dot 1.2s ease-in-out infinite;
}
.loading__step--active { color: #0f172a; font-weight: 500; }

@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 4px rgba(37,99,235,0.18); }
  50%       { box-shadow: 0 0 0 7px rgba(37,99,235,0.07); }
}

/* ============================================================
   RESULTS
   ============================================================ */
.results {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.results__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.results__heading {
  font-size: 0.95rem;
  font-weight: 600;
  color: #0f172a;
}

/* ============================================================
   ERROR
   ============================================================ */
.error {
  background: #fff;
  border: 1px solid #fecaca;
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.error__message { font-weight: 600; color: #991b1b; }

.error__detail {
  font-size: 0.82rem;
  color: #6b7280;
  font-family: 'Courier New', monospace;
}

/* ============================================================
   STATUS BADGE
   ============================================================ */
.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.status-badge--pass    { background: #dcfce7; color: #166534; }
.status-badge--fail    { background: #fee2e2; color: #991b1b; }
.status-badge--unknown { background: #f3f4f6; color: #6b7280; }

/* ============================================================
   PATIENT CARD
   ============================================================ */
.patient-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.patient-card__title {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #2563eb;
  margin-bottom: 1rem;
}

.patient-card__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.patient-card__lists { display: flex; flex-direction: column; gap: 0.5rem; }

.patient-card__field { display: flex; flex-direction: column; gap: 3px; }

.patient-card__label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #94a3b8;
  font-weight: 600;
}

.patient-card__value {
  font-size: 0.875rem;
  color: #0f172a;
  font-weight: 500;
}

/* ============================================================
   TRIAL CARD
   ============================================================ */
.trial-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.trial-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.trial-card__name  { font-weight: 600; font-size: 0.95rem; color: #0f172a; }

.trial-card__id {
  display: inline-block;
  font-size: 0.75rem;
  color: #2563eb;
  margin-top: 3px;
  text-decoration: none;
}
.trial-card__id:hover { text-decoration: underline; }

.trial-card__score-label { font-size: 1.1rem; font-weight: 700; }

.trial-card__bar-track {
  height: 6px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}

.trial-card__bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 600ms ease;
}

.trial-card__toggle {
  align-self: flex-start;
  background: none;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.3rem 0.75rem;
  font-size: 0.8rem;
  cursor: pointer;
  color: #64748b;
  font-family: inherit;
  transition: background 150ms;
}
.trial-card__toggle:hover { background: #f8fafc; }

/* Criteria table */
.criteria-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.criteria-table th {
  text-align: left;
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid #e2e8f0;
  color: #64748b;
  font-weight: 600;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.criteria-table td {
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: top;
}
.criteria-table tr:last-child td { border-bottom: none; }

/* Missing info */
.trial-card__missing {
  margin-top: 0.25rem;
  padding: 0.75rem;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #f1f5f9;
}
.trial-card__missing-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 0.25rem;
}
.trial-card__missing ul {
  padding-left: 1.25rem;
  font-size: 0.8rem;
  color: #64748b;
}

/* ============================================================
   HISTORY DRAWER
   ============================================================ */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15,23,42,0.4);
  z-index: 20;
  opacity: 0;
  pointer-events: none;
  transition: opacity 200ms;
}
.drawer-overlay--open {
  opacity: 1;
  pointer-events: all;
}

.drawer {
  position: fixed;
  top: 0;
  right: 0;
  height: 100%;
  width: 320px;
  background: #fff;
  z-index: 30;
  display: flex;
  flex-direction: column;
  transform: translateX(100%);
  transition: transform 250ms cubic-bezier(0.4,0,0.2,1);
  box-shadow: -4px 0 24px rgba(0,0,0,0.12);
}
.drawer--open { transform: translateX(0); }

.drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.25rem 1rem;
  border-bottom: 1px solid #e2e8f0;
}
.drawer__title { font-size: 0.9rem; font-weight: 600; color: #0f172a; }
.drawer__close {
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  font-size: 1.4rem;
  line-height: 1;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: inherit;
}
.drawer__close:hover { background: #f1f5f9; color: #0f172a; }

.drawer__list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.drawer__empty {
  padding: 2rem 1rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.875rem;
}

.drawer__item {
  padding: 0.875rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: background 150ms, border-color 150ms;
  background: #fff;
  text-align: left;
  width: 100%;
  font-family: inherit;
}
.drawer__item:hover { background: #f8fafc; border-color: #2563eb; }

.drawer__item-snippet {
  font-size: 0.875rem;
  font-weight: 500;
  color: #0f172a;
  margin-bottom: 0.25rem;
}
.drawer__item-meta { font-size: 0.75rem; color: #94a3b8; }

.drawer__footer {
  padding: 0.875rem 1.25rem;
  border-top: 1px solid #e2e8f0;
  text-align: center;
}
.drawer__clear {
  background: none;
  border: none;
  cursor: pointer;
  color: #ef4444;
  font-size: 0.8rem;
  font-family: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.drawer__clear:hover { color: #b91c1c; }
```

- [ ] **Step 3: Run dev server and verify visual shell**

```bash
cd C:\Users\Stephen\t2d-trial-screener\frontend
npm run dev
```

Open `http://localhost:5173` (or 5174). Verify:
- Dark slate header bar renders with title and subtitle
- Body background is light blue-gray (`#f1f5f9`)
- Textarea has white card style with focus ring when clicked
- "Find Matching Trials" button is solid blue
- Font is Inter (check DevTools → Computed → font-family)

- [ ] **Step 4: Commit**

```bash
cd C:\Users\Stephen\t2d-trial-screener
git add frontend/index.html frontend/src/App.css
git commit -m "style: full CSS rewrite — modern clinical dashboard, Inter font"
```

---

### Task 2: Sample Note Button + Loading Step Indicator

**Files:**
- Modify: `src/App.jsx`

**Interfaces:**
- Consumes: `.input-section__footer`, `.input-section__sample-link`, `.loading__steps`, `.loading__step`, `.loading__step-dot`, `.loading__step--active`, `.loading__step--done` (all defined in Task 1)
- Produces: `SAMPLE_NOTE` constant, `loadingStep` state drives step indicator

- [ ] **Step 1: Replace `src/App.jsx` with this updated version**

The changes vs current file:
1. Add `SAMPLE_NOTE` constant after `LOADING_STEPS`
2. Restructure the input section footer to add the sample note link
3. Replace the spinner div with the step indicator

Full updated file:

```jsx
import { useState, useEffect, useRef } from 'react';
import PatientCard from './components/PatientCard';
import TrialCard from './components/TrialCard';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL;

const LOADING_STEPS = [
  'Extracting patient profile...',
  'Searching clinical trials...',
  'Checking eligibility criteria...',
  'Scoring matches...',
];

const SAMPLE_NOTE = `S: 58-year-old male presents for follow-up management of Type 2 Diabetes Mellitus, diagnosed 12 years ago. Reports increased fatigue and occasional blurred vision. Denies chest pain or edema.

O: Vitals: BP 142/88 mmHg, Weight 94 kg, Height 175 cm (BMI 30.7).
Labs: HbA1c 8.2%, eGFR 61 mL/min/1.73m², Creatinine 1.1 mg/dL, LDL 118, HDL 42.
Medications: Metformin 1000mg BID, Sitagliptin 100mg QD, Lisinopril 10mg QD, Atorvastatin 20mg QD, Aspirin 81mg QD.
PMH: T2DM (12 yrs), Hypertension, Hyperlipidemia, CKD Stage 2. Allergies: NKDA.

A: T2DM suboptimally controlled (HbA1c 8.2%). Hypertension not at goal (BP 142/88). CKD Stage 2 stable.

P: Consider GLP-1 agonist or SGLT2 inhibitor given CKD and CV risk. Increase Lisinopril to 20mg. Refer endocrinology, ophthalmology. Follow up 8 weeks.`;

export default function App() {
  const [view, setView] = useState('input');
  const [note, setNote] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const intervalRef = useRef(null);

  function startInterval() {
    setLoadingStep(0);
    intervalRef.current = setInterval(() => {
      setLoadingStep(s => Math.min(s + 1, LOADING_STEPS.length - 1));
    }, 20000);
  }

  function stopInterval() { clearInterval(intervalRef.current); }

  useEffect(() => () => stopInterval(), []);

  async function handleSubmit() {
    setView('loading');
    setError(null);
    startInterval();
    try {
      const res = await fetch(`${API_URL}/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setResult(data);
      setView('results');
    } catch (e) {
      setError(e.message);
      setView('error');
    } finally {
      stopInterval();
    }
  }

  function reset() {
    setView('input');
    setNote('');
    setResult(null);
    setError(null);
  }

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__header-inner">
          <div>
            <p className="app__title">T2D Trial Pre-Screener</p>
            <p className="app__subtitle">Clinical trial matching for Type 2 Diabetes</p>
          </div>
        </div>
      </header>

      <main className="app__main">
        {(view === 'input' || view === 'loading') && (
          <div className="input-section">
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
                <div className="input-section__footer">
                  <button
                    className="input-section__sample-link"
                    onClick={() => setNote(SAMPLE_NOTE)}
                  >
                    Load sample note
                  </button>
                  <p className="input-section__hint">Analysis takes ~90 seconds</p>
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
          </div>
        )}

        {view === 'results' && result && (
          <div className="results">
            <div className="results__actions">
              <button className="btn btn--secondary btn--sm" onClick={reset}>
                New Search
              </button>
            </div>
            <PatientCard patient={result.patient} />
            <h2 className="results__heading">
              {result.matches.length} Trial{result.matches.length !== 1 ? 's' : ''} Found
            </h2>
            {result.matches.map(m => (
              <TrialCard key={m.trial_id} match={m} />
            ))}
          </div>
        )}

        {view === 'error' && (
          <div className="error">
            <p className="error__message">Something went wrong. Please try again.</p>
            <p className="error__detail">{error}</p>
            <button className="btn btn--secondary" onClick={reset}>Try Again</button>
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

With `npm run dev` still running:
- Click "Load sample note" → textarea fills with the SOAP note
- Click "Find Matching Trials" — loading view shows a list of 4 steps, first step has a pulsing blue dot, text is bold
- (Cancel or wait) — step indicator should be visible

- [ ] **Step 3: Commit**

```bash
cd C:\Users\Stephen\t2d-trial-screener
git add frontend/src/App.jsx
git commit -m "feat: add sample note pre-fill and animated loading step indicator"
```

---

### Task 3: HistoryDrawer Component + App.jsx History Integration

**Files:**
- Create: `src/components/HistoryDrawer.jsx`
- Modify: `src/App.jsx`

**Interfaces:**
- Consumes: All `.drawer-*` CSS classes from Task 1
- Produces:
  - `HistoryDrawer` component: `props = { open: bool, history: HistoryEntry[], onClose: () => void, onRestore: (entry) => void, onClear: () => void }`
  - `HistoryEntry` shape: `{ id: string, timestamp: string, snippet: string, matchCount: number, result: object }`
  - `buildSnippet(patient): string` — e.g. `"58 yrs • HbA1c 8.2% • BMI 30.7"`

- [ ] **Step 1: Create `src/components/HistoryDrawer.jsx`**

```jsx
import { useEffect } from 'react';

function formatDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function HistoryDrawer({ open, history, onClose, onRestore, onClear }) {
  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose(); }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <>
      <div
        className={`drawer-overlay${open ? ' drawer-overlay--open' : ''}`}
        onClick={onClose}
      />
      <aside className={`drawer${open ? ' drawer--open' : ''}`}>
        <div className="drawer__header">
          <span className="drawer__title">Recent Searches</span>
          <button className="drawer__close" onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="drawer__list">
          {history.length === 0 ? (
            <p className="drawer__empty">No searches yet.</p>
          ) : (
            history.map(entry => (
              <button
                key={entry.id}
                className="drawer__item"
                onClick={() => onRestore(entry)}
              >
                <p className="drawer__item-snippet">{entry.snippet}</p>
                <p className="drawer__item-meta">
                  {entry.matchCount} trial{entry.matchCount !== 1 ? 's' : ''} · {formatDate(entry.timestamp)}
                </p>
              </button>
            ))
          )}
        </div>

        {history.length > 0 && (
          <div className="drawer__footer">
            <button className="drawer__clear" onClick={onClear}>Clear history</button>
          </div>
        )}
      </aside>
    </>
  );
}
```

- [ ] **Step 2: Update `src/App.jsx` — add history state + drawer + wire HistoryDrawer**

Replace the entire file with:

```jsx
import { useState, useEffect, useRef } from 'react';
import PatientCard from './components/PatientCard';
import TrialCard from './components/TrialCard';
import HistoryDrawer from './components/HistoryDrawer';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL;

const LOADING_STEPS = [
  'Extracting patient profile...',
  'Searching clinical trials...',
  'Checking eligibility criteria...',
  'Scoring matches...',
];

const SAMPLE_NOTE = `S: 58-year-old male presents for follow-up management of Type 2 Diabetes Mellitus, diagnosed 12 years ago. Reports increased fatigue and occasional blurred vision. Denies chest pain or edema.

O: Vitals: BP 142/88 mmHg, Weight 94 kg, Height 175 cm (BMI 30.7).
Labs: HbA1c 8.2%, eGFR 61 mL/min/1.73m², Creatinine 1.1 mg/dL, LDL 118, HDL 42.
Medications: Metformin 1000mg BID, Sitagliptin 100mg QD, Lisinopril 10mg QD, Atorvastatin 20mg QD, Aspirin 81mg QD.
PMH: T2DM (12 yrs), Hypertension, Hyperlipidemia, CKD Stage 2. Allergies: NKDA.

A: T2DM suboptimally controlled (HbA1c 8.2%). Hypertension not at goal (BP 142/88). CKD Stage 2 stable.

P: Consider GLP-1 agonist or SGLT2 inhibitor given CKD and CV risk. Increase Lisinopril to 20mg. Refer endocrinology, ophthalmology. Follow up 8 weeks.`;

function buildSnippet(patient) {
  const parts = [];
  if (patient.age != null) parts.push(`${patient.age} yrs`);
  if (patient.hba1c != null) parts.push(`HbA1c ${patient.hba1c}%`);
  if (patient.bmi != null) parts.push(`BMI ${patient.bmi}`);
  return parts.join(' • ') || 'Patient';
}

export default function App() {
  const [view, setView] = useState('input');
  const [note, setNote] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [history, setHistory] = useState(() => {
    try { return JSON.parse(localStorage.getItem('t2d_history') || '[]'); }
    catch { return []; }
  });
  const intervalRef = useRef(null);

  function startInterval() {
    setLoadingStep(0);
    intervalRef.current = setInterval(() => {
      setLoadingStep(s => Math.min(s + 1, LOADING_STEPS.length - 1));
    }, 20000);
  }

  function stopInterval() { clearInterval(intervalRef.current); }

  useEffect(() => () => stopInterval(), []);

  function saveHistory(data) {
    const entry = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      snippet: buildSnippet(data.patient),
      matchCount: data.matches.length,
      result: data,
    };
    const next = [entry, ...history].slice(0, 5);
    setHistory(next);
    try { localStorage.setItem('t2d_history', JSON.stringify(next)); } catch {}
  }

  async function handleSubmit() {
    setView('loading');
    setError(null);
    startInterval();
    try {
      const res = await fetch(`${API_URL}/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setResult(data);
      saveHistory(data);
      setView('results');
    } catch (e) {
      setError(e.message);
      setView('error');
    } finally {
      stopInterval();
    }
  }

  function reset() {
    setView('input');
    setNote('');
    setResult(null);
    setError(null);
  }

  function restoreFromHistory(entry) {
    setResult(entry.result);
    setView('results');
    setDrawerOpen(false);
  }

  function clearHistory() {
    setHistory([]);
    try { localStorage.removeItem('t2d_history'); } catch {}
  }

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__header-inner">
          <div>
            <p className="app__title">T2D Trial Pre-Screener</p>
            <p className="app__subtitle">Clinical trial matching for Type 2 Diabetes</p>
          </div>
          <button className="btn btn--ghost" onClick={() => setDrawerOpen(true)}>
            Recent Searches
          </button>
        </div>
      </header>

      <main className="app__main">
        {(view === 'input' || view === 'loading') && (
          <div className="input-section">
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
                <div className="input-section__footer">
                  <button
                    className="input-section__sample-link"
                    onClick={() => setNote(SAMPLE_NOTE)}
                  >
                    Load sample note
                  </button>
                  <p className="input-section__hint">Analysis takes ~90 seconds</p>
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
          </div>
        )}

        {view === 'results' && result && (
          <div className="results">
            <div className="results__actions">
              <button className="btn btn--secondary btn--sm" onClick={reset}>
                New Search
              </button>
            </div>
            <PatientCard patient={result.patient} />
            <h2 className="results__heading">
              {result.matches.length} Trial{result.matches.length !== 1 ? 's' : ''} Found
            </h2>
            {result.matches.map(m => (
              <TrialCard key={m.trial_id} match={m} />
            ))}
          </div>
        )}

        {view === 'error' && (
          <div className="error">
            <p className="error__message">Something went wrong. Please try again.</p>
            <p className="error__detail">{error}</p>
            <button className="btn btn--secondary" onClick={reset}>Try Again</button>
          </div>
        )}
      </main>

      <HistoryDrawer
        open={drawerOpen}
        history={history}
        onClose={() => setDrawerOpen(false)}
        onRestore={restoreFromHistory}
        onClear={clearHistory}
      />
    </div>
  );
}
```

- [ ] **Step 3: Verify in browser**

- Click "Recent Searches" button in header → drawer slides in from right, overlay dims the background
- Drawer shows "No searches yet."
- Press Escape or click backdrop → drawer closes
- Load sample note, submit a search, wait for results
- Click "Recent Searches" → entry appears: snippet (e.g. `58 yrs • HbA1c 8.2% • BMI 30.7`), match count, timestamp
- Click the entry → results view restores, drawer closes
- Click "Clear history" → list empties
- Refresh page → history is empty (was cleared from localStorage)

- [ ] **Step 4: Commit**

```bash
cd C:\Users\Stephen\t2d-trial-screener
git add frontend/src/App.jsx frontend/src/components/HistoryDrawer.jsx
git commit -m "feat: add search history drawer with localStorage persistence"
```

---

### Task 4: Copy Results + Download CSV

**Files:**
- Modify: `src/App.jsx`

**Interfaces:**
- Consumes: `result` state (shape: `{ patient: object, matches: Array<{ trial_id, trial_name, score, criteria: Array<{ criterion, status, patient_value }> }> }`)
- Produces: `handleCopy()`, `handleDownloadCSV()`, `copied` state for button label toggle

- [ ] **Step 1: Add helpers and handlers to `src/App.jsx`**

Add these two pure functions before the `App` component (after `buildSnippet`):

```jsx
function buildCopyText(result) {
  const p = result.patient;
  const fmt = (val, unit) => val != null ? `${val}${unit}` : '—';
  const lines = [
    'T2D Trial Pre-Screener Results',
    '',
    'Patient Profile:',
    `Age: ${fmt(p.age, ' yrs')} | HbA1c: ${fmt(p.hba1c, '%')} | BMI: ${fmt(p.bmi, '')} | eGFR: ${fmt(p.egfr, ' mL/min')}`,
    `BP: ${fmt(p.systolic_bp, '')}/${fmt(p.diastolic_bp, '')} mmHg | Weight: ${fmt(p.weight_kg, ' kg')}`,
    `Medications: ${p.medications?.join(', ') || '—'}`,
    `Diagnoses: ${p.diagnoses?.join(', ') || '—'}`,
    '',
    `Matched Trials (${result.matches.length}):`,
    '',
  ];
  result.matches.forEach((m, i) => {
    const pct = Math.round(m.score * 100);
    lines.push(`${i + 1}. ${m.trial_name} (${m.trial_id}) — ${pct}%`);
    m.criteria.forEach(c => {
      const sym = c.status === 'PASS' ? '✓' : c.status === 'FAIL' ? '✗' : '?';
      lines.push(`   ${sym} ${c.criterion}: ${c.status}${c.patient_value ? ` (${c.patient_value})` : ''}`);
    });
    lines.push('');
  });
  return lines.join('\n');
}

function buildCSV(result) {
  const rows = [['Trial Name', 'Trial ID', 'Score (%)', 'Criterion', 'Status', 'Patient Value']];
  result.matches.forEach(m => {
    const pct = Math.round(m.score * 100);
    m.criteria.forEach(c => {
      rows.push([
        `"${m.trial_name.replace(/"/g, '""')}"`,
        m.trial_id,
        pct,
        `"${c.criterion.replace(/"/g, '""')}"`,
        c.status,
        c.patient_value ? `"${String(c.patient_value).replace(/"/g, '""')}"` : '',
      ]);
    });
  });
  return rows.map(r => r.join(',')).join('\n');
}
```

- [ ] **Step 2: Add `copied` state and handlers inside the `App` component**

Add `const [copied, setCopied] = useState(false);` alongside the other state declarations.

Add these two functions inside `App` (after `clearHistory`):

```jsx
async function handleCopy() {
  try {
    await navigator.clipboard.writeText(buildCopyText(result));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  } catch {}
}

function handleDownloadCSV() {
  const csv = buildCSV(result);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 't2d-screener-results.csv';
  a.click();
  URL.revokeObjectURL(url);
}
```

- [ ] **Step 3: Add Copy and CSV buttons to the results actions row**

Find the `results__actions` div in the JSX (currently has only "New Search"). Replace it with:

```jsx
<div className="results__actions">
  <button className="btn btn--secondary btn--sm" onClick={reset}>
    New Search
  </button>
  <button className="btn btn--secondary btn--sm" onClick={handleCopy}>
    {copied ? 'Copied!' : 'Copy Results'}
  </button>
  <button className="btn btn--secondary btn--sm" onClick={handleDownloadCSV}>
    Download CSV
  </button>
</div>
```

- [ ] **Step 4: Verify in browser**

With a completed results view showing:
- Three buttons appear in a row: "New Search", "Copy Results", "Download CSV"
- Click "Copy Results" → button label changes to "Copied!" for 2 seconds, then resets
- Paste into a text editor → plain text summary with patient profile and trial list
- Click "Download CSV" → browser downloads `t2d-screener-results.csv`
- Open CSV in Excel/Sheets → columns: Trial Name, Trial ID, Score (%), Criterion, Status, Patient Value; one row per criterion

- [ ] **Step 5: Commit**

```bash
cd C:\Users\Stephen\t2d-trial-screener
git add frontend/src/App.jsx
git commit -m "feat: add copy results to clipboard and CSV download"
```

---

### Task 5: TrialCard NCT Link + Score Color Refresh

**Files:**
- Modify: `src/components/TrialCard.jsx`

**Interfaces:**
- Consumes: `.trial-card__id` (styled as link in Task 1 CSS)
- Produces: NCT ID renders as `<a>` linking to `https://clinicaltrials.gov/study/{trial_id}`

- [ ] **Step 1: Update `src/components/TrialCard.jsx`**

Replace the entire file with:

```jsx
import { useState } from 'react';
import StatusBadge from './StatusBadge';

function scoreColor(score) {
  if (score >= 0.7) return '#16a34a';
  if (score >= 0.4) return '#d97706';
  return '#dc2626';
}

export default function TrialCard({ match }) {
  const [expanded, setExpanded] = useState(false);
  const { trial_id, trial_name, score, criteria, missing_info } = match;
  const pct = Math.round(score * 100);

  return (
    <div className="trial-card">
      <div className="trial-card__header">
        <div>
          <p className="trial-card__name">{trial_name}</p>
          <a
            className="trial-card__id"
            href={`https://clinicaltrials.gov/study/${trial_id}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {trial_id} ↗
          </a>
        </div>
        <span className="trial-card__score-label" style={{ color: scoreColor(score) }}>
          {pct}%
        </span>
      </div>

      <div className="trial-card__bar-track">
        <div
          className="trial-card__bar-fill"
          style={{ width: `${pct}%`, background: scoreColor(score) }}
        />
      </div>

      <button
        className="trial-card__toggle"
        onClick={() => setExpanded(e => !e)}
      >
        {expanded ? 'Hide criteria' : 'Show criteria'}
      </button>

      {expanded && (
        <div className="trial-card__criteria">
          <table className="criteria-table">
            <thead>
              <tr>
                <th>Criterion</th>
                <th>Status</th>
                <th>Patient Value</th>
              </tr>
            </thead>
            <tbody>
              {criteria.map((c, i) => (
                <tr key={i}>
                  <td>{c.criterion}</td>
                  <td><StatusBadge status={c.status} /></td>
                  <td>{c.patient_value ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {missing_info.length > 0 && (
            <div className="trial-card__missing">
              <p className="trial-card__missing-label">Missing information:</p>
              <ul>
                {missing_info.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

With results showing:
- Each trial card's NCT ID (e.g. `NCT04128020`) is a blue link followed by `↗`
- Clicking the NCT ID opens `https://clinicaltrials.gov/study/NCT04128020` in a new tab
- Score bar color reflects score (green ≥70%, amber 40–69%, red <40%)

- [ ] **Step 3: Commit**

```bash
cd C:\Users\Stephen\t2d-trial-screener
git add frontend/src/components/TrialCard.jsx
git commit -m "feat: NCT ID links to clinicaltrials.gov, refresh score color palette"
```

---

### Task 6: Build + Deploy to Vercel

**Files:**
- No source changes — build and push only

**Interfaces:**
- Consumes: All completed tasks 1–5
- Produces: Updated live URL at Vercel

- [ ] **Step 1: Confirm `.env` is set correctly**

Check that `frontend/.env` contains:
```
VITE_API_URL=https://t2d-trial-screener-production.up.railway.app
```

- [ ] **Step 2: Build and check for errors**

```bash
cd C:\Users\Stephen\t2d-trial-screener\frontend
npm run build
```

Expected: build completes with no errors. Output goes to `frontend/dist/`.

- [ ] **Step 3: Push to trigger Vercel redeploy**

```bash
cd C:\Users\Stephen\t2d-trial-screener
git push
```

Vercel will auto-redeploy on push (it was already linked). Watch for a successful build in the Vercel dashboard or run:

```bash
npx vercel --prod
```

if you prefer a manual production deploy.

- [ ] **Step 4: Smoke test the live URL**

Open `https://frontend-gray-chi-cjlfezgi0t.vercel.app` and verify:
- Dark header renders, Inter font loads
- "Load sample note" fills the textarea
- "Recent Searches" button opens the drawer
- After a completed search: Copy Results, Download CSV, NCT links, and history drawer entry all work
