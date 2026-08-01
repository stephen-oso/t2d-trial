# T2D Trial Pre-Screener — Frontend Redesign & Feature Completion

**Date:** 2026-08-01  
**Status:** Approved  

---

## Overview

Redesign and complete the Vite+React frontend for the T2D Trial Pre-Screener. The backend is live on Railway and fully functional. The frontend has working logic (state machine, API integration, components) but is missing most layout/button/form CSS and has no polish. This spec covers a visual redesign to a modern clinical dashboard aesthetic plus four new features.

---

## Visual Design

### Color & Typography
- **Font:** Inter (loaded via Google Fonts) — replaces system stack
- **Base background:** `#f1f5f9`
- **Card background:** `#ffffff`
- **Header bar:** `#1e293b` (dark slate)
- **Primary accent:** `#2563eb` (blue)
- **Text primary:** `#0f172a`
- **Text secondary:** `#64748b`
- **Border:** `#e2e8f0`

### Layout
- Centered container, `max-width: 720px`, `padding: 0 1.5rem`
- Header bar spans full width with title left-aligned and "Recent Searches" button top-right
- Cards use `border-radius: 12px` and `box-shadow: 0 1px 4px rgba(0,0,0,0.08)`
- Consistent 8px spacing grid

### Buttons
- **Primary:** solid `#2563eb` fill, white text, hover darkens to `#1d4ed8`, `border-radius: 8px`
- **Secondary/ghost:** white background, `#e2e8f0` border, `#374151` text
- Smooth `150ms` transitions on hover

### Score Bar
- Gradient fill: red (`#ef4444`) at 0% → amber (`#f59e0b`) at ~50% → green (`#22c55e`) at 100%
- Implemented via dynamic inline `background` using score percentage

### Status Badges
- Pill shape (`border-radius: 9999px`), slightly larger (`font-size: 0.8rem`, `padding: 3px 10px`)
- PASS: green; FAIL: red; UNKNOWN: gray (existing palette kept)

### Loading State
- Spinner replaced with animated step indicator — 4 steps shown as a progress list, active step highlighted in blue
- Steps: "Extracting patient profile", "Searching clinical trials", "Checking eligibility criteria", "Scoring matches"

---

## Features

### 1. Sample Note Button
- "Load sample note" text link below the textarea
- Pre-fills a realistic T2D SOAP note (58-year-old male, HbA1c 8.2%, BMI 31, metformin + sitagliptin, hypertension comorbidity)
- Clicking it replaces textarea content

### 2. ClinicalTrials.gov Links
- Each `TrialCard` NCT ID becomes an anchor: `https://clinicaltrials.gov/study/{trial_id}`
- Opens in new tab, `rel="noopener noreferrer"`
- Styled as a subtle link (no underline until hover)

### 3. Copy Results (Clipboard)
- "Copy Results" button in the results header row (next to "New Search")
- Copies a plain-text summary: patient profile fields + each trial name, score, and per-criterion status
- Button label toggles to "Copied!" for 2 seconds after click

### 4. Export CSV
- "Download CSV" button in the results header row
- Generates a CSV with columns: Trial Name, Trial ID, Score (%), Criterion, Status, Patient Value
- One row per criterion per trial — flat structure, easy to open in Excel
- Download triggered via `Blob` + anchor click (no library needed)

### 5. History Drawer
- Last 5 searches persisted in `localStorage` as JSON (keyed by timestamp)
- Each entry stores: timestamp, patient profile summary (age, HbA1c, BMI), match count, full result payload
- "Recent Searches" button in header opens a right-side slide-in drawer (`position: fixed`)
- Drawer shows list of entries: date, patient snippet, match count
- Clicking an entry restores the full result view
- "Clear history" link at drawer bottom
- Drawer closes on backdrop click or Escape key

---

## Architecture

No new dependencies added. All features implemented with plain React + vanilla JS:
- CSV export: `Blob` + programmatic anchor click
- Clipboard: `navigator.clipboard.writeText`
- History: `localStorage` read/write in `App.jsx`
- Drawer: CSS `transform: translateX` toggle, `position: fixed` overlay

### File changes
| File | Change |
|------|--------|
| `index.html` | Add Inter font `<link>` |
| `src/App.css` | Full rewrite — adds all missing classes + redesign |
| `src/App.jsx` | Add history state, drawer toggle, copy/export handlers, sample note |
| `src/components/TrialCard.jsx` | Add NCT ID link |
| `src/components/PatientCard.jsx` | Minor style updates only |
| `src/components/StatusBadge.jsx` | No changes |
| `src/components/HistoryDrawer.jsx` | New component — drawer UI |

---

## Error Handling

- Clipboard API unavailable: catch the rejection silently, skip the "Copied!" toggle
- localStorage unavailable (private browsing): wrap reads/writes in try/catch, history feature degrades gracefully (no crash)
- History entry with missing fields: defensive access with optional chaining when rendering drawer entries

---

## Out of Scope
- PDF export (requires a library; CSV covers the clinical use case)
- Pagination of history beyond 5 entries
- Backend changes
