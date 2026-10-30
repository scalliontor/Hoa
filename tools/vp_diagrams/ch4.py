"""Chapter 4 (Design): analysis classes, data model, tables, design classes, layers, checkout sequence."""
from .classmodel import class_model, erd


def analysis(root):
    class_model(root, "c41_analysis", "4.1 Class Diagram in Analysis", "analysis", "analysis",
                "4.1 Analysis model", col_gap=170, row_gap=100)


def orm(root):
    """Data model: every class persistable, generalizations become 1 - 0..1 'is a' associations."""
    class_model(root, "c42_orm", "4.2a Data Model (ORM-Persistable)", "orm", "datamodel", "4.2 Data model",
                col_gap=190, row_gap=110)


def tables(root):
    """Physical model drawn as «table» classes: VP renders these reliably when exporting headless."""
    class_model(root, "c42_tables", "4.2b Database - tables, keys and foreign keys", "tables", "tables",
                "4.2 Database (tables)", col_gap=200, row_gap=110)


def design(root):
    class_model(root, "c43_design", "4.3 Class Diagram in Design", "design", "design", "4.3-4.5 Design model",
                col_gap=200, row_gap=110)




# ------------------------------------------------------------- 4.4 layers
from .common import (LINE, Diagram, Seq, caption_size, class_size, design_class, design_members, note_w,
                     text_w, DIAGRAMS)
import model


def _hidden_size(name):
    from .common import STEREO
    c = model.DESIGN_BY_NAME[name]
    return class_size(name, [], STEREO.get(c["kind"]), hidden=True)


def _use(d, a, b, pts, side="right", seg=-1, stereotype="use", caption=True, at=None):
    """«use» (or «create») dependency with its label beside segment `seg` (or centred on `at`)."""
    lines = [f"<<{stereotype}>>"]
    if not caption:
        d.edge("Dependency", a, b, pts, stereotype=stereotype, caption=False)
        return
    w, h = caption_size(lines)
    if at is not None:
        d.edge("Dependency", a, b, pts, label=lines, at=at, stereotype=stereotype)
        return
    (x1, y1), (x2, y2) = pts[seg - 1] if seg == -1 else pts[seg], pts[seg] if seg == -1 else pts[seg + 1]
    if seg == -1:
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
    if x1 == x2:
        at = (x1 + (w / 2 + 8) * (1 if side == "right" else -1), (y1 + y2) / 2)
    else:
        at = ((x1 + x2) / 2, y1 + (h / 2 + 7) * (-1 if side in ("above", "right") else 1))
    d.edge("Dependency", a, b, pts, label=lines, at=at, stereotype=stereotype)


def checkout_seq(root):
    """Design sequence of CheckoutService.checkout (slide A05): controller, service, domain, repositories."""
    d = Diagram(root, "c44_checkout_seq", "4.4d Checkout across the layers (design sequence)", "sequence",
                "design", "4.3-4.5 Design model", numbers=True)
    parts = [(p, p) for p in ["Customer", "CheckoutController", "CheckoutService", "Order", "CartRepository",
                              "CustomerRepository", "ProductRepository", "OrderRepository"]]
    msgs = [
        ("Customer", "CheckoutController", "checkout(customerId, cartId, addressId, paymentMethod)", "call"),
        ("CheckoutController", "CheckoutService", "checkout(cartId, customerId, addressId, payment)", "call"),
        ("CheckoutService", "CartRepository", "findById(cartId)", "call"),
        ("CartRepository", "CheckoutService", "Cart", "return"),
        ("CheckoutService", "CustomerRepository", "findById(customerId)", "call"),
        ("CustomerRepository", "CheckoutService", "Customer", "return"),
        ("CheckoutService", "Order", "<<create>>", "send"),
        ("CheckoutService", "ProductRepository", "findById(productId)", "call"),
        ("ProductRepository", "CheckoutService", "Product", "return"),
        ("CheckoutService", "Order", "addItem(OrderItem.fromCartItem(item, current))", "send"),
        ("CheckoutService", "Order", "calculateTotal(discountRate)", "send"),
        ("CheckoutService", "OrderRepository", "save(order)", "send"),
        ("CheckoutService", "ProductRepository", "decreaseStock(productId, quantity)", "send"),
        ("CheckoutService", "CartRepository", "clear(cartId)", "send"),
        ("CheckoutService", "CheckoutController", "Order", "return"),
        ("CheckoutController", "Customer", "Order (PLACED)", "return"),
    ]
    frags = [("loop", 7, 9, [("for each cart item", 7)],
              ["CheckoutService", "Order", "CartRepository", "CustomerRepository", "ProductRepository"])]
    Seq(d, parts, msgs, frags).draw()


