"""Analysis sequence diagrams in the boundary / control / entity (robustness) style: UC02, UC07 and UC11.

Each lifeline is an analysis object: one «boundary» page and one «control» per use case, and «entity» objects
that are classes of model.ANALYSIS. Messages use the words of the use case specifications (Chapter 2) and simple
operation names, not the signatures of the design classes (compare 2.5, 3.2 and 4.4d).
"""
from .common import Rect, Diagram, Seq, text_w
import model

SCOPE = ("sequence", "analysis", "4.1 Analysis model")   # entity lifelines share the analysis classes
B, C, E = "boundary", "control", "entity"


class BceSeq(Seq):
    """Seq whose lifelines carry a robustness stereotype.

    The activation bars are recomputed: a reply in a later operand of an alt continues the bar that the reply of
    an earlier operand closed, because each operand may end with its own reply. The actor's bar is registered like
    an activation, so a fragment that covers the actor may cross it."""

    HEAD = 52          # VP draws the icon from y 40 to 76 and the name under it, down to y 92

    def __init__(self, d, parts, msgs, frags=(), stereotypes=None, gap=40, left=16):
        super().__init__(d, parts, msgs, frags, gap=gap)
        self.stereotypes = stereotypes
        # fragments that cover the actor start left of it: keep them `left` px from the diagram edge
        lo = min([self.cx[0] - self.frag_gw(f) for f in frags if self.parts[0][0] in f[4]] + [left])
        self.cx = [c + left - lo for c in self.cx]

    @staticmethod
    def frag_gw(frag):
        """Room Seq leaves left of the first covered lifeline for the operand guards."""
        return max(text_w(f"[{g}]") for g, _ in frag[3]) + 50

    def spans(self):
        open_, spans = [], []
        for i, (f, t, text, kind) in enumerate(self.msgs):
            y = self.ys[i]
            if kind in ("call", "create"):
                open_.append([t, y])
            elif kind == "send":
                spans.append([t, y, y + 18])
            elif kind == "return":
                for k in range(len(open_) - 1, -1, -1):
                    if open_[k][0] == f:
                        spans.append([f, open_[k][1], y])
                        del open_[k]
                        break
                else:                    # reply of a later alt operand: the bar closed above runs on
                    prev = max((s for s in spans if s[0] == f and s[2] <= y), key=lambda s: s[2])
                    prev[2] = y
        for t, y in open_:               # no reply drawn: active until its last message
            last = max(i for i, m in enumerate(self.msgs) if self.ys[i] >= y and t in (m[0], m[1]))
            spans.append([t, y, self.ys[last] + (28 if self.msgs[last][3] == "self" else 10)])
        return spans

    def draw(self):
        super().draw()
        d, actor = self.d, self.parts[0][0]
        for n in d.el.findall("node"):
            if n.get("type") == "Lifeline":
                n.set("stereotype", self.stereotypes[n.get("id")])
        for a in d.el.findall("activation"):
            d.el.remove(a)
        for k in [k for k in d.boxes if k.startswith("act ")]:
            del d.boxes[k]
        for pid, _ in self.parts[1:]:
            r = d.boxes[pid + "#head"][0]
            d.boxes[pid + "#head"] = (Rect(r.x, r.y, r.w, self.HEAD), "solid")
        bar = d.boxes.pop(actor + "#bar")[0]
        d.boxes[f"act {actor} {bar.y}"] = (bar, "solid")
        for who, y1, y2 in self.spans():
            if who == actor:
                continue
            d.activation(who, y1, y2)
            cx = self.cx[self.idx[who]]
            d.boxes[f"act {who} {y1}"] = (Rect(cx - 4, y1, 8, y2 - y1), "solid")


def _check_entities(stereotypes):
    for name, st in stereotypes.items():
        if st == E:
            assert name in model.ANALYSIS, f"{name} is not an analysis class"


def bce(root, id_, name, parts, msgs, frags, gap=40):
    stereotypes = {p: st for p, st in parts}
    _check_entities(stereotypes)
    d = Diagram(root, id_, name, *SCOPE, numbers=True)
    seq_parts = [("Customer", "Customer")] + [(p, p) for p, _ in parts]
    BceSeq(d, seq_parts, msgs, frags, stereotypes, gap=gap).draw()


