"""Chapter 3 (AI in e-commerce): AI components, image-search and shopping-assistant sequences."""
from .common import Diagram, Seq, caption_size, class_size, design_class, design_members, note_w
import model

SHOW_ATTRS = {"RankingService", "VectorIndex", "GemmaClient", "WhisperClient", "LlmReply", "ToolCall"}


def _size(name):
    c = model.DESIGN_BY_NAME[name]
    attrs, ops = design_members(name, attrs=name in SHOW_ATTRS, ctor=False)
    from .common import STEREO
    return class_size(name, attrs + ops, STEREO.get(c["kind"]), compartments=(2 if attrs else 1) if ops else 1)


def ai_architecture(root):
    """The services that call AI, the LlmClient/SpeechClient ports and their adapters."""
    d = Diagram(root, "c3_ai_architecture", "3.1 AI Components (Gemma 4 and Whisper)", "class", "design",
                "4.3-4.5 Design model")
    W = {n: _size(n) for n in ["AssistantService", "SearchService", "RankingService", "QueryService",
                               "ImageService", "VectorIndex", "LlmClient", "GemmaClient", "LlmReply", "ToolCall",
                               "SpeechService", "SpeechClient", "WhisperClient"]}
    gap, vgap = 70, 110
    xa = 40
    wa = max(W[n][0] for n in ("AssistantService", "LlmClient", "GemmaClient"))
    xb = xa + wa + gap
    xb2 = xb + W["QueryService"][0] + gap
    wb = xb2 + W["ImageService"][0] - xb
    xc = xb + wb + gap + 30
    B = {}

    def put(name, x, y):
        B[name] = design_class(d, name, x, y, attrs=name in SHOW_ATTRS, ctor=False)

    y1 = 40
    put("AssistantService", xa, y1)
    put("SearchService", xb + (wb - W["SearchService"][0]) / 2, y1)
    put("RankingService", xc, y1)
    y2 = y1 + max(W[n][1] for n in ("AssistantService", "SearchService", "RankingService")) + vgap
    put("QueryService", xb, y2)
    put("ImageService", xb2, y2)
    put("VectorIndex", xc, y2)
    y3 = y2 + max(W[n][1] for n in ("QueryService", "ImageService", "VectorIndex")) + vgap
    put("LlmClient", xa, y3)
    put("SpeechService", xc, y3)
    y4 = y3 + max(W[n][1] for n in ("LlmClient", "SpeechService")) + vgap
    put("GemmaClient", xa, y4)
    put("LlmReply", xb, y4)
    put("ToolCall", xb + W["LlmReply"][0] + gap, y4)
    put("SpeechClient", xc, y4)
    y5 = y4 + max(W[n][1] for n in ("GemmaClient", "LlmReply", "SpeechClient")) + vgap
    put("WhisperClient", xc, y5)

    def use(a, b, pts, side="right", seg=None):
        lines = ["<<use>>"]
        w, h = caption_size(lines)
        (x1, y1_), (x2, y2_) = (pts[seg], pts[seg + 1]) if seg is not None else (pts[-2], pts[-1])
        if x1 == x2:
            at = (x1 + (w / 2 + 8) * (1 if side == "right" else -1), (y1_ + y2_) / 2)
        else:
            at = ((x1 + x2) / 2, y1_ - h / 2 - 7)
        d.edge("Dependency", a, b, pts, label=lines, at=at, stereotype="use")

    a, s, r = B["AssistantService"], B["SearchService"], B["RankingService"]
    q, im, vi, llm = B["QueryService"], B["ImageService"], B["VectorIndex"], B["LlmClient"]
    deps = {(c, sup) for c, sup, st in model.DESIGN_DEPENDENCIES_44 if st == "use"}
    assert {("AssistantService", "SearchService"), ("AssistantService", "LlmClient"), ("SearchService", "QueryService"),
            ("SearchService", "ImageService"), ("SearchService", "VectorIndex"), ("SearchService", "RankingService"),
            ("QueryService", "LlmClient"), ("ImageService", "LlmClient"), ("SpeechService", "SpeechClient")} <= deps
    yA = a.y + 30
    use("AssistantService", "SearchService", [(a.r, yA), (s.x, yA)])
    use("AssistantService", "LlmClient", [(a.cx, a.b), (a.cx, llm.y)])
    use("SearchService", "QueryService", [(s.x + 30, s.b), (s.x + 30, q.y)])
    use("SearchService", "ImageService", [(s.r - 30, s.b), (s.r - 30, im.y)])
    use("SearchService", "RankingService", [(s.r, yA), (r.x, yA)])
    xv = (im.r + vi.x) / 2
    yv = s.b - 26
    use("SearchService", "VectorIndex", [(s.r, yv), (xv, yv), (xv, vi.cy), (vi.x, vi.cy)], seg=0)
    yl = llm.y + 26
    use("QueryService", "LlmClient", [(q.cx, q.b), (q.cx, yl), (llm.r, yl)], seg=0)
    use("ImageService", "LlmClient", [(im.cx, im.b), (im.cx, yl), (llm.r, yl)], seg=0)
    sp, sc, wc, g = B["SpeechService"], B["SpeechClient"], B["WhisperClient"], B["GemmaClient"]
    use("SpeechService", "SpeechClient", [(sp.cx, sp.b), (sp.cx, sc.y)])
    d.edge("Realization", "GemmaClient", "LlmClient", [(g.cx, g.y), (g.cx, llm.b)])
    d.edge("Realization", "WhisperClient", "SpeechClient", [(wc.cx, wc.y), (wc.cx, sc.b)])
    n = d.note("gemma", "Gemma 4 on the L40S server (vLLM behind Nginx :8000)\n"
                        "OpenAI-compatible API: chat completions, images, tool calling", xa, g.b + 70)
    d.edge("Anchor", "gemma", "GemmaClient", [(xa + 40, n.y), (xa + 40, g.b)])
    text = "Self-hosted Whisper (faster-whisper) on 127.0.0.1:9000\nAudio never leaves the laptop"
    nw = note_w(text)
    d.note("whisper", text, wc.x - 70 - nw, wc.cy - 23, w=nw)
    d.edge("Anchor", "whisper", "WhisperClient", [(wc.x - 70, wc.cy), (wc.x, wc.cy)])


