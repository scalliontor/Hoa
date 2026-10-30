"""Chapter 1 (Requirement Determination): context view and use case diagram."""
from .common import Diagram, LINE, caption_size, text_w
import model

SYSTEM = "Họa. Gallery"
USE_CASE = {uid: (name, actor, kind) for uid, name, actor, kind in model.USE_CASES}


def context(root):
    """Slide 01 context view: the system as one black box, the four external parties and their flows.
    (VP Community Edition has no DFD, so flows are «flow» dependencies in a class diagram.)"""
    d = Diagram(root, "c1_context", "1.1 Context View - Hoa Gallery", "class", "usecase", "1 Use cases")
    sys_w, sys_h = 240, 70
    sx, sy = 560, 300
    d.node("system", "Class", SYSTEM, sx, sy, sys_w, sys_h, stereotype="system", hideMembers=True)
    cx, cy = sx + sys_w / 2, sy + sys_h / 2
    cust = d.actor("Customer", "Customer", 120, cy - 40)
    pay = d.actor("Payment Service", "Payment Service", sx + sys_w + 400, cy - 40)
    admin = d.actor("Administrator", "Administrator", cx - 20, 30)
    gemma = d.actor("Gemma 4 Service", "Gemma 4 Service", cx - 20, sy + sys_h + 150)

    def flow(frm, to, text, pts, side):
        lines = ["<<flow>>", text]
        w, h = caption_size(lines)
        (x1, y1), (x2, y2) = pts
        if side == "above":
            at = ((x1 + x2) / 2, y1 - 8 - h / 2)
        elif side == "below":
            at = ((x1 + x2) / 2, y1 + 8 + h / 2)
        elif side == "left":
            at = (x1 - 10 - w / 2, (y1 + y2) / 2)
        else:
            at = (x1 + 10 + w / 2, (y1 + y2) / 2)
        d.edge("Dependency", frm, to, pts, label=lines, at=at, stereotype="flow", name=text)

    top, bottom = cy - 12, cy + 12
    left, right = cx - 12, cx + 12
    flow("Customer", "system", "search queries (text, voice, image), cart, orders",
         [(cust.r, top), (sx, top)], "above")
    flow("system", "Customer", "search results, order status, assistant answers",
         [(sx, bottom), (cust.r, bottom)], "below")
    flow("system", "Payment Service", "payment request (order id, amount)",
         [(sx + sys_w, top), (pay.x, top)], "above")
    flow("Payment Service", "system", "authorisation result (authorizationCode)",
         [(pay.x, bottom), (sx + sys_w, bottom)], "below")
    below_admin = admin.b + LINE + 12          # lines start under the actor's name
    flow("Administrator", "system", "paintings, prices, stock, order status",
         [(left, below_admin), (left, sy)], "left")
    flow("system", "Administrator", "painting and order lists",
         [(right, sy), (right, below_admin)], "right")
    flow("system", "Gemma 4 Service", "prompts, photos, tool definitions",
         [(left, sy + sys_h), (left, gemma.y)], "left")
    flow("Gemma 4 Service", "system", "filters, photo descriptions, tool calls, answers",
         [(right, gemma.y), (right, sy + sys_h)], "right")


