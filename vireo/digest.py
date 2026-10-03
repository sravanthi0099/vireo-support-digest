import pandas as pd
from . import clean
from .issues import FAMILY

LABEL = lambda s: s.replace("_", " ")


def last_full_week(t):
    mx = t.created_at.max()
    wk = mx.to_period("W-SUN").start_time
    if mx < wk + pd.Timedelta(days=6, hours=23):   # data ends mid-week -> use the previous complete week
        wk -= pd.Timedelta(weeks=1)
    return wk


def build(t, week_start=None, trail=4, min_n=8):
    ws = pd.Timestamp(week_start) if week_start else last_full_week(t)
    cur = t[t.week == ws]
    prev = t[(t.week >= ws - pd.Timedelta(weeks=trail)) & (t.week < ws)]
    c = cur.issue.value_counts().rename("this_week")
    p = (prev.issue.value_counts() / trail).round(1).rename("avg_prev_4w")
    iss = pd.concat([c, p], axis=1).fillna(0).sort_values("this_week", ascending=False)
    iss["delta_vs_avg"] = (iss.this_week - iss.avg_prev_4w).round(1)
    iss["chg_pct"] = ((iss.this_week / iss.avg_prev_4w.where(iss.avg_prev_4w > 0) - 1) * 100).round(0)
    iss["flag"] = ((iss.this_week >= min_n) & (iss.chg_pct >= 40)).map({True: "RISING", False: ""})
    ex = {}
    for name in iss.index[:8]:
        m = cur[(cur.issue == name)].customer_message.dropna()
        m = m[m.str.len().between(25, 160)]
        if len(m):
            ex[name] = " ".join(m.iloc[0].split())
    hot = (cur.groupby(["product_sku", "issue"]).size().rename("n").reset_index().sort_values("n", ascending=False).head(5))
    d = cur[cur.done]
    reps = cur[cur.repeat30_loose] if "repeat30_loose" in cur else cur.iloc[0:0]
    stats = {
        "week_start": ws, "new_tickets": len(cur), "avg_prev_4w": round(len(prev) / trail, 1),
        "sla_breaches": int(cur.sla_breach.sum()), "sla_credit_inr": int(cur.sla_breach.sum()) * clean.SLA_CREDIT,
        "refund_inr": int(cur.refund_amount_inr.sum()),
        "csat": round(cur.csat_score.mean(), 2) if cur.csat_score.notna().any() else None, "csat_n": int(cur.csat_score.notna().sum()),
        "repeat_contacts_from_this_weeks_closures": int(reps.shape[0]),
        "unclassified_share": round((cur.issue == "unclassified").mean(), 3),
    }
    return stats, iss, ex, hot


def render(stats, iss, ex, hot, narrative=None):
    s = stats; ws = s["week_start"]
    L = [f"# Vireo support digest: week of {ws:%d %b %Y} (Mon-Sun)", ""]
    if narrative:
        L += ["## In short", narrative, ""]
    delta = s["new_tickets"] - s["avg_prev_4w"]
    L += ["## Numbers",
          f"- New tickets: **{s['new_tickets']}** ({delta:+.0f} vs 4-week average of {s['avg_prev_4w']})",
          f"- First-response breaches: {s['sla_breaches']} (Rs {s['sla_credit_inr']:,} in SLA credits at Rs 350 each)",
          f"- Refunds raised on these tickets: Rs {s['refund_inr']:,}",
          f"- CSAT: {s['csat']} from {s['csat_n']} responses (blanks excluded, not counted as zero)",
          f"- Customers who came back within 30 days of an earlier closed ticket: {s['repeat_contacts_from_this_weeks_closures']} (counted on tickets opened this week; most recent weeks undercount, see README)",
          ""]
    L += ["## What people are complaining about", "", "| Issue | This week | 4-wk avg | Change | |", "|---|---:|---:|---:|---|"]
    for name, r in iss.head(12).iterrows():
        ch = "new" if r.avg_prev_4w == 0 else f"{r.chg_pct:+.0f}%"
        L.append(f"| {LABEL(name)} ({FAMILY.get(name,'')}) | {int(r.this_week)} | {r.avg_prev_4w} | {ch} | {r.flag} |")
    rising = iss[iss.flag == "RISING"]
    L += ["", "## Worth a look" ]
    L += [f"- **{LABEL(n)}** is up {r.chg_pct:.0f}% on its recent average ({int(r.this_week)} vs {r.avg_prev_4w})." for n, r in rising.iterrows()] or ["- Nothing rose more than 40% on a base of 8+ tickets."]
    L += ["", "Hot spots (product x issue):"] + [f"- {r.product_sku}: {LABEL(r.issue)} ({r.n})" for r in hot.itertuples()]
    L += ["", "## In customers' words (one example per top issue)"] + [f"- *{LABEL(k)}*: \"{v}\"" for k, v in ex.items()]
    L += ["", f"_Classifier left {s['unclassified_share']:.1%} of tickets unclassified. Issue labels come from the message and closing note, not the bot's category tag._"]
    return "\n".join(L)
