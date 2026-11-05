"""One grid for the six class models of the essay, so they read as the same model:
domain (2.x, names only), analysis (4.1), the data model at three levels -- conceptual (4.2a: names and
named links only), logical (4.2b: attributes, «ORM-Persistable», multiplicities) and physical (4.2c: «table»
classes with types and keys) -- and design (4.3). Every relation has a hand-made orthogonal route relative to the boxes."""
import xml.etree.ElementTree as ET

from .common import (LINE, Diagram, Rect, STEREO, analysis_size, assoc, caption_size, class_size,
                     design_class, design_members, end_label, text_w)
import model

# logical name -> (column, row); PayCash / PayCredit sit on row 5 left and right of column 3.
CELLS = {"CustomerVIP": (0, 0), "CustomerNew": (0, 2), "FullName": (1, 0), "Customer": (1, 1), "Cart": (2, 1),
         "CartItem": (3, 1), "Product": (3, 2), "Order": (2, 3), "OrderItem": (3, 3), "Painting": (4, 1),
         "Frame": (4, 3), "Artist": (5, 1), "Address": (0, 4), "Shipping": (1, 4), "Payment": (3, 4),
         "Feature": (4, 2), "OrderStatus": (2, 2), "ShippingStatus": (1, 5), "PaymentStatus": (4, 4)}
TABLE = {"Customer": "customer", "CustomerVIP": "customer_vip", "CustomerNew": "customer_new",
         "Address": "address", "Product": "product", "Artist": "artist", "Painting": "painting", "Frame": "frame",
         "Feature": "product_feature", "Cart": "cart", "CartItem": "cart_item", "Order": "orders",
         "OrderItem": "order_item", "Shipping": "shipping", "Payment": "payment", "PayCash": "pay_cash",
         "PayCredit": "pay_credit"}
LOGICAL = {t: k for k, t in TABLE.items()}
GENS = [("CustomerVIP", "Customer"), ("CustomerNew", "Customer"), ("Painting", "Product"), ("Frame", "Product"),
        ("PayCash", "Payment"), ("PayCredit", "Payment")]


def sql_type(c):
    if c["length"] is None:
        return c["type"]
    return f'{c["type"]}({c["length"]}' + (f',{c["scale"]}' if c["scale"] is not None else "") + ")"


def keys(c):
    k = [n for n, on in (("PK", c["pk"]), ("FK", c["fk"]), ("U", c["unique"]), ("NULL", c["nullable"])) if on]
    return " {" + ", ".join(k) + "}" if k else ""


def _table_lines(t):
    return [f'+{c["name"]} : {sql_type(c)}{keys(c)}' for c in t["columns"]]


TABLES = {t["name"]: t for t in model.TABLES}


def _members(mode):
    if mode == "tables":
        return list(TABLE)
    names = list(model.ANALYSIS)
    if mode == "design":
        names += ["OrderStatus", "ShippingStatus", "PaymentStatus"]
    return names


def _size(mode, name):
    if mode in ("domain", "conceptual"):
        return analysis_size(name, hidden=True)
    if mode == "analysis":
        return analysis_size(name)
    if mode == "orm":
        return analysis_size(name, stereotype="ORM-Persistable")
    if mode == "tables":
        t = TABLES[TABLE[name]]
        return class_size(t["name"], _table_lines(t), "table", compartments=1)
    attrs, ops = design_members(name, ctor=False)
    c = model.DESIGN_BY_NAME[name]
    return class_size(name, attrs + ops + list(c["literals"]), STEREO.get(c["kind"]))


def _draw(d, mode, name, x, y):
    if mode in ("domain", "conceptual", "analysis", "orm"):
        from .common import analysis_class
        return analysis_class(d, name, x, y, hidden=mode in ("domain", "conceptual"),
                              stereotype="ORM-Persistable" if mode == "orm" else None)
    if mode == "tables":
        t = TABLES[TABLE[name]]
        w, h = _size(mode, name)
        n = d.node(name, "Class", t["name"], x, y, w, h, stereotype="table", hideOperations=True)
        for c in t["columns"]:
            ET.SubElement(n, "attr", name=c["name"], type=sql_type(c) + keys(c), vis="public")
        return d.rect(name)
    return design_class(d, name, x, y, ctor=False)


