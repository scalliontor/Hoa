"""Activity diagrams of UC04 Search by Image, UC11 Cancel Order, UC13 Update Order Status and UC12 Manage Products.

Vertical swimlanes in the style of ch2.activity_checkout / ch2.activity_search: the actor on the left, the
Họa. system in the middle, the supporting party (Gemma 4 Service or the database) on the right. Every decision
comes from a business rule or requirement of Chapter 2 and every path ends in an activity final node.
"""
from .ch2 import LANE_SYSTEM
from .common import Diagram, act_node, flow, swimlanes

X0, Y0 = 20, 20


def _borders(lanes):
    """x of the left border of every lane."""
    xs, x = [], X0
    for _, w in lanes:
        xs.append(x)
        x += w
    return xs


def _left_guard(d, frm, to, pts, guard, border, decision):
    """Guard of a flow leaving a decision to the left: centred above the segment, between the lane border
    and the diamond, so it stays inside the system lane."""
    flow(d, frm, to, pts, guard=guard, at=((border + decision.x) / 2, decision.cy - 17))


# ------------------------------------------------------------------ UC04
def activity_image(root):
    d = Diagram(root, "c2_activity_image", "2.2c Activity - Search by Image (UC04)", "activity", "activity",
                "2 Behaviour")
    lanes = [("Customer", 260), (LANE_SYSTEM, 500), ("Gemma 4 Service", 280)]
    L0, L1, L2 = swimlanes(d, lanes, X0, Y0, 1190)
    sys_x = _borders(lanes)[1]
    a = L1 - 130                                   # side column of the fallback
    n = {}
    n["start"] = act_node(d, "start", "Initial", L0, 85, lane=0)
    n["choose"] = act_node(d, "choose", "Action", L0, 150, "Choose a photo and start the search", lane=0,
                           width=200)
    n["check"] = act_node(d, "check", "Action", L1, 150, "validate(file): JPEG, PNG or WebP, at most 5 MB",
                          lane=1, width=280)
    n["valid"] = act_node(d, "valid", "Decision", L1, 240, lane=1)
    n["refuse"] = act_node(d, "refuse", "Action", L0, 240, "See the refusal with the allowed formats and size",
                           lane=0, width=200)
    n["end1"] = act_node(d, "end1", "Final", L0, 325, lane=0)
    n["describe"] = act_node(d, "describe", "Action", L1, 340, 'describe(image, "artwork")', lane=1)
    n["gemma"] = act_node(d, "gemma", "Action", L2, 340,
                          "Describe style, subject and dominant colour in the shop's vocabulary", lane=2,
                          width=220)
    n["ai"] = act_node(d, "ai", "Decision", L1, 450, lane=1)
    n["local"] = act_node(d, "local", "Action", a, 540,
                          "Read the average colour locally, name the closest catalogue colour (NFR02)", lane=1,
                          width=200)
    n["m"] = act_node(d, "m", "Merge", L1, 630, lane=1)
    n["vector"] = act_node(d, "vector", "Action", L1, 710,
                           "toVector(style, subject, color): one-hot vector of 10 + 8 + 10 = 28 values", lane=1,
                           width=250)
    n["nearest"] = act_node(d, "nearest", "Action", L1, 800,
                            "nearest(queryEmbedding, k): cosine similarity, keep scores above 0", lane=1,
                            width=250)
    n["rank"] = act_node(d, "rank", "Action", L1, 885, "rank(query, candidates, limit)", lane=1, width=230)
    n["found"] = act_node(d, "found", "Decision", L1, 970, lane=1)
    n["results"] = act_node(d, "results", "Action", L0, 970, "See the paintings, each with its similarity and reason",
                            lane=0, width=190)
    n["empty"] = act_node(d, "empty", "Action", L0, 1065, "See an empty state instead of a noisy list", lane=0,
                          width=190)
    n["end"] = act_node(d, "end", "Final", L0, 1150, lane=0)
    N = n
    flow(d, "start", "choose", [N["start"].bottom, N["choose"].top])
    flow(d, "choose", "check", [N["choose"].right, N["check"].left])
    flow(d, "check", "valid", [N["check"].bottom, N["valid"].top])
    _left_guard(d, "valid", "refuse", [N["valid"].left, N["refuse"].right], "wrong type or over 5 MB", sys_x,
                N["valid"])
    flow(d, "refuse", "end1", [N["refuse"].bottom, N["end1"].top])
    flow(d, "valid", "describe", [N["valid"].bottom, N["describe"].top], guard="valid image")
    flow(d, "describe", "gemma", [N["describe"].right, N["gemma"].left])
    y = N["ai"].cy - 50
    flow(d, "gemma", "ai", [N["gemma"].bottom, (L2, y), (L1, y), N["ai"].top])
    flow(d, "ai", "local", [N["ai"].left, (a, N["ai"].cy), N["local"].top], guard="error or timeout",
         at=(N["ai"].x - 70, N["ai"].cy - 17))
    flow(d, "ai", "m", [N["ai"].bottom, N["m"].top], guard="description received")
    flow(d, "local", "m", [N["local"].bottom, (a, N["m"].cy), N["m"].left])
    flow(d, "m", "vector", [N["m"].bottom, N["vector"].top])
    flow(d, "vector", "nearest", [N["vector"].bottom, N["nearest"].top])
    flow(d, "nearest", "rank", [N["nearest"].bottom, N["rank"].top])
    flow(d, "rank", "found", [N["rank"].bottom, N["found"].top])
    _left_guard(d, "found", "results", [N["found"].left, N["results"].right], "similar paintings", sys_x,
                N["found"])
    flow(d, "found", "empty", [N["found"].bottom, (L1, N["empty"].cy), N["empty"].right], guard="nothing close")
    flow(d, "empty", "end", [N["empty"].bottom, N["end"].top])
    x = X0 + 16
    flow(d, "results", "end", [N["results"].left, (x, N["results"].cy), (x, N["end"].cy), N["end"].left])


