"""Business and data-flow diagrams that need the full edition of Visual Paradigm (BPMN, ArchiMate, DFD).

The Community Edition refuses these diagram types, so they are marked edition="trial": tools/build_vp.py builds
them in the trial edition's window and saves a screenshot of the window (tools/vp_shots.py) instead of a
watermarked export. The essay labels these figures as screenshots of the trial edition.

    c1_process       1.4 business process, order to delivery (BPMN: pools, lanes, message flows)
    c1_stakeholders  1.3 stakeholder map (ArchiMate: stakeholders, concerns, goals)
    c1_problems      1.6 problem tree (ArchiMate: root causes -> problems -> impacts)
    c1_dfd0          1.7 context diagram as DFD level 0
    c2_dfd1          2.x DFD level 1, balanced with level 0
"""
from .common import Diagram, LINE, caption_size, text_w

TRIAL = dict(kind="raw", edition="trial")


def label_at(pts, seg, side, lines, gap=8, along=0.5):
    """Centre of a caption box next to segment seg of pts: above/below a horizontal one, left/right of a vertical."""
    (x1, y1), (x2, y2) = pts[seg], pts[seg + 1]
    w, h = caption_size(lines)
    mx, my = x1 + (x2 - x1) * along, y1 + (y2 - y1) * along
    if side == "above":
        return mx, my - gap - h / 2
    if side == "below":
        return mx, my + gap + h / 2
    if side == "left":
        return mx - gap - w / 2, my
    return mx + gap + w / 2, my


# ------------------------------------------------------------------ DFD
def _dfd(root, id_, name):
    return Diagram(root, id_, name, scope="dfd", scope_name="1 Data flows", vptype="DataFlowDiagram", **TRIAL)


def _flow(d, frm, to, pts, text, seg=0, side="above", along=0.5):
    lines = [text]
    d.edge("DFDataFlow", frm, to, pts, label=lines, at=label_at(pts, seg, side, lines, along=along), name=text)


def dfd0(root):
    """Context diagram as a DFD: the whole of Họa. is process 0, the four external entities and eight flows
    (the same flows as Table tab:contextflows)."""
    d = _dfd(root, "c1_dfd0", "1.7 Context Diagram - DFD Level 0")
    px, py, pw, ph = 560, 300, 200, 120
    cx, cy = px + pw / 2, py + ph / 2
    d.node("P0", "DFProcess", "Họa. Gallery", px, py, pw, ph, number="0")
    d.node("Customer", "DFExternalEntity", "Customer", 40, cy - 30, 150, 60)
    d.node("Payment", "DFExternalEntity", "Payment Service", 1130, cy - 30, 170, 60)
    d.node("Admin", "DFExternalEntity", "Administrator", cx - 85, 40, 170, 60)
    d.node("Gemma", "DFExternalEntity", "Gemma 4 Service", cx - 85, 640, 170, 60)
    top, bottom, left, right = cy - 14, cy + 14, cx - 14, cx + 14
    _flow(d, "Customer", "P0", [(190, top), (px, top)], "search queries (text, voice, image), cart, orders")
    _flow(d, "P0", "Customer", [(px, bottom), (190, bottom)], "search results, order status, assistant answers",
          side="below")
    _flow(d, "P0", "Payment", [(px + pw, top), (1130, top)], "payment request (order id, amount)")
    _flow(d, "Payment", "P0", [(1130, bottom), (px + pw, bottom)], "authorisation result", side="below")
    _flow(d, "Admin", "P0", [(left, 100), (left, py)], "paintings, prices, stock, order status", side="left")
    _flow(d, "P0", "Admin", [(right, py), (right, 100)], "painting and order lists", side="right")
    _flow(d, "P0", "Gemma", [(left, py + ph), (left, 640)], "prompts, photos, tool definitions", side="left")
    _flow(d, "Gemma", "P0", [(right, 640), (right, py + ph)], "filters, photo descriptions, tool calls, answers",
          side="right")


