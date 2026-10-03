"""Issue classifier: ordered regex rules, no model calls. Run separately on the customer's message and the agent's note.
The bot's category tag is NOT used as truth (it is set from intake answers; ~15% 'Other')."""
import re
import pandas as pd

RULES = [
 ("wrong_item",        r"wrong (item|variant|product|colou?r|model)|incorrect product|differ\w* colo|ordered (black|white|blue|grey|gray|red)|got (white|black|blue)|not what i (paid|ordered|asked)|what.s inside is not"),
 ("damaged_in_transit",r"damag|crack|in transit|transit dam|smash|kick|kiked|dented|\bdent\b|box (was )?(torn|crushed)|crushed"),
 ("refund_pending",    r"r?e?fund (was|is|has|not|pending|delay|status|still|hasn)|r?e?fund.{0,20}(promised|nothing|pending|delay)|promised.{0,20}refund|not credited|credit(ed)? not|rfnd|haven.t (got|received).{0,15}(refund|money)|money.{0,25}(hasn.t|has not|not|yet|return|come back)|where is the money"),
 ("reverse_pickup",    r"(?<!mic )(?<!mic)pick ?up|picked up|reverse|\bpkp\b"),
 ("delivery_delayed",  r"delay|dlvry|late\b|dispatch|not (yet )?shipped|stuck on shipped"),
 ("delivery_not_received", r"(haven.t|havent|have not|not|nt) (yet )?(been )?(deliver|receiv|rcvd|rec'd|arriv|got)|undeliver|never (came|arrived|got)|out for delivery|tracking|shipment|where is my|ord not|order not|nothing in hand"),
 ("address_change",    r"address|pin ?code|old flat|moved house"),
 ("cancellation",      r"cancel|cancl"),
 ("double_charge",     r"bank (says|shows|statement)|went to you|money (was )?(deducted|gone)|\bcharged (twice|two|me)|card charged|twice (charged|deducted)|double (charge|payment|debit)|duplicate|deducted|debited|failed (order|after)|payment (failed|page)|page failed|paid.{0,30}(no order|nothing)|payment went through"),
 ("coupon_price",      r"coupon|promo|discount|price (drop|adj)|offer|full price|\bad said|\d+ ?% off"),
 ("invoice",           r"invoice (not|request|download|with|for|copy)|(need|share|send|want|get).{0,20}invoice|\bgst\b|tax bill|\bbill\b"),
 ("login_otp",         r"log ?in|\botp\b|locked out|password|sign ?in|sent me a code"),
 ("app_crash",         r"app (crash|not open|keeps|white|freez|wont|won't|closes)|white screen|crash|device page"),
 ("warranty_rma",      r"warranty|\bwty\b|\brma\b|repair"),
 ("mic_issue",         r"\bmic\b|microphone|callers?|repeat myself|(cant|can't|cannot|can not) hear me|people cannot hear"),
 ("display_touch",     r"touch|swipe|tap ten|finger|screen lights up|does nothing|unresponsive|display (is|ignores|not|dead|flicker|blank|just)|strap|watch face|\bband\b"),
 ("firmware_update",   r"firmware|\bfw\b|update"),
 ("compat_presales",   r"connect (two|2|multiple)|compat|pre-?sales|enquiry|inquiry|will (it|the|this) .{0,30}work|does .{0,30}(support|work with)|which (one|model)|difference between|old nokia|\bbuy\b"),
 ("pairing_connectivity", r"stutter|wifi|wi-fi|losing my phone|loses? (the )?(connection|phone)|finds the speaker|pair|bluet|bluetooht|disconnect|dropout|dropping|discover|connect|drops?\b|doesn.t see it"),
 ("battery_charging",  r"batt|charg|drain|backup|case.*(dead|led)|(?<![\d.])0 ?(%|percent)|dies by|barely lasts|lasts? (only |maybe )?\d|get maybe \d|twice a day"),
 ("audio_fault",       r"audio|sound|silent|static|distort|crackl|buzz|volume|muffl|one side|left (bud|side|one)|right (bud|side)|no sound|decoration|one of them|frying|mute"),
 ("refund_wish",       r"refund|money back"),
]
_ORDER_FIX = None
_COMPILED = [(n, re.compile(p, re.I)) for n, p in RULES]
# closing notes that carry no issue information
UNINFORMATIVE_NOTE = re.compile(r"^(?:\W*(?:see prev|same|recurred|was told fixed last time|closed|resolved|done|ok)\W*(?:\[closed\])?)$", re.I)
ISSUE_NAMES = [n for n, _ in RULES]