SUB_ID = {pkg: "pkg_" + pkg.replace(".", "_") for _, _, subs in model.LAYERS for pkg in subs}


def layers(root):
    """The four layers as packages with their Java sub-packages; classes are owned at model level."""
    d = Diagram(root, "c44_layers", "4.4a Layers and Packages", "class", "design", "4.3-4.5 Design model")
    W, H, gap, x0 = 1000, 150, 90, 40
    top = {}
    y = 40
    for title, lid, subs in model.LAYERS:
        d.node("pkg_" + lid, "Package", lid, x0, y, W, H, role="frame")
        tw = text_w(lid) + 10
        d.text(lid, x0 + W / 2 - tw / 2, y + 22, tw, 18, owner="pkg_" + lid)
        n = len(subs)
        sw = (W - 60 - 30 * (n - 1)) / n
        x = x0 + 30
        for pkg in subs:
            short = pkg.split(".", 1)[1]
            d.node(SUB_ID[pkg], "Package", short, x, y + 55, sw, 70, parent="pkg_" + lid, role="frame")
            tw = text_w(short) + 10
            d.text(short, x + sw / 2 - tw / 2, y + 55 + 22, tw, 18, owner=SUB_ID[pkg])
            x += sw + 30
        top[title] = y
        y += H + gap
    b = lambda t: top[t] + H
    tab = 20                                     # the package body starts below its tab
    _use(d, "pkg_presentation", "pkg_application", [(x0 + 300, b("Presentation")),
                                                    (x0 + 300, top["Application"] + tab)])
    _use(d, "pkg_application", "pkg_domain", [(x0 + 300, b("Application")), (x0 + 300, top["Domain"] + tab)])
    xr = x0 + W + 70
    ya, yi = top["Application"] + H / 2, top["Infrastructure"] + H / 2
    _use(d, "pkg_application", "pkg_infrastructure", [(x0 + W, ya), (xr, ya), (xr, yi), (x0 + W, yi)], seg=1)
    _use(d, "pkg_infrastructure", "pkg_domain", [(x0 + 700, top["Infrastructure"] + tab), (x0 + 700, b("Domain"))])
    # model ownership of every design class drawn in an earlier diagram of the design scope
    drawn = {n.get("name") for dg in DIAGRAMS if dg.el.get("scope") == "design"
             for n in dg.el.findall("node") if n.get("type") == "Class"}
    import xml.etree.ElementTree as ET
    for c in model.DESIGN:
        if c["name"] in drawn:
            ET.SubElement(d.el, "contain", package=SUB_ID[c["package"]], **{"class": c["name"]})