def dfd1(root):
    """Level 1: process 0 split into four processes and three data stores. Every flow of level 0 appears again
    (balancing). The customer and D1 are drawn twice so that no flow crosses another."""
    d = _dfd(root, "c2_dfd1", "2.9c Data Flow Diagram - Level 1")
    PX, PW = 420, 190            # processes on the left
    SX, SW = 800, 200            # data stores in the middle
    QX, QW = 1190, 190           # checkout process on the right
    EX, EW = 1620, 170           # external entities on the right
    # Process 1 (top left) and process 3 (bottom left) face the customer on the left.
    d.node("P1", "DFProcess", "Find paintings and answer questions", PX, 120, PW, 130, number="1")
    d.node("P3", "DFProcess", "Follow and cancel orders", PX, 520, PW, 110, number="3")
    d.node("Customer", "DFExternalEntity", "Customer", 40, 120, 150, 510)
    d.node("Gemma", "DFExternalEntity", "Gemma 4 Service", SX + 15, 20, 170, 60)
    d.node("D1", "DFDataStore", "Paintings and artists", SX, 205, SW, 40, number="1")
    d.node("D2", "DFDataStore", "Carts", SX, 375, SW, 40, number="2")
    d.node("D3", "DFDataStore", "Orders, payments, shipping", SX, 545, SW, 40, number="3")
    # Process 2 (checkout) sits right of the stores; process 4 (administration) below them.
    d.node("P2", "DFProcess", "Shop and check out", QX, 180, QW, 430, number="2")
    d.node("Customer2", "DFExternalEntity", "Customer", EX, 220, EW, 60)
    d.node("Payment", "DFExternalEntity", "Payment Service", EX, 470, EW, 60)
    d.node("P4", "DFProcess", "Administer catalogue and orders", SX + 5, 720, SW - 10, 120, number="4")
    d.node("D1b", "DFDataStore", "Paintings and artists", 420, 760, SW, 40, number="1")
    d.node("Admin", "DFExternalEntity", "Administrator", 1250, 750, 190, 60)

    # Customer <-> 1 and 3 (left).
    _flow(d, "Customer", "P1", [(190, 168), (PX, 168)], "search query, question")
    _flow(d, "P1", "Customer", [(PX, 200), (190, 200)], "ranked paintings, answers", side="below")
    _flow(d, "Customer", "P3", [(190, 560), (PX, 560)], "order id, cancel request")
    _flow(d, "P3", "Customer", [(PX, 592), (190, 592)], "order status", side="below")
    # 1 <-> Gemma (up), D1 -> 1, D3 -> 1 (own orders for the assistant).
    _flow(d, "P1", "Gemma", [(PX + PW, 135), (SX + 40, 135), (SX + 40, 80)], "prompts, photos, tools", seg=0,
          side="above", along=0.4)
    _flow(d, "Gemma", "P1", [(SX + 160, 80), (SX + 160, 150), (PX + PW, 150)], "filters, descriptions, tool calls",
          seg=1, side="below", along=0.5)
    _flow(d, "D1", "P1", [(SX, 225), (PX + PW, 225)], "painting data")
    _flow(d, "D3", "P1", [(SX, 552), (720, 552), (720, 238), (PX + PW, 238)], "own orders", seg=1, side="right",
          along=0.75)
    # 3 <-> D3.
    _flow(d, "D3", "P3", [(SX, 568), (PX + PW, 568)], "orders", side="below", along=0.38)
    _flow(d, "P3", "D3", [(PX + PW, 612), (SX + 30, 612), (SX + 30, 585)], "status CANCELLED", side="below",
          along=0.45)
    # 2 <-> D1, D2, D3 (left side of process 2), Customer and Payment Service (right side).
    _flow(d, "D1", "P2", [(SX + SW, 215), (QX, 215)], "price, stock")
    _flow(d, "P2", "D1", [(QX, 235), (SX + SW, 235)], "stock decrease", side="below")
    _flow(d, "D2", "P2", [(SX + SW, 385), (QX, 385)], "cart lines")
    _flow(d, "P2", "D2", [(QX, 405), (SX + SW, 405)], "cart changes", side="below")
    _flow(d, "P2", "D3", [(QX, 565), (SX + SW, 565)], "new order, payment")
    _flow(d, "Customer2", "P2", [(EX, 240), (QX + QW, 240)], "cart, address, payment method")
    _flow(d, "P2", "Customer2", [(QX + QW, 262), (EX, 262)], "order confirmation", side="below")
    _flow(d, "P2", "Payment", [(QX + QW, 490), (EX, 490)], "payment request")
    _flow(d, "Payment", "P2", [(EX, 512), (QX + QW, 512)], "authorisation result", side="below")
    # 4 <-> D3 (above), D1 (left copy), Administrator (right).
    _flow(d, "D3", "P4", [(SX + 70, 585), (SX + 70, 720)], "orders", side="left", along=0.55)
    _flow(d, "P4", "D3", [(SX + 130, 720), (SX + 130, 585)], "new status", side="right", along=0.45)
    _flow(d, "P4", "D1b", [(SX + 5, 780), (420 + SW, 780)], "painting changes")
    _flow(d, "Admin", "P4", [(1250, 770), (SX + SW - 5, 770)], "paintings, prices, stock, status")
    _flow(d, "P4", "Admin", [(SX + SW - 5, 795), (1250, 795)], "painting and order lists", side="below")


