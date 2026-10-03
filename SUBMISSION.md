# Submission form answers (Vireo Audio, Set A)
Items in [BRACKETS] are things only you can fill in. Everything else was computed or done in this repo.

**1. What did you build, and what business outcome does it move? (number + money)**
A one-command pipeline (cleaning -> issue labels -> weekly digest -> fair leaderboard -> business case), no paid model calls required. Outcome: **cut the 30-day repeat-contact rate from 28.7% to ~25.6% (3 points), by bringing Billing (36%) and Delivery (32%) tickets down to the rest-of-desk rate (26%). Worth ~Rs 69k a quarter at 650 tickets/week (~Rs 16k on the 152/week actually in the export), at Rs 268 per repeat contact; ~Rs 46k at Finance's Rs 180.** All in `out/business_case.json`.

**2. What does one run cost? A month at ~650 tickets/week?**
Core pipeline: Rs 0 (no API calls; ~10 s on a laptop). Optional `--llm` narrative: one call per week on the aggregate table, ~2,000 input + 300 output tokens. At Haiku-class pricing I assumed $1 / $5 per million tokens (from memory, verify): 4.33 weeks x (2,000 x $1/1M + 300 x $5/1M) = 4.33 x $0.0035 = ~$0.015/month (~Rs 1.3 at Rs 85/$). For Arjun's "November surprise": labelling every ticket with an LLM instead would be 650 x 52/12 = 2,817 tickets/month x ~420 tokens (400 in, 20 out) = 1.13M in + 56k out = ~$1.13 + $0.28 = ~$1.4/month (~Rs 120). I did not do that because the rules are free, but this is the ceiling if you want to replace them. The optional call was NOT tested (no API key), so treat that cost as an estimate.

**3. How do you know it works?**
- Cleaning: 9 tests. Strongest: after the +5:30 shift, the legacy copy equals the helpdesk copy on all 618 duplicate pairs that have a timestamp (an independent check, not a circular one).
- Issue labels: 80 random tickets not used for tuning, reviewed against message + note: **82.5% issue-level (95% CI 73-89%), 88.8% at family level**. A first 110-ticket class-stratified sample scored 80% before I changed the rules; after tuning it scores 96% but that number is optimistic and not reported as accuracy. `python eval/score.py` reproduces both.
- Reviewer was Claude, not a person. No human has checked the labels. Known failure types: customers describing a symptom in unusual words (e.g. "sounds like a badly tuned radio", "everything sounds from one direction"); words that appear in two contexts ("crackling" vs "cracked"; "please reverse" = cancel, not pickup); no class for "won't power on" (ends up unclassified, 1.7% overall); delivery "not received" vs "delayed" are interchangeable in the data, so I report them as one family.
- Repeat-contact: checked against a permutation baseline (shuffle customers within SKU, 10 runs): chance level 8.2% (sd 0.15 pt), so I report 28.7% raw and ~20.6 points above chance.

**4. Did you change, narrow, or push back on the client's ask?**
Yes. (a) Leaderboard: kept, but ranked within team and Tier 2 excluded, per policy s6 and Neha; added repeat rate / CSAT beside volume because "tickets closed" alone rewards closing, not fixing. (b) "Digest of complaints": the bot's category tag is unreliable (15% "Other"), so the digest uses the customer's words. (c) Cost per contact: used the policy's channel costs, not Arjun's Rs 180 or the Rs 290 blend, and show sensitivity. (d) Declined to claim the SLA-credit saving (Rs 2.6 lakh/qtr at their volume): breach rate is flat (~9%) by hour, weekday and agent, so no lever is visible in this data. (e) Flagged that the export has 152 tickets/week, not 650. Decided on day 1 after profiling the data.

**5. What is wrong with what you are handing us?**
- Classifier is regex rules at ~82%; it will miss novel phrasing and has no "power fault" class.
- Reviewed by an AI, not a human. Sample of 80 is small.
- "Same issue" for repeat contact is customer + product, not customer + issue (my labels were too noisy to use: it cut matches to 8.3%). So some repeats are different problems on the same product; I estimate ~8 points of chance overlap but the permutation baseline is itself an approximation.
- The target (3 points) is "match the rest of the desk", not a proven achievable effect; the data does not show why customers return.
- Latest ~4 weeks undercount repeats (30-day window incomplete); the digest says so.
- Legacy refund amounts: the policy says legacy tool used "its native unit"; legacy refunds look like rupees (similar means) and I did not convert; I did not audit this further. Refund-by-reason, double remedies (4 cases) and lot analysis are not in the product.
- Order join: 34% of tickets use the customer+SKU fallback (latest order), which can pick the wrong order.
- Leaderboard assumes one roster row per agent (true in this file); no shift/site adjustment beyond team. The 38 Tier 1 agents' rates are over different mixes of channel.
- `--llm` path untested. The digest's "customer's words" quote is the first short message of that issue, sometimes mislabelled (a mislabelled example showed up in testing and one rule was fixed).

**6. What did you deliberately leave out, and why?**
Per-lot manufacturing defect detection (numerators too small and the lot join is ambiguous for 34% of tickets); refund fraud / double-remedy audit (4 cases); a dashboard/UI (Priya said "I don't need a platform"); automatic per-ticket LLM labelling (rules are free and I could not show an LLM would be better in the time); staffing/rota model for SLA breaches. Chose the repeat-contact number because it ties to the policy's own definition (s10), has a stated cost per contact, and Arjun asked for contacts taken out of the queue.

**7. Anything you built or found that nobody asked for?**
The data defects (653 duplicates, UTC legacy times, zero CSAT); the chance baseline for repeat contacts; the SLA-credit finding that breaches are flat and mis-attributed to resolving agents; a test of Neha's "I already told your colleague" claim (openers are ~3x more common after a prior contact, 11% vs 4%, but not specific to chat; repeats return to the same agent 10% of the time vs ~20% by chance within team).

**8. What did you use AI for?**
[Edit to match what you actually did.] Claude (Sonnet) in the chat interface for data profiling, writing the pipeline code, drafting the memo and this form. It helped most on spotting data traps and building the code quickly; it wasted time on first-draft regex rules that over-matched ("charged" inside "discharged", "pickup" inside "mic pickup", refund wishes), which I discarded after the first review and rewrote; I discarded the per-lot defect analysis and the first "colleague" claim (chance explained the 90% different-agent figure). Cost: [your subscription / API cost]. Screen recording: [link]. Script in `VIDEO_SCRIPT.md`.

**9. Public Google Drive link:** [link]

**10. Someone picks this up on Monday and you are unreachable. The three things they need to know.**
1. `python -m vireo.run --data data --out out` regenerates everything; `python -m pytest -q tests` and `python eval/score.py` tell you if it is still correct.
2. Before trusting any week's small counts, have a person check ~50 labels in `eval/heldout_labels.csv`-style; the regex rules live in `vireo/issues.py` (`RULES`, ordered, first match wins).
3. Open question for the client: is volume 650/week or 152/week, and who owns the repeat-contact goal; also the SLA breach (flat 9%) needs a staffing analysis, not more digests.

**11. Honest hours spent:** [your number]

**12. GitHub repo link:** [link]