def layout(d, mode, col_gap, row_gap, x0=40, y0=40):
    names = _members(mode)
    size = {n: _size(mode, n) for n in names}
    cols, rows = {}, {}
    for n in names:
        if n in ("PayCash", "PayCredit"):
            continue
        c, r = CELLS[n]
        cols[c] = max(cols.get(c, 0), size[n][0])
        rows[r] = max(rows.get(r, 0), size[n][1])
    rows[5] = max([rows.get(5, 0)] + [size[n][1] for n in ("PayCash", "PayCredit")])
    X, x = {}, x0
    for c in sorted(cols):
        X[c] = x + cols[c] / 2
        x += cols[c] + col_gap
    Y, y = {}, y0
    for r in sorted(rows):
        Y[r] = y + rows[r] / 2
        y += rows[r] + row_gap
    B = {}
    for n in names:
        w, h = size[n]
        if n in ("PayCash", "PayCredit"):
            dx = max(size["PayCash"][0], size["PayCredit"][0]) / 2 + col_gap / 2
            cx = X[3] + (-dx if n == "PayCash" else dx)
            B[n] = _draw(d, mode, n, cx - w / 2, Y[5] - h / 2)
        else:
            c, r = CELLS[n]
            B[n] = _draw(d, mode, n, X[c] - w / 2, Y[r] - h / 2)
    return B, X, Y


def routes(B, Y):
    """Orthogonal route of every association pair (points from the first to the second class)."""
    c, cart, ci, p, o, oi = B["Customer"], B["Cart"], B["CartItem"], B["Product"], B["Order"], B["OrderItem"]
    ad, sh, pay, ar, pt = B["Address"], B["Shipping"], B["Payment"], B["Artist"], B["Painting"]
    yr = (o.b + sh.y) / 2 if "Order" in B else 0
    R = {
        ("Customer", "Cart"): [(c.r, c.cy), (cart.x, c.cy)],
        ("Cart", "CartItem"): [(cart.r, cart.cy), (ci.x, cart.cy)],
        ("Customer", "Order"): [(c.cx + 24, c.b), (c.cx + 24, o.cy), (o.x, o.cy)],
        ("Customer", "Address"): [(c.cx - 24, c.b), (c.cx - 24, yr), (ad.cx, yr), (ad.cx, ad.y)],
        ("CartItem", "Product"): [(ci.cx, ci.b), (ci.cx, p.y)],
        ("OrderItem", "Product"): [(oi.cx, oi.y), (oi.cx, p.b)],
        ("Order", "OrderItem"): [(o.r, o.cy), (oi.x, o.cy)],
        ("Order", "Shipping"): [(o.cx - 24, o.b), (o.cx - 24, sh.cy), (sh.r, sh.cy)],
        ("Order", "Payment"): [(o.cx + 24, o.b), (o.cx + 24, pay.cy), (pay.x, pay.cy)],
        ("Shipping", "Address"): [(sh.x, sh.cy), (ad.r, sh.cy)],
        ("Artist", "Painting"): [(ar.x, ar.cy), (pt.r, ar.cy)],
    }
    if "FullName" in B:
        R[("Customer", "FullName")] = [(c.cx, c.y), (c.cx, B["FullName"].b)]
    if "Feature" in B:
        R[("Product", "Feature")] = [(p.r, p.cy), (B["Feature"].x, p.cy)]
    return R


# Label sides per pair: (mult side, name side, name segment); +1 = below / right, -1 = above / left.
SIDES = {("Customer", "FullName"): (1, -1, None), ("Customer", "Cart"): (1, -1, None),
         ("Cart", "CartItem"): (1, -1, None), ("Customer", "Order"): (1, -1, 1),
         ("Customer", "Address"): (-1, -1, 1), ("CartItem", "Product"): (1, -1, None),
         ("OrderItem", "Product"): (1, -1, None), ("Order", "OrderItem"): (1, -1, None),
         ("Order", "Shipping"): (-1, -1, 1), ("Order", "Payment"): (1, -1, 1),
         ("Shipping", "Address"): (1, -1, None), ("Artist", "Painting"): (1, -1, None),
         ("Product", "Feature"): (1, -1, None)}
END_SIDES = {("Customer", "Address"): (-1, 1), ("Order", "Shipping"): (-1, 1), ("Order", "Payment"): (1, 1),
             ("Customer", "Order"): (1, 1)}


def _assoc(d, a, b, pts, name, a_mult, b_mult, key, ids, **kw):
    ms, ns, seg = SIDES[key]
    a_side, b_side = END_SIDES.get(key, (ms, ms))
    if key != (a, b):           # drawn in the other direction: swap the end sides
        a_side, b_side = b_side, a_side
    assoc(d, ids[a], ids[b], pts, name=name, a_mult=a_mult, b_mult=b_mult, mult_side=ms, name_side=ns,
          name_seg=None if seg is None else (seg if key == (a, b) else len(pts) - 2 - seg),
          a_side=a_side, b_side=b_side, **kw)