# ------------------------------------------------------------------ UC11
def activity_cancel(root):
    d = Diagram(root, "c2_activity_cancel", "2.2d Activity - Cancel Order (UC11)", "activity", "activity",
                "2 Behaviour")
    lanes = [("Customer", 270), (LANE_SYSTEM, 490), ("Database", 280)]
    L0, L1, L2 = swimlanes(d, lanes, X0, Y0, 800)
    sys_x = _borders(lanes)[1]
    c = L1 + 20                                    # room for the longest guard left of the decisions
    n = {}
    n["start"] = act_node(d, "start", "Initial", L0, 85, lane=0)
    n["open"] = act_node(d, "open", "Action", L0, 150, "Open my orders and choose an order", lane=0, width=230)
    n["ask"] = act_node(d, "ask", "Action", L0, 235, "Ask to cancel the order", lane=0)
    n["request"] = act_node(d, "request", "Action", c, 235,
                            "cancelOrder(customerId, orderId), customerId from the session", lane=1, width=240)
    n["read"] = act_node(d, "read", "Action", L2, 235, "Read the order (table orders)", lane=2, width=200)
    n["own"] = act_node(d, "own", "Decision", c, 345, lane=1)
    n["notfound"] = act_node(d, "notfound", "Action", L0, 345, 'See "order not found in your account"', lane=0,
                             width=232)
    n["end1"] = act_node(d, "end1", "Final", L0, 420, lane=0)
    n["status"] = act_node(d, "status", "Decision", c, 495, lane=1)
    n["refuse"] = act_node(d, "refuse", "Action", L0, 495,
                           "See why the order cannot be cancelled; nothing changes", lane=0, width=200)
    n["end2"] = act_node(d, "end2", "Final", L0, 575, lane=0)
    n["cancel"] = act_node(d, "cancel", "Action", c, 600, "cancel(): the status becomes CANCELLED", lane=1,
                           width=240)
    n["save"] = act_node(d, "save", "Action", L2, 600, "Save the status CANCELLED (updateStatus)", lane=2,
                         width=200)
    n["back"] = act_node(d, "back", "Action", c, 690, "Return the Order (CANCELLED)", lane=1, width=240)
    n["seen"] = act_node(d, "seen", "Action", L0, 690, "See the order as CANCELLED", lane=0, width=200)
    n["end"] = act_node(d, "end", "Final", L0, 765, lane=0)
    N = n
    flow(d, "start", "open", [N["start"].bottom, N["open"].top])
    flow(d, "open", "ask", [N["open"].bottom, N["ask"].top])
    flow(d, "ask", "request", [N["ask"].right, N["request"].left])
    flow(d, "request", "read", [N["request"].right, N["read"].left])
    y = N["own"].cy - 50
    flow(d, "read", "own", [N["read"].bottom, (L2, y), (c, y), N["own"].top])
    _left_guard(d, "own", "notfound", [N["own"].left, N["notfound"].right], "not found or not owned", sys_x,
                N["own"])
    flow(d, "notfound", "end1", [N["notfound"].bottom, N["end1"].top])
    flow(d, "own", "status", [N["own"].bottom, N["status"].top], guard="owned by the customer")
    _left_guard(d, "status", "refuse", [N["status"].left, N["refuse"].right], "SHIPPED, DELIVERED or CANCELLED",
                sys_x, N["status"])
    flow(d, "refuse", "end2", [N["refuse"].bottom, N["end2"].top])
    flow(d, "status", "cancel", [N["status"].bottom, N["cancel"].top], guard="PLACED or PROCESSING")
    flow(d, "cancel", "save", [N["cancel"].right, N["save"].left])
    flow(d, "save", "back", [N["save"].bottom, (L2, N["back"].cy), N["back"].right])
    flow(d, "back", "seen", [N["back"].left, N["seen"].right])
    flow(d, "seen", "end", [N["seen"].bottom, N["end"].top])