# ------------------------------------------------------------------ BPMN
def process(root):
    """Order to delivery in BPMN: the customer, the gallery (administrator and warehouse lanes) and the two
    outside services as black-box pools, joined by message flows (Table tab:processes, tab:exceptions)."""
    d = Diagram(root, "c1_process", "1.4 Business Process - Order to Delivery (BPMN)", scope="bpmn",
                scope_name="1 Business processes", vptype="BusinessProcessDiagram", **TRIAL)
    W = 1760
    # Pools and lanes (role frame: shapes sit inside them).
    d.node("cust", "BPPool", "Customer", 20, 20, W, 150, role="frame")
    d.node("hoa", "BPPool", "Họa. Gallery", 20, 230, W, 360, role="frame")
    d.node("adm", "BPLane", "Administrator", 50, 230, W - 30, 180, parent="hoa", role="frame")
    d.node("wh", "BPLane", "Warehouse staff", 50, 410, W - 30, 180, parent="hoa", role="frame")
    d.node("pay", "BPPool", "Payment Service", 600, 660, 520, 60, role="frame", blackBox=True)
    d.node("car", "BPPool", "Delivery carrier", 1180, 660, 520, 60, role="frame", blackBox=True)

    def task(nid, name, x, cy, parent, w=130):
        d.node(nid, "BPTask", name, x, cy - 30, w, 60, parent=parent)
        return d.rect(nid)

    def event(nid, type_, cx, cy, parent, **kw):
        d.node(nid, type_, "", cx - 15, cy - 15, 30, 30, parent=parent, **kw)

    def seq(frm, to, pts, guard=None, at=None):
        if guard:
            d.edge("BPSequenceFlow", frm, to, pts, label=[guard], at=at, name=guard)
        else:
            d.edge("BPSequenceFlow", frm, to, pts)

    def msg(frm, to, pts, text, seg=0, side="right", along=0.5):
        lines = [text]
        d.edge("BPMessageFlow", frm, to, pts, label=lines, at=label_at(pts, seg, side, lines, along=along),
               name=text)

    yc = 95                      # customer row
    event("c0", "BPStartEvent", 110, yc, "cust")
    t1 = task("c1", "Find a painting", 170, yc, "cust")
    t2 = task("c2", "Add prints and frames to the cart", 350, yc, "cust", w=150)
    t3 = task("c3", "Place the order", 550, yc, "cust")
    t4 = task("c4", "Receive the parcel", 1390, yc, "cust")
    event("c9", "BPEndEvent", 1580, yc, "cust")
    seq("c0", "c1", [(125, yc), (t1.x, yc)])
    seq("c1", "c2", [(t1.r, yc), (t2.x, yc)])
    seq("c2", "c3", [(t2.r, yc), (t3.x, yc)])
    seq("c4", "c9", [(t4.r, yc), (1565, yc)])

    ya = 320                     # administrator row
    event("a0", "BPStartEvent", 600, ya - 60, "adm", trigger="message")
    a1 = task("a1", "Check cart and stock, freeze prices", 650, ya, "adm", w=160)
    d.node("g1", "BPGateway", "", 860, ya - 20, 40, 40, parent="adm")
    a2 = task("a2", "Request card authorisation", 960, ya + 50, "adm", w=150)
    d.node("g2", "BPGateway", "", 1160, ya - 20, 40, 40, parent="adm")
    a3 = task("a3", "Create the order (PLACED)", 1240, ya, "adm", w=150)
    a4 = task("a4", "Mark the order DELIVERED", 1500, ya, "adm", w=150)
    event("a9", "BPEndEvent", 1710, ya, "adm")
    seq("a0", "a1", [(600, ya - 45), (600, ya), (a1.x, ya)])
    seq("a1", "g1", [(a1.r, ya), (860, ya)])
    seq("g1", "a2", [(880, ya + 20), (880, ya + 50), (a2.x, ya + 50)], "card", at=(925, ya + 34))
    seq("a2", "g2", [(a2.r, ya + 50), (1180, ya + 50), (1180, ya + 20)])
    seq("g1", "g2", [(900, ya), (1160, ya)], "cash on delivery", at=(1030, ya - 18))
    seq("g2", "a3", [(1200, ya), (a3.x, ya)])
    seq("a4", "a9", [(a4.r, ya), (1695, ya)])

    yw = 500                     # warehouse row
    w1 = task("w1", "Pick and pack the order (PROCESSING)", 1230, yw, "wh", w=170)
    w2 = task("w2", "Hand over to the carrier (SHIPPED)", 1460, yw, "wh", w=170)
    seq("a3", "w1", [(1315, ya + 30), (1315, yw - 30)])
    seq("w1", "w2", [(w1.r, yw), (w2.x, yw)])
    seq("w2", "a4", [(1575, yw - 30), (1575, ya + 30)])

    msg("c3", "a0", [(600, yc + 30), (600, ya - 75)], "order", side="right")
    msg("a2", "pay", [(1005, ya + 80), (1005, 660)], "payment request", side="left", along=0.55)
    msg("pay", "a2", [(1065, 660), (1065, ya + 80)], "authorisation result", side="right", along=0.45)
    msg("w2", "car", [(1545, yw + 30), (1545, 660)], "parcel, address", side="right", along=0.83)
    msg("car", "c4", [(1740, 660), (1740, 140), (1455, 140), (1455, yc + 30)], "parcel", side="left",
        along=0.077)


