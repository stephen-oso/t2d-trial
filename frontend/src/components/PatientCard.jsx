const FIELDS = [
  { label: 'Age',        key: 'age',             unit: ' yrs'    },
  { label: 'HbA1c',     key: 'hba1c',           unit: '%'       },
  { label: 'FPG',       key: 'fasting_glucose',  unit: ' mg/dL'  },
  { label: 'OGTT 2hr',  key: 'ogtt_2hr',         unit: ' mg/dL'  },
  { label: 'BMI',       key: 'bmi',              unit: ''        },
  { label: 'eGFR',      key: 'egfr',             unit: ' mL/min' },
  { label: 'AST',       key: 'ast',              unit: ' U/L'    },
  { label: 'ALT',       key: 'alt',              unit: ' U/L'    },
  { label: 'ALP',       key: 'alp',              unit: ' U/L'    },
  { label: 'Bilirubin', key: 'bilirubin',        unit: ' mg/dL'  },
];

export default function PatientCard({ patient, location }) {
  const fmt = (val, unit) => val != null ? `${val}${unit}` : '—';
  const fmtList = (arr) =>
    Array.isArray(arr) && arr.length > 0 ? arr.join(', ') : '—';

  return (
    <div className="patient-card">
      <h2 className="patient-card__title">Extracted Patient Profile</h2>
      <div className="patient-card__grid">
        {FIELDS.map(({ label, key, unit }) => (
          <div key={key} className="patient-card__field">
            <span className="patient-card__label">{label}</span>
            <span className="patient-card__value">{fmt(patient[key], unit)}</span>
          </div>
        ))}
      </div>
      <div className="patient-card__lists">
        {location && (
          <div className="patient-card__field">
            <span className="patient-card__label">Location</span>
            <span className="patient-card__value">{location}</span>
          </div>
        )}
        <div className="patient-card__field">
          <span className="patient-card__label">Medications</span>
          <span className="patient-card__value">{fmtList(patient.current_medications)}</span>
        </div>
        <div className="patient-card__field">
          <span className="patient-card__label">Exclusion Flags</span>
          <span className="patient-card__value">{fmtList(patient.exclusion_flags)}</span>
        </div>
      </div>
    </div>
  );
}