def classes_front(root):
    """Presentation -> application -> domain, one vertical slice per feature (names only)."""
    d = Diagram(root, "c44_classes", "4.4b Classes per Layer - presentation to application", "class",
                "design", "4.3-4.5 Design model")
    pitch, x0 = 215, 110
    col = {k: x0 + i * pitch for i, k in enumerate(["room", "search", "cart", "checkout", "order", "admin",
                                                     "assistant", "web"])}
    Y = {"help": 40, "view": 170, "ctrl": 320, "svc": 470, "dom": 620}
    B = {}

    def put(name, cx, row, dx=0):
        w, h = _hidden_size(name)
        B[name] = design_class(d, name, cx - w / 2 + dx, Y[row], hidden=True)

    hx = col["search"]
    helpers = ["VoiceInput", "ImageUpload", "SearchResultView"]
    widths = [_hidden_size(n)[0] for n in helpers]
    total = sum(widths) + 40 * 2
    x = hx - total / 2
    for n, w in zip(helpers, widths):
        put(n, x + w / 2, "help")
        x += w + 40
    put("RoomPreview", col["room"], "view")
    put("SearchUI", col["search"], "view")
    put("CartView", col["cart"], "view")
    put("OrderView", col["order"], "view")
    put("AdminView", col["admin"], "view")
    put("AssistantView", col["assistant"], "view")
    put("EcomApplication", col["web"], "view")
    for k, n in [("search", "SearchController"), ("cart", "CartController"), ("checkout", "CheckoutController"),
                 ("order", "OrderController"), ("admin", "AdminController"), ("assistant", "AssistantController"),
                 ("web", "WebServer")]:
        put(n, col[k], "ctrl")
    w = _hidden_size("SpeechService")[0]
    put("SpeechService", col["search"] - 5 - w / 2, "svc")
    w = _hidden_size("SearchService")[0]
    put("SearchService", col["search"] + 5 + w / 2, "svc")
    put("CartService", col["cart"], "svc")
    put("CheckoutService", col["checkout"], "svc")
    put("OrderService", col["order"], "svc")
    w = _hidden_size("ProductService")[0]
    put("ProductService", col["admin"] + w / 2, "svc")
    put("AssistantService", col["assistant"], "svc")
    put("SessionManager", col["web"], "svc")
    put("Cart", col["cart"], "dom")
    put("Order", col["checkout"], "dom")

    deps = {(c, s): st for c, s, st in model.DESIGN_DEPENDENCIES_44}

    def dep(a, b, pts, **kw):
        assert (a, b) in deps, (a, b)
        _use(d, a, b, pts, stereotype=deps[(a, b)], **kw)

    ui = B["SearchUI"]
    ybus = ui.y - 44
    for i, n in enumerate(helpers):
        r = B[n]
        pts = [(ui.cx, ui.y), (ui.cx, ybus)] + ([(r.cx, ybus)] if r.cx != ui.cx else []) + [(r.cx, r.b)]
        if r.cx == ui.cx:
            pts = [(ui.cx, ui.y), (r.cx, r.b)]
        dep("SearchUI", n, pts, seg=0, caption=n == "ImageUpload")
    sc = B["SearchController"]
    dep("SearchUI", "SearchController", [(ui.cx, ui.b), (ui.cx, sc.y)])
    rp = B["RoomPreview"]
    dep("RoomPreview", "SearchController", [(rp.cx, rp.b), (rp.cx, sc.cy), (sc.x, sc.cy)], seg=0, side="left")
    cv, cc, kc = B["CartView"], B["CartController"], B["CheckoutController"]
    dep("CartView", "CartController", [(cv.cx, cv.b), (cv.cx, cc.y)])
    dep("CartView", "CheckoutController", [(cv.r, cv.cy), (kc.cx, cv.cy), (kc.cx, kc.y)])
    for v, c in [("OrderView", "OrderController"), ("AdminView", "AdminController"),
                 ("AssistantView", "AssistantController")]:
        dep(v, c, [(B[v].cx, B[v].b), (B[v].cx, B[c].y)])
    ws, sm = B["WebServer"], B["SessionManager"]
    dep("WebServer", "SessionManager", [(ws.cx, ws.b), (ws.cx, sm.y)])
    sp, ss = B["SpeechService"], B["SearchService"]
    dep("SearchController", "SpeechService", [(sc.cx - 15, sc.b), (sc.cx - 15, sp.y)], side="left")
    dep("SearchController", "SearchService", [(sc.cx + 15, sc.b), (sc.cx + 15, ss.y)])
    for c, s in [("CartController", "CartService"), ("CheckoutController", "CheckoutService"),
                 ("OrderController", "OrderService"), ("AssistantController", "AssistantService")]:
        dep(c, s, [(B[c].cx, B[c].b), (B[c].cx, B[s].y)])
    ac, os_, ps = B["AdminController"], B["OrderService"], B["ProductService"]
    dep("AdminController", "OrderService", [(ac.cx - 15, ac.b), (ac.cx - 15, os_.cy), (os_.r, os_.cy)], seg=0,
        side="left")
    dep("AdminController", "ProductService", [(ac.cx + 15, ac.b), (ac.cx + 15, ps.y)])
    dep("CartService", "Cart", [(B["CartService"].cx, B["CartService"].b), (B["Cart"].cx, B["Cart"].y)])
    dep("CheckoutService", "Order", [(B["CheckoutService"].cx, B["CheckoutService"].b),
                                     (B["Order"].cx, B["Order"].y)])
    text = "WebServer passes every HTTP request to the\ncontroller of the page; the customer id\nalways comes from SessionManager."
    d.note("web_note", text, col["order"] - 40, Y["dom"] - 10, w=note_w(text))


