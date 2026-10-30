"""Write the report tables (report/generated/*.tex) from tools/model.py.

Every class, method, table, requirement and use case name printed in the report
comes from here, so the text cannot drift from the model, the VP diagrams and the
code. Only the short explanations below are written by hand.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import model  # noqa: E402

OUT = ROOT / "report" / "generated"

UC_GOAL = {
    "UC01": "Find paintings (general use case)", "UC02": "Find paintings with keywords or a natural sentence",
    "UC03": "Find paintings by speaking", "UC04": "Find paintings that look like a photo",
    "UC05": "Decide on one painting", "UC06": "Prepare the purchase", "UC07": "Turn the cart into an order",
    "UC08": "Follow my orders", "UC09": "Check one of my orders by its id", "UC10": "Get help from the AI curator",
    "UC11": "Stop an order that is not shipped", "UC12": "Keep the catalogue, price and stock right",
    "UC13": "Move an order to its next status", "UC14": "Get paintings that suit my room",
}
ACTOR_TEXT = {
    "Customer": ("Person", "Buys paintings: searches, views, orders, tracks and cancels own orders"),
    "Administrator": ("Person", "Runs the gallery: manages paintings, price, stock and order status"),
    "Gemma 4 Service": ("External system", "Understands sentences, describes photos, chooses assistant tools"),
    "Payment Service": ("External system", "Confirms card payments and returns an authorisation code (simulated)"),
}
PRIORITY = {rid: detail[0] for rid, detail in model.REQUIREMENT_DETAILS.items()}
NFR_CHECK = {
    "NFR01": "Customer C002 asks for order 20261001 of C001 and is refused; the customer id is never read from the request body.",
    "NFR02": "With a wrong Gemma address the search still returns results from keyword rules and the page says that the fallback is used.",
    "NFR03": "A file that is not an image, or is larger than 5 MB, is rejected before Gemma is called.",
    "NFR04": "Views call controllers only; repositories, GemmaClient and WhisperClient are created only in the composition root.",
    "NFR05": "Table pay_credit has card_last4 and authorization_code and no column for the full card number.",
    "NFR06": "The application runs on one machine with a SQLite file; its only outside connection is the Gemma 4 server.",
    "NFR07": "searchText is timed on the demo data; a Gemma call is cut after the timeoutSeconds of GemmaClient.",
    "NFR08": "Audio is sent only to the Whisper server on 127.0.0.1; the time to transcribe a 5-second sentence is measured (build/eval/voice_eval.txt).",
}
CLASS_TEXT = {
    "FullName": "Name of a customer, a value object", "Customer": "A customer with an account",
    "Address": "Contact and delivery address", "CustomerVIP": "VIP customer with a discount and reward points",
    "CustomerNew": "Newly registered customer with a welcome voucher", "Cart": "Current shopping state (temporary)",
    "CartItem": "A product and the intended quantity in the cart", "Order": "A confirmed purchase transaction",
    "OrderItem": "A purchased product with its frozen transaction price", "Shipping": "Delivery of one order to one address",
    "Payment": "One payment attempt (abstract)", "PayCash": "Cash on delivery", "PayCredit": "Card payment through the payment service",
    "Product": "Anything the gallery sells (abstract)", "Artist": "Painter of the original work",
    "Painting": "A fine-art print of one painting", "Frame": "A frame sold with a print",
}
ASSOC_TEXT = {
    ("Customer", "FullName"): "Each customer has exactly one name; the name does not exist without the customer, hence composition.",
    ("Customer", "Address"): "A customer keeps at least one delivery address; Shipping also uses it, so only aggregation.",
    ("Customer", "Cart"): "At most one active cart per customer; a new customer may have none.",
    ("Customer", "Order"): "A customer places many orders; a new customer has none yet.",
    ("Cart", "CartItem"): "A cart line exists only inside its cart; an empty cart is valid.",
    ("Order", "OrderItem"): "An order line is part of its order; an order without lines makes no sense.",
    ("CartItem", "Product"): "Each cart line refers to exactly one product; a product appears in many carts.",
    ("OrderItem", "Product"): "Each order line refers to exactly one product; a product appears in many orders.",
    ("Order", "Shipping"): "A new order may not be shipped yet; once shipped it has exactly one delivery record.",
    ("Shipping", "Address"): "Each delivery goes to exactly one address; an address receives many deliveries.",
    ("Order", "Payment"): "An order may be unpaid, or have several attempts when one fails.",
    ("Artist", "Painting"): "An artist has many paintings in the gallery; each print belongs to exactly one artist.",
}
GEN_TEXT = {
    "Customer": "Both kinds of customer reuse the attributes of Customer and add their own.",
    "Payment": "Both payment methods share amount, date and status.",
    "Product": "Paintings and frames share id, name, price, stock, image and description.",
}
OP_TEXT = {
    "FullName.getDisplayName": "Joins first, middle and last name for display",
    "Address.format": "Address on one line, printed on the order",
    "Customer.getDisplayName": "Display name taken from FullName",
    "Customer.getDiscountRate": "Default discount 0, overridden by subclasses",
    "Customer.addAddress": "Adds a delivery address",
    "Customer.findAddress": "Finds an address by id; fails when it is not the customer's",
    "CustomerVIP.getDiscountRate": "Discount rate of the VIP tier (polymorphism)",
    "CustomerVIP.addPoints": "Adds reward points, refuses negative values",
    "CustomerNew.hasWelcomeVoucher": "Tells whether the new customer still has a voucher",
    "Product.isAvailable": "Checks that enough stock is left for a quantity",
    "Product.decreaseStock": "Decreases stock when ordered; refuses to oversell",
    "Product.getCategory": "Kind of product, decided by the subclass (abstract)",
    "Product.keywords": "Keywords used by text search",
    "Artist.getDisplayName": "Artist name with years of birth and death",
    "Painting.getCategory": "Returns PAINTING",
    "Painting.keywords": "Adds style, subject, colour, medium and artist name to the keywords",
    "Painting.sizeLabel": "Print size as \"width x height cm\"",
    "Frame.getCategory": "Returns FRAME",
    "Frame.keywords": "Adds frame material and colour to the keywords",
    "Cart.addItem": "Adds a product; merges with an existing line of the same product",
    "Cart.updateQuantity": "Changes a quantity; 0 removes the line",
    "Cart.removeItem": "Removes one line",
    "Cart.calculateTotal": "Provisional total of the cart",
    "Cart.isEmpty": "Whether the cart is empty (checkout refuses an empty cart)",
    "Cart.clear": "Empties the cart after a successful checkout",
    "CartItem.CartItem": "Creates a line and records the price when added",
    "CartItem.getSubtotal": "Amount of the cart line",
    "CartItem.increase": "Increases the quantity when the same product is added again",
    "Order.addItem": "Adds an order line",
    "Order.addPayment": "Attaches a payment attempt",
    "Order.calculateTotal": "Total = subtotal - discount + shipping fee, never negative",
    "Order.cancel": "Cancels the order; allowed only when PLACED or PROCESSING",
    "Order.advanceTo": "Moves the status in the order PLACED, PROCESSING, SHIPPED, DELIVERED",
    "Order.isOwnedBy": "Checks that the order belongs to the signed-in customer",
    "OrderItem.fromCartItem": "Turns a cart line into an order line at the current catalogue price",
    "OrderItem.getSubtotal": "Amount of the order line at the frozen price",
    "Shipping.updateStatus": "Changes the delivery status",
    "Shipping.markDelivered": "Records the delivery date and DELIVERED",
    "Payment.process": "Processes the payment, each method in its own way (abstract)",
    "Payment.markSucceeded": "Marks success and records the time",
    "Payment.markFailed": "Marks failure",
    "PayCash.process": "Checks the cash received and computes the change",
    "PayCredit.process": "Succeeds only with an authorisation code from the payment service",
    "PayCredit.maskedCard": "Shows the card as **** **** **** 1234",
}
FK_TEXT = {
    "customer_vip.customer_id": "VIP part of a customer", "customer_new.customer_id": "New-customer part of a customer",
    "address.customer_id": "Addresses of a customer", "painting.product_id": "Painting part of a product",
    "painting.artist_id": "Artist of the painting", "frame.product_id": "Frame part of a product",
    "product_feature.product_id": "Feature vector used by search",
    "cart.customer_id": "At most one cart per customer (UNIQUE)", "cart_item.cart_id": "Lines of a cart",
    "cart_item.product_id": "Product of a cart line", "orders.customer_id": "Customer who placed the order",
    "order_item.order_id": "Lines of an order", "order_item.product_id": "Purchased product",
    "shipping.order_id": "At most one delivery per order (UNIQUE)", "shipping.address_id": "Delivery address",
    "payment.order_id": "Payment attempts of an order", "pay_cash.payment_id": "Cash part of a payment",
    "pay_credit.payment_id": "Card part of a payment",
}
PACKAGE_TEXT = {
    "presentation.view": "Browser components (HTML, CSS, JS) named after the A06 presentation layer",
    "presentation.controller": "Receive decoded requests, call services, return results",
    "presentation.web": "HTTP server, sessions, composition root",
    "application.service": "Coordinate the cart, checkout, order, product and assistant use cases",
    "application.search": "Multimodal search: common query, speech, image, ranking",
    "domain.customer": "Customer, name, address, customer tiers",
    "domain.product": "Product, painting, frame, artist",
    "domain.cart": "Cart and cart lines",
    "domain.order": "Order, order lines, shipping and their statuses",
    "domain.payment": "Payments and payment status",
    "infrastructure.repository": "Repository interfaces used by the application layer",
    "infrastructure.repository.sqlite": "JDBC implementations of the repositories on a SQLite file",
    "infrastructure.search": "Vector index and cosine similarity",
    "infrastructure.ai": "Clients of Gemma 4 (OpenAI-compatible) and of the Whisper voice server",
}
LINK_NOTE = {
    ("UC02", "UC01"): "Searching with keywords is one way to find paintings",
    ("UC03", "UC01"): "Searching by voice is one way to find paintings",
    ("UC04", "UC01"): "Searching with a photo is one way to find paintings",
    ("UC14", "UC01"): "Finding a painting for a room is one way to find paintings; the input is a room photo",
    ("UC07", "UC06"): "Checkout always reads and checks the cart",
    ("UC10", "UC01"): "The assistant calls the painting search tool",
    ("UC10", "UC09"): "The assistant calls the order look-up tool",
    ("UC05", "UC01"): "From the results the customer may open a painting",
    ("UC11", "UC08"): "While viewing an order that is not shipped, the customer may cancel it",
}
EXCERPTS = ["EcomApplication", "WebServer_routes", "SearchService", "QueryService", "ImageService", "VectorIndex",
            "RankingService", "GemmaClient", "AssistantService", "CheckoutService", "OrderService",
            "SqliteOrderRepository", "SpeechService", "WhisperClient", "search_ui", "voice_input", "room_preview"]
FOLDERS = [
    ("tools/model.py", "Shared specification: requirements, use cases, classes, relationships, layers, tables", "1--5"),
    ("vp/", "Visual Paradigm project with every diagram", "1--5"),
    ("figures/vp/", "Diagrams exported from Visual Paradigm (PNG, SVG)", "1--5"),
    ("figures/demo/", "Screenshots of the demo and of the database", "3--5"),
    ("demo/db/", "SQLite schema and seed data generated from tools/model.py", "4"),
    ("demo/generated/src/", "Java skeleton generated from the 4.4 model", "4"),
    ("demo/src/main/java/", "Java source of the application, one folder per package", "4, 5"),
    ("demo/web/", "Browser views (HTML, CSS, JavaScript) and painting images", "5"),
    ("demo/tests/java/", "Automated tests of the demo and their fixtures", "5"),
    ("demo/README.md", "Package map of the demo and how to build, run and test it", "5"),
    ("build/MODEL_CHANGES.md", "Changes to tools/model.py proposed while coding, with reasons", "4, 5"),
    ("demo/data/", "Painting catalogue, image credits, evaluation images", "3, 5"),
    ("demo/voice-server/", "Self-hosted Whisper server for speech-to-text", "3, 5"),
    ("build/eval/", "Evaluation results of search and voice", "3, 5"),
    ("build/excerpts5/", "Code excerpts printed in this essay", "4, 5"),
    ("report/", "LaTeX source of this essay; report/build.sh rebuilds the PDF", "--"),
    ("slides/", "Presentation", "--"),
]


def say(table, key):
    """Explanation for a model element; a missing one is reported, not fatal."""
    if key not in table:
        print(f"  (no explanation for {key})")
        return ""
    return table[key]


def esc(text):
    out = []
    for ch in text:
        out.append({"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\\": r"\textbackslash{}",
                    "→": r"$\rightarrow$"}.get(ch, ch))
    return "".join(out)


def code(text):
    return r"\code{" + text + "}"


def longtable(spec, caption, label, header, rows, size=r"\small"):
    head = " & ".join(size + rf" \textbf{{{h}}}" for h in header) + r"\\"
    lines = [rf"\begin{{longtable}}{{@{{}}{spec}@{{}}}}",
             rf"\caption{{{caption}}}\label{{{label}}}\\",
             r"\toprule", head, r"\midrule", r"\endfirsthead",
             r"\toprule", head, r"\midrule", r"\endhead",
             r"\bottomrule", r"\endlastfoot"]
    for row in rows:
        lines.append(" & ".join(size + " " + cell for cell in row) + r"\\")
    lines.append(r"\end{longtable}")
    return "\n".join(lines) + "\n"


def write(name, text):
    (OUT / name).write_text(text, encoding="utf-8")


def signature(op):
    params = ", ".join(f"{p}: {t}" for p, t in op["params"])
    ret = f": {op['ret']}" if op["ret"] else ""
    flag = r" \{static\}" if op["static"] else (r" \{abstract\}" if op["abstract"] else "")
    return code(f"{op['vis']}{op['name']}({params}){ret}") + flag


def norm(name):
    return "".join(ch for ch in name.lower() if ch.isalnum())


def source_paths():
    """Find the real file behind each code excerpt, e.g. SearchService -> demo/.../SearchService.java."""
    files = [f for f in (ROOT / "demo").rglob("*") if f.is_file() and f.suffix in (".java", ".js", ".py")
             and not any(part in ("build", "generated", "classes", "node_modules", ".venv") for part in f.parts)]
    found = {}
    for name in EXCERPTS:
        key = norm(name.replace("_routes", ""))
        hits = sorted((f for f in files if norm(f.stem) == key), key=lambda f: len(f.parts))
        if hits:
            found[name] = hits[0].relative_to(ROOT).as_posix()
    return found


def schema_excerpt():
    """Copy the CREATE TABLE statements of a few tables from the real SQLite DDL."""
    ddl = [f for folder in ("demo/db", "db") for f in sorted((ROOT / folder).glob("**/*.sql"))
           if "CREATE TABLE" in f.read_text(errors="ignore")]
    if not ddl:
        write("schema.tex", r"\newcommand{\schemaPath}{demo/db/ (no DDL file yet)}" + "\n")
        return
    src = ddl[0]
    text = src.read_text(encoding="utf-8", errors="ignore")
    keep = []
    for table in ("product", "painting", "order_item"):
        match = re.search(rf"CREATE TABLE (IF NOT EXISTS )?{table}\b", text)
        if match:
            keep.append(text[match.start():text.find(";", match.start()) + 1])
    (OUT / "schema_excerpt.sql").write_text("\n\n".join(keep) + "\n", encoding="utf-8")
    write("schema.tex", r"\newcommand{\schemaPath}{" + esc(src.relative_to(ROOT).as_posix()) + "}\n")


# Methods shown when build/excerpts5/<name> is not there yet: the listing is cut from the real file.
EXCERPT_METHODS = {
    "EcomApplication": ["main"], "WebServer_routes": ["route"],
    "SearchService": ["searchText", "searchVoice", "searchImage", "searchRoom"],
    "QueryService": ["textQuery", "voiceQuery", "understand"], "ImageService": ["embed", "describe"],
    "VectorIndex": ["toVector", "cosineSimilarity"], "RankingService": ["rank", "businessScore"],
    "GemmaClient": ["chat"], "AssistantService": ["ask", "tools"], "CheckoutService": ["checkout"],
    "OrderService": ["getOrder", "cancelOrder", "updateStatus"], "SqliteOrderRepository": ["save", "updateStatus"],
    "SpeechService": ["transcribe"], "WhisperClient": ["transcribe"],
    "search_ui": ["submitText", "submitVoice", "submitImage"], "voice_input": ["start", "stop", "upload"],
    "room_preview": ["chooseRoom", "placePainting"],
}
ENDPOINT_UC = {
    "POST /api/login": "--", "GET /api/session": "--", "GET /api/products": "UC01", "GET /api/search": "UC02",
    "POST /api/voice/transcribe": "UC03", "POST /api/search/voice": "UC03", "POST /api/search/image": "UC04",
    "POST /api/search/multimodal": "UC01", "POST /api/room/describe": "UC14", "POST /api/room/search": "UC14",
    "POST /api/assistant": "UC10", "GET /api/cart": "UC06", "POST /api/cart/items": "UC06",
    "PUT /api/cart/items": "UC06", "DELETE /api/cart/items": "UC06", "POST /api/checkout": "UC07",
    "GET /api/orders": "UC08", "GET /api/orders/": "UC08, UC09", "POST /api/orders/": "UC11",
    "GET /api/admin/products": "UC12", "PUT /api/admin/products/": "UC12", "POST /api/admin/paintings": "UC12",
    "GET /api/admin/orders": "UC13", "PUT /api/admin/orders/": "UC13",
}
CONFIG_READER = {"server": "WebServer", "db": "Database", "gemma": "GemmaClient", "whisper": "WhisperClient",
                 "ranking": "RankingService"}


def without_strings(line):
    return re.sub(r'"(\\.|[^"\\])*"|\'(\\.|[^\'\\])*\'|`[^`]*`', '""', line)


def method_text(lines, name, js):
    """Lines of one method or function, with its comment, cut at the closing brace."""
    if js:
        decl = re.compile(rf"^\s*(export\s+)?(async\s+)?(static\s+)?(function\s+{name}\s*\(|{name}\s*\([^)]*\)\s*\{{"
                          rf"|(const|let|var)?\s*{name}\s*[:=]\s*(async\s+)?(function\b|\())")
    else:
        decl = re.compile(rf"^\s*(public|private|protected)\b[^=;]*\b{name}\s*\(")
    for start, line in enumerate(lines):
        if not decl.search(line):
            continue
        first = start
        while first > 0 and lines[first - 1].strip().startswith(("/**", "*", "*/", "//", "@")):
            first -= 1
        depth, opened = 0, False
        for end in range(start, min(len(lines), start + 70)):
            clean = without_strings(lines[end])
            depth += clean.count("{") - clean.count("}")
            opened = opened or "{" in clean
            if opened and depth <= 0:
                return lines[first:end + 1]
        return None
    return None


def excerpt_fallbacks(found):
    """Write report/generated/excerpts/<name>.java|js from the real source files."""
    folder = OUT / "excerpts"
    folder.mkdir(exist_ok=True)
    made = []
    for name, methods in EXCERPT_METHODS.items():
        if name not in found:
            continue
        src = ROOT / found[name]
        js = src.suffix == ".js"
        lines = src.read_text(encoding="utf-8", errors="ignore").split("\n")
        parts = [m for m in (method_text(lines, meth, js) for meth in methods) if m]
        if not parts:
            continue
        body = list(parts[0])
        for part in parts[1:]:
            if len(body) + len(part) + 1 > 46:
                break
            body += [""] + part
        if not js:
            header = next((l for l in lines if re.match(r"^public\s+(final\s+|abstract\s+)*(class|interface|enum)\s", l)), None)
            if header:
                body = [header.rstrip(" {") + " {", "    // ... (other members omitted)"] + body + ["}"]
        (folder / f"{name}{src.suffix}").write_text("\n".join(body) + "\n", encoding="utf-8")
        made.append(name)
    return made


def english_only():
    """Evaluation outputs without their secondary Vietnamese sections (the essay is in English)."""
    for name in ("voice_eval.txt", "eval_summary.txt"):
        src = ROOT / "build" / "eval" / name
        if not src.exists():
            continue
        keep, skipping = [], False
        for line in src.read_text(encoding="utf-8").splitlines():
            if line.startswith("Vietnamese"):
                skipping = True
            elif skipping and line and not line[0].isspace():
                skipping = False
            if not skipping:
                keep.append(line)
        (OUT / name.replace(".txt", "_en.txt")).write_text("\n".join(keep) + "\n", encoding="utf-8")


def listing_copies():
    """Copies of the excerpts for listings: the demo's (build/excerpts5) or the fallback (report/generated/excerpts).

    listings cannot keep characters above U+00FF in place under XeTeX (``Họa.'' prints as ``ọHa.''), so every run of
    non-ASCII characters is wrapped in an escape character that does not occur in that file."""
    folder = OUT / "listings"
    folder.mkdir(exist_ok=True)
    macros = []
    for name in EXCERPTS:
        demo = sorted((ROOT / "build" / "excerpts5").glob(f"{name}.*"))
        mine = sorted((OUT / "excerpts").glob(f"{name}.*"))
        src = demo[0] if demo else (mine[0] if mine else None)
        if src is None:
            continue
        text = src.read_text(encoding="utf-8", errors="ignore")
        escape = next((c for c in "`@|!?" if c not in text), None) if any(ord(c) > 127 for c in text) else None
        if escape:
            text = re.sub(r"[^\x00-\x7f]+", lambda m: escape + m.group(0) + escape, text)
            macros.append(r"\expandafter\def\csname lstesc:" + name + r"\endcsname{\lstset{escapechar=" + escape + "}}")
        if not demo:
            macros.append(r"\expandafter\def\csname lstnote:" + name + r"\endcsname{ (excerpt)}")
        (folder / f"{name}{src.suffix}").write_text(text, encoding="utf-8")
    write("listings.tex", "\n".join(macros) + "\n")


EVAL_ROWS = {"Text, Gemma 4": "TextGemma", "Text, keyword rules": "TextRules", "Paraphrased text, Gemma 4": "ParaGemma",
             "Paraphrased text, keyword rules": "ParaRules", "Voice": "Voice", "Image, Gemma 4 vision": "ImageGemma",
             "Image, local colour": "ImageLocal", "Gemma 4 tool calling": "AsstGemma", "Rules": "AsstRules",
             "Gemma 4 reads and picks": "RoomGemma", "Vector ranking": "RoomVector"}
EVAL_COLS = {"Search": ["N", "HitOne", "Second", "MRR", "Sec"], "Assistant": ["N", "Correct", "Tool", "Leaks", "Sec"],
             "Room": ["Rooms", "Picks", "Length", "Concrete", "Sec"]}


def eval_values():
    r"""Single values of build/eval/eval_tables.tex and the Whisper line of eval_summary.txt as macros \ev<Row><Column>."""
    macros = []
    src = ROOT / "build" / "eval" / "eval_tables.tex"
    text = src.read_text(encoding="utf-8") if src.exists() else ""
    for block, cols in EVAL_COLS.items():
        body = re.search(r"\\newcommand\{\\eval" + block + r"Rows\}\{(.*?)\n\}", text, re.S)
        for line in (body.group(1).splitlines() if body else []):
            cells = [c.strip() for c in line.rstrip("\\ ").split("&")]
            key = next((v for k, v in sorted(EVAL_ROWS.items(), key=lambda kv: -len(kv[0])) if cells[0].startswith(k)), None)
            if key and len(cells) == len(cols) + 1:
                macros += [rf"\newcommand{{\ev{key}{c}}}{{{v.replace('$^*$', '')}}}" for c, v in zip(cols, cells[1:])]
    summary = ROOT / "build" / "eval" / "eval_summary.txt"
    m = re.search(r"Whisper: (\d+) recordings, mean WER ([\d.]+), ([\d.]+) s per recording, order numbers kept (\d+)/(\d+)",
                  summary.read_text(encoding="utf-8") if summary.exists() else "")
    for name, value in zip(("WhisperRecordings", "WhisperWer", "WhisperSec", "OrderKept", "OrderTotal"),
                           m.groups() if m else ["[n/a]"] * 5):
        macros.append(rf"\newcommand{{\ev{name}}}{{{value}}}")
    defined = {re.search(r"\\newcommand\{\\(\w+)\}", m_).group(1) for m_ in macros}
    for key in EVAL_ROWS.values():
        for cols in EVAL_COLS.values():
            for c in cols:
                if f"ev{key}{c}" not in defined:
                    macros.append(rf"\providecommand{{\ev{key}{c}}}{{[n/a]}}")
    write("eval_values.tex", "\n".join(macros) + "\n")


def voice_values():
    """Numbers of the English part of build/eval/voice_eval.txt as macros \voiceWER, \voiceExact, ..."""
    src = ROOT / "build" / "eval" / "voice_eval.txt"
    text = src.read_text(encoding="utf-8").split("Vietnamese")[0] if src.exists() else ""
    found = {}
    for pattern, names in ((r"Model: (\S+) \| device: (\S+) \((\w+)\)", ("Model", "Device", "Compute")),
                           (r"Test set: (\d+) utterances", ("Utterances",)),
                           (r"Transcription time: mean ([\d.]+) s, max ([\d.]+) s", ("MeanSeconds", "MaxSeconds")),
                           (r"WER ([\d.]+)% \| CER ([\d.]+)% \| exact sentences (\d+)/(\d+)", ("WER", "CER", "Exact", "ExactOf"))):
        m = re.search(pattern, text)
        for i, name in enumerate(names):
            found[name] = m.group(i + 1) if m else "[n/a]"
    write("voice_values.tex", "\n".join(rf"\newcommand{{\voice{k}}}{{{v}}}" for k, v in found.items()) + "\n")


def eval_errors():
    """The incorrect results of build/eval/eval_summary.txt (A06: ``examples of incorrect results''), as written."""
    src = ROOT / "build" / "eval" / "eval_summary.txt"
    if not src.exists():
        return
    keep = []
    for line in src.read_text(encoding="utf-8").splitlines():
        image_miss = line.startswith("[image/") and " rank 1 " not in line
        if "hit1=0" in line or image_miss or "correct=False" in line or ("leaks=[" in line and "leaks=[]" not in line):
            keep.append(line if len(line) <= 112 else line[:109] + "...")
    local = [l for l in keep if l.startswith("[image/local colour]")]
    if len(local) > 1:
        ids = [re.search(r"\] (Q\d+)", l).group(1) for l in local if re.search(r"\] (Q\d+)", l)]
        keep = [l for l in keep if not l.startswith("[image/local colour]")]
        keep.append(f"[image/local colour] {len(local)} photos not ranked first: {', '.join(ids)}")
    header = "Incorrect results of the run (from build/eval/eval_summary.txt; long lines shortened with ...)"
    (OUT / "eval_errors.txt").write_text("\n".join([header, ""] + (keep or ["(none)"])) + "\n", encoding="utf-8")


def split_test_results():
    """build/test_results.txt -> the scenario tests (Chapter 5) and a condensed model check (Section 4.5).

    Runs of per-class "OK" lines are collapsed into one counted line; every other line is kept as written."""
    src = ROOT / "build" / "test_results.txt"
    if not src.exists():
        return
    lines = src.read_text(encoding="utf-8").splitlines()
    cut = next((i for i, l in enumerate(lines) if l.startswith("== Code versus model")), len(lines))
    (OUT / "test_scenarios.txt").write_text("\n".join(lines[:cut]).rstrip() + "\n", encoding="utf-8")
    check, run = [], 0
    for line in lines[cut:] + [""]:
        if line.startswith("OK ") and ("fields" in line or line.startswith("OK    view")):
            run += 1
            continue
        if run:
            check.append(f"OK    ... {run} lines of this section, one per element, all OK")
            run = 0
        check.append(line)
    (OUT / "model_check.txt").write_text("\n".join(check).rstrip() + "\n", encoding="utf-8")


def code_facts():
    """Fallback code tree and statistics of the demo (the demo build may write its own in build/)."""
    java_root = ROOT / "demo" / "src" / "main" / "java"
    java = sorted(java_root.rglob("*.java")) if java_root.exists() else []
    web = [f for f in sorted((ROOT / "demo" / "web").rglob("*")) if f.is_file() and f.suffix in (".js", ".html", ".css")]
    lines = ["demo/"]
    for folder, note in (("config/", "app.properties, read by EcomApplication"), ("db/", "SQLite schema and seed data"),
                         ("data/", "catalogue, image credits, ecom.db (created at the first start)"),
                         ("lib/", "Gson, sqlite-jdbc, slf4j"), ("scripts/", "build.sh, run.sh"),
                         ("voice-server/", "self-hosted Whisper server (Python)"),
                         ("web/", ", ".join(sorted(f.name + ("/" if f.is_dir() else "") for f in (ROOT / "demo" / "web").iterdir()
                                            if not f.name.startswith(".")))),
                         ("generated/src/", "skeleton generated from the 4.4 model")):
        if (ROOT / "demo" / folder).exists():
            lines.append("  " + folder.ljust(37) + note)
    lines.append("  src/main/java/com/ptit/ecom/")
    packages = {}
    for f in java:
        packages.setdefault(f.parent.relative_to(java_root / "com" / "ptit" / "ecom").as_posix(), []).append(f.stem)
    for pkg, classes in sorted(packages.items()):
        row, first = "    " + (pkg + "/").ljust(35), True
        for i, cls_name in enumerate(classes):
            piece = cls_name + (", " if i < len(classes) - 1 else "")
            if len(row) + len(piece) > 108:
                lines.append(row.rstrip())
                row, first = " " * 39, False
            row += piece
        lines.append(row.rstrip())
    (OUT / "code_tree.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    java_lines = sum(len(f.read_text(encoding="utf-8", errors="ignore").splitlines()) for f in java)
    js = [f for f in web if f.suffix == ".js"]
    stats = [rf"\providecommand{{\javaFileCount}}{{{len(java)}}}", rf"\providecommand{{\javaLineCount}}{{{java_lines}}}"]
    if js:
        stats.append(rf"\providecommand{{\jsFileCount}}{{{len(js)}}}")
    write("code_stats.tex", "\n".join(stats) + "\n")


def endpoints(found):
    """HTTP endpoints of WebServer.java: method and path, controller method called, identity, use case."""
    if "WebServer_routes" not in found:
        write("endpoints.tex", r"\assetbox{Endpoint table (generated from WebServer.java)}{demo/src/.../WebServer.java}" + "\n")
        return
    text = (ROOT / found["WebServer_routes"]).read_text(encoding="utf-8")
    customer_at = text.find("private Object customerRoute(")
    admin_at = text.find("private Object admin(")
    rows = []
    for m in re.finditer(r'route\.(equals|startsWith)\("(\w+) (/api/[^"]*)"\)( && route\.endsWith\("([^"]*)"\))?', text):
        verb, path, suffix = m.group(2), m.group(3), m.group(5)
        key = f"{verb} {path}"
        shown = path + ("<id>" if path.endswith("/") else "") + (suffix or "")
        if m.group(1) == "startsWith" and not path.endswith("/") and not suffix:
            shown = path
        ends = [i for i in (text.find(mark, m.end()) for mark in ("if (route", "throw new", "\n    }")) if i > 0]
        seg = text[m.end(): min(ends) if ends else m.end() + 400]
        calls = re.findall(r"(\w+Controller|sessionManager)\.(\w+)\(", seg)
        if not calls:
            helper = re.search(r"return\s+(\w+)\(exchange", seg)
            body_at = text.find(f"private Object {helper.group(1)}(") if helper else -1
            if body_at >= 0:
                calls = re.findall(r"(\w+Controller|sessionManager)\.(\w+)\(", text[body_at: body_at + 1500])[:1]
        names = []
        for obj, meth in calls:
            name = obj[0].upper() + obj[1:] + "." + meth
            if name not in names:
                names.append(name)
        target = ", ".join(code(n) for n in names) if names else "--"
        if admin_at >= 0 and m.start() > admin_at:
            who = "administrator session"
        elif (customer_at >= 0 and customer_at < m.start() < (admin_at if admin_at > customer_at else len(text))) \
                or "customer(exchange)" in seg:
            who = "customer session"
        else:
            who = "--"
        rows.append([code(f"{verb} {shown}"), target, who, ENDPOINT_UC[key] if key in ENDPOINT_UC else (say({}, key) or "--")])
    write("endpoints.tex", longtable(
        "P{5.6cm}P{5.0cm}P{2.6cm}P{1.8cm}", "HTTP endpoints of WebServer, the controller method each one calls and its use case",
        "tab:endpoints", ["Method and path", "Controller method", "Identity", "Use case"], rows, size=r"\footnotesize"))


def config_table():
    """Settings of demo/config/app.properties as a table and as macros \\cfg<Key>; the API key is never printed."""
    src = ROOT / "demo" / "config" / "app.properties"
    if not src.exists():
        write("config.tex", r"\assetbox{Configuration table}{demo/config/app.properties}" + "\n")
        write("config_values.tex", "")
        return
    rows, macros = [], []
    for line in src.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        secret = "key" in key.lower()
        shown = r"\emph{(read at start-up, not printed)}" if secret else code(value)
        rows.append([code(key), shown, code(CONFIG_READER.get(key.split(".")[0], "--"))])
        if not secret:
            name = "cfg" + "".join(part[0].upper() + part[1:] for part in re.split(r"[._]", key) if part)
            macros.append(rf"\providecommand{{\{name}}}{{{esc(value)}}}")
    write("config.tex", longtable(
        "P{4.4cm}P{6.6cm}P{4.0cm}", "Settings in demo/config/app.properties and the class that reads them",
        "tab:config", ["Key", "Value", "Read by"], rows, size=r"\footnotesize"))
    write("config_values.tex", "\n".join(macros) + "\n")


def error_table(found):
    """How WebServer.handleApi turns exceptions into HTTP status codes."""
    if "WebServer_routes" not in found:
        write("errors.tex", "")
        return
    text = (ROOT / found["WebServer_routes"]).read_text(encoding="utf-8")
    start = text.find("private void handleApi(")
    block = text[start: text.find("\n    }", start)]
    meaning = {"200": "Success; the result object is returned as JSON", "400": "Bad request: invalid input",
               "403": "Forbidden: wrong or missing session", "404": "Not found, also used for orders of another customer",
               "409": "Conflict with a business rule (stock, status, payment)", "500": "Unexpected error"}
    rows = [[code("(no exception)"), "200", meaning["200"]]]
    for exc, status in re.findall(r"catch \((\w+) e\) \{\s*send\(exchange, (\d{3})", block):
        rows.append([code(exc), status, meaning.get(status, "--")])
    write("errors.tex", longtable(
        "P{4.6cm}P{1.6cm}P{8.8cm}", "Exceptions of the application layer and the HTTP status returned by WebServer",
        "tab:errors", ["Exception", "Status", "Meaning for the browser"], rows, size=r"\footnotesize"))


def views_table():
    """Browser views of the model (presentation.view) and the JavaScript file that implements each one."""
    web = [f for f in (ROOT / "demo" / "web").rglob("*.js")] if (ROOT / "demo" / "web").exists() else []
    rows = []
    for c in (c for c in model.DESIGN if c["kind"] == "view"):
        ops = [o["name"] for o in c["ops"]]
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", c["name"]).lower().replace("u_i", "ui")
        hit = next((f for f in web if norm(f.stem) in (norm(c["name"]), norm(snake))), None)
        if hit is None:
            hit = next((f for f in web if re.search(rf"\b(class|function|const|let|var)\s+{c['name']}\b",
                                                     f.read_text(encoding="utf-8", errors="ignore"))), None)
        if hit:
            lines = hit.read_text(encoding="utf-8", errors="ignore").split("\n")
            present = [o for o in ops if method_text(lines, o, True)]
            where, status = code(hit.relative_to(ROOT).as_posix()), f"{len(present)}/{len(ops)}"
        else:
            where, status = "not written yet", "--"
        rows.append([code(c["name"]), ", ".join(code(o) for o in ops), where, status])
    write("views.tex", longtable(
        "P{3.0cm}P{6.0cm}P{4.4cm}P{1.6cm}", "Browser views of the design model and their JavaScript files",
        "tab:views", ["View class", "Methods in the model", "JavaScript file", "Found"], rows, size=r"\footnotesize"))


def folder_map(found):
    figs, lists = [], []
    for ch in sorted((ROOT / "report" / "chapters").glob("ch*.tex")):
        text = ch.read_text(encoding="utf-8")
        num = re.match(r"ch(\d)", ch.stem).group(1)
        for kind, name in re.findall(r"\\(vpfig|demofig)\{([^}]+)\}", text):
            path = f"figures/vp/{name}.png" if kind == "vpfig" else f"figures/demo/{name}.png"
            figs.append((num, path, (ROOT / path).exists()))
        for name in re.findall(r"\\excerpt\{[^}]*\}\{([^}.]+)\.[a-z]+\}", text):
            lists.append((num, name))
    rows = [[num, code(path), r"$\checkmark$" if ok else "missing"] for num, path, ok in figs]
    out = longtable("P{1.7cm}P{10.4cm}P{2.6cm}", "Figures of the essay and their files", "tab:mapfigs",
                    ["Chapter", "File", "Status"], rows, size=r"\footnotesize")
    def origin(name):
        hits = sorted((ROOT / "build" / "excerpts5").glob(f"{name}.*")) or sorted((OUT / "excerpts").glob(f"{name}.*"))
        return hits[0].relative_to(ROOT).as_posix() if hits else f"build/excerpts5/{name}"
    rows = [[num, code(origin(name)), code(found.get(name, "not found in demo/"))] for num, name in lists]
    out += longtable("P{1.7cm}P{5.4cm}P{7.9cm}", "Code excerpts of the essay and their real source files",
                     "tab:maplists", ["Chapter", "Excerpt", "Source file"], rows, size=r"\footnotesize")
    rows = [[code(path), esc(what), chs] for path, what, chs in FOLDERS]
    out += longtable("P{4.0cm}P{9.0cm}P{2.0cm}", "Main folders of the project", "tab:mapfolders",
                     ["Path", "Content", "Chapter"], rows, size=r"\footnotesize")
    origin = {"endpoints.tex": "demo/src/main/java/.../WebServer.java", "errors.tex": "demo/src/main/java/.../WebServer.java",
              "config.tex": "demo/config/app.properties", "views.tex": "tools/model.py, demo/web/"}
    rows = [[code("report/generated/" + f.name), code(origin.get(f.name, "tools/model.py"))]
            for f in sorted(OUT.glob("*.tex"))
            if f.name not in ("folder_map.tex", "paths.tex", "counts.tex", "schema.tex", "code_stats.tex",
                              "config_values.tex")]
    out += longtable("P{7.0cm}P{8.0cm}", "Tables generated from the shared specification and the code", "tab:mapgen",
                     ["Table file", "Generated from"], rows, size=r"\footnotesize")
    write("folder_map.tex", out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reqs = model.REQUIREMENTS
    uc_of = {uc: [r for r, _, _, ucs in reqs if uc in ucs] for uc, *_ in model.USE_CASES}
    ordered = sorted(reqs, key=lambda r: (r[1] != "FR", int(r[0][-2:])))

    def req_rows(kind):
        return [[r"\textbf{" + rid + "}", esc(model.REQUIREMENT_DETAILS[rid][2]), kind, PRIORITY[rid],
                 esc(model.REQUIREMENT_DETAILS[rid][1]), ", ".join(ucs)]
                for rid, k, title, ucs in ordered if k == kind]
    header = ["ID", "Requirement", "Type", "Priority", "Source", "Use case"]
    spec = "P{1.2cm}P{6.7cm}P{0.9cm}P{1.3cm}P{2.6cm}P{1.8cm}"
    write("req_fr.tex", longtable(spec, "Functional requirements (ID / Type / Priority / Source)", "tab:fr",
                                  header, req_rows("FR")))
    write("req_nfr.tex", longtable(spec, "Non-functional requirements (ID / Type / Priority / Source)", "tab:nfr",
                                   header, req_rows("NFR")))
    write("nfr_check.tex", longtable(
        "P{1.3cm}P{5.0cm}P{8.7cm}", "How the non-functional requirements are verified", "tab:nfrcheck",
        ["ID", "Short statement", "Verification"],
        [[r"\textbf{" + rid + "}", esc(title), esc(say(NFR_CHECK, rid))]
         for rid, kind, title, ucs in ordered if kind == "NFR"]))
    levels = {"Must": "Without it the gallery cannot operate or is not safe.",
              "Should": "Important differentiator; has a fallback when missing.",
              "Could": "Improves the experience, never blocks a purchase."}
    rows = [[lvl, ", ".join(r for r, *_ in ordered if PRIORITY[r] == lvl), levels[lvl]]
            for lvl in ("Must", "Should", "Could")]
    rows.append(["Won't (this release)", "Real payments, real carriers, personalised recommendations, account registration",
                 "Outside the scope of the essay; recorded for later."])
    write("moscow.tex", longtable(
        "P{2.4cm}P{6.3cm}P{6.3cm}", "MoSCoW prioritisation of the demo release", "tab:moscow",
        ["Level", "Requirements", "Meaning"], rows))

    write("actors.tex", longtable(
        "P{3.0cm}P{2.4cm}P{6.0cm}P{3.6cm}", "Actor catalogue", "tab:actors",
        ["Actor", "Kind", "Role", "Use cases"],
        [[esc(a), ACTOR_TEXT[a][0], esc(ACTOR_TEXT[a][1]),
          ", ".join([uc for uc, n, actor, k in model.USE_CASES if actor == a] +
                    [uc for uc, sup in model.SUPPORTING_ACTORS.items() if a in sup])]
         for a, _ in model.ACTORS]))
    rank = {"Must": 0, "Should": 1, "Could": 2}

    def uc_priority(uc):
        """Priority of the use case's functional requirements; an abstract use case takes its best child."""
        children = [a for a, b, k in model.USE_CASE_LINKS if b == uc and k == "Generalization"]
        if children:
            return min((uc_priority(c) for c in children), key=lambda p: rank[p])
        linked = [r for r in uc_of[uc] if r.startswith("FR")] or uc_of[uc]
        return min((PRIORITY[r] for r in linked), key=lambda p: rank[p]) if linked else "--"
    write("usecases.tex", longtable(
        "P{1.0cm}P{3.0cm}P{3.8cm}P{2.2cm}P{2.0cm}P{1.2cm}P{1.3cm}", "Use case catalogue",
        "tab:usecases", ["ID", "Use case", "Goal", "Primary actor", "Supporting actor", "Priority", "Req."],
        [[r"\textbf{" + uc + "}", esc(name) + (r" \emph{(abstract)}" if kind == "abstract" else ""),
          esc(UC_GOAL[uc]), esc(actor), esc(", ".join(model.SUPPORTING_ACTORS.get(uc, []))) or "--",
          uc_priority(uc), ", ".join(uc_of[uc])] for uc, name, actor, kind in model.USE_CASES],
        size=r"\footnotesize"))
    names = {uc: n for uc, n, *_ in model.USE_CASES}
    kind_text = {"Generalization": "Generalization", "Include": "«include»", "Extend": "«extend»"}
    write("uc_links.tex", longtable(
        "P{5.4cm}P{2.6cm}P{7.0cm}", "Relationships between use cases", "tab:uclinks",
        ["Relationship", "Kind", "Meaning"],
        [[f"{a} {esc(names[a])} $\\rightarrow$ {b} {esc(names[b])}", kind_text[k], esc(say(LINK_NOTE, (a, b)))]
         for a, b, k in model.USE_CASE_LINKS]))

    ucs = [uc for uc, *_ in model.USE_CASES]
    rows = [[r"\textbf{" + rid + "}"] + [r"$\bullet$" if uc in linked else "" for uc in ucs]
            for rid, kind, title, linked in ordered]
    matrix = longtable(
        "P{1.2cm}" + ">{\\centering\\arraybackslash}p{0.74cm}" * len(ucs), "Requirement -- use case traceability matrix",
        "tab:traceuc", ["ID"] + [r"\scriptsize " + uc for uc in ucs], rows, size=r"\scriptsize")
    write("trace_req_uc.tex", "{\\setlength{\\tabcolsep}{2.2pt}\n" + matrix + "}\n")

    write("analysis_classes.tex", longtable(
        "P{2.6cm}P{5.2cm}P{7.2cm}", "The analysis classes", "tab:classes41",
        ["Class", "Business meaning", "Attributes"],
        [[code(name) + (r" \emph{(abstract)}" if name in model.ANALYSIS_ABSTRACT else ""),
          esc(say(CLASS_TEXT, name)), ", ".join(code(a.split(":")[0].strip()) for a in attrs)]
         for name, attrs in model.ANALYSIS.items()]))
    kinds = {"composition": "Composition", "aggregation": "Aggregation", "association": "Association"}
    rows = [[code(a["a"]) + " -- " + code(a["b"]) + f" ({esc(a['name'])})", kinds[a["kind"]],
             f"{a['a_mult']} -- {a['b_mult']}", esc(say(ASSOC_TEXT, (a["a"], a["b"])))] for a in model.ANALYSIS_ASSOCIATIONS]
    parents = {}
    for child, parent in model.ANALYSIS_GENERALIZATIONS:
        parents.setdefault(parent, []).append(child)
    for parent, children in parents.items():
        rows.append([", ".join(code(c) for c in children) + r" $\rightarrow$ " + code(parent), "Generalization", "",
                     esc(say(GEN_TEXT, parent))])
    for client, supplier, stereo, name in model.ANALYSIS_DEPENDENCIES:
        rows.append([code(client) + r" $\dashrightarrow$ " + code(supplier) + f" ({esc(name)})",
                     f"Dependency «{stereo}»", "", "Checkout uses the cart content to create a new order; the cart is then emptied."])
    write("analysis_rel.tex", longtable(
        "P{4.3cm}P{2.3cm}P{2.0cm}P{6.4cm}", "Relationships between the analysis classes", "tab:rel41",
        ["Relationship (name)", "Kind", "Multiplicity", "Business meaning"], rows))

    domain = [c for c in model.DESIGN if c["package"].startswith("domain.")]
    rows = []
    for c in domain:
        if c["kind"] == "enum":
            rows.append([code(c["name"]) + r"\newline\emph{«enumeration»}", ", ".join(code(l) for l in c["literals"]),
                         "Valid status values"])
            continue
        for o in c["ops"]:
            rows.append([code(c["name"]), signature(o), esc(say(OP_TEXT, f"{c['name']}.{o['name']}"))])
    write("design_ops.tex", longtable(
        "P{2.6cm}P{7.0cm}P{5.4cm}", "Methods of the domain classes at design level", "tab:ops43",
        ["Class", "Method", "Responsibility"], rows, size=r"\footnotesize"))
    write("design_attrs.tex", longtable(
        "P{2.4cm}P{12.6cm}", "Typed attributes of the domain classes", "tab:attrs43",
        ["Class", "Attributes (private)"],
        [[code(c["name"]), ", ".join(code(f"{a['name']}: {a['type']}") for a in c["attrs"])]
         for c in domain if c["kind"] == "class" and c["attrs"]], size=r"\footnotesize"))
    write("design_nav.tex", longtable(
        "P{3.5cm}P{3.8cm}P{2.0cm}P{5.7cm}", "Directed relationships at design level", "tab:nav43",
        ["Relationship", "Direction and role", "Multiplicity", "Meaning"],
        [[code(a["src"]) + " -- " + code(a["dst"]) + f" ({esc(a['name'])})",
          code(f"{a['src']} -> {a['role']}"), f"{a['src_mult']} -- {a['mult']}",
          esc(ASSOC_TEXT.get((a["src"], a["dst"])) or ASSOC_TEXT.get((a["dst"], a["src"]), ""))]
         for a in model.DESIGN_ASSOCIATIONS], size=r"\footnotesize"))

    rows = []
    for title, lid, subs in model.LAYERS:
        for pkg in subs:
            members = [c["name"] for c in model.DESIGN if c["package"] == pkg]
            rows.append([title, code(f"{model.BASE_PACKAGE}.{pkg}"), ", ".join(code(m) for m in members),
                         esc(say(PACKAGE_TEXT, pkg))])
    write("layers.tex", longtable(
        "P{2.1cm}P{4.4cm}P{4.8cm}P{3.7cm}", "Layers, packages and classes of Họa.", "tab:layers",
        ["Layer", "Package", "Classes", "Responsibility"], rows, size=r"\footnotesize"))

    rows = []
    for i, t in enumerate(model.TABLES, 1):
        pk = [c["name"] for c in t["columns"] if c["pk"]]
        fks = [code(c["name"]) + r" $\rightarrow$ " + code(c["fk"].split(".")[0]) for c in t["columns"] if c["fk"]]
        rows.append([str(i), code(t["name"]), ", ".join(code(p) for p in pk), "; ".join(fks) or "--", esc(t["source"])])
    write("tables_list.tex", longtable(
        "P{0.6cm}P{2.8cm}P{3.2cm}P{5.0cm}P{3.4cm}", "Tables of the database", "tab:tables",
        ["\\#", "Table", "Primary key", "Foreign key $\\rightarrow$ parent", "Source class"], rows))
    rows = []
    for child, column, parent, _ in model.foreign_keys():
        name, pm, cm = model.FK_LABELS[f"{child}.{column}"]
        rows.append([code(f"{child}.{column}") + r" $\rightarrow$ " + code(parent), esc(name), f"{pm} -- {cm}",
                     esc(say(FK_TEXT, f"{child}.{column}"))])
    write("fks.tex", longtable(
        "P{5.4cm}P{2.3cm}P{2.0cm}P{5.3cm}", "Foreign keys, relationship names and multiplicities", "tab:fks",
        ["Foreign key", "Name", "Multiplicity", "Meaning"], rows))

    java = [c for c in model.DESIGN if c["kind"] != "view"]
    views = [c for c in model.DESIGN if c["kind"] == "view"]
    write("counts.tex", "\n".join([
        rf"\newcommand{{\nAnalysisClasses}}{{{len(model.ANALYSIS)}}}",
        rf"\newcommand{{\nDesignClasses}}{{{len(model.DESIGN)}}}",
        rf"\newcommand{{\nJavaTypes}}{{{len(java)}}}",
        rf"\newcommand{{\nViews}}{{{len(views)}}}",
        rf"\newcommand{{\nTables}}{{{len(model.TABLES)}}}",
        rf"\newcommand{{\nFks}}{{{len(list(model.foreign_keys()))}}}",
        rf"\newcommand{{\nReqs}}{{{len(reqs)}}}",
        rf"\newcommand{{\nFR}}{{{sum(1 for r in reqs if r[1] == 'FR')}}}",
        rf"\newcommand{{\nNFR}}{{{sum(1 for r in reqs if r[1] == 'NFR')}}}",
        rf"\newcommand{{\nUseCases}}{{{len(model.USE_CASES)}}}",
        rf"\newcommand{{\nDeps}}{{{len(model.DESIGN_DEPENDENCIES_44)}}}",
        rf"\newcommand{{\nDomainTypes}}{{{len(domain)}}}",
    ]) + "\n")

    rows = []
    for c in model.DESIGN:
        if c["package"].startswith("domain."):
            continue
        ops = [o["name"] for o in c["ops"] if o["name"] != c["name"]]
        kind = {"interface": "interface", "enum": "enum", "view": "view (JS)"}.get(c["kind"], "class")
        rows.append([code(c["name"]), kind, code(c["package"]), ", ".join(code(o) for o in ops[:7])])
    write("app_classes.tex", longtable(
        "P{3.3cm}P{1.6cm}P{4.5cm}P{5.6cm}", "Classes outside the domain layer: kind, package and public methods",
        "tab:appclasses", ["Class", "Kind", "Package", "Methods"], rows, size=r"\footnotesize"))

    schema_excerpt()
    found = source_paths()
    lines = [r"\expandafter\def\csname srcpath:" + name + r"\endcsname{"
             + esc(found.get(name, f"demo/.../{name} (not written yet)")).replace("/", "/\\allowbreak{}") + "}"
             for name in EXCERPTS]
    write("paths.tex", "\n".join(lines) + "\n")
    made = excerpt_fallbacks(found)
    english_only()
    split_test_results()
    eval_errors()
    voice_values()
    eval_values()
    listing_copies()
    code_facts()
    endpoints(found)
    config_table()
    error_table(found)
    views_table()
    folder_map(found)
    print(f"wrote {len(list(OUT.glob('*.tex')))} tables to {OUT}; sources found {len(found)}/{len(EXCERPTS)}; "
          f"fallback excerpts {len(made)}")


if __name__ == "__main__":
    main()
