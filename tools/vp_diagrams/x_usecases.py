"""Section 2.4 detail use case diagrams: search and discovery, cart/checkout/orders, assistant and administration.

Same conventions as ch1.usecase() (the overview c1_usecase): use cases inside the "Họa. Gallery" system
frame, primary actors on the left with their lines starting under the actor's hand, supporting actors on
the right, «include» from base to addition, «extend» from extension to base, generalization child -> parent.
Names, links and supporting actors come from model.USE_CASES, USE_CASE_LINKS and SUPPORTING_ACTORS.
"""
from .common import Diagram, LINE, caption_size, text_w
import model

SYSTEM = "Họa. Gallery"
USE_CASE = {uid: (name, actor, kind) for uid, name, actor, kind in model.USE_CASES}
STEREO = {"Include": "<<Include>>", "Extend": "<<Extend>>"}
H, PITCH, TOP = 46, 84, 100           # ellipse height, row pitch, centre of the first row (as in c1_usecase)
A_LEFT = 330                          # left edge of the first use case column
ACTOR_X = 120                         # primary actors
SIDE = 120                            # gap between the system frame and a supporting actor


def label(uid):
    return f"{uid} {USE_CASE[uid][0]}"


def col_width(uids):
    return int(max(text_w(label(u)) for u in uids) + 64)


def links_between(uids):
    """USE_CASE_LINKS whose two ends are both drawn."""
    return [(f, t, k) for f, t, k in model.USE_CASE_LINKS if f in uids and t in uids]


def supporting(uids):
    return [(uid, actor) for uid, actors in model.SUPPORTING_ACTORS.items() if uid in uids for actor in actors]


class Board:
    """One use case diagram: positions of the ellipses, the system frame and the connector helpers."""

    def __init__(self, root, id_, name):
        # Own model package per diagram ("1 Use cases - 2.4a ..."): VP renames a second System called
        # "Họa. Gallery" in one package to "Họa. Gallery2". Actors stay shared with every other diagram.
        self.d = Diagram(root, id_, name, "usecase", id_, "1 Use cases - " + name.replace(" Use Cases -", ""))
        self.pos = {}                 # uid -> (left x, centre y, width)

    def place(self, uid, x, cy, w):
        self.pos[uid] = (x, cy, w)

    def left(self, uid):
        x, cy, w = self.pos[uid]
        return x, cy

    def right(self, uid):
        x, cy, w = self.pos[uid]
        return x + w, cy

    def draw(self):
        """System frame around every use case (title on top), then the ellipses inside it."""
        d = self.d
        x0 = min(x for x, _, _ in self.pos.values()) - 50
        x1 = max(x + w for x, _, w in self.pos.values()) + 50
        y0 = min(cy for _, cy, _ in self.pos.values()) - H / 2 - 47
        y1 = max(cy for _, cy, _ in self.pos.values()) + H / 2 + 40
        d.node("system", "System", SYSTEM, x0, y0, x1 - x0, y1 - y0, role="frame")
        d.text(SYSTEM, (x0 + x1) / 2 - 50, y0, 100, LINE + 4, owner="system")
        for uid, (x, cy, w) in self.pos.items():
            abstract = USE_CASE[uid][2] == "abstract"
            d.node(uid, "UseCase", label(uid), x, cy - H / 2, w, H, parent="system", abstract=abstract or None)
        return x1

    # ------------------------------------------------------------ connectors
    def primary(self, actor, uids):
        """Associations from the primary actor's hand to the left end of each use case."""
        r = self.d.rect(actor)
        for uid in uids:
            assert USE_CASE[uid][1] == actor, (uid, actor)
            self.d.edge("Association", actor, uid, [(r.r, r.y + 34), self.left(uid)])

    def helper(self, actor, uid):
        """Supporting actor on the right: straight line on the use case's row, else from the actor's hand."""
        assert actor in model.SUPPORTING_ACTORS.get(uid, ()), (uid, actor)
        r = self.d.rect(actor)
        end = self.right(uid)
        start = (r.x, end[1]) if r.y < end[1] < r.y + 60 else (r.x, r.y + 34)
        self.d.edge("Association", actor, uid, [start, end])

    def vertical(self, frm, to, kind):
        """«include» / «extend» between two use cases of one column, caption right of the line."""
        text = STEREO[kind]
        w, _ = caption_size([text])
        fx, fy, fw = self.pos[frm]
        tx, ty, tw = self.pos[to]
        x = fx + fw / 2
        assert x == tx + tw / 2, (frm, to)
        y1 = fy - H / 2 if fy > ty else fy + H / 2
        y2 = ty + H / 2 if fy > ty else ty - H / 2
        self.d.edge(kind, frm, to, [(x, y1), (x, y2)], label=[text], at=(x + 10 + w / 2, (y1 + y2) / 2))

    def generalization(self, child, parent, trunk):
        """Child (right column) -> parent (left column) through a shared vertical trunk."""
        fx, fy = self.left(child)
        tx, ty = self.right(parent)
        pts = [(fx, fy), (tx, ty)] if fy == ty else [(fx, fy), (trunk, fy), (trunk, ty), (tx, ty)]
        self.d.edge("Generalization", child, parent, pts)


