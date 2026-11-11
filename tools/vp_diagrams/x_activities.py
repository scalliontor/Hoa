"""Activity diagrams of UC04 Search by Image, UC11 Cancel Order and UC13 Update Order Status.

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


def build(root):
    activity_image(root)
    activity_cancel(root)
    activity_admin(root)
