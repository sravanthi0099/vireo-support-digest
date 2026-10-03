import os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, pytest
from vireo import clean, issues

DATA = os.environ.get("VIREO_DATA", "data")
pytestmark = pytest.mark.skipif(not glob.glob(f"{DATA}/*tickets.csv"), reason="data not present")

@pytest.fixture(scope="module")
def loaded():
    raw, agents, orders, products = clean.load(DATA)
    t, rep = clean.clean(raw, orders)
    return raw, t, rep

def test_dedupe_unique(loaded):
    raw, t, rep = loaded
    assert t.ticket_id.is_unique and len(t) == raw.ticket_id.nunique()

def test_legacy_tz_fix_matches_helpdesk_copy_on_all_duplicate_pairs(loaded):
    """The independent check on the +5.5h fix: after shifting, the legacy copy equals the helpdesk copy for every pair."""
    raw, t, rep = loaded
    d = raw[raw.ticket_id.duplicated(keep=False)]
    h = d[d.source_system == "helpdesk"].set_index("ticket_id").resolved_at
    l = d[d.source_system == "legacy_fd"].set_index("ticket_id").resolved_at + pd.Timedelta(hours=5.5)
    common = h.index.intersection(l.index)
    h, l = h[common].dropna(), l[common].dropna()   # open tickets have no resolved_at
    assert len(h) == 618 and (h == l.reindex(h.index)).all()

def test_no_negative_durations(loaded):
    _, t, _ = loaded
    assert (t.resolved_at.dropna() >= t.created_at[t.resolved_at.notna()]).all()

def test_csat_has_no_zeros(loaded):
    _, t, _ = loaded
    assert not (t.csat_score == 0).any()

@pytest.mark.parametrize("msg,exp", [
    ("payment went through but i got no order id", "double_charge"),
    ("people cannot hear me on calls", "mic_issue"),
    ("hey your ad said 20% off and the cart says full price", "coupon_price"),
    ("I have fully charged and discharged twice. Dies by lunchtime", "battery_charging"),
    ("you picked up the item 7 days ago and my money hasn't come back", "refund_pending"),
])
def test_classifier_known_cases(msg, exp):
    assert issues.classify_text(msg) == exp
