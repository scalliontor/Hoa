"""Shared toolkit of the VP figure modules (ch1.py ... ch5.py).

* XML for the TieuLuanBuilder plugin (vp/plugin/TieuLuanBuilder.java). Every coordinate is explicit:
  VP's own layout and fitSize() do nothing useful when it runs headless.
* Text metrics of VP's default font (Java "SansSerif" 11 px, measured with VP's own runtime), used to
  size boxes and to place every connector label.
* A geometric self-check run before VP: no label may touch a shape, a line or another label, no line
  may run through a shape, shapes may not overlap. Exported PNGs are still inspected by eye.
"""
import xml.etree.ElementTree as ET

import model

PROJECT = "vp/tieuluan_design.vpp"
VIS = {"+": "public", "-": "private", "#": "protected", "~": "package"}
DIAGRAMS = []          # every Diagram built in this run, in build order

# --------------------------------------------------------------- metrics
# Advance widths (px) of Java SansSerif 11, plain and bold, measured with VP's JRE.
_PLAIN = {32: 3.48, 33: 3.48, 34: 4.11, 35: 6.96, 36: 6.96, 37: 7.35, 38: 7.67, 39: 2.52, 40: 3.58, 41: 3.58,
          42: 5.30, 43: 8.74, 44: 3.48, 45: 6.37, 46: 3.48, 47: 5.77, 48: 6.96, 49: 6.96, 50: 6.96, 51: 6.96,
          52: 6.96, 53: 6.96, 54: 6.96, 55: 6.96, 56: 6.96, 57: 6.96, 58: 3.48, 59: 3.48, 60: 8.74, 61: 8.74,
          62: 8.74, 63: 4.64, 64: 9.44, 65: 7.59, 66: 6.33, 67: 7.61, 68: 8.24, 69: 5.96, 70: 5.90, 71: 7.95,
          72: 8.08, 73: 3.17, 74: 3.42, 75: 7.18, 76: 5.87, 77: 9.47, 78: 8.13, 79: 8.54, 80: 6.08, 81: 8.54,
          82: 6.96, 83: 5.92, 84: 6.96, 85: 7.62, 86: 7.19, 87: 9.41, 88: 6.89, 89: 6.85, 90: 6.65, 91: 3.58,
          92: 5.77, 93: 3.58, 94: 6.96, 95: 5.50, 96: 6.76, 97: 6.08, 98: 6.92, 99: 5.63, 100: 6.92, 101: 6.13,
          102: 4.04, 103: 6.86, 104: 6.83, 105: 3.18, 106: 3.35, 107: 6.43, 108: 3.18, 109: 10.27, 110: 6.83,
          111: 6.76, 112: 6.92, 113: 6.92, 114: 4.50, 115: 5.61, 116: 4.11, 117: 6.83, 118: 5.69, 119: 8.48,
          120: 6.75, 121: 5.75, 122: 6.31, 123: 3.58, 124: 4.11, 125: 3.58, 126: 6.96, 171: 5.76, 183: 3.48,
          187: 5.76, 945: 7.63, 946: 6.63, 947: 6.16, 7885: 6.76, 8211: 5.50, 8212: 11.00, 8230: 11.00,
          8594: 11.00}
_BOLD_EXTRA = 1.07     # bold glyphs are about 7 % wider
LINE = 14              # line height of the default font


def text_w(text, bold=False):
    w = sum(_PLAIN.get(ord(c), 7.0) for c in text)
    return w * _BOLD_EXTRA if bold else w


def note_w(text):
    """Width of a note that VP does not wrap (text margin plus the folded corner)."""
    return int(max(text_w(t) for t in text.split("\n")) + 64)


def caption_size(lines):
    """Box VP needs to draw a connector caption without truncating it ('...')."""
    return int(max(text_w(t) for t in lines) + 26), LINE * len(lines) + 6


def wrap(text, width):
    """Greedy word wrap with the default font metrics."""
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if cur and text_w(trial) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