def gen_tree(d, B, ids, as_assoc=None):
    """Generalizations as trees; with as_assoc=(name_of, mults_of) they become 'is a' associations with
    their own routes (data model and tables)."""
    c, p, pay = B["Customer"], B["Product"], B["Payment"]
    vip, new, pt, fr = B["CustomerVIP"], B["CustomerNew"], B["Painting"], B["Frame"]
    cash, credit = B["PayCash"], B["PayCredit"]
    xc = (vip.r + c.x) / 2
    xp = (p.r + pt.x) / 2
    ym = (pay.b + cash.y) / 2
    if not as_assoc:
        for child in ("CustomerVIP", "CustomerNew"):
            r = B[child]
            d.edge("Generalization", ids[child], ids["Customer"], [(r.r, r.cy), (xc, r.cy), (xc, c.cy), (c.x, c.cy)])
        for child in ("Painting", "Frame"):
            r = B[child]
            d.edge("Generalization", ids[child], ids["Product"], [(r.x, r.cy), (xp, r.cy), (xp, p.cy), (p.r, p.cy)])
        for child in ("PayCash", "PayCredit"):
            r = B[child]
            d.edge("Generalization", ids[child], ids["Payment"],
                   [(r.cx, r.y), (r.cx, ym), (pay.cx, ym), (pay.cx, pay.b)])
        return
    label_of = as_assoc
    # parent -> child, each with its own entry point on the parent
    pairs = {
        "CustomerVIP": ("Customer", [(c.x, c.y + 18), (xc - 12, c.y + 18), (xc - 12, vip.cy), (vip.r, vip.cy)], -1),
        "CustomerNew": ("Customer", [(c.x, c.b - 18), (xc + 12, c.b - 18), (xc + 12, new.cy), (new.r, new.cy)], 1),
        "Painting": ("Product", [(p.r, p.y + 18), (xp, p.y + 18), (xp, pt.cy), (pt.x, pt.cy)], 1),
        "Frame": ("Product", [(p.r, p.b - 18), (xp, p.b - 18), (xp, fr.cy), (fr.x, fr.cy)], 1),
        "PayCash": ("Payment", [(pay.cx - 16, pay.b), (pay.cx - 16, ym), (cash.cx, ym), (cash.cx, cash.y)], -1),
        "PayCredit": ("Payment", [(pay.cx + 16, pay.b), (pay.cx + 16, ym), (credit.cx, ym), (credit.cx, credit.y)], 1),
    }
    for child, (parent, pts, side) in pairs.items():
        name, pm, cm = label_of(parent, child)
        if child.startswith("Pay"):
            assoc(d, ids[parent], ids[child], pts, name=name, a_mult=pm, b_mult=cm, name_seg=1, name_side=-1,
                  a_side=side, b_side=side)
        elif child.startswith("Customer"):
            assoc(d, ids[parent], ids[child], pts, name=name, a_mult=pm, b_mult=cm, name_seg=1, name_side=-1,
                  a_side=-side, b_side=side)
        else:
            assoc(d, ids[parent], ids[child], pts, name=name, a_mult=pm, b_mult=cm, name_seg=1, name_side=1,
                  a_side=1 if child == "Frame" else -1, b_side=1)


