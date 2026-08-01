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