_SENT_STRIP = re.compile(r"(?i)\b(?:i|i've|i have|we)\s+(?:already\s+|have\s+|had\s+)?(?:tried|checked|turned off|updated|cleared|restarted|kept|changed|fully|did|reset|tested|rebooted|reinstalled|swapped|used|emailed|called|raised|waited|asked)[^.?!\n]*[.?!]?|\bi (?:request|want|need|would like)[^.?!\n]*(?:refund|replacement|resolution)[^.?!\n]*[.?!]?")


def _strip_template(text):
    text = _SENT_STRIP.sub(" ", text)
    # structured customer messages carry an 'expected: refund/replacement/fix' line that is a wish, not the issue
    text = re.sub(r"(?im)^\s*(expected|tried)\s*:.*$", " ", text)
    text = re.sub(r"(?i)\b(refund|replacement) or (a )?(refund|replacement)\b", " ", text)
    return text


def classify_text(text, strip=True):
    if not isinstance(text, str) or not text.strip():
        return None
    s = _strip_template(text) if strip else text
    if strip and not any(rx.search(s) for _, rx in _COMPILED):
        s = text   # nothing left after stripping wishes/troubleshooting -> fall back to the raw text (catches pure 'give me my refund')
    # structured template: prefer the 'issue:' line
    m = re.search(r"(?im)^\s*issue\s*:\s*(.+)$", s)
    for chunk in ([m.group(1)] if m else []) + [s]:
        for name, rx in _COMPILED:
            if rx.search(chunk):
                return name
    return None


def classify_note(note):
    if not isinstance(note, str) or UNINFORMATIVE_NOTE.match(note.strip()):
        return None
    # the actions/outcome half of a note often contains words like 'refund' or 'reset'; use text before first '->' or sentence of actions
    n = note.replace("\n", " ")
    m = (re.search(r"(?i)(?:issue|reported|re|raised|query)\s*[:\-]\s*([^.|>\n]{4,60})", n)
         or re.search(r"(?i)\bre\s+([a-z /&\-]{4,40}?)(?:\.|\||,|->|$)", n)
         or re.search(r"(?i)^\s*1\.\s*([^/]{4,50}?)\s*(?:2\.|$)", n)
         or re.search(r"(?i)(?:cx|customer|cust)\s+(?:says|reported|reached out|contacted)\s*[-:]?\s*(?:re\s+)?([^.|>]{4,50})", n))
    if m:
        r = classify_text(m.group(1), strip=False)
        if r:
            return r
    head = re.split(r"->|\. (?:checked|chk|asked|walked|conf|shared|xfer|transferred)|\|", n, maxsplit=1)[0]
    return classify_text(head, strip=False) or classify_text(n, strip=False)


def assign(t):
    t = t.copy()
    t["issue_msg"] = t.customer_message.map(classify_text)
    t["issue_note"] = t.agent_notes.map(classify_note)
    # Resolution order: customer's own words first (what they are complaining about), note as backup, else 'unclassified'
    t["issue"] = t.issue_msg.fillna(t.issue_note).fillna("unclassified").replace({"refund_wish": "refund_pending"})
    t["issue_note"] = t.issue_note.replace({"refund_wish": "refund_pending"})
    t["issue_msg"] = t.issue_msg.replace({"refund_wish": "refund_pending"})
    t["family"] = t.issue.map(FAMILY)
    t["issue_source"] = ["msg" if isinstance(a, str) else "note" if isinstance(b, str) else "none"
                         for a, b in zip(t.issue_msg, t.issue_note)]
    return t


FAMILY = {
 "delivery_not_received": "Delivery", "delivery_delayed": "Delivery", "damaged_in_transit": "Delivery", "wrong_item": "Delivery", "address_change": "Delivery",
 "refund_pending": "Refunds & returns", "reverse_pickup": "Refunds & returns", "cancellation": "Refunds & returns",
 "double_charge": "Billing", "coupon_price": "Billing", "invoice": "Billing",
 "pairing_connectivity": "Product fault", "battery_charging": "Product fault", "audio_fault": "Product fault", "mic_issue": "Product fault", "display_touch": "Product fault",
 "app_crash": "App & account", "firmware_update": "App & account", "login_otp": "App & account",
 "warranty_rma": "Warranty", "compat_presales": "Pre-sales", "unclassified": "Unclassified"}