# ------------------------------------------------------------------ UC13
def activity_admin(root):
    d = Diagram(root, "c2_activity_admin", "2.2e Activity - Update Order Status (UC13)", "activity", "activity",
                "2 Behaviour")
    lanes = [("Administrator", 270), (LANE_SYSTEM, 490), ("Database", 280)]
    L0, L1, L2 = swimlanes(d, lanes, X0, Y0, 800)
    sys_x = _borders(lanes)[1]
    c = L1 + 20
    n = {}
    n["start"] = act_node(d, "start", "Initial", L0, 85, lane=0)
    n["open"] = act_node(d, "open", "Action", L0, 150, "Open the back office and select an order", lane=0,
                         width=170)
    n["choose"] = act_node(d, "choose", "Action", L0, 235, "Choose the next status", lane=0)
    n["request"] = act_node(d, "request", "Action", c, 235, "updateOrderStatus(orderId, status)", lane=1,
                            width=240)
    n["read"] = act_node(d, "read", "Action", L2, 235, "Read the order (table orders)", lane=2, width=200)
    n["check"] = act_node(d, "check", "Action", c, 340,
                          "Check that the new status is the next step of "
                          "PLACED → PROCESSING → SHIPPED → DELIVERED; CANCELLED and DELIVERED are final",
                          lane=1, width=290)
    n["valid"] = act_node(d, "valid", "Decision", c, 445, lane=1)
    n["refuse"] = act_node(d, "refuse", "Action", L0, 445, "See the refusal: the order of statuses is wrong", lane=0,
                           width=200)
    n["end1"] = act_node(d, "end1", "Final", L0, 525, lane=0)
    n["advance"] = act_node(d, "advance", "Action", c, 560, "advanceTo(next): set the new status", lane=1,
                            width=240)
    n["save"] = act_node(d, "save", "Action", L2, 560, "Save the new status (updateStatus)", lane=2, width=200)
    n["back"] = act_node(d, "back", "Action", c, 655, "Return the Order with its new status", lane=1, width=240)
    n["seen"] = act_node(d, "seen", "Action", L0, 655, "See the new status in the list", lane=0, width=200)
    n["end"] = act_node(d, "end", "Final", L0, 735, lane=0)
    N = n
    flow(d, "start", "open", [N["start"].bottom, N["open"].top])
    flow(d, "open", "choose", [N["open"].bottom, N["choose"].top])
    flow(d, "choose", "request", [N["choose"].right, N["request"].left])
    flow(d, "request", "read", [N["request"].right, N["read"].left])
    flow(d, "read", "check", [N["read"].bottom, (L2, N["check"].cy), N["check"].right])
    flow(d, "check", "valid", [N["check"].bottom, N["valid"].top])
    _left_guard(d, "valid", "refuse", [N["valid"].left, N["refuse"].right], "invalid transition", sys_x,
                N["valid"])
    flow(d, "refuse", "end1", [N["refuse"].bottom, N["end1"].top])
    flow(d, "valid", "advance", [N["valid"].bottom, N["advance"].top], guard="valid transition")
    flow(d, "advance", "save", [N["advance"].right, N["save"].left])
    flow(d, "save", "back", [N["save"].bottom, (L2, N["back"].cy), N["back"].right])
    flow(d, "back", "seen", [N["back"].left, N["seen"].right])
    flow(d, "seen", "end", [N["seen"].bottom, N["end"].top])


