"""One-shot end-to-end run of answer_rules on the blind set (SPEC.md §5); writes results.json.
Run from the repo root: .venv/Scripts/python evidence/blind-eval/run_blind_eval.py"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import guard, rules

SP = Path(__file__).parent  # evidence/blind-eval
d = json.load(open(SP / "blind_set.json", encoding="utf-8"))
KIND = {guard.OUT_OF_SCOPE: "out_of_scope", guard.UNRELIABLE: "unreliable", guard.RULES_REFUSAL: "refused"}
out, t = {}, time.time()
for group, qs in d.items():
    rows = []
    for q in qs:
        a, s = rules.answer_rules(q)
        kind = KIND.get(a, "hidden_fixed" if a in guard.HIDDEN_DECK + guard.HIDDEN_ITEMS else "answered")
        rows.append({"q": q, "kind": kind, "answer": a, "sources": s})
    out[group] = rows
    counts = {}
    for r in rows:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    print(group, counts, flush=True)
json.dump(out, open(SP / "results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"done {time.time() - t:.0f}s")