# -------------------------------------------------------------- geometry
class Rect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def r(self):
        return self.x + self.w

    @property
    def b(self):
        return self.y + self.h

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    def grow(self, m):
        return Rect(self.x - m, self.y - m, self.w + 2 * m, self.h + 2 * m)

    def hits(self, o):
        return self.x < o.r and o.x < self.r and self.y < o.b and o.y < self.b

    def inside(self, o):
        return o.x <= self.x and o.y <= self.y and self.r <= o.r and self.b <= o.b

    def edges(self):
        p = [(self.x, self.y), (self.r, self.y), (self.r, self.b), (self.x, self.b)]
        return [(p[i], p[(i + 1) % 4]) for i in range(4)]

    def __repr__(self):
        return f"({self.x:.0f},{self.y:.0f},{self.w:.0f},{self.h:.0f})"


def seg_hits(seg, rect):
    """Does the segment (axis-parallel or not) touch the rectangle? Liang-Barsky clipping."""
    (x1, y1), (x2, y2) = seg
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - rect.x), (dx, rect.r - x1), (-dy, y1 - rect.y), (dy, rect.b - y1)):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def segs_cross(a, b):
    """Proper crossing of two segments (shared end points do not count)."""
    (x1, y1), (x2, y2) = a
    (x3, y3), (x4, y4) = b

    def orient(ax, ay, bx, by, cx, cy):
        v = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        return (v > 1e-9) - (v < -1e-9)

    o1, o2 = orient(x1, y1, x2, y2, x3, y3), orient(x1, y1, x2, y2, x4, y4)
    o3, o4 = orient(x3, y3, x4, y4, x1, y1), orient(x3, y3, x4, y4, x2, y2)
    return o1 * o2 < 0 and o3 * o4 < 0


def segments(points):
    return list(zip(points, points[1:]))


# --------------------------------------------------------------- diagram
def _fmt(v):
    return "true" if v is True else str(int(round(v))) if isinstance(v, float) else str(v)


