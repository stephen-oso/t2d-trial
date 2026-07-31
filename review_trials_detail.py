import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

candidates = [
    "NCT04932928.json",
    "NCT05776563.json",
    "NCT06942195.json",
    "NCT07716059.json",
    "NCT07303803.json",
    "NCT06028503.json",
    "NCT06524960.json",
    "NCT05307731.json",
    "NCT06752018.json",
    "NCT07237685.json",
    "NCT07093476.json",
    "NCT06652763.json",
]

trials_dir = Path("data/trials")
for fname in candidates:
    f = trials_dir / fname
    if not f.exists():
        print(f"MISSING: {fname}")
        continue
    d = json.loads(f.read_text(encoding="utf-8"))
    print(f"=== {fname} ===")
    print(f"Title: {d['title']}")
    print(f"Status: {d['status']}")
    print(f"INCLUSION ({len(d['inclusion'])}):")
    for i, c in enumerate(d["inclusion"], 1):
        print(f"  {i}. {c[:130]}")
    print(f"EXCLUSION ({len(d['exclusion'])}):")
    for i, c in enumerate(d["exclusion"], 1):
        print(f"  {i}. {c[:130]}")
    print()
