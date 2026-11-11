"""4.4 The three logical components of Họa. as a UML component diagram.

Each layer of model.LAYERS is a component holding one component per Java package; the domain model is a fourth
component shared by the three layers; the database file and the two AI servers are external components. Every
dependency is labelled with what crosses it. The layer and package names come from model.LAYERS / DOMAIN_MODEL.
"""
from .common import Diagram, LINE, text_w
from .x_business import label_at
import model

# package -> (component name, column); columns line the packages up so that calls run straight down.
PARTS = {
    "presentation.view": ("Browser views", 0),
    "presentation.web": ("Web server and session", 1),
    "presentation.controller": ("Controllers", 2),
    "application.service": ("Shop services", 1),
    "application.search": ("Search and AI services", 2),
    "infrastructure.repository.sqlite": ("SQLite repositories", 0),
    "infrastructure.repository": ("Repository interfaces", 1),
    "infrastructure.search": ("Vector index", 2),
    "infrastructure.ai": ("AI clients", 3),
}
EXTERNAL = {"db": ("SQLite database ecom.db", 0), "gemma": ("Gemma 4 service (vLLM)", 2),
            "whisper": ("Whisper speech server", 3)}
W, H, GAP = 190, 60, 110         # inner component and the gap between columns (room for a label)
LEFT, TOP = 40, 40
FRAME_H, FRAME_GAP = H + 86, 96  # layer frame: title band, component, margin


def _x(col):
    return LEFT + GAP + col * (W + GAP)


def _flow(d, frm, to, pts, text, seg=0, side="right", along=0.5):
    lines = [text]
    d.edge("Dependency", frm, to, pts, label=lines, at=label_at(pts, seg, side, lines, along=along), name=text)


def components(root):
    in_model = {c["package"] for c in model.DESIGN}
    layered = {p for _, _, packs in model.LAYERS for p in packs}
    assert set(PARTS) == layered and layered <= in_model, (set(PARTS) ^ layered, layered - in_model)
    d = Diagram(root, "c44_components", "4.4a Three Logical Components", "raw", "components", "4.4 Components",
                vptype="ComponentDiagram")
    frame_w = 4 * W + 5 * GAP
    rows = {}
    for i, (title, _, packs) in enumerate(model.LAYERS):
        y = TOP + i * (FRAME_H + FRAME_GAP)
        rows[title] = y
        name = f"{title} layer"
        d.node(f"L_{title}", "Component", name, LEFT, y, frame_w, FRAME_H, role="frame", stereotype="layer")
        d.text(name, LEFT + 8, y + 4, text_w(name, bold=True) + 60, 2 * LINE + 6, owner=f"L_{title}")
        for p in packs:
            label, col = PARTS[p]
            d.node(p, "Component", label, _x(col), y + 60, W, H, parent=f"L_{title}")
    ext_y = TOP + 3 * (FRAME_H + FRAME_GAP)
    for nid, (label, col) in EXTERNAL.items():
        d.node(nid, "Component", label, _x(col), ext_y, W, H, stereotype="external")
    dom_x, dom_h = LEFT + frame_w + 130, 3 * FRAME_H + 2 * FRAME_GAP
    parts = ", ".join(p.split(".")[1] for p in model.DOMAIN_MODEL[2])
    d.node("domain", "Component", f"{model.DOMAIN_MODEL[0]}: {parts}", dom_x, TOP, 230, dom_h, stereotype="shared")

    r = d.rect
    v, web, ctl = r("presentation.view"), r("presentation.web"), r("presentation.controller")
    svc, srch = r("application.service"), r("application.search")
    sql, rep, idx, ai = (r("infrastructure.repository.sqlite"), r("infrastructure.repository"),
                         r("infrastructure.search"), r("infrastructure.ai"))
    db, gem, wh = r("db"), r("gemma"), r("whisper")
    # Presentation: views -> web server -> controllers -> the two kinds of services below.
    _flow(d, "presentation.view", "presentation.web", [(v.r, v.cy), (web.x, v.cy)], "HTTP, JSON", side="above")
    _flow(d, "presentation.web", "presentation.controller", [(web.r, web.cy), (ctl.x, web.cy)], "dispatch",
          side="above")
    _flow(d, "presentation.controller", "application.search", [(ctl.cx, ctl.b), (ctl.cx, srch.y)], "calls",
          side="right", along=0.45)
    turn = (ctl.b + rows["Application"]) / 2
    _flow(d, "presentation.controller", "application.service", [(ctl.x + 30, ctl.b), (ctl.x + 30, turn),
          (svc.cx, turn), (svc.cx, svc.y)], "calls", seg=2, side="left", along=0.62)
    _flow(d, "application.service", "application.search", [(svc.r, svc.cy), (srch.x, svc.cy)], "assistant",
          side="above")
    # Application -> data: the services see only interfaces.
    _flow(d, "application.service", "infrastructure.repository", [(svc.cx, svc.b), (svc.cx, rep.y)],
          "repository interfaces", side="right", along=0.45)
    _flow(d, "application.search", "infrastructure.search", [(srch.cx, srch.b), (srch.cx, idx.y)], "vectors",
          side="right", along=0.45)
    _flow(d, "application.search", "infrastructure.ai", [(srch.r, srch.cy), (ai.cx, srch.cy), (ai.cx, ai.y)],
          "LlmClient, SpeechClient", seg=1, side="right", along=0.45)
    _flow(d, "infrastructure.repository.sqlite", "infrastructure.repository", [(sql.r, sql.cy), (rep.x, sql.cy)],
          "implements", side="above")
    # Data -> outside.
    _flow(d, "infrastructure.repository.sqlite", "db", [(sql.cx, sql.b), (sql.cx, db.y)], "SQL over JDBC",
          side="right")
    turn = (ai.b + rows["Data"] + FRAME_H) / 2
    _flow(d, "infrastructure.ai", "gemma", [(ai.x + 30, ai.b), (ai.x + 30, turn), (gem.cx, turn), (gem.cx, gem.y)],
          "HTTPS, OpenAI-compatible API", seg=2, side="left", along=0.6)
    _flow(d, "infrastructure.ai", "whisper", [(ai.r - 30, ai.b), (ai.r - 30, wh.y)], "HTTP, audio", side="right")
    # Every layer uses the shared domain model.
    dom = r("domain")
    for title, y in rows.items():
        _flow(d, f"L_{title}", "domain", [(LEFT + frame_w, y + FRAME_H / 2), (dom.x, y + FRAME_H / 2)], "uses",
              side="above")


def build(root):
    components(root)