# ----------------------------------------------------------------- UC02
def search(root):
    parts = [("SearchUI", B), ("SearchControl", C), ("Painting", E), ("Artist", E)]
    msgs = [
        ("Customer", "SearchUI", "enter search text", "call"),
        ("SearchUI", "SearchControl", "search(text)", "call"),
        ("SearchControl", "SearchControl", "interpret request", "self"),
        ("SearchControl", "Painting", "findCandidates(conditions)", "call"),
        ("Painting", "Artist", "getName()", "call"),
        ("Artist", "Painting", "artist name", "return"),
        ("Painting", "SearchControl", "candidate paintings", "return"),
        ("SearchControl", "SearchControl", "rank by relevance", "self"),              # 7
        ("SearchControl", "SearchUI", "ranked paintings", "return"),
        ("SearchUI", "Customer", "show results and reasons", "return"),
        ("SearchControl", "SearchUI", "no result", "return"),                        # 10
        ("SearchUI", "Customer", "show empty state and hint", "return"),
    ]
    frags = [("alt", 7, 11, [("paintings found", 7), ("no match", 10)],
              ["Customer", "SearchUI", "SearchControl"])]
    bce(root, "c2_bce_search", "2.6a Analysis Sequence - Search by Keyword (UC02)", parts, msgs, frags)


# ----------------------------------------------------------------- UC07
def checkout(root):
    parts = [("CheckoutUI", B), ("CheckoutControl", C), ("Cart", E), ("Painting", E), ("Order", E),
             ("OrderItem", E), ("Payment", E)]
    msgs = [
        ("Customer", "CheckoutUI", "confirm order", "call"),
        ("CheckoutUI", "CheckoutControl", "checkout(address, method)", "call"),
        ("CheckoutControl", "Cart", "getLines()", "call"),
        ("Cart", "CheckoutControl", "cart lines", "return"),
        ("CheckoutControl", "Painting", "checkStock(quantity)", "call"),            # 4
        ("Painting", "CheckoutControl", "stock, current price", "return"),
        ("CheckoutControl", "CheckoutUI", "refused, item name", "return"),         # 6
        ("CheckoutUI", "Customer", "show item out of stock", "return"),
        ("CheckoutControl", "Order", "create(cart lines)", "call"),                # 8
        ("Order", "OrderItem", "create(frozen price)", "send"),
        ("Order", "Order", "calculateTotal()", "self"),
        ("Order", "CheckoutControl", "order", "return"),
        ("CheckoutControl", "Payment", "record(total, method)", "send"),
        ("CheckoutControl", "Painting", "reduceStock(quantity)", "send"),
        ("CheckoutControl", "Cart", "empty()", "send"),
        ("CheckoutControl", "CheckoutUI", "order id, PLACED", "return"),
        ("CheckoutUI", "Customer", "show order id, PLACED", "return"),
    ]
    frags = [("loop", 4, 5, [("for each cart line", 4)], ["CheckoutControl", "Cart", "Painting"]),
             ("alt", 6, 16, [("item out of stock", 6), ("all items in stock", 8)],
              ["Customer", "CheckoutUI", "CheckoutControl", "Cart", "Painting", "Order", "OrderItem", "Payment"])]
    bce(root, "c2_bce_checkout", "2.6b Analysis Sequence - Checkout (UC07)", parts, msgs, frags, gap=0)


# ----------------------------------------------------------------- UC11
def cancel(root):
    parts = [("OrderUI", B), ("CancelOrderControl", C), ("Order", E)]
    msgs = [
        ("Customer", "OrderUI", "cancel order", "call"),
        ("OrderUI", "CancelOrderControl", "cancel(orderId)", "call"),
        ("CancelOrderControl", "Order", "find(orderId)", "call"),
        ("Order", "CancelOrderControl", "order, owner, status", "return"),
        ("CancelOrderControl", "CancelOrderControl", "check owner and status", "self"),
        ("CancelOrderControl", "OrderUI", "not found", "return"),                  # 5
        ("OrderUI", "Customer", "show \"not found in your account\"", "return"),
        ("CancelOrderControl", "OrderUI", "refused: already shipped", "return"),    # 7
        ("OrderUI", "Customer", "show why it cannot be cancelled", "return"),
        ("CancelOrderControl", "OrderUI", "already cancelled", "return"),           # 9
        ("OrderUI", "Customer", "show \"already cancelled\"", "return"),
        ("CancelOrderControl", "Order", "cancel()", "call"),                       # 11
        ("Order", "CancelOrderControl", "status CANCELLED", "return"),
        ("CancelOrderControl", "OrderUI", "cancelled", "return"),
        ("OrderUI", "Customer", "show status CANCELLED", "return"),
    ]
    frags = [("alt", 5, 14, [("not the customer's order", 5), ("already shipped", 7), ("already cancelled", 9),
                             ("PLACED or PROCESSING", 11)], ["Customer", "OrderUI", "CancelOrderControl", "Order"])]
    bce(root, "c2_bce_cancel", "2.6c Analysis Sequence - Cancel Order (UC11)", parts, msgs, frags)


def build(root):
    search(root)
    checkout(root)
    cancel(root)
