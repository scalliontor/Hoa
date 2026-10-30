"""Chapter 2 (Analysis): domain model, two activity diagrams, the A06 voice sequence, Order states."""
from .classmodel import class_model
from .common import Diagram, Seq, act_node, caption_size, flow, swimlanes
import model

LANE_SYSTEM = "Họa. system"


# ------------------------------------------------------------------ domain
def domain(root):
    """The 17 analysis classes with names only, associations with multiplicities, generalizations."""
    class_model(root, "c2_domain", "2.1 Domain Model (concepts)", "domain", "analysis", "4.1 Analysis model",
                col_gap=170, row_gap=90)


# ---------------------------------------------------------------- activity
def activity_checkout(root):
    d = Diagram(root, "c2_activity_checkout", "2.2 Activity - Checkout", "activity", "activity", "2 Behaviour")
    L0, L1, L2 = swimlanes(d, [("Customer", 300), (LANE_SYSTEM, 420), ("Database", 320)], 20, 20, 1190)
    n = {}
    n["start"] = act_node(d, "start", "Initial", L0, 85, lane=0)
    n["view"] = act_node(d, "view", "Action", L0, 150, "View the cart", lane=0)
    n["choose"] = act_node(d, "choose", "Action", L0, 230, "Choose the delivery address and the payment method",
                           lane=0, width=200)
    n["place"] = act_node(d, "place", "Action", L0, 320, "Place the order", lane=0)
    n["checkout"] = act_node(d, "checkout", "Action", L1, 320, "checkout(cartId, customerId, addressId, payment)",
                             lane=1, width=230)
    n["readCart"] = act_node(d, "readCart", "Action", L2, 320, "Read cart and cart_item", lane=2)
    n["d1"] = act_node(d, "d1", "Decision", L1, 430, lane=1)
    n["readStock"] = act_node(d, "readStock", "Action", L2, 520, "Read price and stock_quantity", lane=2)
    n["d2"] = act_node(d, "d2", "Decision", L1, 610, lane=1)
    n["merge"] = act_node(d, "merge", "Merge", L0, 610, lane=0)
    n["error"] = act_node(d, "error", "Action", L0, 700, "See the error and fix the cart", lane=0)
    n["stop"] = act_node(d, "stop", "FlowFinal", L0, 790, lane=0)
    n["create"] = act_node(d, "create", "Action", L1, 700, "Create Order and OrderItem, freeze unitPrice",
                           lane=1, width=230)
    n["total"] = act_node(d, "total", "Action", L1, 790, "calculateTotal(discountRate)", lane=1)
    n["pay"] = act_node(d, "pay", "Action", L1, 870, "Create Payment (PENDING)", lane=1)
    n["save"] = act_node(d, "save", "Action", L2, 870,
                         "Save orders, order_item, payment and shipping (one transaction)", lane=2, width=240)
    n["stock"] = act_node(d, "stock", "Action", L2, 960, "Decrease stock_quantity, clear cart_item", lane=2,
                          width=240)
    n["placed"] = act_node(d, "placed", "Action", L1, 1060, "Return the Order (PLACED)", lane=1)
    n["confirm"] = act_node(d, "confirm", "Action", L0, 1060, "See the order confirmation", lane=0)
    n["end"] = act_node(d, "end", "Final", L0, 1140, lane=0)
    N = n
    flow(d, "start", "view", [N["start"].bottom, N["view"].top])
    flow(d, "view", "choose", [N["view"].bottom, N["choose"].top])
    flow(d, "choose", "place", [N["choose"].bottom, N["place"].top])
    flow(d, "place", "checkout", [N["place"].right, (N["checkout"].x, N["place"].cy)])
    flow(d, "checkout", "readCart", [N["checkout"].right, (N["readCart"].x, N["checkout"].cy)])
    y = N["d1"].cy - 50
    flow(d, "readCart", "d1", [N["readCart"].bottom, (L2, y), (L1, y), N["d1"].top])
    in_lane = (320 + N["d1"].left[0]) / 2          # guards stay inside the system lane
    flow(d, "d1", "merge", [N["d1"].left, (L0, N["d1"].cy), N["merge"].top], guard="empty or not owned",
         at=(in_lane, N["d1"].cy - 17))
    flow(d, "d1", "readStock", [N["d1"].bottom, (L1, N["readStock"].cy), (N["readStock"].x, N["readStock"].cy)],
         guard="cart OK", side="left")
    y = N["d2"].cy - 50
    flow(d, "readStock", "d2", [N["readStock"].bottom, (L2, y), (L1, y), N["d2"].top])
    flow(d, "d2", "merge", [N["d2"].left, N["merge"].right], guard="out of stock", at=(in_lane, N["d2"].cy - 17))
    flow(d, "d2", "create", [N["d2"].bottom, N["create"].top], guard="in stock")
    flow(d, "merge", "error", [N["merge"].bottom, N["error"].top])
    flow(d, "error", "stop", [N["error"].bottom, N["stop"].top])
    flow(d, "create", "total", [N["create"].bottom, N["total"].top])
    flow(d, "total", "pay", [N["total"].bottom, N["pay"].top])
    flow(d, "pay", "save", [N["pay"].right, (N["save"].x, N["pay"].cy)])
    flow(d, "save", "stock", [N["save"].bottom, N["stock"].top])
    flow(d, "stock", "placed", [N["stock"].bottom, (L2, N["placed"].cy), N["placed"].right])
    flow(d, "placed", "confirm", [N["placed"].left, N["confirm"].right])
    flow(d, "confirm", "end", [N["confirm"].bottom, N["end"].top])


