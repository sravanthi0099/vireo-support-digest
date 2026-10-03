# Vireo support digest + fair leaderboard

Weekly "what are customers complaining about" digest, an agent leaderboard that is fair to compare, and a number-backed business case, built from the ticket export. **No paid model calls are needed.** Runs in about 10 seconds.

## Run it (clean machine, Python 3.10+)
```bash
git clone https://github.com/sravanthi0099/vireo-support-digest.git
cd vireo-support-digest
pip install -r requirements.txt
# copy tickets, agents, orders, customers, products CSVs into data/
python -m vireo.run --data data --out out
python -m pytest -q tests
python eval/score.py
```
Outputs in `out/`:
| file | what |
|---|---|
| `digest_<Monday>.md` | the weekly digest (default: last complete Mon-Sun week in the data) |
| `leaderboard_tier1_alltime.csv`, `..._last4w.csv` | Tier 1 agents, ranked **within team** |
| `tier2_resolution_days.csv` | Warranty/Escalations team, measured in days, **unranked** (policy s6) |
| `business_case.json` | every number used in the memo, computed |
| `tickets_labelled.csv` | each ticket with its issue label (for audit) |

`--llm` adds one optional narrative paragraph to the digest (one Claude Haiku call per week on the aggregate table, needs `ANTHROPIC_API_KEY`, `pip install anthropic`). **Untested** (no key available when built). Nothing else depends on it.

## What it does (in order)
1. **Clean** (`vireo/clean.py`): 12,528 rows -> 11,875 real tickets (653 re-imported Freshdesk duplicates; helpdesk copy kept). Remaining legacy `resolved_at` is UTC -> +5:30 (verified: shifting makes the legacy copy equal the helpdesk copy on all 618 duplicate pairs with a timestamp). Legacy CSAT 0 -> blank. Order/lot join falls back to customer+SKU for the 34% of tickets without `order_id`.
2. **Issue labels** (`vireo/issues.py`): 22 issues / 8 families from ordered regex rules over the customer's message, with the agent's note as backup. The bot's category tag is not used (15% "Other"; set from intake answers).
3. **Digest** (`vireo/digest.py`): volume vs 4-week average, ranked issues with change, RISING flag (>=+40% and >=8 tickets), product x issue hot spots, one customer quote per issue, SLA credits, refunds, CSAT (blanks excluded).
4. **Leaderboard** (`vireo/leaderboard.py`): Tier 1 only, tickets closed per active week, ranked within team, shown beside repeat-contact rate, CSAT (with response counts), auto-closed share, transfers. Agents with <4 active weeks get no rate.
5. **Business case** (`vireo/analysis.py`): repeat-contact rate, chance baseline (permutation), cost per repeat from the policy's channel costs, target and money.

## Decisions I made where the pack was silent
- Duplicates: keep the `helpdesk` row. Timestamps: IST everywhere.
- "Same issue" for repeat contact = same customer + same product within 30 days of resolution (the policy's 30-day rule; product, not my noisy issue label, because label noise cut matches from 28.7% to 8.3%). ~8 points of that is coincidence (see below); the tool reports both.
- Cost: policy channel costs (Rs 210/260/520/240; repeat mix averages Rs 268.5), not Finance's Rs 180 and not blanket Rs 290.
- Leaderboard ranks within team and excludes Tier 2 (policy s6, Neha's request). Priya asked for the leaderboard to stay; it stays, with those two changes.

## Known limits (details in SUBMISSION.md)
Classifier ~82% issue-level / ~89% family-level on an 80-ticket held-out sample (95% CI 73-89%), labelled by an AI reviewer, not a human. Latest weeks undercount repeat contacts (the 30-day window is not complete). No per-lot defect analysis. Export averages 152 tickets/week vs the 650 quoted by the client.
