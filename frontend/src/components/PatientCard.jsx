const FIELDS = [
  { label: 'Age',         key: 'age',          unit: ' yrs' },
  { label: 'HbA1c',      key: 'hba1c',        unit: '%'    },
  { label: 'BMI',        key: 'bmi',          unit: ''     },
  { label: 'eGFR',       key: 'egfr',         unit: ' mL/min' },
  { label: 'Systolic BP', key: 'systolic_bp',  unit: ' mmHg' },
  { label: 'Diastolic BP',key: 'diastolic_bp', unit: ' mmHg' },
  { label: 'Weight',     key: 'weight_kg',    unit: ' kg'  },
];

export default function PatientCard({ patient }) {
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
        <div className="patient-card__field">
          <span className="patient-card__label">Medications</span>
          <span className="patient-card__value">{fmtList(patient.medications)}</span>
        </div>
        <div className="patient-card__field">
          <span className="patient-card__label">Diagnoses</span>
          <span className="patient-card__value">{fmtList(patient.diagnoses)}</span>
        </div>
      </div>
    </div>
  );
}