# ------------------------------------------------------------------ ArchiMate
def _archi(root, id_, name):
    return Diagram(root, id_, name, scope="archimate", scope_name="1 Motivation", vptype="ArchiMateDiagram",
                   **TRIAL)


STAKEHOLDERS = ["Support staff", "Customer", "Payment service", "Shop owner", "Shop administrator",
                "Warehouse staff", "Gemma 4 AI service", "Developer and lecturer"]
CONCERNS = [  # (concern, stakeholders who have it, goal), ordered so that no association crosses another
    ("Know where an order is", ["Support staff", "Customer"], 2),
    ("Find a painting without knowing its title", ["Customer"], 0),
    ("Nobody sees another person's order; card and voice stay private",
     ["Customer", "Payment service", "Shop owner"], 4),
    ("Increase revenue, see best sellers", ["Shop owner"], 3),
    ("Correct catalogue, prices and stock", ["Shop administrator", "Warehouse staff"], 1),
    ("AI can be slow or unavailable", ["Gemma 4 AI service"], 5),
    ("Model follows the lectures; demo runs", ["Developer and lecturer"], 6),
]
GOALS = ["Multimodal search with reasons (FR01-FR04, FR14)", "Accurate stock at checkout (FR07)",
         "Self-service order tracking and cancellation (FR08-FR11)", "Back office for paintings and orders (FR12, FR13)",
         "Ownership checks, no card numbers, local voice (NFR01, NFR05, NFR08)", "Keyword fallback when AI fails (NFR02)",
         "One shared specification for diagrams, code and data"]


