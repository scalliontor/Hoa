"""New diagrams (2026-11-11 catalogue): x_design.

* c44_packages    the design packages (three layers and the shared domain model) and their «use» links;
* c44_seq_search  design sequence of UC02 (search by keyword) through the layers;
* c44_seq_cancel  design sequence of UC11 (cancel an order) through the layers.

Every package comes from model.PACKAGE_GROUPS, every link from model.LAYER_DEPENDENCIES and from the class
dependencies of model.DESIGN / DESIGN_DEPENDENCIES_44 (asserted below). Every call between objects is an
operation of model.DESIGN (asserted by call()), in the order of demo/src/main/java/com/ptit/ecom; return
messages carry the returned type, the exception or the HTTP status that WebServer sends.
"""
import re

from .common import Diagram, Rect, Seq, caption_size, note_w, text_w
import model

SCOPE, SCOPE_NAME = "design", "4.3-4.5 Design model"


# ------------------------------------------------------------------ model checks
def _package_of():
    return {c["name"]: c["package"] for c in model.DESIGN}


def _layer_of(package):
    for title, _, packages in model.PACKAGE_GROUPS:
        if package in packages:
            return title
    raise KeyError(package)


def _package_links():
    """Package -> package links implied by the class dependencies and the implemented interfaces."""
    pkg = _package_of()
    links = set()
    for client, supplier, _ in model.DESIGN_DEPENDENCIES_44:
        links.add((pkg[client], pkg[supplier]))
    for c in model.DESIGN:
        for iface in c["implements"]:
            links.add((pkg[c["name"]], pkg[iface]))
    return {(a, b) for a, b in links if a != b}


def _uses_domain(layer):
    """Does a class of the layer name a domain class in an attribute, a parameter or a return type?"""
    pkg = _package_of()
    domain = {n for n, p in pkg.items() if _layer_of(p) == model.DOMAIN_MODEL[0]}
    for c in model.DESIGN:
        if _layer_of(c["package"]) != layer:
            continue
        types = [a["type"] for a in c["attrs"]]
        for o in c["ops"]:
            types += [t for _, t in o["params"]] + [o["ret"] or ""]
        if any(w in domain for t in types for w in re.findall(r"\w+", t)):
            return True
    return False


def _op(cls, name):
    ops = [o for o in model.DESIGN_BY_NAME[cls]["ops"] if o["name"] == name]
    assert ops, f"{cls}.{name} is not an operation of model.DESIGN"
    return ops[0]


def call(cls, name, *args):
    """Message text 'name(args)' for an operation of model.DESIGN; the arguments default to its parameters."""
    o = _op(cls, name)
    assert not args or len(args) == len(o["params"]), (cls, name, args)
    return f"{name}({', '.join(args or [p for p, _ in o['params']])})"


# ------------------------------------------------------------------ 4.4c packages
SUB_H = 60          # sub-package: 20 px tab + 40 px body
LINK_GAP = 110      # horizontal gap that holds a «use» caption
GAP = 40            # gap between packages without a link
PAD = 30            # inner margin of a layer frame
HEAD = 56           # frame top -> first row of sub-packages (frame title in between)
ROW_GAP = 50        # vertical gap that holds a «use» caption
USE = ["<<use>>"]


def _sub_w(name):
    return max(150, int(text_w(name) + 50))


