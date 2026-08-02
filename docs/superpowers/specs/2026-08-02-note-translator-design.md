# Note Translator — Design Spec
**Date:** 2026-08-02  
**Project:** T2D Trial Pre-Screener  
**Status:** Approved

---

## Problem

The trial matcher extracts a PatientProfile from a SOAP note. When key fields (FPG, OGTT, liver enzymes, etc.) are absent from the note, those fields come back null and the eligibility checker returns UNKNOWN for every criterion that depends on them. The note translator reduces UNKNOWNs by helping the user bring their note up to the level of detail the matcher needs.

---

## Goal

Give users a way to paste a rough or incomplete SOAP note and receive a cleaned-up, SOAP-formatted version with explicit placeholders for any missing fields — so they can fill in real values from the chart before running the matcher.

---

## What We Are NOT Building

- No hallucinated values. The translator never invents clinical data.
- No mandatory form before submission. Optimizing is optional.
- No multi-step question wizard. Single-pass rewrite only.

---

## User Flow

1. User lands on the input screen — default tab is **"Optimize Note"**
2. User pastes their raw note (can be messy, incomplete, informal)
3. Clicks **"Optimize Note"** button
4. ~5 second loading state while API call runs
5. Optimized SOAP note appears in an editable textarea below
6. A summary banner lists missing fields: *"Missing: FPG, OGTT, AST — fill in what you have"*
7. User edits the note inline, fills in values they have, deletes placeholders they don't
8. Clicks **"Use This Note →"** — note is copied into the **"Find Trials"** tab and view switches
9. User adds optional location and clicks **"Find Matching Trials"**

Users can skip the Optimize tab entirely and go straight to Find Trials — nothing is gated.

---

## Architecture

### Backend

**New file:** `extraction/optimize.py`  
**New endpoint:** `POST /optimize` in `api/main.py`  
**New models:** `OptimizeRequest`, `OptimizeResponse` in `api/models.py`

#### `OptimizeRequest`
```python
class OptimizeRequest(BaseModel):
    note: str = Field(min_length=10)
```

#### `OptimizeResponse`
```python
class OptimizeResponse(BaseModel):
    optimized_note: str
    missing_fields: list[str]
```

#### `optimize_note(note: str) -> dict`

Calls Claude Haiku with a single prompt that:
1. Rewrites the note as clean SOAP format (S / O / A / P sections)
2. Preserves all existing clinical values exactly as written
3. Inserts `[not found — add if available]` placeholders in the O section for any of these fields not present in the original note:
   - HbA1c, Fasting Plasma Glucose (FPG), OGTT 2-hour glucose
   - BMI, eGFR, AST, ALT, ALP, Total Bilirubin
   - Age, Sex, Months since T2D diagnosis
   - Current medications, Insulin use
4. Returns the optimized note as a string

The function also parses which fields received placeholders and returns them as `missing_fields` (plain names, e.g. `["FPG", "OGTT", "AST"]`).

Error handling: wraps Claude call in try/except; on failure returns the original note unchanged with an empty `missing_fields` list.

---

### Frontend

#### Tab structure (`App.jsx`)

Two tabs replace the current single input view:
- **"Optimize Note"** — default, the new translator tab
- **"Find Trials"** — existing flow, unchanged internally

Tab state is a simple string: `'optimize' | 'find'`.

#### Optimize tab components

- Textarea for raw note input (same styling as existing textarea)
- **"Optimize Note"** button — disabled when textarea is empty, shows spinner during API call
- Editable result textarea — appears after successful API call, pre-filled with optimized note
- Missing fields banner — appears below result textarea: *"Missing: FPG, OGTT, AST — fill in what you have"* (hidden if `missing_fields` is empty)
- **"Use This Note →"** button — copies optimized note into Find Trials tab's note state and switches tab

#### Find Trials tab

Identical to current input view. Accepts pre-filled note from Optimize tab via shared state. Location input and submit button unchanged.

#### State additions to `App.jsx`
```js
const [tab, setTab] = useState('optimize');
const [rawNote, setRawNote] = useState('');
const [optimizedNote, setOptimizedNote] = useState('');
const [missingFields, setMissingFields] = useState([]);
const [optimizing, setOptimizing] = useState(false);
```

The existing `note` state (used by Find Trials) stays as-is. The Optimize tab writes into it when the user clicks "Use This Note →".

---

## Data Flow

```
User pastes note → POST /optimize → Claude Haiku rewrites + flags gaps
→ editable result textarea + missing fields banner
→ user edits → "Use This Note →" → note state in Find Trials tab
→ POST /match (existing flow)
```

---

## Files Changed

| File | Change |
|---|---|
| `extraction/optimize.py` | New — `optimize_note()` function |
| `api/models.py` | Add `OptimizeRequest`, `OptimizeResponse` |
| `api/main.py` | Add `POST /optimize` endpoint |
| `frontend/src/App.jsx` | Add tab state, optimize tab UI, shared note state |
| `frontend/src/App.css` | Tab styles, missing fields banner styles |

No changes to: `matching/`, `extraction/extract.py`, `extraction/models.py`, `TrialCard`, `PatientCard`, `HistoryDrawer`.

---

## Out of Scope

- Saving optimized notes to history
- Diff view showing what changed between original and optimized
- Per-field explanations of why a value matters
