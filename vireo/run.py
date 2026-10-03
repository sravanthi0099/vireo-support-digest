"""python -m vireo.run --data data/ --out out/ [--week 2026-06-22] [--llm]"""
import argparse, json, os
import pandas as pd
from . import clean, issues, digest, leaderboard, analysis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data"); ap.add_argument("--out", default="out")
    ap.add_argument("--week", help="Monday of the week to report (default: last complete week)")
    ap.add_argument("--llm", action="store_true", help="optional one-call narrative (needs ANTHROPIC_API_KEY)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    raw, agents, orders, products = clean.load(a.data)
    t, rep = clean.clean(raw, orders)
    t = issues.assign(t)
    t = clean.add_repeat_flags(t)
    stats, iss, ex, hot = digest.build(t, a.week)
    narr = None
    if a.llm:
        from .llm import narrate
        narr = narrate({k: str(v) for k, v in stats.items()}, iss.head(10).to_markdown())
    ws = stats["week_start"]
    open(f"{a.out}/digest_{ws:%Y-%m-%d}.md", "w").write(digest.render(stats, iss, ex, hot, narr))
    t1, t2 = leaderboard.build(t, agents)
    t1_4w, _ = leaderboard.build(t, agents, window_weeks=4)
    t1.to_csv(f"{a.out}/leaderboard_tier1_alltime.csv", index=False)
    t1_4w.to_csv(f"{a.out}/leaderboard_tier1_last4w.csv", index=False)
    t2.to_csv(f"{a.out}/tier2_resolution_days.csv", index=False)
    bc = analysis.business_case(t)
    json.dump({"cleaning": rep, "business_case": bc}, open(f"{a.out}/business_case.json", "w"), indent=2, default=str)
    t[["ticket_id", "created_at", "channel", "product_sku", "category", "issue", "family", "issue_source", "repeat30_loose"]].to_csv(f"{a.out}/tickets_labelled.csv", index=False)
    print(f"cleaned {rep['rows_in']} rows -> {rep['rows_after_dedupe']} tickets; digest for week {ws:%Y-%m-%d}; outputs in {a.out}/")


if __name__ == "__main__":
    main()