def packages(root):
    """The four package groups of model.PACKAGE_GROUPS as transparent frames (the convention of c44_layers),
    each with its Java sub-packages; «use» between the layers (model.LAYER_DEPENDENCIES), from every layer to
    the domain model, and inside a layer between the sub-packages that depend on each other."""
    d = Diagram(root, "c44_packages", "4.4c Package Diagram - Design Packages", "raw", SCOPE, SCOPE_NAME,
                vptype="PackageDiagram")
    groups = {title: packages_ for title, _, packages_ in model.PACKAGE_GROUPS}
    domain_title = model.DOMAIN_MODEL[0]
    links = _package_links()
    W = {p: _sub_w(p) for ps in groups.values() for p in ps}
    B = {}

    # rows of sub-packages per layer: (packages, gaps between them)
    rows = {
        "Presentation": [(["presentation.view", "presentation.controller", "presentation.web"], [LINK_GAP, LINK_GAP])],
        "Application": [(["application.service", "application.search"], [LINK_GAP])],
        "Data": [(["infrastructure.repository", "infrastructure.search", "infrastructure.ai"], [GAP, GAP]),
                 (["infrastructure.repository.sqlite"], [])],
    }
    assert set(rows) | {domain_title} == set(groups)
    for title, rs in rows.items():
        assert sorted(p for ps, _ in rs for p in ps) == sorted(groups[title]), title

    def row_w(ps, gaps):
        return sum(W[p] for p in ps) + sum(gaps)

    inner = max(row_w(ps, gaps) for rs in rows.values() for ps, gaps in rs)
    left, fw = 40, inner + 2 * PAD
    frame_ids = {"Presentation": "layer_presentation", "Application": "layer_application", "Data": "layer_data"}
    titles = {"Presentation": "Presentation Layer", "Application": "Application Layer", "Data": "Data Layer"}
    F = {}

    def frame(fid, title, x, y, w, h):
        # same ids and names as the frames of c44_layers: one package per layer in the VP model
        d.node(fid, "Package", title, x, y, w, h, role="frame", transparent=True)
        tw = text_w(title) + 10
        d.text(title, x + w / 2 - tw / 2, y + 20, tw, 18, owner=fid)
        return d.rect(fid)

    def nid(p):
        return "pkg_" + p.replace(".", "_")

    def sub(name, parent, x, y):
        # VP writes the name at the top of the body, under the 20 px tab
        d.node(nid(name), "Package", name, x, y, W[name], SUB_H, parent=parent)
        tw = text_w(name) + 8
        d.text(name, x + W[name] / 2 - tw / 2, y + 20, tw, 18, owner=nid(name))
        B[name] = d.rect(nid(name))

    y = 40
    for key, rs in rows.items():
        h = HEAD + len(rs) * SUB_H + (len(rs) - 1) * ROW_GAP + 28
        F[key] = frame(frame_ids[key], titles[key], left, y, fw, h)
        y += h + 70
    # sub-packages: rows centred in their frame; the second Data row sits under its interface package
    for key, rs in rows.items():
        f = F[key]
        for r, (ps, gaps) in enumerate(rs):
            ry = f.y + HEAD + r * (SUB_H + ROW_GAP)
            x = f.x + (f.w - row_w(ps, gaps)) / 2
            if key == "Data" and r == 1:
                x = B["infrastructure.repository"].x
            for i, p in enumerate(ps):
                sub(p, frame_ids[key], x, ry)
                x += W[p] + (gaps[i] if i < len(gaps) else 0)

    # domain model: a column on the right, as high as the three layers
    dw = max(W[p] for p in groups[domain_title])
    dx = left + fw + 130
    dy, db = F["Presentation"].y, F["Data"].b
    dom = frame("domain_model", "Domain Model", dx, dy, dw + 2 * PAD, db - dy)
    n = len(groups[domain_title])
    step = (dom.h - HEAD - 28 - SUB_H) / (n - 1)
    for i, p in enumerate(groups[domain_title]):
        sub(p, "domain_model", dx + PAD + (dw - W[p]) / 2, dy + HEAD + i * step)

    def use(a, b, pts, at):
        d.edge("Dependency", a, b, pts, label=USE, at=at, stereotype="use")

    uw, uh = caption_size(USE)

    # inside a layer: side to side, caption above the arrow
    def side_link(a, b):
        assert (a, b) in links, (a, b)
        ra, rb = B[a], B[b]
        yy = ra.y + 40                       # middle of the body (below the 20 px tab)
        xa, xb = (ra.r, rb.x) if ra.x < rb.x else (ra.x, rb.r)
        use(nid(a), nid(b), [(xa, yy), (xb, yy)], ((xa + xb) / 2, yy - uh / 2 - 7))

    side_link("presentation.view", "presentation.controller")
    side_link("presentation.web", "presentation.controller")
    side_link("application.service", "application.search")
    # sqlite -> repository: up from the tab of the lower package, caption on the right
    a, b = "infrastructure.repository.sqlite", "infrastructure.repository"
    assert (a, b) in links
    ra, rb = B[a], B[b]
    xx = ra.x + 14
    use(nid(a), nid(b), [(xx, ra.y), (xx, rb.b)], (xx + 8 + uw / 2, (ra.y + rb.b) / 2))

    # between the layers (model.LAYER_DEPENDENCIES): from the bottom of a frame into the tab of the next one
    xl = left + 70
    for upper, lower in model.LAYER_DEPENDENCIES:
        fu, fl = F[upper], F[lower]
        assert any(_layer_of(p) == upper and _layer_of(q) == lower for p, q in links), (upper, lower)
        use(frame_ids[upper], frame_ids[lower], [(xl, fu.b), (xl, fl.y)], (xl + 8 + uw / 2, (fu.b + fl.y) / 2))
    # every layer uses the domain model: from the right border of the frame, above its sub-packages
    for key in rows:
        assert _uses_domain(key), key
        f = F[key]
        yy = f.y + 44
        use(frame_ids[key], "domain_model", [(f.r, yy), (dom.x, yy)], ((f.r + dom.x) / 2, yy - uh / 2 - 7))


