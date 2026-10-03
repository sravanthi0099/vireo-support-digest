"""Business-case numbers, computed from data (not typed in)."""
import numpy as np, pandas as pd
from . import clean


def repeat_baseline(t, n=10, seed=0):
    """Chance level of 'same customer+product within 30d': shuffle customers within each SKU and recompute.
    Heavy-repeat customers make this non-zero, so part of the raw repeat rate is coincidence."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        s = t.copy()
        s["customer_id"] = s.groupby("product_sku").customer_id.transform(lambda x: rng.permutation(x.values))
        s = s.sort_values("created_at")
        nxt = s.groupby(["customer_id", "product_sku"]).created_at.shift(-1)
        out.append((s.done & ((nxt - s.resolved_at).dt.total_seconds() / 86400).between(0, 30)).mean())
    return float(np.mean(out)), float(np.std(out))


def business_case(t, weekly_volume=650):
    d = t[t.done]
    # Target: bring the two families that "chase" (Billing, Delivery) down to the repeat rate of the rest of the desk.
    chase = d.family.isin(["Billing", "Delivery"])
    r_chase, r_rest = d[chase].repeat30_loose.mean(), d[~chase].repeat30_loose.mean()
    target_pts = round(float((r_chase - r_rest) * chase.mean() * 100), 1)
    raw = d.repeat30_loose.mean()
    base, base_sd = repeat_baseline(t)
    # cost of one repeat = cost of the channel the *next* contact used (policy s10)
    t2 = t.sort_values("created_at")
    nxt_ch = t2.groupby(["customer_id", "product_sku"]).channel.shift(-1)
    t2["next_cost"] = nxt_ch.map(clean.COST)
    r = t2[t2.done & t2.repeat30_loose]
    avg_cost = r.next_cost.mean()
    weeks = (t.created_at.max() - t.created_at.min()).days / 7
    by = d.groupby("family").repeat30_loose.agg(["mean", "size"]).round(3)
    q_tickets_export = len(d) / weeks * 13
    q_tickets_vireo = weekly_volume * 13 * len(d) / len(t)   # only closed/resolved tickets can generate a repeat
    res = {
        "done_tickets": int(len(d)), "weeks_in_export": round(weeks, 1),
        "tickets_per_week_in_export": round(len(t) / weeks, 1),
        "repeat_rate_raw": round(raw, 4), "repeat_rate_chance": round(base, 4), "chance_sd": round(base_sd, 4),
        "repeat_rate_above_chance": round(raw - base, 4),
        "avg_cost_per_repeat_inr": round(avg_cost, 1), "policy_blended_cost": clean.BLENDED,
        "target_rate": round(raw - target_pts / 100, 4), "target_pts": target_pts, "chase_families_rate": round(float(r_chase), 4), "rest_rate": round(float(r_rest), 4), "chase_share_of_tickets": round(float(chase.mean()), 3),
        "saving_per_quarter_export_scale_inr": round(q_tickets_export * target_pts / 100 * avg_cost),
        "saving_per_quarter_vireo_scale_inr": round(q_tickets_vireo * target_pts / 100 * avg_cost),
        "repeat_by_family": by.to_dict("index"),
        "sla_credit_per_quarter_vireo_scale_inr": round(weekly_volume * 13 * float(t.sla_breach.mean()) * clean.SLA_CREDIT),
        "sla_breach_rate": round(float(t.sla_breach.mean()), 4),
        "sla_credit_total_inr": int(t.sla_breach.sum() * clean.SLA_CREDIT),
        "transfers_total": int(t.transfers.sum()), "transfer_cost_total_inr": int(t.transfers.sum() * clean.TRANSFER_COST),
    }
    return res
