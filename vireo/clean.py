"""Load + repair the Vireo export. Every fix is traceable to support-policy.pdf or an observed data check."""
import glob, os
import numpy as np, pandas as pd

SLA_MIN = {"chat": 15, "voice": 120, "social": 240, "email": 480}      # policy s3
COST = {"chat": 210, "email": 260, "voice": 520, "social": 240}        # policy s4
BLENDED = 290
TRANSFER_COST = 305
SLA_CREDIT = 350
IST_OFFSET = pd.Timedelta(hours=5.5)


def _find(data_dir, name):
    hits = sorted(glob.glob(os.path.join(data_dir, f"*{name}.csv")))
    if not hits:
        raise FileNotFoundError(f"no *{name}.csv in {data_dir}")
    return hits[0]


def load(data_dir):
    t = pd.read_csv(_find(data_dir, "tickets"), parse_dates=["created_at", "first_response_at", "resolved_at"])
    agents = pd.read_csv(_find(data_dir, "agents"), parse_dates=["from_date", "to_date"])
    orders = pd.read_csv(_find(data_dir, "orders"), parse_dates=["order_date"])
    products = pd.read_csv(_find(data_dir, "products"))
    return t, agents, orders, products


def clean(t, orders):
    """Returns (clean_df, report_dict)."""
    rep = {"rows_in": len(t), "unique_ticket_ids": int(t.ticket_id.nunique())}
    # 1. Re-imported legacy rows duplicate helpdesk rows: keep the helpdesk copy (policy s9, Sameer's email).
    t = t.assign(_pri=(t.source_system != "helpdesk").astype(int)).sort_values(["ticket_id", "_pri"])
    t = t.drop_duplicates("ticket_id", keep="first").drop(columns="_pri").copy()
    rep["rows_after_dedupe"] = len(t)
    # 2. Remaining legacy rows: resolved_at is UTC (observed: exactly 5.5h behind the helpdesk copy in all duplicate pairs).
    L = t.source_system == "legacy_fd"
    t.loc[L, "resolved_at"] += IST_OFFSET
    rep["legacy_rows_tz_shifted"] = int(L.sum())
    # 3. Legacy csat 0 == no response (README). Never average zeros (policy s8).
    t.loc[t.csat_score == 0, "csat_score"] = np.nan
    # 4. Order join: order_id, else latest order for customer+sku (README fallback).
    o = orders.rename(columns={"sku": "product_sku"})
    t = t.merge(o[["order_id", "lot_code"]], on="order_id", how="left")
    fb = (o.sort_values("order_date").drop_duplicates(["customer_id", "product_sku"], keep="last")
            .rename(columns={"lot_code": "lot_fb"})[["customer_id", "product_sku", "lot_fb"]])
    t = t.merge(fb, on=["customer_id", "product_sku"], how="left")
    t["order_join"] = np.where(t.order_id.notna(), "order_id", np.where(t.lot_fb.notna(), "cust+sku", "none"))
    t["lot_code"] = t.lot_code.fillna(t.lot_fb)
    t = t.drop(columns=["lot_fb"])
    # 5. Derived fields
    t["frt_min"] = (t.first_response_at - t.created_at).dt.total_seconds() / 60
    t["sla_breach"] = t.frt_min > t.channel.map(SLA_MIN)
    t["done"] = t.status.isin(["resolved", "closed"])           # policy s10 "attendance"
    t["resolve_days"] = (t.resolved_at - t.created_at).dt.total_seconds() / 86400
    t["week"] = t.created_at.dt.to_period("W-SUN").dt.start_time
    t["closed_week"] = t.resolved_at.dt.to_period("W-SUN").dt.start_time
    rep["resolved_before_created"] = int((t.resolved_at < t.created_at).sum())
    rep["order_join_share"] = t.order_join.value_counts(normalize=True).round(3).to_dict()
    return t.sort_values("created_at").reset_index(drop=True), rep


def add_repeat_flags(t):
    """Policy s10: repeat = same customer contacts again about the same issue within 30d of resolution.
    'Same issue' = same customer + product + issue class (vireo.issues). 'loose' = customer + product only."""
    t = t.sort_values("created_at").copy()
    for name, keys in (("repeat30", ["customer_id", "product_sku", "issue"]),
                       ("repeat30_loose", ["customer_id", "product_sku"])):
        nxt = t.groupby(keys).created_at.shift(-1)
        t[name] = t.done & ((nxt - t.resolved_at).dt.total_seconds() / 86400).between(0, 30)
    g = t.groupby(["customer_id", "product_sku"])
    t["next_agent"] = g.agent_id.shift(-1)
    t["next_msg"] = g.customer_message.shift(-1)
    t["next_created"] = g.created_at.shift(-1)
    return t
