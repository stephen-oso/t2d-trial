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