# ------------------------------------------------------------------ UC12
def activity_products(root):
    d = Diagram(root, "c2_activity_products", "2.2f Activity - Manage Products (UC12)", "activity", "activity",
                "2 Behaviour")
    lanes = [("Administrator", 300), (LANE_SYSTEM, 480), ("Database", 280)]
    L0, L1, L2 = swimlanes(d, lanes, X0, Y0, 1230)
    sys_x, db_x = _borders(lanes)[1:]
    s = L1 - 120                                   # session check, left of listProducts()
    a, b = L1 - 115, L1 + 105                      # system columns of the new painting and of the price change
    side = X0 + 16                                 # [new painting] runs down beside the left border
    far = db_x + 260                               # the saved price change runs down beside the right border
    n = {}
    n["start"] = act_node(d, "start", "Initial", L0, 85, lane=0)
    n["open"] = act_node(d, "open", "Action", L0, 150, "Open the back office", lane=0)
    n["session"] = act_node(d, "session", "Decision", s, 150, lane=1)
    n["list"] = act_node(d, "list", "Action", b, 150, "listProducts()", lane=1)
    n["read"] = act_node(d, "read", "Action", L2, 150, "Read every product with its category, price and stock",
                         lane=2, width=200)
    n["denied"] = act_node(d, "denied", "Action", L0, 228, "See that access is refused", lane=0, width=200)
    n["end1"] = act_node(d, "end1", "Final", L0, 298, lane=0)
    n["seen"] = act_node(d, "seen", "Action", L0, 372, "See the products with their category, price and stock",
                         lane=0, width=200)
    n["choice"] = act_node(d, "choice", "Decision", L0, 458, lane=0)
    n["edit"] = act_node(d, "edit", "Action", L0, 550, "Change the price or stock of a product", lane=0,
                         width=155)
    n["enter"] = act_node(d, "enter", "Action", L0, 640,
                          "Enter a new painting with its category, artist, style, subject, colour, size and image",
                          lane=0, width=200)
    n["update"] = act_node(d, "update", "Action", b, 550,
                           "updatePriceAndStock(productId, price, stock): check price and stock", lane=1,
                           width=220)
    n["add"] = act_node(d, "add", "Action", a, 640, "addPainting(painting): check title, artist, price and stock",
                        lane=1, width=200)
    n["m1"] = act_node(d, "m1", "Merge", L1, 722, lane=1)
    n["valid"] = act_node(d, "valid", "Decision", L1, 802, lane=1)
    n["refuse"] = act_node(d, "refuse", "Action", L0, 802, "See the refusal naming the wrong field", lane=0,
                           width=180)
    n["end2"] = act_node(d, "end2", "Final", L0, 874, lane=0)
    n["save"] = act_node(d, "save", "Action", L2, 802, "save(product): UPDATE price and stock of the product row",
                         lane=2, width=200)
    n["accepts"] = act_node(d, "accepts", "Action", L1, 892,
                            "Category.accepts(painting): does the chosen category hold paintings?", lane=1,
                            width=240)
    n["cat"] = act_node(d, "cat", "Decision", L1, 980, lane=1)
    n["wrong"] = act_node(d, "wrong", "Action", L0, 980, "See the refusal: wrong category, nothing is written",
                          lane=0, width=200)
    n["end3"] = act_node(d, "end3", "Final", L0, 1055, lane=0)
    n["insert"] = act_node(d, "insert", "Action", L2, 980,
                           "save(painting): INSERT the product row, its painting row and its feature vector in one "
                           "transaction", lane=2, width=200)
    n["m2"] = act_node(d, "m2", "Merge", L2, 1120, lane=2)
    n["show"] = act_node(d, "show", "Action", L1, 1120, "listProducts(): show the updated list", lane=1,
                         width=240)
    n["updated"] = act_node(d, "updated", "Action", L0, 1120, "See the updated list", lane=0)
    n["end"] = act_node(d, "end", "Final", L0, 1195, lane=0)
    N = n

    def right_guard(frm, to, pts, guard, decision, until=db_x):
        """Guard of a flow leaving a decision to the right: centred above the segment, between the diamond
        and `until` (the database lane border or the next action), so it stays inside the system lane."""
        flow(d, frm, to, pts, guard=guard, at=((decision.x + decision.w + until) / 2, decision.cy - 17))

    flow(d, "start", "open", [N["start"].bottom, N["open"].top])
    flow(d, "open", "session", [N["open"].right, N["session"].left])
    right_guard("session", "list", [N["session"].right, N["list"].left], "administrator session", N["session"],
                until=N["list"].x)
    flow(d, "list", "read", [N["list"].right, N["read"].left])
    flow(d, "session", "denied", [N["session"].bottom, (s, N["denied"].cy), N["denied"].right],
         guard="not an administrator session")
    flow(d, "denied", "end1", [N["denied"].bottom, N["end1"].top])
    flow(d, "read", "seen", [N["read"].bottom, (L2, N["seen"].cy), N["seen"].right])
    flow(d, "seen", "choice", [N["seen"].bottom, N["choice"].top])
    flow(d, "choice", "edit", [N["choice"].bottom, N["edit"].top], guard="price or stock")
    flow(d, "choice", "enter", [N["choice"].left, (side, N["choice"].cy), (side, N["enter"].cy), N["enter"].left],
         guard="new painting", at=((X0 + N["choice"].x) / 2, N["choice"].cy - 17))
    flow(d, "edit", "update", [N["edit"].right, N["update"].left])
    flow(d, "enter", "add", [N["enter"].right, N["add"].left])
    flow(d, "update", "m1", [N["update"].bottom, (b, N["m1"].cy), N["m1"].right])
    flow(d, "add", "m1", [N["add"].bottom, (a, N["m1"].cy), N["m1"].left])
    flow(d, "m1", "valid", [N["m1"].bottom, N["valid"].top])
    _left_guard(d, "valid", "refuse", [N["valid"].left, N["refuse"].right], "negative value or missing field",
                sys_x, N["valid"])
    flow(d, "refuse", "end2", [N["refuse"].bottom, N["end2"].top])
    right_guard("valid", "save", [N["valid"].right, N["save"].left], "valid price or stock change", N["valid"])
    flow(d, "valid", "accepts", [N["valid"].bottom, N["accepts"].top], guard="valid new painting")
    flow(d, "accepts", "cat", [N["accepts"].bottom, N["cat"].top])
    _left_guard(d, "cat", "wrong", [N["cat"].left, N["wrong"].right], "category of another kind", sys_x, N["cat"])
    flow(d, "wrong", "end3", [N["wrong"].bottom, N["end3"].top])
    right_guard("cat", "insert", [N["cat"].right, N["insert"].left], "category accepts a painting", N["cat"])
    flow(d, "save", "m2", [N["save"].right, (far, N["save"].cy), (far, N["m2"].cy), N["m2"].right])
    flow(d, "insert", "m2", [N["insert"].bottom, N["m2"].top])
    flow(d, "m2", "show", [N["m2"].left, N["show"].right])
    flow(d, "show", "updated", [N["show"].left, N["updated"].right])
    flow(d, "updated", "end", [N["updated"].bottom, N["end"].top])


def build(root):
    activity_image(root)
    activity_cancel(root)
    activity_admin(root)
    activity_products(root)