class Diagram:
    """One VP diagram: XML plus the geometry needed by check()."""

    def __init__(self, root, id_, name, kind, scope, scope_name, **extra):
        self.id = id_
        self.el = ET.SubElement(root, "diagram", id=id_, name=name, kind=kind, scope=scope, scopeName=scope_name)
        for k, v in extra.items():
            if v is not None:
                self.el.set(k, _fmt(v))
        self.boxes = {}      # node id -> (Rect, role) ; role: solid | frame | none
        self.paths = []      # (label, points, from id, to id)
        self.texts = []      # (label, Rect, owner): a text may sit on the shape that owns it
        self.guides = []     # segments that labels must avoid (lane borders, lifelines, frame edges)
        DIAGRAMS.append(self)

    # ---------------------------------------------------------- nodes
    def node(self, nid, type_, name, x, y, w, h, role="solid", **attrs):
        n = ET.SubElement(self.el, "node", id=nid, type=type_, name=name, x=_fmt(float(x)), y=_fmt(float(y)),
                          w=_fmt(float(w)), h=_fmt(float(h)))
        for k, v in attrs.items():
            if v is not None and v is not False:
                n.set(k, _fmt(v))
        self.boxes[nid] = (Rect(x, y, w, h), role)
        return n

    def rect(self, nid):
        return self.boxes[nid][0]

    def text(self, label, x, y, w, h, owner=None):
        """Register text that VP draws by itself (actor names, frame titles, guards) for check()."""
        self.texts.append((label, Rect(x, y, w, h), owner))

    def note(self, nid, text, x, y, w=None, anchor=None, anchor_pts=None):
        lines = text.split("\n")
        w = w or note_w(text)
        h = LINE * len(lines) + 24
        self.node(nid, "Note", text, x, y, w, h)
        if anchor:
            self.edge("Anchor", nid, anchor, anchor_pts)
        return self.rect(nid)

    def actor(self, nid, name, x, y):
        """UML actor 40 x 80; VP writes the name centred below the figure."""
        self.node(nid, "Actor", name, x, y, 40, 80)
        w = text_w(name) + 4
        self.text(name, x + 20 - w / 2, y + 80, w, LINE + 2, owner=nid)
        return self.rect(nid)

    # ---------------------------------------------------------- edges
    def edge(self, type_, frm, to, points=None, label=None, at=None, ends=None, **attrs):
        """label: caption lines as VP draws them; at: centre of the caption box.
        ends: {"fromMult"|"toMult"|"fromRoleBox"|"toRoleBox": (text, cx, cy)} end labels."""
        e = ET.SubElement(self.el, "edge", type=type_, **{"from": frm, "to": to})
        for k, v in attrs.items():
            if v is not None and v is not False:
                e.set(k, _fmt(v))
        for x, y in points or ():
            ET.SubElement(e, "pt", x=_fmt(float(x)), y=_fmt(float(y)))
        if attrs.get("caption") is False:
            e.set("caption", "false")
        if label:
            if at is None:
                raise ValueError(f"{self.id}: label {label} of {frm}->{to} needs a position")
            w, h = caption_size(label)
            box = Rect(at[0] - w / 2, at[1] - h / 2, w, h)
            for k, v in (("labelX", box.x), ("labelY", box.y), ("labelW", w), ("labelH", h)):
                e.set(k, _fmt(float(v)))
            self.texts.append(("/".join(label), box, None))
        for key, (txt, cx, cy) in (ends or {}).items():
            w, h = text_w(txt) + 10, LINE + 4
            box = Rect(cx - w / 2, cy - h / 2, w, h)
            for k, v in (("X", box.x), ("Y", box.y), ("W", w), ("H", h)):
                e.set(key + k, _fmt(float(v)))
            self.texts.append((f"{frm}->{to} {key} {txt}", box, None))
        if points:
            self.paths.append((f"{type_} {frm}->{to}", [tuple(p) for p in points], frm, to))
        return e

    def activation(self, on, y1, y2):
        ET.SubElement(self.el, "activation", on=on, y1=_fmt(y1), y2=_fmt(y2))

    # ---------------------------------------------------------- check
    def check(self, margin=4):
        out = []
        solids = [(k, r) for k, (r, role) in self.boxes.items() if role == "solid"]
        frames = [(k, r) for k, (r, role) in self.boxes.items() if role == "frame"]
        frame_edges = [(k, s) for k, r in frames for s in r.edges()]
        for i, (a, ra) in enumerate(solids):
            for b, rb in solids[i + 1:]:
                if ra.hits(rb):
                    out.append(f"shapes overlap: {a} {ra} / {b} {rb}")
            for f, rf in frames:
                if ra.hits(rf) and not ra.inside(rf) and not a.startswith("act "):
                    out.append(f"shape {a} crosses frame {f}")
        for i, (t, rt, owner) in enumerate(self.texts):
            g = rt.grow(margin)
            for k, r in solids:
                if k != owner and g.hits(r):
                    out.append(f"text '{t}' {rt} touches shape {k} {r}")
            for k, s in frame_edges:
                if k != owner and seg_hits(s, g):
                    out.append(f"text '{t}' {rt} touches the border of {k}")
            for name, pts, _, _ in self.paths:
                for s in segments(pts):
                    if seg_hits(s, g):
                        out.append(f"text '{t}' {rt} touches line {name}")
                        break
            for s in self.guides:
                if seg_hits(s, g):
                    out.append(f"text '{t}' {rt} touches guide line {s}")
                    break
            for u, ru, _ in self.texts[i + 1:]:
                if g.hits(ru):
                    out.append(f"texts overlap: '{t}' {rt} / '{u}' {ru}")
        for name, pts, f, to in self.paths:
            for s in segments(pts):
                for k, r in solids:
                    base = k.split()[1] if k.startswith("act ") else k.split("#")[0]
                    if base in (f, to):
                        continue
                    if seg_hits(s, r.grow(-1)):
                        out.append(f"line {name} runs through shape {k}")
        for i, (n1, p1, _, _) in enumerate(self.paths):
            for n2, p2, _, _ in self.paths[i + 1:]:
                if any(segs_cross(a, b) for a in segments(p1) for b in segments(p2)):
                    out.append(f"lines cross: {n1} / {n2}")
        return [f"{self.id}: {p}" for p in out]


def new_root():
    DIAGRAMS.clear()
    return ET.Element("diagrams", project=PROJECT)


