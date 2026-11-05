"""Chapter 4 (Design): analysis classes, data model, tables, design classes, layers, checkout sequence."""
from .classmodel import class_model, erd


def analysis(root):
    class_model(root, "c41_analysis", "4.1 Class Diagram in Analysis", "analysis", "analysis",
                "4.1 Analysis model", col_gap=170, row_gap=100)


def conceptual(root):
    """Conceptual data model: the entities by name and the named links between them, nothing else."""
    class_model(root, "c42_conceptual", "2.9a Conceptual Data Model", "conceptual", "datamodel",
                "4.2 Data model", col_gap=150, row_gap=90)


def orm(root):
    """Logical data model: attributes, every class persistable, every link named with multiplicities;
    generalizations become 1 - 0..1 'is a' associations."""
    class_model(root, "c42_orm", "2.9b Logical Data Model (ORM-Persistable)", "orm", "datamodel",
                "4.2 Data model", col_gap=190, row_gap=110)


def tables(root):
    """Physical data model drawn as «table» classes: VP renders these reliably when exporting headless."""
    class_model(root, "c42_tables", "4.2 Physical Data Model - tables, keys and foreign keys", "tables", "tables",
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


def layers(root):
    """The three layers (Presentation, Application, Data) as frames with their classes inside, each class
    linked to the classes it uses -- inside its layer and in the layer below (the style of the reference
    essay and of A06). One column per feature keeps most links vertical; the few long links and the domain
    model shared by all layers are named in a note. Every arrow is a dependency of DESIGN_DEPENDENCIES_44."""
    d = Diagram(root, "c44_layers", "4.4a Three Layers - classes and their links", "class", "design",
                "4.3-4.5 Design model")
    pitch = 240
    col = {k: 150 + (i + 1) * pitch for i, k in enumerate(
        ["speech", "assistant", "query", "image", "search", "ranking", "product", "cart", "checkout", "order",
         "web"])}
    col["helper"] = col["search"]
    B = {}

    def put(name, cx, y):
        w, h = _hidden_size(name)
        B[name] = design_class(d, name, cx - w / 2, y, hidden=True)
        return B[name]

    deps = {(c, s_): st for c, s_, st in model.DESIGN_DEPENDENCIES_44}

    def use(a, b, pts):
        assert (a, b) in deps, (a, b)
        d.edge("Dependency", a, b, pts, stereotype=deps[(a, b)], caption=False)

    def realize(impl, iface):
        m, i = B[impl], B[iface]
        d.edge("Realization", impl, iface, [(m.cx, m.y), (i.cx, i.b)])

    # ------------------------------------------------------------ rows and frames
    left = col["speech"] - 150
    right = col["web"] + 150
    frames = {}

    def frame(lid, title, y0, y1):
        # transparent: VP CE draws an opaque package over the classes placed on it
        d.node("layer_" + lid, "Package", title, left, y0, right - left, y1 - y0, role="frame", transparent=True)
        tw = text_w(title) + 10
        d.text(title, (left + right) / 2 - tw / 2, y0 + 22, tw, 18, owner="layer_" + lid)
        frames[lid] = (y0, y1)

    yP = 40
    P0, P1, P2 = yP + 60, yP + 170, yP + 270          # helper views, views, controllers
    yA = yP + 400
    A1 = yA + 80
    yD = yA + 280
    D1, D2, D3 = yD + 60, yD + 170, yD + 270
    frame("presentation", "Presentation Layer", yP, P2 + 26 + 34)
    frame("application", "Application Layer", yA, A1 + 26 + 44)
    frame("data", "Data Layer", yD, D3 + 26 + 34)

    # ------------------------------------------------------------ presentation
    for name, k in [("VoiceInput", "query"), ("ImageUpload", "search"), ("SearchResultView", "ranking")]:
        put(name, col[k], P0)
    for name, k in [("AssistantView", "assistant"), ("SearchUI", "search"), ("RoomPreview", "ranking"),
                    ("AdminView", "product"), ("CartView", "cart"), ("OrderView", "order"), ("WebServer", "web")]:
        put(name, col[k], P1)
    for name, k in [("AssistantController", "assistant"), ("SearchController", "search"),
                    ("AdminController", "product"), ("CartController", "cart"), ("CheckoutController", "checkout"),
                    ("OrderController", "order"), ("SessionManager", "web")]:
        put(name, col[k], P2)
    # ------------------------------------------------------------ application
    for name, k in [("SpeechService", "speech"), ("AssistantService", "assistant"), ("QueryService", "query"),
                    ("ImageService", "image"), ("SearchService", "search"), ("RankingService", "ranking"),
                    ("ProductService", "product"), ("CartService", "cart"), ("CheckoutService", "checkout"),
                    ("OrderService", "order")]:
        put(name, col[k], A1)
    # ------------------------------------------------------------ data
    for name, k in [("SpeechClient", "speech"), ("LlmClient", "assistant"), ("VectorIndex", "image"),
                    ("ProductRepository", "search"), ("CartRepository", "cart"),
                    ("CustomerRepository", "checkout"), ("OrderRepository", "order")]:
        put(name, col[k], D1)
    for name, k in [("WhisperClient", "speech"), ("GemmaClient", "assistant"), ("SqliteProductRepository", "search"),
                    ("SqliteCartRepository", "cart"), ("SqliteCustomerRepository", "checkout"),
                    ("SqliteOrderRepository", "order")]:
        put(name, col[k], D2)
    put("Database", (col["product"] + col["cart"]) / 2, D3)

    # ------------------------------------------------------------ links inside the presentation layer
    ui = B["SearchUI"]
    ybus = P0 + 40 + 25
    for n in ("VoiceInput", "ImageUpload", "SearchResultView"):
        r = B[n]
        pts = [(ui.cx, ui.y), (r.cx, r.b)] if r.cx == ui.cx else [(ui.cx, ui.y), (ui.cx, ybus), (r.cx, ybus), (r.cx, r.b)]
        use("SearchUI", n, pts)
    for v, c in [("AssistantView", "AssistantController"), ("SearchUI", "SearchController"),
                 ("AdminView", "AdminController"), ("CartView", "CartController"), ("OrderView", "OrderController")]:
        use(v, c, [(B[v].cx, B[v].b), (B[v].cx, B[c].y)])
    cv, kc = B["CartView"], B["CheckoutController"]
    use("CartView", "CheckoutController", [(cv.r, cv.cy), (kc.cx, cv.cy), (kc.cx, kc.y)])
    rp, sc = B["RoomPreview"], B["SearchController"]
    use("RoomPreview", "SearchController", [(rp.cx, rp.b), (rp.cx, sc.cy), (sc.r, sc.cy)])
    ws, sm = B["WebServer"], B["SessionManager"]
    use("WebServer", "SessionManager", [(ws.cx, ws.b), (ws.cx, sm.y)])

    # ------------------------------------------------------------ presentation -> application
    yPA = frames["presentation"][1] + (yA - frames["presentation"][1]) / 2
    use("SearchController", "SearchService", [(sc.cx, sc.b), (sc.cx, B["SearchService"].y)])
    sp = B["SpeechService"]
    use("SearchController", "SpeechService", [(sc.cx - 30, sc.b), (sc.cx - 30, yPA), (sp.cx, yPA), (sp.cx, sp.y)])
    for c, s_ in [("AssistantController", "AssistantService"), ("AdminController", "ProductService"),
                  ("CartController", "CartService"), ("CheckoutController", "CheckoutService"),
                  ("OrderController", "OrderService")]:
        use(c, s_, [(B[c].cx, B[c].b), (B[c].cx, B[s_].y)])

    # ------------------------------------------------------------ links inside the application layer
    ss = B["SearchService"]
    yA0 = A1 - 26
    for n in ("QueryService", "ImageService"):
        r = B[n]
        use("SearchService", n, [(ss.x + 12, ss.y), (ss.x + 12, yA0), (r.cx, yA0), (r.cx, r.y)])
    use("SearchService", "RankingService", [(ss.r, ss.cy), (B["RankingService"].x, ss.cy)])

    # ------------------------------------------------------------ application -> data
    gap0 = frames["application"][1]
    lane = lambda i: gap0 + 22 + 20 * i               # horizontal lanes between the two frames
    llm, qs, im = B["LlmClient"], B["QueryService"], B["ImageService"]
    use("AssistantService", "LlmClient", [(llm.cx, B["AssistantService"].b), (llm.cx, llm.y)])
    use("QueryService", "LlmClient", [(qs.cx, qs.b), (qs.cx, lane(0)), (llm.cx + 20, lane(0)), (llm.cx + 20, llm.y)])
    use("ImageService", "LlmClient", [(im.cx, im.b), (im.cx, lane(1)), (llm.cx + 40, lane(1)), (llm.cx + 40, llm.y)])
    use("SpeechService", "SpeechClient", [(sp.cx, sp.b), (sp.cx, B["SpeechClient"].y)])
    vi, pr = B["VectorIndex"], B["ProductRepository"]
    use("SearchService", "VectorIndex", [(ss.cx - 30, ss.b), (ss.cx - 30, lane(2)), (vi.cx + 15, lane(2)),
                                         (vi.cx + 15, vi.y)])
    use("SearchService", "ProductRepository", [(ss.cx, ss.b), (ss.cx, pr.y)])
    ps, cs, ks, os_ = B["ProductService"], B["CartService"], B["CheckoutService"], B["OrderService"]
    use("ProductService", "ProductRepository", [(ps.cx - 15, ps.b), (ps.cx - 15, lane(0)), (pr.cx + 20, lane(0)),
                                                (pr.cx + 20, pr.y)])
    use("CartService", "ProductRepository", [(cs.cx - 15, cs.b), (cs.cx - 15, lane(1)), (pr.cx + 40, lane(1)),
                                             (pr.cx + 40, pr.y)])
    use("CheckoutService", "ProductRepository", [(ks.cx - 35, ks.b), (ks.cx - 35, lane(2)), (pr.cx + 60, lane(2)),
                                                 (pr.cx + 60, pr.y)])
    cr = B["CartRepository"]
    use("CartService", "CartRepository", [(cs.cx, cs.b), (cs.cx, cr.y)])
    use("CheckoutService", "CartRepository", [(ks.cx - 15, ks.b), (ks.cx - 15, lane(3)), (cr.cx + 25, lane(3)),
                                              (cr.cx + 25, cr.y)])
    use("CheckoutService", "CustomerRepository", [(ks.cx, ks.b), (ks.cx, B["CustomerRepository"].y)])
    orp = B["OrderRepository"]
    use("CheckoutService", "OrderRepository", [(ks.cx + 20, ks.b), (ks.cx + 20, lane(0)), (orp.cx - 25, lane(0)),
                                               (orp.cx - 25, orp.y)])
    use("OrderService", "OrderRepository", [(os_.cx, os_.b), (os_.cx, orp.y)])

    # ------------------------------------------------------------ links inside the data layer
    for impl, iface in [("SqliteProductRepository", "ProductRepository"), ("SqliteCartRepository", "CartRepository"),
                        ("SqliteCustomerRepository", "CustomerRepository"), ("SqliteOrderRepository", "OrderRepository"),
                        ("GemmaClient", "LlmClient"), ("WhisperClient", "SpeechClient")]:
        realize(impl, iface)
    db = B["Database"]
    ydb = D3 - 35
    for impl in ("SqliteProductRepository", "SqliteCartRepository", "SqliteCustomerRepository",
                 "SqliteOrderRepository"):
        m = B[impl]
        d.edge("Dependency", impl, "Database", [(m.cx, m.b), (m.cx, ydb), (db.cx, ydb), (db.cx, db.y)],
               stereotype="use", caption=False)

    text = ("Dashed arrow: «use» dependency. Dashed arrow with a hollow triangle: realization.\n"
            "Not drawn, to keep the figure readable: WebServer passes each request to the\n"
            "controller of the page; AdminController also uses OrderService; AssistantService\n"
            "calls SearchService and OrderService as tools.\n"
            "The domain classes (Customer, Product, Cart, Order, Payment ...) are the model\n"
            "shared by all three layers: see the design class diagram.")
    d.note("layers_note", text, left, frames["data"][1] + 30, w=note_w(text) + 60)


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


def _ops_size(name):
    """Box of a class drawn with its public methods only (no attributes, no constructor)."""
    from .common import STEREO
    _, ops = design_members(name, attrs=False, ops=True, ctor=False)
    return class_size(name, ops, STEREO.get(model.DESIGN_BY_NAME[name]["kind"]))


def classes_backend(root):
    """Application services -> repository interfaces -> SQLite implementations -> Database.
    The services and the repository interfaces show their methods (design class model of Lecture 05);
    the SQLite classes implement the same methods and are drawn by name only."""
    d = Diagram(root, "c44_classes_backend", "4.4c Classes per Layer - application to data", "class",
                "design", "4.3-4.5 Design model")
    repos = ["ProductRepository", "CartRepository", "CustomerRepository", "OrderRepository"]
    impls = ["SqliteProductRepository", "SqliteCartRepository", "SqliteCustomerRepository", "SqliteOrderRepository"]
    svcs = ["ProductService", "CartService", "CheckoutService", "OrderService"]
    with_ops = set(svcs + repos)
    size = {n: _ops_size(n) if n in with_ops else _hidden_size(n) for n in svcs + repos + impls + ["Database"]}
    pitch = max(size[n][0] for n in svcs + repos) + 80
    x0 = 40 + max(size[svcs[0]][0], size[repos[0]][0]) / 2
    top = 40
    ybase = top + max(size[n][1] for n in svcs)          # lowest service bottom: the corridors start below it
    Y = {"svc": top, "repo": ybase + 210}
    Y["impl"] = Y["repo"] + max(size[n][1] for n in repos) + 110
    Y["db"] = Y["impl"] + max(size[n][1] for n in impls) + 110
    B = {}

    def put(name, cx, row):
        w, h = size[name]
        x = cx - w / 2
        if name in with_ops:
            B[name] = design_class(d, name, x, Y[row], attrs=False, ops=True, ctor=False)
        else:
            B[name] = design_class(d, name, x, Y[row], hidden=True)

    for i, (s, r, m) in enumerate(zip(svcs, repos, impls)):
        cx = x0 + i * pitch
        put(s, cx, "svc")
        put(r, cx, "repo")
        put(m, cx, "impl")
    put("Database", x0 + 1.5 * pitch, "db")
    deps = {(c, s) for c, s, st in model.DESIGN_DEPENDENCIES_44}

    def dep(a, b, pts, **kw):
        assert (a, b) in deps, (a, b)
        _use(d, a, b, pts, **kw)

    P, C, U, O = (B[n] for n in repos)
    ps, cs, ks, os_ = (B[n] for n in svcs)
    # Routes to the far left take the outer corridor (left-most start, highest turn): one crossing remains,
    # CheckoutService -> ProductRepository over CartService -> CartRepository.
    yA, yC, yB = ybase + 50, ybase + 100, ybase + 150
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
    conceptual(root)
    orm(root)
    tables(root)
    erd(root)
    design(root)
    classes_front(root)
    classes_backend(root)
    checkout_seq(root)
    layers(root)