# ------------------------------------------------------------------ design sequences
class _Seq(Seq):
    """Seq with explicit activations [(lifeline, first message, last message, extra px)] (the automatic ones
    pair a call with the first matching return, which ends too early when every alt operand returns), an
    optional note below the lifelines and a tighter horizontal layout (A4 portrait)."""
    HEAD_GAP, LABEL_M, SELF_M, GUARD_M = 20, 22, 8, 16

    def __init__(self, d, parts, msgs, frags=(), acts=None, note=None, **kw):
        super().__init__(d, parts, msgs, frags, **kw)
        self.acts, self.note_text = acts, note
        self.cx = self._columns()

    def _columns(self):
        """Seq's column rule with smaller margins: heads HEAD_GAP apart, every caption in one gap with
        LABEL_M to spare, self-message captions before the next lifeline, guards left of the fragment."""
        n = len(self.parts)
        need = [self.heads[i] / 2 + self.heads[i + 1] / 2 + self.HEAD_GAP for i in range(n - 1)]
        for i, (f, t, _, kind) in enumerate(self.msgs):
            w = caption_size([self.texts[i]])[0]
            a, b = self.idx[f], self.idx[t]
            if kind == "self":
                if a < n - 1:
                    need[a] = max(need[a], 44 + w + self.SELF_M)
                continue
            if not any(need[k] >= w + self.LABEL_M for k in range(min(a, b), max(a, b))):
                k = a if a < b else a - 1
                need[k] = max(need[k], w + self.LABEL_M)
        for _, _, _, operands, covers in self.frags:
            lo = min(self.idx[c] for c in covers)
            gw = max(text_w(f"[{g}]") for g, _ in operands) + 50
            if lo > 0:
                need[lo - 1] = max(need[lo - 1], gw + self.GUARD_M)
        cx = [100]
        for k in range(n - 1):
            cx.append(cx[-1] + need[k])
        return cx

    def draw(self):
        super().draw()
        d = self.d
        if self.acts is not None:
            for el in [e for e in d.el if e.tag == "activation"]:
                d.el.remove(el)
            for k in [k for k in d.boxes if k.startswith("act ")]:
                del d.boxes[k]
            for who, first, last, extra in self.acts:
                y1, y2 = self.ys[first], self.ys[last] + extra
                d.activation(who, y1, y2)
                cx = self.cx[self.idx[who]]
                d.boxes[f"act {who} {y1}"] = (Rect(cx - 4, y1, 8, y2 - y1), "solid")
        if self.note_text:
            # VP wraps a note sized by note_w() alone (as in c44_layers): give it 60 px more
            d.note("seq_note", self.note_text, 40, self.bottom + 24, w=note_w(self.note_text) + 60)


def seq_search(root):
    """UC02 'Search by keyword' (SearchService.searchText): the request through the controller and the search
    service; QueryService asks Gemma 4 for the filters and falls back to keyword rules; retrieve() reads the
    products and rebuilds the vector index; RankingService orders the candidates."""
    d = Diagram(root, "c44_seq_search", "4.4d Design Sequence - Search by Keyword (UC02)", "sequence", SCOPE,
                SCOPE_NAME, numbers=True)
    parts = [(p, p) for p in ["Customer", "SearchUI", "SearchController", "SearchService", "QueryService",
                              "LlmClient", "ProductRepository", "VectorIndex", "RankingService"]]
    msgs = [
        ("Customer", "SearchUI", call("SearchUI", "submitText"), "call"),                       # 0
        ("SearchUI", "SearchController", call("SearchController", "search"), "call"),          # 1
        ("SearchController", "SearchService", call("SearchService", "searchText"), "call"),    # 2
        ("SearchService", "QueryService", call("QueryService", "textQuery"), "call"),          # 3
        ("QueryService", "QueryService", call("QueryService", "understand"), "self"),          # 4
        ("QueryService", "LlmClient", call("LlmClient", "chat"), "call"),                      # 5
        ("LlmClient", "QueryService", "LlmReply (JSON filters)", "return"),                    # 6
        ("QueryService", "QueryService", call("QueryService", "parseRules"), "self"),          # 7
        ("QueryService", "SearchService", "CommonQuery", "return"),                            # 8
        ("SearchService", "SearchService", call("SearchService", "retrieve"), "self"),         # 9
        ("SearchService", "ProductRepository", call("ProductRepository", "allProducts"), "call"),  # 10
        ("ProductRepository", "SearchService", "List<Product>", "return"),                     # 11
        ("SearchService", "VectorIndex", call("VectorIndex", "build"), "send"),                # 12
        ("SearchService", "RankingService", call("RankingService", "rank"), "call"),           # 13
        ("RankingService", "SearchService", "List<SearchResult>", "return"),                   # 14
        ("SearchService", "SearchController", "List<SearchResult>", "return"),                 # 15
        ("SearchController", "SearchUI", "JSON", "return"),                                    # 16
        ("SearchUI", "Customer", "ranked paintings", "return"),                                # 17
    ]
    frags = [("alt", 5, 7, [("Gemma 4 replies", 5), ("error or timeout → keyword rules", 7)],
              ["QueryService", "LlmClient"])]
    acts = [("SearchUI", 0, 17, 0), ("SearchController", 1, 16, 0), ("SearchService", 2, 15, 0),
            ("QueryService", 3, 8, 0), ("LlmClient", 5, 6, 0), ("ProductRepository", 10, 11, 0),
            ("VectorIndex", 12, 12, 18), ("RankingService", 13, 14, 0)]
    for cls, name in [("VectorIndex", "nearest"), ("SearchResultView", "render")]:      # named in the note
        _op(cls, name)
    note = ("QueryService only knows the LlmClient interface; at run time it is GemmaClient, which calls Gemma 4\n"
            "(vLLM, OpenAI-compatible API) with a time limit. A text query has no image embedding: retrieve()\n"
            "scores keywords and attributes, and VectorIndex.nearest() is not called. SearchUI shows the\n"
            "results with SearchResultView.render(results).")
    _Seq(d, parts, msgs, frags, acts=acts, note=note).draw()