def activity_search(root):
    d = Diagram(root, "c2_activity_search", "2.3 Activity - Multimodal Search", "activity", "activity",
                "2 Behaviour")
    L0, L1, L2 = swimlanes(d, [("Customer", 290), (LANE_SYSTEM, 620), ("Gemma 4 Service", 300)], 20, 20, 1190)
    a, b, c = L1 - 190, L1, L1 + 190
    n = {}
    n["start"] = act_node(d, "start", "Initial", L0, 85, lane=0)
    n["input"] = act_node(d, "input", "Action", L0, 150, "Type a sentence, speak or choose a photo", lane=0,
                          width=200)
    n["mode"] = act_node(d, "mode", "Decision", b, 240, lane=1)
    n["text"] = act_node(d, "text", "Action", a, 330, "textQuery(text)", lane=1)
    n["voice"] = act_node(d, "voice", "Action", b, 330, "transcribe(audioInput) with self-hosted Whisper",
                          lane=1, width=165)
    n["photo"] = act_node(d, "photo", "Action", c, 330, "Check the photo: JPEG, PNG or WebP, at most 5 MB",
                          lane=1, width=165)
    n["m1"] = act_node(d, "m1", "Merge", b, 440, lane=1)
    n["ai"] = act_node(d, "ai", "Decision", b, 530, lane=1)
    n["gemma"] = act_node(d, "gemma", "Action", L2, 530,
                          "Understand the query: style, subject, colour, artist, maxPrice", lane=2, width=230)
    n["rules"] = act_node(d, "rules", "Action", a, 620, "Keyword rules; a photo gets no vector (NFR02)",
                          lane=1, width=165)
    n["m2"] = act_node(d, "m2", "Merge", b, 710, lane=1)
    n["retrieve"] = act_node(d, "retrieve", "Action", b, 790,
                             "retrieve(query): candidates from allProducts() and nearest()", lane=1, width=240)
    n["rank"] = act_node(d, "rank", "Action", b, 880,
                         "rank(query, candidates, limit): S = α·Stext + β·Simage + γ·Sbusiness", lane=1,
                         width=250)
    n["found"] = act_node(d, "found", "Decision", b, 970, lane=1)
    n["results"] = act_node(d, "results", "Action", L0, 970, "See the paintings and why each one fits",
                            lane=0, width=200)
    n["empty"] = act_node(d, "empty", "Action", L0, 1060, "See an empty state and a hint", lane=0)
    n["end"] = act_node(d, "end", "Final", L0, 1150, lane=0)
    N = n
    flow(d, "start", "input", [N["start"].bottom, N["input"].top])
    flow(d, "input", "mode", [N["input"].right, (b, N["input"].cy), N["mode"].top])
    flow(d, "mode", "text", [N["mode"].left, (a, N["mode"].cy), N["text"].top], guard="text")
    flow(d, "mode", "voice", [N["mode"].bottom, N["voice"].top], guard="voice")
    flow(d, "mode", "photo", [N["mode"].right, (c, N["mode"].cy), N["photo"].top], guard="photo")
    flow(d, "text", "m1", [N["text"].bottom, (a, N["m1"].cy), N["m1"].left])
    flow(d, "voice", "m1", [N["voice"].bottom, N["m1"].top])
    flow(d, "photo", "m1", [N["photo"].bottom, (c, N["m1"].cy), N["m1"].right])
    flow(d, "m1", "ai", [N["m1"].bottom, N["ai"].top])
    flow(d, "ai", "gemma", [N["ai"].right, (N["gemma"].x, N["ai"].cy)], guard="Gemma 4 replies")
    flow(d, "ai", "rules", [N["ai"].left, (a, N["ai"].cy), N["rules"].top], guard="error or timeout")
    flow(d, "gemma", "m2", [N["gemma"].bottom, (L2, N["m2"].cy), N["m2"].right])
    flow(d, "rules", "m2", [N["rules"].bottom, (a, N["m2"].cy), N["m2"].left])
    flow(d, "m2", "retrieve", [N["m2"].bottom, N["retrieve"].top])
    flow(d, "retrieve", "rank", [N["retrieve"].bottom, N["rank"].top])
    flow(d, "rank", "found", [N["rank"].bottom, N["found"].top])
    flow(d, "found", "results", [N["found"].left, N["results"].right], guard="results")
    flow(d, "found", "empty", [N["found"].bottom, (b, N["empty"].cy), N["empty"].right], guard="no result")
    flow(d, "empty", "end", [N["empty"].bottom, N["end"].top])
    x = 38
    flow(d, "results", "end", [N["results"].left, (x, N["results"].cy), (x, N["end"].cy), N["end"].left])


