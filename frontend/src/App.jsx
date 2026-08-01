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

export default function App() {
  const [view, setView] = useState('input');
  const [note, setNote] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [copied, setCopied] = useState(false);
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
              <button className="btn btn--secondary btn--sm" onClick={handleCopy}>
                {copied ? 'Copied!' : 'Copy Results'}
              </button>
              <button className="btn btn--secondary btn--sm" onClick={handleDownloadCSV}>
                Download CSV
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