def seq_cancel(root):
    """UC11 'Cancel order' (OrderService.cancelOrder): getOrder() checks that the order exists and belongs to
    the signed-in customer, Order.cancel() allows it only before shipment, then the new status is saved."""
    d = Diagram(root, "c44_seq_cancel", "4.4e Design Sequence - Cancel Order (UC11)", "sequence", SCOPE,
                SCOPE_NAME, numbers=True)
    parts = [(p, p) for p in ["Customer", "OrderView", "OrderController", "OrderService", "OrderRepository",
                              "Order"]]
    msgs = [
        ("Customer", "OrderView", "click Cancel order and confirm", "call"),                    # 0
        ("OrderView", "OrderController", call("OrderController", "cancelOrder"), "call"),      # 1
        ("OrderController", "OrderService", call("OrderService", "cancelOrder"), "call"),      # 2
        ("OrderService", "OrderService", call("OrderService", "getOrder"), "self"),            # 3
        ("OrderService", "OrderRepository", call("OrderRepository", "findOrder"), "call"),     # 4
        ("OrderRepository", "OrderService", "Order", "return"),                                # 5
        ("OrderService", "Order", call("Order", "isOwnedBy"), "call"),                         # 6
        ("Order", "OrderService", "boolean", "return"),                                        # 7
        ("OrderService", "OrderController", "NoSuchElementException", "return"),               # 8
        ("OrderController", "OrderView", "404 Not Found", "return"),                           # 9
        ("OrderService", "Order", call("Order", "cancel"), "call"),                            # 10
        ("Order", "OrderService", "IllegalStateException", "return"),                          # 11
        ("OrderService", "OrderController", "IllegalStateException", "return"),                # 12
        ("OrderController", "OrderView", "409 Conflict", "return"),                            # 13
        ("OrderService", "Order", call("Order", "cancel"), "send"),                            # 14
        ("OrderService", "OrderRepository", call("OrderRepository", "updateStatus", "orderId", "CANCELLED"),
         "send"),                                                                              # 15
        ("OrderService", "OrderController", "void", "return"),                                 # 16
        ("OrderController", "OrderView", "Order (CANCELLED)", "return"),                       # 17
        ("OrderView", "Customer", "show the result message", "return"),                        # 18
    ]
    frags = [("alt", 8, 17, [("not the customer's order → not found", 8),
                             ("not cancellable: SHIPPED, DELIVERED, CANCELLED", 10),
                             ("PLACED or PROCESSING → cancel ok", 14)],
              ["OrderView", "OrderController", "OrderService", "OrderRepository", "Order"])]
    acts = [("OrderView", 0, 18, 0), ("OrderController", 1, 17, 0), ("OrderService", 2, 16, 0),
            ("OrderRepository", 4, 5, 0), ("Order", 6, 7, 0), ("Order", 10, 11, 0), ("Order", 14, 14, 18),
            ("OrderRepository", 15, 15, 18)]
    _op("OrderController", "viewOrder")                                                 # named in the note
    note = ("WebServer takes customerId from the session (SessionManager), never from the page. It answers\n"
            "NoSuchElementException with 404 and IllegalStateException with 409; after a cancel it returns\n"
            "OrderController.viewOrder(customerId, orderId), the order with its new status.")
    _Seq(d, parts, msgs, frags, acts=acts, note=note).draw()


def build(root):
    packages(root)
    seq_search(root)
    seq_cancel(root)