def stakeholders(root):
    """Stakeholder map: who has which concern (driver), and which goal of the system answers it
    (Table tab:stakeholders)."""
    d = _archi(root, "c1_stakeholders", "1.3 Stakeholder Map (ArchiMate)")
    sw, sh, cw, ch, gw, gh = 190, 52, 300, 64, 340, 64
    sx, cx, gx = 40, 420, 900
    ys = {s_: 40 + i * 76 for i, s_ in enumerate(STAKEHOLDERS)}
    for i, s_ in enumerate(STAKEHOLDERS):
        d.node(f"s{i}", "ArchiMateStakeholder", s_, sx, ys[s_], sw, sh)
    for j, (concern, owners, goal) in enumerate(CONCERNS):
        y = 30 + j * 86
        d.node(f"c{j}", "ArchiMateDriver", concern, cx, y, cw, ch)
        d.node(f"g{j}", "ArchiMateGoal", GOALS[goal], gx, y, gw, gh)
        d.edge("ArchiMateInfluence", f"c{j}", f"g{j}", [(cx + cw, y + ch / 2), (gx, y + ch / 2)])
        for k, owner in enumerate(owners):
            i = STAKEHOLDERS.index(owner)
            y2 = y + ch / 2 + (k - (len(owners) - 1) / 2) * 16
            d.edge("ArchiMateAssociation", f"s{i}", f"c{j}", [(sx + sw, ys[owner] + sh / 2), (cx, y2)])


PROBLEMS = [  # (root cause, problem, impact)
    ("Search by title only; no style, subject or colour data; photos and speech unusable",
     "P1 Customers cannot find a suitable painting", "Lost customers, long consultations"),
    ("Stock updated by hand, separate from orders", "P2 Sold-out prints are sold", "Cancelled or late orders, lost trust"),
    ("Order status only in a staff spreadsheet", "P3 Customers do not know where their order is",
     "Repeated questions, overloaded staff"),
    ("No administration tool", "P4 Orders and prices handled by hand", "Wrong prices, slow delivery"),
    ("Customers identified by an order id in a message; card numbers written down",
     "P5 Risk of leaking order and payment data", "Legal risk, loss of trust"),
]


def problems(root):
    """Problem tree: each root cause influences a problem, each problem an impact (Table tab:pcin)."""
    d = _archi(root, "c1_problems", "1.6 Problem Tree (ArchiMate)")
    w, gap = 220, 40
    rows = {"impact": (40, 70), "problem": (230, 70), "cause": (420, 90)}
    for i, (cause, problem, impact) in enumerate(PROBLEMS):
        x = 40 + i * (w + gap)
        d.node(f"i{i}", "ArchiMateOutcome", impact, x, rows["impact"][0], w, rows["impact"][1])
        d.node(f"p{i}", "ArchiMateAssessment", problem, x, rows["problem"][0], w, rows["problem"][1])
        d.node(f"c{i}", "ArchiMateAssessment", cause, x, rows["cause"][0], w, rows["cause"][1])
        mid = x + w / 2
        d.edge("ArchiMateInfluence", f"c{i}", f"p{i}", [(mid, rows["cause"][0]), (mid, 230 + 70)])
        d.edge("ArchiMateInfluence", f"p{i}", f"i{i}", [(mid, 230), (mid, 40 + 70)])
    left = 40 + 5 * (w + gap) + 10
    for text, (y, h) in (("Impacts", rows["impact"]), ("Problems", rows["problem"]), ("Root causes", rows["cause"])):
        d.node(f"t_{text}", "Note", text, left, y + h / 2 - 18, text_w(text) + 64, LINE + 24)


def build(root):
    process(root)
    stakeholders(root)
    problems(root)
    dfd0(root)
    dfd1(root)
