import numpy as np, pandas as pd


def _active_weeks(row, t_min, t_max):
    start = max(row.from_date, t_min) if pd.notna(row.from_date) else t_min
    end = min(row.to_date, t_max) if pd.notna(row.to_date) else t_max
    return max((end - start).days / 7, 0)


def build(t, agents, window_weeks=None):
    """Tier 1 leaderboard. Ranked WITHIN team (queues differ). Tier 2 listed without rank (policy s6, Neha's email)."""
    t_max = t.resolved_at.max().normalize(); t_min = t.created_at.min().normalize()
    d = t[t.done].copy()
    if window_weeks:
        d = d[d.resolved_at >= t_max - pd.Timedelta(weeks=window_weeks)]
        t_min = max(t_min, t_max - pd.Timedelta(weeks=window_weeks))
    ag = agents.sort_values("from_date").drop_duplicates("agent_id", keep="last").set_index("agent_id")
    rows = []
    for aid, g in d.groupby("agent_id"):
        if aid not in ag.index:
            continue
        a = ag.loc[aid]
        wk = _active_weeks(a, t_min, t_max)
        rows.append({
            "agent_id": aid, "name": a["name"], "team": a.team, "tier": int(a.tier), "site": a.site, "shift": a["shift"],
            "closed": len(g), "auto_closed": int((g.status == "closed").sum()), "active_weeks": round(wk, 1),
            "closed_per_week": round(len(g) / wk, 2) if wk >= 4 else np.nan,
            "median_resolve_days": round(g.resolve_days.median(), 2),
            "csat_mean": round(g.csat_score.mean(), 2), "csat_responses": int(g.csat_score.notna().sum()),
            "repeat_rate": round(g.repeat30_loose.mean(), 3) if "repeat30_loose" in g else np.nan,
            "transfers_per_100": round(g.transfers.sum() / len(g) * 100, 1),
        })
    df = pd.DataFrame(rows)
    t1 = df[df.tier == 1].copy()
    med = t1.groupby("team").closed_per_week.transform("median")
    t1["vs_team_median"] = (t1.closed_per_week / med).round(2)
    t1["rank_in_team"] = t1.groupby("team").closed_per_week.rank(ascending=False, method="min")
    t1 = t1.sort_values(["team", "rank_in_team"])
    t2 = df[df.tier == 2].drop(columns=["closed_per_week", "vs_team_median"], errors="ignore").sort_values("median_resolve_days")
    return t1, t2
