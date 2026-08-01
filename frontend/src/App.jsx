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

  function stopInterval() {
    clearInterval(intervalRef.current);
  }

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
        <h1>T2D Trial Pre-Screener</h1>
        <p>Paste a patient note to find matching clinical trials.</p>
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
                <button
                  className="btn btn--primary"
                  onClick={handleSubmit}
                  disabled={note.trim().length === 0}
                >
                  Find Matching Trials
                </button>
                <p className="input-section__hint">Analysis takes ~90 seconds</p>
              </>
            )}
            {view === 'loading' && (
              <div className="loading">
                <div className="loading__spinner" />
                <p className="loading__message">{LOADING_STEPS[loadingStep]}</p>
              </div>
            )}
          </div>
        )}

        {view === 'results' && result && (
          <div className="results">
            <button className="btn btn--secondary" onClick={reset}>
              New Search
            </button>
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
            <button className="btn btn--secondary" onClick={reset}>
              Try Again
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