def search(root):
    """2.4a: abstract UC01 with its four specialisations, UC05 extending it, Gemma 4 behind the AI searches."""
    b = Board(root, "c2_uc_search", "2.4a Use Cases - Search and Discovery")
    d = b.d
    kids = [f for f, t, k in model.USE_CASE_LINKS if k == "Generalization" and t == "UC01"]   # UC02 UC03 UC04 UC14
    extension = [f for f, t, k in model.USE_CASE_LINKS if k == "Extend" and t == "UC01"]      # UC05
    col_a, col_b = ["UC01"] + extension, kids
    wa, wb = col_width(col_a), col_width(col_b)
    b_left = A_LEFT + wa + 190
    rows = [TOP + i * PITCH for i in range(len(kids))]
    for uid, cy in zip(kids, rows):
        b.place(uid, b_left, cy, wb)
    parent_y = (rows[1] + rows[2]) / 2                 # UC01 level with the middle of its children
    b.place("UC01", A_LEFT, parent_y, wa)
    b.place(extension[0], A_LEFT, rows[-1], wa)        # UC05 below UC01
    right = b.draw()

    d.actor("Customer", "Customer", ACTOR_X, (parent_y + rows[-1]) / 2 - 34)
    d.actor("Gemma 4 Service", "Gemma 4 Service", right + SIDE, parent_y - 34)

    b.primary("Customer", ["UC01"] + extension)
    for uid, actor in supporting(set(b.pos)):
        b.helper(actor, uid)
    trunk = (A_LEFT + wa + b_left) / 2
    for frm, to, kind in links_between(set(b.pos)):
        if kind == "Generalization":
            b.generalization(frm, to, trunk)
        else:
            b.vertical(frm, to, kind)


def purchase(root):
    """2.4b: cart, checkout (includes Manage Cart, uses Payment Service) and the order use cases."""
    b = Board(root, "c2_uc_purchase", "2.4b Use Cases - Cart, Checkout and Orders")
    d = b.d
    order = ["UC06", "UC07", "UC09", "UC08", "UC11"]   # one column: include and extend run vertically
    w = col_width(order)
    rows = [TOP + i * PITCH for i in range(len(order))]
    for uid, cy in zip(order, rows):
        b.place(uid, A_LEFT, cy, w)
    right = b.draw()

    d.actor("Customer", "Customer", ACTOR_X, rows[2] - 34)
    d.actor("Payment Service", "Payment Service", right + SIDE, rows[1] - 40)
    b.primary("Customer", order)
    for uid, actor in supporting(set(b.pos)):
        b.helper(actor, uid)
    for frm, to, kind in links_between(set(b.pos)):
        b.vertical(frm, to, kind)


def assistant_admin(root):
    """2.4c: the shopping assistant (includes UC01 and UC09, uses Gemma 4) and the administrator's use cases."""
    b = Board(root, "c2_uc_assistant_admin", "2.4c Use Cases - Assistant and Administration")
    d = b.d
    above, below = "UC09", "UC01"                       # UC10 includes both: one above it, one below
    assert {(f, t) for f, t, k in model.USE_CASE_LINKS if k == "Include" and f == "UC10"} == {("UC10", above),
                                                                                               ("UC10", below)}
    admin = [uid for uid, _, actor, _ in model.USE_CASES if actor == "Administrator"]          # UC12 UC13
    order = [above, "UC10", below] + admin
    w = col_width(order)
    gap = 20                                            # a little air between the two actors' groups
    rows = [TOP + i * PITCH + (gap if i >= 3 else 0) for i in range(len(order))]
    for uid, cy in zip(order, rows):
        b.place(uid, A_LEFT, cy, w)
    right = b.draw()

    d.actor("Customer", "Customer", ACTOR_X, rows[1] - 34)
    d.actor("Administrator", "Administrator", ACTOR_X, (rows[3] + rows[4]) / 2 - 34)
    d.actor("Gemma 4 Service", "Gemma 4 Service", right + SIDE, rows[1] - 40)
    b.primary("Customer", ["UC10"])
    b.primary("Administrator", admin)
    for uid, actor in supporting(set(b.pos)):
        b.helper(actor, uid)
    for frm, to, kind in links_between(set(b.pos)):
        b.vertical(frm, to, kind)


def build(root):
    search(root)
    purchase(root)
    assistant_admin(root)