def class_model(root, id_, title, mode, scope, scope_name, col_gap=170, row_gap=100):
    d = Diagram(root, id_, title, "class", scope, scope_name)
    B, X, Y = layout(d, mode, col_gap, row_gap)
    ids = {k: k for k in B}
    R = routes(B, Y)
    agg = {"composition": "composite", "aggregation": "shared"}
    if mode in ("domain", "conceptual", "analysis", "orm"):
        # analysis: attributes and the kind of each relationship only (no names, no multiplicities, no ORM);
        # conceptual data model: names and named links; logical (orm): names, multiplicities, «ORM-Persistable».
        named = mode in ("conceptual", "orm")
        counted = mode == "orm"
        for a in model.ANALYSIS_ASSOCIATIONS:
            key = (a["a"], a["b"])
            _assoc(d, a["a"], a["b"], R[key], a["name"] if named else None, a["a_mult"] if counted else None,
                   a["b_mult"] if counted else None, key, ids,
                   aggregation=None if mode == "conceptual" else agg.get(a["kind"]))
        if mode == "orm":
            gen_tree(d, B, ids, as_assoc=lambda parent, child: ("is a", "1", "0..1"))
        else:
            gen_tree(d, B, ids)
        if mode not in ("orm", "conceptual"):
            for client, supplier, stereotype, name in model.ANALYSIS_DEPENDENCIES:
                cart = B[client]
                lines = [f"<<{stereotype}>>"]
                w, h = caption_size(lines)
                d.edge("Dependency", client, supplier, [(cart.cx, cart.b), (cart.cx, B[supplier].y)], label=lines,
                       at=(cart.cx + 8 + w / 2, (cart.b + B[supplier].y) / 2), stereotype=stereotype)
    elif mode == "tables":
        gen_children = {"customer_vip", "customer_new", "painting", "frame", "pay_cash", "pay_credit"}
        labels = {}
        for child, column, parent, _ in model.foreign_keys():
            name, pm, cm = model.FK_LABELS[f"{child}.{column}"]
            label = f"{name} ({column})"
            if child in gen_children and not (child == "painting" and column == "artist_id"):
                labels[(LOGICAL[parent], LOGICAL[child])] = (label, pm, cm)
                continue
            a, b = LOGICAL[parent], LOGICAL[child]
            key = (a, b) if (a, b) in R else (b, a)
            pts = R[key] if key == (a, b) else list(reversed(R[key]))
            _assoc(d, a, b, pts, label, pm, cm, key, ids)
        gen_tree(d, B, ids, as_assoc=lambda parent, child: labels[(parent, child)])
    else:   # design
        for a in model.DESIGN_ASSOCIATIONS:
            src, dst = a["src"], a["dst"]
            key = (src, dst) if (src, dst) in R else (dst, src)
            pts = R[key] if key == (src, dst) else list(reversed(R[key]))
            ms, ns, seg = SIDES[key]
            a_side, b_side = END_SIDES.get(key, (ms, ms))
            if key != (src, dst):
                a_side, b_side = b_side, a_side
            role = a["role"]
            (px, py), (qx, qy) = pts[-1], pts[-2]
            mult_len = text_w(a["mult"]) + 10 if py == qy else LINE + 4
            ends_extra = {"toRoleBox": (role, *end_label(pts[-1], pts[-2], role, b_side, along=mult_len + 8))}
            assoc(d, src, dst, pts, name=a["name"], a_mult=a["src_mult"], b_mult=a["mult"], mult_side=ms,
                  name_side=ns, name_seg=None if seg is None else (seg if key == (src, dst) else len(pts) - 2 - seg),
                  a_side=a_side, b_side=b_side, navigable=True, fromNav="non", toRole=role, extra_ends=ends_extra,
                  aggregation=agg.get(a["kind"]))
        gen_tree(d, B, ids)
        for client, supplier, stereotype in model.DESIGN_DEPENDENCIES_43:
            # OrderItem -> CartItem through the empty band between the rows, left of Product
            oi, ci = B[client], B[supplier]
            col2r = max(B[n].r for n in ("Cart", "Order", "OrderStatus"))
            col3l = min(B[n].x for n in ("CartItem", "Product", "OrderItem", "Payment"))
            xch = (col2r + col3l) / 2
            pts = [(oi.x + 16, oi.y), (oi.x + 16, oi.y - 24), (xch, oi.y - 24), (xch, ci.b + 24),
                   (ci.x + 16, ci.b + 24), (ci.x + 16, ci.b)]
            lines = [f"<<{stereotype}>>"]
            w, h = caption_size(lines)
            d.edge("Dependency", client, supplier, pts, label=lines, at=(xch + 8 + w / 2, (oi.y + ci.b) / 2),
                   stereotype=stereotype)
    return d, B


ERD_HEADER, ERD_ROW = 24, 18       # VP CE entity: one header line, then one row per column


def erd(root):
    """The database as a VP entity relationship diagram (the 'yellow tables'), drawn on the grid of the
    physical data model c42_tables: same tables, same places, same foreign keys and names. The caption box is
    set to one line, otherwise VP keeps a tall default header and clips the columns."""
    d = Diagram(root, "c42_erd", "4.2 Database - entity relationship diagram", "erd", "database",
                "4.2 Database")
    d2 = Diagram(ET.Element("x"), "tmp", "tmp", "class", "tmp", "tmp")
    from . import common
    common.DIAGRAMS.remove(d2)
    B, X, Y = layout(d2, "tables", 200, 110)          # the col_gap / row_gap of c42_tables
    for logical, r in B.items():
        t = TABLES[TABLE[logical]]
        w = r.w + 40
        h = ERD_HEADER + ERD_ROW * len(t["columns"]) + 6
        n = d.node(t["name"], "DBTable", t["name"], r.x, r.y, w, h, role="none",
                   captionX=0, captionY=0, captionW=w, captionH=ERD_HEADER - 2)
        for c in t["columns"]:
            el = ET.SubElement(n, "column", name=c["name"], type=c["type"])
            for key in ("length", "scale"):
                if c[key] is not None:
                    el.set(key, str(c[key]))
            for key in ("pk", "nullable", "unique"):
                if c[key]:
                    el.set(key, "true")
            if c["fk"]:
                el.set("fk", c["fk"])
    for child, column, parent, _ in model.foreign_keys():
        name, parent_mult, child_mult = model.FK_LABELS[f"{child}.{column}"]
        pk = next(c["pk"] for c in TABLES[child]["columns"] if c["name"] == column)
        d.edge("DBForeignKey", parent, child, None, name=name, fromMult=parent_mult, toMult=child_mult,
               toColumn=column, identifying=pk or None)
    return d
