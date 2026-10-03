# 3-minute screen recording: what to say and show (you record it; ~2:45)
0:00 Terminal: `python -m vireo.run --data data --out out` then open `out/digest_2026-06-22.md`. (15s) "One command, no API calls, ~10 seconds."
0:15 The data traps (30s): show `business_case.json -> cleaning`: 12,528 rows -> 11,875; the +5:30 test (`pytest -q`); legacy csat zeros.
0:45 Prompts / AI use (45s): be honest. Show the prompts you actually gave your assistant (first: "profile these files"; then the repeat-contact question; then "tune the regex rules against these disagreements"). Say which output you discarded.
1:30 Versions (45s): classifier v1 (80% on first 110-ticket sample, errors: refund-wish sentences, "mic pickup" matched pickup, "discharged twice" matched double charge) -> v2 (strip troubleshooting/wish sentences, reorder rules) -> fresh 80-ticket sample 82.5%. Run `python eval/score.py`.
2:15 Thrown away (30s): lot-defect analysis (numerators too small), over-reading the "colleague" hypothesis (repeats return to the same agent 10% of the time vs ~20% if random within team: suggestive, not proof of a handoff problem), SLA by-agent view (breach rate flat ~9% by hour/day).
2:45 Stop. Link goes in the form.
