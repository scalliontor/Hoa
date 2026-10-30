"""Chapter 5 (Code): deployment of the demo (laptop) and of Gemma 4 (L40S server)."""
from .common import LINE, Diagram, caption_size, text_w


def _title(d, nid, lines, r):
    """Register the stereotype and name VP writes centred at the top of a node."""
    w = max(text_w(t, bold=True) for t in lines) + 10
    d.text("/".join(lines), r.cx - w / 2, r.y + 8, w, LINE * len(lines) + 4, owner=nid)


def deployment(root):
    d = Diagram(root, "c5_deployment", "5.1 Deployment - offline demo, Whisper and Gemma 4 server", "deployment",
                "deployment", "5 Deployment")

    def node(nid, type_, name, x, y, w, h, stereotype=None, parent=None, frame=False):
        d.node(nid, type_, name, x, y, w, h, stereotype=stereotype, parent=parent,
               role="frame" if frame else "solid")
        r = d.rect(nid)
        _title(d, nid, ([f"<<{stereotype}>>"] if stereotype else []) + [name], r)
        return r

    lx, ly, lw, lh = 40, 40, 860, 470
    lap = node("laptop", "Node", "Demo laptop (macOS)", lx, ly, lw, lh, stereotype="device", frame=True)
    br = node("browser", "Node", "Web browser", lx + 30, ly + 70, 280, 170, stereotype="executionEnvironment",
              parent="laptop", frame=True)
    ui = node("ui", "Artifact", "web UI (index.html, js)", br.x + 30, br.y + 80, 220, 60, parent="browser")
    jvm = node("jvm", "Node", "Java 17 runtime", lx + lw - 30 - 320, ly + 70, 320, 170,
               stereotype="executionEnvironment", parent="laptop", frame=True)
    app = node("app", "Artifact", "hoa-demo (EcomApplication, :8686)", jvm.x + 30, jvm.y + 80, 260, 60,
               parent="jvm")
    db = node("db", "Artifact", "ecom.db (SQLite)", jvm.x + 150, ly + 340, 170, 60, parent="laptop")
    py = node("python", "Node", "Python voice server 127.0.0.1:9000", lx + 30, ly + 300, 280, 140,
              stereotype="executionEnvironment", parent="laptop", frame=True)
    wh = node("whisper", "Artifact", "faster-whisper (small)", py.x + 30, py.y + 66, 220, 56, parent="python")

    sx = lap.r + 300
    srv = node("server", "Node", "L40S GPU server 171.226.10.121", sx, ly, 340, lh, stereotype="device", frame=True)
    ng = node("nginx", "Node", "Nginx :8000 (/llm/v1/)", sx + 30, ly + 70, 280, 90,
              stereotype="executionEnvironment", parent="server")
    vl = node("vllm", "Node", "vLLM", sx + 30, ly + 250, 280, 180, stereotype="executionEnvironment",
              parent="server", frame=True)
    gm = node("gemma", "Artifact", "Gemma 4 (model gemma-4)", vl.x + 30, vl.y + 80, 220, 60, parent="vllm")

    def link(type_, a, b, pts, text, at):
        d.edge(type_, a, b, pts, label=[text], at=at, name=text)

    y = br.y + 40
    t = "HTTP localhost:8686"
    w, h = caption_size([t])
    link("Association", "browser", "jvm", [(br.r, y), (jvm.x, y)], t, ((br.r + jvm.x) / 2, y - h / 2 - 7))
    t = "JDBC (sqlite-jdbc)"
    w, h = caption_size([t])
    x = db.x + 60
    link("Dependency", "app", "db", [(x, app.b), (x, db.y)], t, (x + 8 + w / 2, (jvm.b + db.y) / 2))
    t = "HTTP POST /transcribe"
    w, h = caption_size([t])
    x = jvm.x + 40
    link("Association", "jvm", "python", [(x, jvm.b), (x, py.cy), (py.r, py.cy)], t,
         ((py.r + x) / 2, py.cy - h / 2 - 7))
    t = "HTTP + API key: /llm/v1/chat/completions"
    w, h = caption_size([t])
    y = ng.cy
    link("Association", "jvm", "nginx", [(jvm.r, y), (ng.x, y)], t, ((lap.r + srv.x) / 2, y - h / 2 - 7))
    t = "reverse proxy"
    w, h = caption_size([t])
    link("Association", "nginx", "vllm", [(ng.cx, ng.b), (ng.cx, vl.y)], t, (ng.cx + 8 + w / 2, (ng.b + vl.y) / 2))


def build(root):
    deployment(root)