def classes_backend(root):
    """Application services -> repository interfaces -> SQLite implementations -> Database."""
    d = Diagram(root, "c44_classes_backend", "4.4c Classes per Layer - application to infrastructure", "class",
                "design", "4.3-4.5 Design model")
    pitch, x0 = 280, 140
    repos = ["ProductRepository", "CartRepository", "CustomerRepository", "OrderRepository"]
    impls = ["SqliteProductRepository", "SqliteCartRepository", "SqliteCustomerRepository", "SqliteOrderRepository"]
    svcs = ["ProductService", "CartService", "CheckoutService", "OrderService"]
    Y = {"svc": 40, "repo": 260, "impl": 420, "db": 570}
    B = {}

    def put(name, cx, row):
        w, h = _hidden_size(name)
        B[name] = design_class(d, name, cx - w / 2, Y[row], hidden=True)

    for i, (s, r, m) in enumerate(zip(svcs, repos, impls)):
        cx = x0 + i * pitch
        put(r, cx, "repo")
        put(m, cx, "impl")
    put("ProductService", x0, "svc")
    put("CartService", x0 + pitch, "svc")
    put("CheckoutService", x0 + 2 * pitch, "svc")
    put("OrderService", x0 + 3 * pitch, "svc")
    put("Database", x0 + 1.5 * pitch, "db")
    deps = {(c, s) for c, s, st in model.DESIGN_DEPENDENCIES_44}

    def dep(a, b, pts, **kw):
        assert (a, b) in deps, (a, b)
        _use(d, a, b, pts, **kw)

    P, C, U, O = (B[n] for n in repos)
    ps, cs, ks, os_ = (B[n] for n in svcs)
    # Routes to the far left take the outer corridor (left-most start, highest turn): one crossing remains,
    # CheckoutService -> ProductRepository over CartService -> CartRepository.
    yA, yC, yB = ps.b + 50, ps.b + 100, ps.b + 150
    dep("ProductService", "ProductRepository", [(P.cx - 30, ps.b), (P.cx - 30, P.y)], side="left")
    w_use = caption_size(["<<use>>"])[0]
    dep("CartService", "CartRepository", [(C.cx + 10, cs.b), (C.cx + 10, C.y)],
        at=(C.cx + 18 + w_use / 2, (yA + yC) / 2))
    dep("CartService", "ProductRepository", [(cs.cx - 30, cs.b), (cs.cx - 30, yA), (P.cx + 10, yA), (P.cx + 10, P.y)],
        seg=1, side="above")
    dep("CheckoutService", "ProductRepository", [(ks.x + 10, ks.b), (ks.x + 10, yC), (P.cx + 40, yC),
                                                 (P.cx + 40, P.y)], at=((P.cx + C.cx + 50) / 2, yC - 17))
    dep("CheckoutService", "CartRepository", [(ks.cx - 25, ks.b), (ks.cx - 25, yB), (C.cx + 40, yB),
                                              (C.cx + 40, C.y)], seg=-1)
    dep("CheckoutService", "CustomerRepository", [(U.cx, ks.b), (U.cx, U.y)], at=(U.cx + 8 + w_use / 2, (yB + U.y) / 2))
    dep("CheckoutService", "OrderRepository", [(ks.cx + 25, ks.b), (ks.cx + 25, yB), (O.cx - 30, yB),
                                               (O.cx - 30, O.y)], seg=1, side="above")
    dep("OrderService", "OrderRepository", [(O.cx + 20, os_.b), (O.cx + 20, O.y)])
    for r, m in zip(repos, impls):
        rr, mm = B[r], B[m]
        d.edge("Realization", m, r, [(mm.cx, mm.y), (rr.cx, rr.b)])
    db = B["Database"]
    ybus = db.y - 40
    for i, m in enumerate(impls):
        mm = B[m]
        pts = [(mm.cx, mm.b), (mm.cx, ybus), (db.cx, ybus), (db.cx, db.y)]
        lines = ["<<use>>"]
        if i == 1:
            w, h = caption_size(lines)
            d.edge("Dependency", m, "Database", pts, label=lines, at=(db.cx + 8 + w / 2, (ybus + db.y) / 2),
                   stereotype="use")
        else:
            d.edge("Dependency", m, "Database", pts, stereotype="use", caption=False)


def build(root):
    analysis(root)
    orm(root)
    tables(root)
    erd(root)
    design(root)
    classes_front(root)
    classes_backend(root)
    checkout_seq(root)
    layers(root)