# --------------------------------------------------------------- classes
def sig(o, params=True):
    if not params:
        return f'{o["vis"]}{o["name"]}()'
    return (f'{o["vis"]}{o["name"]}(' + ", ".join(f"{p} : {t}" for p, t in o["params"]) + ")"
            + (f' : {o["ret"]}' if o["ret"] else ""))


STEREO = {"interface": "Interface", "enum": "enumeration", "view": "view"}


def class_size(name, members=(), stereotype=None, compartments=2, hidden=False):
    """Size of a class box: members are the display strings, e.g. '-cartId : String'."""
    head = LINE * (2 if stereotype else 1)
    widths = [text_w(name, bold=True)] + [text_w(m) for m in members]
    if stereotype:
        widths.append(text_w(f"<<{stereotype}>>"))
    w = int(max(widths) + 24)
    if hidden:
        return max(w, 90), head + 12
    return max(w, 90), head + compartments * 5 + LINE * len(members) + 6


def design_members(name, attrs=True, ops=True, ctor=True):
    c = model.DESIGN_BY_NAME[name]
    shown_attrs = [f'{a["vis"]}{a["name"]} : {a["type"]}' for a in c["attrs"]] if attrs else []
    shown_ops = [sig(o) for o in c["ops"] if ctor or o["name"] != name] if ops else []
    return shown_attrs, shown_ops


def design_class(d, name, x, y, attrs=True, ops=True, ctor=False, hidden=False, nid=None, w=None):
    """Draw a class of model.DESIGN; constructors are hidden unless ctor=True."""
    c = model.DESIGN_BY_NAME[name]
    stereotype = STEREO.get(c["kind"])
    shown_attrs, shown_ops = design_members(name, attrs, ops, ctor)
    lines = [] if hidden else shown_attrs + shown_ops + list(c["literals"])
    cw, ch = class_size(name, lines, stereotype, compartments=1 if c["kind"] == "enum" else 2, hidden=hidden)
    w = w or cw
    hide_ops = [o["name"] for o in c["ops"] if (not ctor and o["name"] == name)]
    n = d.node(nid or name, "Class", name, x, y, w, ch, stereotype=stereotype, abstract=c["abstract"],
               hideMembers=hidden or None, hideOperations=(not ops and not hidden) or None,
               hideAttributes=(not attrs and not hidden) or None,
               hideOps=",".join(hide_ops) if hide_ops and ops and not hidden else None)
    for a in c["attrs"]:
        ET.SubElement(n, "attr", name=a["name"], type=a["type"], vis=VIS[a["vis"]])
    for lit in c["literals"]:
        ET.SubElement(n, "literal", name=lit)
    for o in c["ops"]:
        el = ET.SubElement(n, "op", name=o["name"], vis=VIS[o["vis"]],
                           params="; ".join(f"{p}: {t}" for p, t in o["params"]))
        if o["ret"]:
            el.set("ret", o["ret"])
        if o["static"]:
            el.set("static", "true")
        if o["abstract"] or c["kind"] == "interface":
            el.set("abstract", "true")
    return d.rect(nid or name)


def analysis_class(d, name, x, y, hidden=False, stereotype=None, nid=None):
    shown = ["-" + t.replace(":", " :") for t in model.ANALYSIS[name]]
    w, h = class_size(name, shown, stereotype, compartments=1 if not hidden else 2, hidden=hidden)
    n = d.node(nid or name, "Class", name, x, y, w, h, stereotype=stereotype,
               abstract=name in model.ANALYSIS_ABSTRACT, hideMembers=hidden or None, hideOperations=True)
    for text in model.ANALYSIS[name]:
        attr_name, attr_type = (s.strip() for s in text.split(":"))
        ET.SubElement(n, "attr", name=attr_name, type=attr_type)
    return d.rect(nid or name)


def analysis_size(name, hidden=False, stereotype=None):
    shown = ["-" + t.replace(":", " :") for t in model.ANALYSIS[name]]
    return class_size(name, shown, stereotype, compartments=1, hidden=hidden)


# ----------------------------------------------------- association labels
def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))