def usecase(root):
    """Four actors, UC01-UC14 with USE_CASE_LINKS and SUPPORTING_ACTORS, no crossing actor lines."""
    d = Diagram(root, "c1_usecase", "1.2 Use Case Diagram - Hoa Gallery", "usecase", "usecase", "1 Use cases")
    col_a = ["UC06", "UC07", "UC08", "UC09", "UC10", "UC01", "UC05", "UC12", "UC13"]   # rows 0..8
    col_b = {"UC11": 2, "UC02": 5, "UC03": 6, "UC04": 7, "UC14": 8}
    assert set(col_a) | set(col_b) == set(USE_CASE)
    label = {uid: f"{uid} {USE_CASE[uid][0]}" for uid in USE_CASE}
    h, pitch, top = 46, 84, 100
    wa = int(max(text_w(label[u]) for u in col_a) + 64)
    wb = int(max(text_w(label[u]) for u in col_b) + 64)
    a_left = 330
    b_left = a_left + wa + 190
    ax, bx = a_left + wa / 2, b_left + wb / 2
    row_y = [top + i * pitch for i in range(9)]           # centre line of each row
    pos = {u: (a_left, row_y[i], wa) for i, u in enumerate(col_a)}
    pos.update({u: (b_left, row_y[r], wb) for u, r in col_b.items()})

    sys_box = (a_left - 50, 30, wa + 190 + wb + 100, row_y[8] + h / 2 + 40 - 30)
    d.node("system", "System", SYSTEM, *sys_box, role="frame")
    d.text(SYSTEM, sys_box[0] + sys_box[2] / 2 - 50, sys_box[1], 100, LINE + 4, owner="system")
    for uid, (x, cy, w) in pos.items():
        abstract = USE_CASE[uid][2] == "abstract"
        d.node(uid, "UseCase", label[uid], x, cy - h / 2, w, h, parent="system", abstract=abstract or None)

    def left_pt(uid):
        x, cy, w = pos[uid]
        return x, cy

    def right_pt(uid):
        x, cy, w = pos[uid]
        return x + w, cy

    # Actors: primary on the left, supporting on the right.
    cust = d.actor("Customer", "Customer", 120, row_y[3] - 40)
    admin = d.actor("Administrator", "Administrator", 120, (row_y[7] + row_y[8]) / 2 - 40)
    pay = d.actor("Payment Service", "Payment Service", b_left + wb + 170, row_y[1] - 40)
    gemma = d.actor("Gemma 4 Service", "Gemma 4 Service", b_left + wb + 170, (row_y[6] + row_y[7]) / 2 - 40)

    primary = {"Customer": ["UC06", "UC07", "UC08", "UC09", "UC10", "UC01", "UC05"],
               "Administrator": ["UC12", "UC13"]}
    for actor, ucs in primary.items():
        r = d.rect(actor)
        for uid in ucs:
            assert USE_CASE[uid][1] == actor
            d.edge("Association", actor, uid, [(r.r, r.y + 34), left_pt(uid)])
    for uid, helpers in model.SUPPORTING_ACTORS.items():
        for actor in helpers:
            r = d.rect(actor)
            if uid in col_b:                       # fan from the actor's left side
                pts = [(r.x, r.y + 34), right_pt(uid)]
            elif actor == "Payment Service":       # same row: straight line
                pts = [(r.x, right_pt(uid)[1]), right_pt(uid)]
            else:                                  # UC10: up from the head, then left through the empty row
                pts = [(r.cx, r.y), (r.cx, right_pt(uid)[1]), right_pt(uid)]
            d.edge("Association", actor, uid, pts)

    trunk = (a_left + wa + b_left) / 2
    stereo = {"Include": "<<Include>>", "Extend": "<<Extend>>"}
    for frm, to, kind in model.USE_CASE_LINKS:
        if kind == "Generalization":
            fx, fy = left_pt(frm)
            tx, ty = right_pt(to)
            pts = [(fx, fy), (tx, ty)] if fy == ty else [(fx, fy), (trunk, fy), (trunk, ty), (tx, ty)]
            d.edge("Generalization", frm, to, pts)
            continue
        text = stereo[kind]
        w, lh = caption_size([text])
        fx, fy, fw = pos[frm]
        tx, ty, tw = pos[to]
        if fx == tx:                               # vertical, in the same column
            x = ax
            y1 = fy - h / 2 if fy > ty else fy + h / 2
            y2 = ty + h / 2 if fy > ty else ty - h / 2
            at = (x + 10 + w / 2, (y1 + y2) / 2)
            pts = [(x, y1), (x, y2)]
        else:                                      # horizontal, from column B to column A
            pts = [left_pt(frm), right_pt(to)]
            at = ((pts[0][0] + pts[1][0]) / 2, fy - 8 - lh / 2)
        d.edge(kind, frm, to, pts, label=[text], at=at)


def build(root):
    context(root)
    usecase(root)