# ---------------------------------------------------------------- sequence
def seq_voice(root):
    """Assignment 06: exactly the seven participants of the problem statement."""
    d = Diagram(root, "c2_seq_voice", "2.5 Sequence - Search by Voice (A06)", "sequence", "design",
                "4.3-4.5 Design model", numbers=True)
    parts = [("Customer", "Customer"), ("SearchUI", "SearchUI"), ("SpeechService", "SpeechService"),
             ("QueryService", "QueryService"), ("SearchService", "SearchService"),
             ("ProductRepository", "ProductRepository"), ("RankingService", "RankingService")]
    q = model.DEMO_QUERIES[0]
    msgs = [
        ("Customer", "SearchUI", f'speak "{q}"', "call"),
        ("SearchUI", "SpeechService", "transcribe(audioInput)", "call"),
        ("SpeechService", "SearchUI", "transcript", "return"),
        ("SearchUI", "Customer", "show the transcript", "return"),
        ("Customer", "SearchUI", "submitVoice(transcript)", "call"),
        ("SearchUI", "SearchService", "searchVoice(transcript)", "call"),
        ("SearchService", "QueryService", "voiceQuery(text)", "call"),
        ("QueryService", "SearchService", "CommonQuery", "return"),
        ("SearchService", "ProductRepository", "allProducts()", "call"),
        ("ProductRepository", "SearchService", "List<Product>", "return"),
        ("SearchService", "RankingService", "rank(query, candidates, limit)", "call"),
        ("RankingService", "SearchService", "List<SearchResult>", "return"),
        ("SearchService", "SearchUI", "List<SearchResult>", "return"),
        ("SearchUI", "Customer", "show the ranked paintings", "return"),
    ]
    Seq(d, parts, msgs).draw()


# ------------------------------------------------------------------- state
def state_order(root):
    d = Diagram(root, "c2_state_order", "2.4 State Machine - Order", "state", "state", "2 Behaviour")
    states = model.DESIGN_BY_NAME["OrderStatus"]["literals"]
    assert states == ["PLACED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]
    w, h, gap, y = 130, 34, 200, 200
    xs = {s: 400 + i * (w + gap) for i, s in enumerate(states[:4])}
    centred = {}
    for s, x in xs.items():
        d.node(s, "State", s, x, y, w, h, **centred)
    cy = y + h / 2
    d.node("init", "InitialState", "", 40, cy - 11, 22, 22)
    cancel_x = (xs["PLACED"] + xs["PROCESSING"] + w) / 2 - w / 2
    d.node("CANCELLED", "State", "CANCELLED", cancel_x, 380, w, h, **centred)
    d.node("end", "FinalState", "", xs["DELIVERED"] + w + 120, cy - 12, 24, 24)
    d.node("endCancel", "FinalState", "", cancel_x + w / 2 - 12, 500, 24, 24)

    def t(a, b, pts, name=None, side="above"):
        label = [name] if name else None
        at = None
        if name:
            lw, lh = caption_size(label)
            (x1, y1), (x2, y2) = pts[0], pts[1]
            if side == "above":
                at = ((x1 + x2) / 2, y1 - lh / 2 - 7)
            elif side == "left":
                at = (x1 - lw / 2 - 8, (y1 + y2) / 2)
            else:
                at = (x1 + lw / 2 + 8, (y1 + y2) / 2)
        d.edge("Transition", a, b, pts, label=label, at=at, name=name)

    px = xs["PLACED"] + w / 2
    t("init", "PLACED", [(62, cy), (xs["PLACED"], cy)], "checkout(cartId, customerId, addressId, payment)")
    for a, b in zip(states[:3], states[1:4]):
        t(a, b, [(xs[a] + w, cy), (xs[b], cy)], f"advanceTo({b})")
    t("DELIVERED", "end", [(xs["DELIVERED"] + w, cy), (xs["DELIVERED"] + w + 120, cy)])
    ccy = 380 + h / 2
    t("PLACED", "CANCELLED", [(px, y + h), (px, ccy), (cancel_x, ccy)], "cancel()", side="left")
    qx = xs["PROCESSING"] + w / 2
    t("PROCESSING", "CANCELLED", [(qx, y + h), (qx, ccy), (cancel_x + w, ccy)], "cancel()", side="right")
    t("CANCELLED", "endCancel", [(cancel_x + w / 2, 380 + h), (cancel_x + w / 2, 500)])


def build(root):
    domain(root)
    activity_checkout(root)
    activity_search(root)
    state_order(root)
    seq_voice(root)