def end_label(p, q, text, side, along=0):
    """Centre of an end label at p for the segment p->q: 10 px (+ along) along the line, beside it on
    `side` (+1 = below / right, -1 = above / left)."""
    w, h = text_w(text) + 10, LINE + 4
    ux, uy = _unit(p, q)
    if uy == 0:          # horizontal segment
        return p[0] + ux * (10 + along + w / 2), p[1] + side * (h / 2 + 7)
    return p[0] + side * (w / 2 + 8), p[1] + uy * (10 + along + h / 2)


def assoc(d, a, b, pts, name=None, a_mult=None, b_mult=None, mult_side=1, name_side=-1, name_seg=None,
          a_side=None, b_side=None, extra_ends=None, **attrs):
    """Association a -> b along pts with its name beside the longest (or given) segment and the
    multiplicities beside both ends."""
    ends = dict(extra_ends or {})
    if a_mult:
        ends["fromMult"] = (a_mult, *end_label(pts[0], pts[1], a_mult, a_side or mult_side))
    if b_mult:
        ends["toMult"] = (b_mult, *end_label(pts[-1], pts[-2], b_mult, b_side or mult_side))
    at = None
    if name:
        segs = segments(pts)
        i = name_seg if name_seg is not None else max(range(len(segs)), key=lambda k: abs(segs[k][1][0] - segs[k][0][0]) + abs(segs[k][1][1] - segs[k][0][1]))
        (x1, y1), (x2, y2) = segs[i]
        w, h = caption_size([name])
        if y1 == y2:
            at = ((x1 + x2) / 2, y1 + name_side * (h / 2 + 7))
        else:
            at = (x1 + name_side * (w / 2 + 8), (y1 + y2) / 2)
    return d.edge("Association", a, b, pts, label=[name] if name else None, at=at, ends=ends, name=name,
                  fromMult=a_mult, toMult=b_mult, **attrs)


# -------------------------------------------------------------- activity
DIAMOND = 36, 44            # bounds of decision/merge nodes; VP draws the diamond 3 px / 7 px inside


class Act:
    """Activity node geometry: top/bottom/left/right attachment points of the drawn shape."""

    def __init__(self, x, y, w, h, kind):
        self.x, self.y, self.w, self.h, self.kind = x, y, w, h, kind
        self.cx, self.cy = x + w / 2, y + h / 2
        ix, iy = (3, 7) if kind in ("Decision", "Merge") else (0, 0)
        self.top, self.bottom = (self.cx, y + iy), (self.cx, y + h - iy)
        self.left, self.right = (x + ix, self.cy), (x + w - ix, self.cy)


def act_node(d, nid, kind, cx, cy, text="", lane=None, width=170):
    if kind == "Action":
        one = text_w(text) + 30
        if one <= width:
            w, lines = max(one, 100), 1
        else:
            w, lines = width, len(wrap(text, width - 30))
        h = LINE * lines + 24
    elif kind in ("Decision", "Merge"):
        w, h = DIAMOND
    elif kind in ("Fork", "Join"):
        w, h = 160, 6
    else:
        w, h = 22, 22
    d.node(nid, kind, text, cx - w / 2, cy - h / 2, w, h, lane=lane)
    return Act(cx - w / 2, cy - h / 2, w, h, kind)


def flow(d, frm, to, pts, guard=None, at=None, side=None):
    """Control flow; the guard sits beside segment 0 unless `at` is given (side: 'above', 'below',
    'left', 'right' of the first segment)."""
    label = [f"[{guard}]"] if guard else None
    if guard and at is None:
        w, h = caption_size(label)
        (x1, y1), (x2, y2) = pts[0], pts[1]
        if y1 == y2:
            x = (x1 + x2) / 2
            at = (x, y1 - h / 2 - 7) if side != "below" else (x, y1 + h / 2 + 7)
        else:
            y = (y1 + y2) / 2
            at = (x1 + w / 2 + 8, y) if side != "left" else (x1 - w / 2 - 8, y)
    return d.edge("ControlFlow", frm, to, pts, label=label, at=at, guard=guard)


