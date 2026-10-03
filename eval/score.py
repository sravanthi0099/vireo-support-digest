"""python eval/score.py  -> accuracy of the CURRENT rules on the held-out reviewed sample (+ Wilson 95% CI)."""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
from vireo import issues

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h

for name in ("heldout_labels.csv", "tuning_sample_v1_labels.csv"):
    s = pd.read_csv(os.path.join(os.path.dirname(__file__), name))
    pred = [(issues.classify_text(m) or issues.classify_note(n) or "unclassified") for m, n in zip(s.customer_message, s.agent_notes)]
    pred = ["refund_pending" if p == "refund_wish" else p for p in pred]
    ok = sum(p == t for p, t in zip(pred, s.reviewer_issue))
    fam = sum(issues.FAMILY.get(p, "?") == issues.FAMILY.get(t, "?") for p, t in zip(pred, s.reviewer_issue))
    lo, hi = wilson(ok, len(s))
    print(f"{name}: n={len(s)} issue-level {ok/len(s):.1%} (95% CI {lo:.0%}-{hi:.0%}); family-level {fam/len(s):.1%}")
    if name.startswith("heldout"):
        bad = s[[p != t for p, t in zip(pred, s.reviewer_issue)]].assign(pred=[p for p, t in zip(pred, s.reviewer_issue) if p != t])
        print(bad[["idx", "pred", "reviewer_issue"]].to_string(index=False))
print("NOTE: tuning_sample numbers are optimistic (rules were fitted to those errors). Held-out is the honest figure.")