def seq_image(root):
    d = Diagram(root, "c3_seq_image", "3.2 Sequence - Search by Image with Gemma 4", "sequence", "design",
                "4.3-4.5 Design model", numbers=True)
    parts = [(p, p) for p in ["Customer", "ImageUpload", "SearchUI", "SearchController", "SearchService",
                              "ImageService", "GemmaClient", "VectorIndex", "RankingService"]]
    msgs = [
        ("Customer", "ImageUpload", "choose(file)", "call"),
        ("ImageUpload", "ImageUpload", "validate(file)", "self"),
        ("ImageUpload", "SearchUI", "submitImage(file)", "call"),
        ("SearchUI", "SearchController", "searchImage(image)", "call"),
        ("SearchController", "SearchService", "searchImage(image)", "call"),
        ("SearchService", "ImageService", "embed(image)", "call"),
        ("ImageService", "GemmaClient", "chat(messages, tools)", "call"),
        ("GemmaClient", "ImageService", "LlmReply: style, subject, colour", "return"),
        ("ImageService", "VectorIndex", "toVector(style, subject, color)", "call"),
        ("VectorIndex", "ImageService", "double[]", "return"),
        ("ImageService", "ImageService", "empty vector (NFR02)", "self"),
        ("ImageService", "SearchService", "embedding", "return"),
        ("SearchService", "VectorIndex", "nearest(queryEmbedding, k)", "call"),
        ("VectorIndex", "SearchService", "Map<String, Double>", "return"),
        ("SearchService", "RankingService", "rank(query, candidates, limit)", "call"),
        ("RankingService", "SearchService", "List<SearchResult>", "return"),
        ("SearchService", "SearchController", "List<SearchResult>", "return"),
        ("SearchController", "SearchUI", "JSON", "return"),
        ("SearchUI", "Customer", "show the paintings and their reasons", "return"),
    ]
    frags = [("alt", 6, 10, [("Gemma 4 replies", 6), ("error or timeout", 10)],
              ["ImageService", "GemmaClient", "VectorIndex"])]
    Seq(d, parts, msgs, frags).draw()


def seq_assistant(root):
    d = Diagram(root, "c3_seq_assistant", "3.3 Sequence - Shopping Assistant (tool calling)", "sequence",
                "design", "4.3-4.5 Design model", numbers=True)
    parts = [(p, p) for p in ["Customer", "AssistantView", "AssistantController", "AssistantService",
                              "GemmaClient", "OrderService", "OrderRepository"]]
    q = model.DEMO_QUERIES[3]
    msgs = [
        ("Customer", "AssistantView", f'send("{q}")', "call"),
        ("AssistantView", "AssistantController", "ask(customerId, message)", "call"),
        ("AssistantController", "AssistantService", "ask(customerId, message)", "call"),
        ("AssistantService", "GemmaClient", "chat(messages, tools())", "call"),
        ("GemmaClient", "AssistantService", "LlmReply with toolCalls", "return"),
        ("AssistantService", "AssistantService", "runTool(customerId, call)", "self"),
        ("AssistantService", "OrderService", "getOrder(customerId, orderId)", "call"),
        ("OrderService", "OrderRepository", "findOrder(orderId)", "call"),
        ("OrderRepository", "OrderService", "Order", "return"),
        ("OrderService", "OrderService", "order.isOwnedBy(customerId)", "self"),
        ("OrderService", "AssistantService", "Order", "return"),
        ("AssistantService", "GemmaClient", "chat(messages + tool result, tools())", "call"),
        ("GemmaClient", "AssistantService", "LlmReply with content", "return"),
        ("AssistantService", "AssistantController", "AssistantReply", "return"),
        ("AssistantController", "AssistantView", "JSON", "return"),
        ("AssistantView", "Customer", "render(reply)", "return"),
    ]
    frags = [("opt", 5, 12, [("Gemma 4 asks for a tool", 5)],
              ["AssistantService", "GemmaClient", "OrderService", "OrderRepository"])]
    Seq(d, parts, msgs, frags).draw()


def build(root):
    ai_architecture(root)
    seq_image(root)
    seq_assistant(root)