def swimlanes(d, lanes, x0, y0, height, header=34):
    """Vertical lanes [(name, width)]; returns the lane centre x list and registers the lane borders."""
    n = d.node("lanes", "Swimlane", "", x0, y0, sum(w for _, w in lanes), height, role="frame", header=header)
    import xml.etree.ElementTree as _ET
    centres, x = [], x0
    for name, w in lanes:
        _ET.SubElement(n, "lane", name=name, w=str(w))
        centres.append(x + w / 2)
        tw = text_w(name) + 8
        d.text(name, x + w / 2 - tw / 2, y0 + header / 2 - 9, tw, 18, owner="lanes")
        x += w
        if x < x0 + sum(w for _, w in lanes):
            d.guides.append(((x, y0), (x, y0 + height)))
    d.guides.append(((x0, y0 + header), (x, y0 + header)))
    return centres


# -------------------------------------------------------------- sequence
class Seq:
    """Automatic sequence layout.

    parts: [(id, label)] where the first is the actor; others are lifelines typed by the class `id`.
    msgs: [(from, to, text, kind)] kind call | return | self | create.
    frags: [(operator, first_msg_index, last_msg_index, [(guard, first_msg_index), ...], covers)]
    """
    STEP, TOP = 40, 130

    def __init__(self, d, parts, msgs, frags=(), numbers=True, gap=40):
        self.d, self.parts, self.msgs, self.frags = d, parts, msgs, frags
        self.numbers = numbers
        ids = [p for p, _ in parts]
        self.idx = {p: i for i, p in enumerate(ids)}
        # 1. vertical positions: fragment guards need room above their first message
        guard_at = {}
        for op, first, last, operands, covers in frags:
            for k, (guard, start) in enumerate(operands):
                guard_at.setdefault(start, []).append((op if k == 0 else None, guard))
        y, self.ys = self.TOP, []
        for i, m in enumerate(msgs):
            if i in guard_at:
                y += 64 if any(o for o, _ in guard_at[i]) else 62
            self.ys.append(y)
            y += self.STEP + (18 if m[3] == "self" else 0)
            if any(last == i for _, _, last, _, _ in frags):
                y += 26
        self.bottom = y + 30
        # 2. horizontal positions from the label widths
        heads = [max(text_w(f": {lbl}", bold=False) + 34, 100) for _, lbl in parts]
        heads[0] = 70
        n = len(parts)
        need = [max(heads[i] / 2 + heads[i + 1] / 2 + gap, 0) for i in range(n - 1)]
        self.texts = [self.caption(i) for i in range(len(msgs))]
        for i, (f, t, text, kind) in enumerate(msgs):
            w = caption_size([self.texts[i]])[0]
            a, b = self.idx[f], self.idx[t]
            if kind == "self":
                if a < n - 1:
                    need[a] = max(need[a], 44 + w + 16)
                continue
            lo, hi = min(a, b), max(a, b)
            if not any(need[k] >= w + 30 for k in range(lo, hi)):
                k = a if a < b else a - 1           # the gap next to the sender
                need[k] = max(need[k], w + 30)
        for op, first, last, operands, covers in frags:
            lo = min(self.idx[c] for c in covers)
            gw = max(text_w(f"[{g}]") for g, _ in operands) + 50
            if lo > 0:
                need[lo - 1] = max(need[lo - 1], gw + 30)
        self.cx = [60]
        for k in range(n - 1):
            self.cx.append(self.cx[-1] + need[k])
        self.cx = [c + 40 for c in self.cx]
        self.heads = heads

    def caption(self, i):
        f, t, text, kind = self.msgs[i]
        return f"{i + 1}: {text}" if self.numbers else text

    def draw(self):
        d = self.d
        ids = [p for p, _ in self.parts]
        for i, (pid, lbl) in enumerate(self.parts):
            cx = self.cx[i]
            if i == 0:
                d.node(pid, "SeqActor", lbl, cx - 20, 40, 40, self.bottom - 40, role="none")
                w = text_w(lbl) + 20
                d.text(lbl, cx - w / 2, 75, w, LINE + 2)
                d.boxes[pid + "#bar"] = (Rect(cx - 5, 100, 10, self.bottom - 100), "solid")
            else:
                w = self.heads[i]
                d.node(pid, "Lifeline", "", cx - w / 2, 40, w, self.bottom - 40, role="none", classifier=pid)
                d.boxes[pid + "#head"] = (Rect(cx - w / 2, 40, w, 34), "solid")
                d.guides.append(((cx, 74), (cx, self.bottom)))
        # activations: call ... matching return
        stack, spans = [], []
        for i, (f, t, text, kind) in enumerate(self.msgs):
            y = self.ys[i]
            if kind in ("call", "create"):
                stack.append((t, y))
            elif kind == "send":
                spans.append((t, y, y + 18))
            elif kind == "return":
                for k in range(len(stack) - 1, -1, -1):
                    if stack[k][0] == f:
                        spans.append((f, stack[k][1], y))
                        del stack[k]
                        break
        for t, y in stack:                      # no return drawn: active until its last message
            last = max([self.ys[i] for i, m in enumerate(self.msgs) if self.ys[i] >= y and t in (m[0], m[1])]
                       + [y + 10])
            spans.append((t, y, last + (28 if any(m[3] == "self" and m[0] == t for m in self.msgs) else 10)))
        for who, y1, y2 in spans:
            if who == ids[0]:
                continue
            d.activation(who, y1, y2)
            cx = self.cx[self.idx[who]]
            d.boxes[f"act {who} {y1}"] = (Rect(cx - 4, y1, 8, y2 - y1), "solid")
        # fragments
        for op, first, last, operands, covers in self.frags:
            lo = min(self.idx[c] for c in covers)
            hi = max(self.idx[c] for c in covers)
            gw = max(text_w(f"[{g}]") for g, _ in operands) + 50
            x = self.cx[lo] - gw
            right = self.cx[hi] + 30
            for i in range(first, last + 1):
                f, t, text, kind = self.msgs[i]
                if kind == "self":
                    right = max(right, self.cx[self.idx[f]] + 44 + caption_size([self.texts[i]])[0] + 12)
            y_top = self.ys[operands[0][1]] - 74
            y_bot = self.ys[last] + 26 + (18 if self.msgs[last][3] == "self" else 0)
            fid = f"frag{first}"
            n = d.node(fid, "Fragment", "", x, y_top, right - x, y_bot - y_top, role="frame", operator=op,
                       covers=",".join(covers))
            d.text(op, x, y_top, 40, 17, owner=fid)
            import xml.etree.ElementTree as _ET
            for k, (guard, start) in enumerate(operands):
                oy = y_top + 17 if k == 0 else self.ys[start] - 58
                oh = (self.ys[operands[k + 1][1]] - 58 if k + 1 < len(operands) else y_bot) - oy
                _ET.SubElement(n, "operand", guard=guard, y=str(int(oy)), h=str(int(oh)))
                gw2 = text_w(f"[{guard}]") + 8
                d.text(f"[{guard}]", x + 18, oy + 7, gw2, 16, owner=fid)
                if k > 0:
                    d.guides.append(((x, oy), (right, oy)))
        # messages
        for i, (f, t, text, kind) in enumerate(self.msgs):
            y = self.ys[i]
            a, b = self.cx[self.idx[f]], self.cx[self.idx[t]]
            label = [self.texts[i]]
            w, h = caption_size(label)
            if kind == "self":
                pts = [(a, y), (a + 34, y), (a + 34, y + 18), (a, y + 18)]
                at = (a + 44 + w / 2, y + 9)
                d.edge("Message", f, t, pts, label=label, at=at, name=text).set("self", "true")
                continue
            lo, hi = min(self.idx[f], self.idx[t]), max(self.idx[f], self.idx[t])
            gaps = [(self.cx[k + 1] - self.cx[k], k) for k in range(lo, hi)]
            fits = [k for g, k in gaps if g >= w + 30]
            k = (fits[0] if self.idx[f] < self.idx[t] else fits[-1]) if fits else max(gaps)[1]
            mid = (self.cx[k] + self.cx[k + 1]) / 2
            at = (mid, y - h / 2 - 7)
            d.edge("Message", f, t, [(a, y), (b, y)], label=label, at=at, name=text,
                   **{"return": kind == "return", "create": kind == "create"})
