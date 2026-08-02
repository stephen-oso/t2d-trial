"""Batch evaluation runner for T2D Trial Pre-Screener.

Hits the Railway API sequentially (each call ~90s due to Groq rate-limit sleep).
20 cases = ~30 minutes total.

Usage:
    python eval_runner.py
    python eval_runner.py --api http://localhost:8000   # local backend
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

API_URL = "https://t2d-trial-screener-production.up.railway.app"

for arg in sys.argv[1:]:
    if arg.startswith("--api"):
        _, _, val = arg.partition("=")
        if not val and sys.argv.index(arg) + 1 < len(sys.argv):
            val = sys.argv[sys.argv.index(arg) + 1]
        API_URL = val.rstrip("/")

CASES_PATH = Path(__file__).parent / "data" / "test_cases" / "cases.json"
cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

print(f"Evaluating {len(cases)} cases against {API_URL}\n")
print("=" * 72)

results = []

for i, case in enumerate(cases, 1):
    case_id = case["id"]
    note = case["note"]
    expected = set(case["correct_trial_ids"])
    should_match = case["should_match"]

    print(f"\n[{i:02d}/{len(cases)}] {case_id}  (expected: {len(expected)} trial(s))")
    t0 = time.time()

    try:
        payload = json.dumps({"note": note}).encode()
        req = urllib.request.Request(
            f"{API_URL}/match",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read())
        elapsed = time.time() - t0

        predicted = {m["trial_id"] for m in body.get("matches", []) if m["score"] > 0}
        tp = predicted & expected
        fp = predicted - expected
        fn = expected - predicted

        precision = len(tp) / len(predicted) if predicted else (1.0 if not expected else 0.0)
        recall    = len(tp) / len(expected)  if expected  else (1.0 if not predicted else 0.0)

        status = "OK" if (not predicted and not expected) or (predicted == expected) else "PARTIAL" if tp else "MISS"

        print(f"  Elapsed : {elapsed:.0f}s")
        print(f"  Got     : {sorted(predicted) or '(none)'}")
        print(f"  Expected: {sorted(expected) or '(none)'}")
        print(f"  TP={len(tp)}  FP={len(fp)}  FN={len(fn)}  P={precision:.2f}  R={recall:.2f}  [{status}]")

        if fp:
            print(f"  False+  : {sorted(fp)}")
        if fn:
            print(f"  Missed  : {sorted(fn)}")

        # Top-scoring match details
        matches = sorted(body.get("matches", []), key=lambda m: m["score"], reverse=True)
        for m in matches[:3]:
            score_pct = f"{m['score']*100:.0f}%"
            passes = sum(1 for c in m["criteria"] if c["status"] == "PASS")
            fails  = sum(1 for c in m["criteria"] if c["status"] == "FAIL")
            unknowns = sum(1 for c in m["criteria"] if c["status"] == "UNKNOWN")
            print(f"  {score_pct:>4s}  {m['trial_id']}  P{passes}/F{fails}/U{unknowns}")

        results.append({
            "case_id": case_id,
            "predicted": predicted,
            "expected": expected,
            "tp": len(tp), "fp": len(fp), "fn": len(fn),
            "precision": precision, "recall": recall,
            "status": status,
            "elapsed": elapsed,
        })

    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERROR {e.code}: {body[:200]}")
        results.append({"case_id": case_id, "status": "ERROR", "predicted": set(), "expected": expected,
                        "tp": 0, "fp": 0, "fn": len(expected), "precision": 0.0, "recall": 0.0, "elapsed": 0})
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        results.append({"case_id": case_id, "status": "ERROR", "predicted": set(), "expected": expected,
                        "tp": 0, "fp": 0, "fn": len(expected), "precision": 0.0, "recall": 0.0, "elapsed": 0})

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("SUMMARY")
print("=" * 72)

total_tp = sum(r["tp"] for r in results)
total_fp = sum(r["fp"] for r in results)
total_fn = sum(r["fn"] for r in results)

macro_p = sum(r["precision"] for r in results) / len(results)
macro_r = sum(r["recall"]    for r in results) / len(results)

micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0.0

perfect   = sum(1 for r in results if r["status"] in ("OK",))
errors    = sum(1 for r in results if r["status"] == "ERROR")
avg_time  = sum(r["elapsed"] for r in results) / len(results)

print(f"Cases      : {len(results)} total  ({perfect} exact match, {errors} errors)")
print(f"Macro P/R  : {macro_p:.3f} / {macro_r:.3f}")
print(f"Micro P/R/F1: {micro_p:.3f} / {micro_r:.3f} / {micro_f1:.3f}")
print(f"Avg latency: {avg_time:.0f}s per case")
print(f"Total TP/FP/FN: {total_tp}/{total_fp}/{total_fn}")

print("\nPer-case:")
for r in results:
    tag = "✓" if r["status"] == "OK" else "~" if r["status"] == "PARTIAL" else "✗"
    print(f"  {tag} {r['case_id']}  P={r['precision']:.2f} R={r['recall']:.2f}  "
          f"TP={r['tp']} FP={r['fp']} FN={r['fn']}")
