"""Generate the Java skeleton of section 4.5 from the 4.4 design model.

Usage: python3 tools/gen_java.py
Writes demo/generated/src/com/ptit/ecom/** (one file per class of model.DESIGN, browser views
excluded) and build/code_tree_generated.txt. Domain classes come out complete because their
method bodies are part of the design; the other classes get TODO bodies that demo/src implements.
"""
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import model  # noqa: E402

SRC = ROOT / "demo" / "generated" / "src"
BUILD = ROOT / "build"
VIS = {"+": "public", "-": "private", "#": "protected", "~": ""}
JDK = {
    "BigDecimal": "java.math.BigDecimal",
    "LocalDate": "java.time.LocalDate",
    "LocalDateTime": "java.time.LocalDateTime",
    "List": "java.util.List",
    "ArrayList": "java.util.ArrayList",
    "Map": "java.util.Map",
    "DataSource": "javax.sql.DataSource",
    "Connection": "java.sql.Connection",
    "PreparedStatement": "java.sql.PreparedStatement",
    "ResultSet": "java.sql.ResultSet",
    "SQLException": "java.sql.SQLException",
    "HashMap": "java.util.HashMap",
}
HEADER = "Generated from the 4.4 design model (tools/model.py)."
# First Javadoc line of every class: which concept of the course slides it realises.
DOCS = {
    "FullName": "Value object for the customer's full name (Kiem tra 01: composition with Customer).",
    "Address": "Delivery address of a customer (Kiem tra 01).",
    "Customer": "Domain class Customer, owner of the cart and the orders (slide A03).",
    "CustomerVIP": "VIP customer with a discount: polymorphic getDiscountRate (Kiem tra 01).",
    "CustomerNew": "New customer with a welcome voucher (Kiem tra 01).",
    "DetailKind": "Which specialisation, and so which detail table, holds a product's own attributes.",
    "Category": "Product category: classifies every product and names its detail kind (domain model 4.1).",
    "Product": "Abstract catalogue product (slide A03: Product).",
    "Artist": "Painter of a painting (painting-shop domain model).",
    "Painting": "Painting sold by the shop, a specialisation of Product (domain model 4.1).",
    "Frame": "Frame sold with a painting, a specialisation of Product (domain model 4.1).",
    "Cart": "Shopping cart: the temporary shopping state (slide A03).",
    "CartItem": "Cart line: product + intended quantity; CartItem is not OrderItem (slide A03).",
    "OrderStatus": "States of the order state machine (slide 03).",
    "Order": "Order: the confirmed transaction produced by checkout (slides A03/A05).",
    "OrderItem": "Order line that keeps the price fixed at checkout (slide A03: OrderItem.unitPrice).",
    "ShippingStatus": "States of a delivery.",
    "Shipping": "Delivery data of one order (Kiem tra 01).",
    "PaymentStatus": "States of a payment.",
    "Payment": "Abstract payment: polymorphic process() (Kiem tra 01).",
    "PayCash": "Cash on delivery.",
    "PayCredit": "Card payment: only the last four digits and the authorisation code are kept (NFR05).",
    "CustomerRepository": "Customer repository (slide A05: a Repository handles persistence).",
    "ProductRepository": "Product repository, all_products() of slide A06.",
    "CartRepository": "Cart repository (slide A05: CartRepository).",
    "OrderRepository": "Order repository, find_order() of slide A06 (slide A05: OrderRepository).",
    "Database": "SQLite database ecom.db (Infrastructure layer, slide A05).",
    "SqliteCustomerRepository": "CustomerRepository implemented with SQLite (slide A05: Repository).",
    "SqliteProductRepository": "ProductRepository implemented with SQLite (slide A06: Product Database).",
    "SqliteCartRepository": "CartRepository implemented with SQLite (slide A05).",
    "SqliteOrderRepository": "OrderRepository implemented with SQLite (slide A06: Order Database).",
    "VectorIndex": "Vector index with the cosine_similarity of slide A06 (Vector Index).",
    "ToolCall": "One tool call chosen by Gemma 4 (tool calling).",
    "LlmReply": "Reply of the language model: text content or a list of tool calls.",
    "LlmClient": "Interface to the AI model, so Gemma can be replaced without touching services (NFR04).",
    "SpeechClient": "Interface to the speech-recognition service (slide A06: Speech-to-Text).",
    "WhisperClient": "Calls the self-hosted Whisper server to turn speech into text (slide A06: Speech-to-Text).",
    "GemmaClient": "Calls Gemma 4 through the OpenAI-compatible API (Chapter 3: AI in e-commerce).",
    "CommonQuery": "Common query representation for text, voice and image (slide A06).",
    "SearchResult": "One search result with its partial scores (slide A06).",
    "QueryService": "QueryService of slide A06: text_query, voice_query, image_query.",
    "SpeechService": "SpeechService of slide A06: transcribe(audio).",
    "ImageService": "ImageService of slide A06: image to feature vector f(I).",
    "RankingService": "RankingService of slide A06: S = a*Stext + b*Simage + c*Sbusiness.",
    "SearchService": "SearchService of slide A06: retrieve candidates, then rank them.",
    "CartService": "Application service that manages the cart (slide A05: Application Service).",
    "CheckoutService": "CheckoutService.checkout(cartID) of slide A05: coordinates the checkout.",
    "OrderService": "Order service: lookups check ownership (slide A05, NFR01).",
    "ProductService": "Product management for the administrator (use case UC12).",
    "AssistantReply": "Answer of the shopping assistant.",
    "AssistantService": "Shopping assistant: Gemma 4 picks a tool, the service runs it (Chapter 3).",
    "SearchController": "Search controller (slide A05: a Controller receives requests).",
    "CartController": "Cart controller (slide A05).",
    "CheckoutController": "CheckoutController of slide A05.",
    "OrderController": "Order controller (slide A05).",
    "AdminController": "Administration controller: paintings and order states (UC12, UC13).",
    "AssistantController": "Controller of the AI shopping assistant (UC10).",
    "SessionManager": "Demo login session: the customer id always comes from the session (NFR01).",
    "WebServer": "Web server of the Presentation layer: routes HTTP requests to controllers (slide A05).",
    "EcomApplication": "Entry point that wires the layers, like main.py in slide A06.",
}
_STRING = re.compile(r'"(?:\\.|[^"\\])*"')
_COMMENT = re.compile(r"//[^\n]*")
_TOKEN = re.compile(r"\b[A-Z][A-Za-z0-9_]*\b")


def many(mult):
    return mult.split("..")[-1] == "*"


def fields_of(c):
    """Attributes followed by association ends navigable from this class."""
    result = [(a["name"], a["type"], False) for a in c["attrs"]]
    for a in model.DESIGN_ASSOCIATIONS:
        if a["src"] == c["name"]:
            if many(a["mult"]):
                result.append((a["role"], f"List<{a['dst']}>", True))
            else:
                result.append((a["role"], a["dst"], False))
    return result


def ancestors(c):
    """Superclass chain and implemented interfaces, nearest first."""
    seen, todo = [], [c]
    while todo:
        cur = todo.pop(0)
        parents = ([cur["extends"]] if cur["extends"] else []) + cur["implements"]
        for p in parents:
            parent = model.DESIGN_BY_NAME.get(p)
            if parent and parent not in seen:
                seen.append(parent)
                todo.append(parent)
    return seen


def signature_key(o):
    return o["name"], tuple(t for _, t in o["params"])


def overrides(c, o):
    key = signature_key(o)
    return any(signature_key(p) == key for a in ancestors(c) for p in a["ops"] if p["name"] != a["name"])


def imports_for(c, field_list):
    text = " ".join(t for _, t, _ in field_list)
    for o in c["ops"]:
        text += " " + " ".join(t for _, t in o["params"]) + " " + (o["ret"] or "")
        if o["body"]:
            text += " " + _COMMENT.sub("", _STRING.sub('""', o["body"]))
    text += " " + " ".join(filter(None, [c["extends"]] + c["implements"]))
    if any(is_list for _, _, is_list in field_list):
        text += " ArrayList"
    result = set()
    for token in set(_TOKEN.findall(text)):
        if token in JDK:
            result.add(JDK[token])
        elif token in model.DESIGN_BY_NAME and token != c["name"]:
            other = model.DESIGN_BY_NAME[token]
            if other["package"] != c["package"]:
                result.add(f"{model.BASE_PACKAGE}.{other['package']}.{token}")
    return sorted(result)


def javadoc(c):
    return f"/**\n * {DOCS[c['name']]}\n * {HEADER}\n */"


def params(o):
    return ", ".join(f"{t} {n}" for n, t in o["params"])


def body_lines(body, indent):
    lines = body.strip("\n").splitlines()
    return [(" " * indent + line) if line.strip() else "" for line in lines]


def method(c, o, interface=False):
    out = []
    is_ctor = o["name"] == c["name"]
    if interface:
        return [f"    {o['ret']} {o['name']}({params(o)});"]
    if not is_ctor and overrides(c, o):
        out.append("    @Override")
    mods = [VIS[o["vis"]]]
    if o["abstract"]:
        mods.append("abstract")
    if o["static"]:
        mods.append("static")
    mods = " ".join(m for m in mods if m)
    head = f"{mods} {o['name']}({params(o)})" if is_ctor else f"{mods} {o['ret']} {o['name']}({params(o)})"
    if o["abstract"]:
        return out + [f"    {head};"]
    out.append(f"    {head} {{")
    if o["body"]:
        out += body_lines(o["body"], 8)
    else:
        out.append(f'        throw new UnsupportedOperationException("TODO: {o["name"]}");')
    out.append("    }")
    return out


VALUE_CLASSES = {"CommonQuery", "SearchResult"}
READ_ONLY = {"ToolCall", "LlmReply", "AssistantReply"}


def wants_accessors(c):
    return c["package"].startswith("domain.") or c["name"] in VALUE_CLASSES | READ_ONLY


def accessors(c, field_list):
    taken = {o["name"] for o in c["ops"]}
    blocks = []
    for name, type_, is_list in field_list:
        cap = name[0].upper() + name[1:]
        if f"get{cap}" not in taken:
            blocks.append([f"    public {type_} get{cap}() {{", f"        return {name};", "    }"])
        if not is_list and f"set{cap}" not in taken and c["name"] not in READ_ONLY:
            blocks.append([f"    public void set{cap}({type_} {name}) {{", f"        this.{name} = {name};", "    }"])
    return blocks


def render(c):
    pkg = f"{model.BASE_PACKAGE}.{c['package']}"
    out = [f"package {pkg};", ""]
    if c["kind"] == "enum":
        out += [javadoc(c), f"public enum {c['name']} {{", "    " + ", ".join(c["literals"]), "}"]
        return "\n".join(out) + "\n"
    field_list = fields_of(c)
    imports = imports_for(c, field_list)
    if imports:
        out += [f"import {i};" for i in imports] + [""]
    out.append(javadoc(c))
    if c["kind"] == "interface":
        out.append(f"public interface {c['name']} {{")
        blocks = [method(c, o, interface=True) for o in c["ops"]]
    else:
        head = "public abstract class" if c["abstract"] else "public class"
        decl = f"{head} {c['name']}"
        if c["extends"]:
            decl += f" extends {c['extends']}"
        if c["implements"]:
            decl += " implements " + ", ".join(c["implements"])
        out.append(decl + " {")
        blocks = []
        if field_list:
            blocks.append([f"    private {t} {n}" + (" = new ArrayList<>();" if is_list else ";")
                           for n, t, is_list in field_list])
        ctors = [o for o in c["ops"] if o["name"] == c["name"]]
        if ctors and c["package"].startswith("domain.") and not any(not o["params"] for o in ctors):
            blocks.append([f"    public {c['name']}() {{", "    }"])
        blocks += [method(c, o) for o in ctors]
        blocks += [method(c, o) for o in c["ops"] if o["name"] != c["name"]]
        if wants_accessors(c):
            blocks += accessors(c, field_list)
    for i, block in enumerate(blocks):
        if i:
            out.append("")
        out += block
    out.append("}")
    return "\n".join(out) + "\n"


def path_of(c):
    return SRC / Path(*model.BASE_PACKAGE.split(".")) / Path(*c["package"].split(".")) / f"{c['name']}.java"


def write_tree():
    base = SRC / Path(*model.BASE_PACKAGE.split("."))
    lines = [model.BASE_PACKAGE.replace(".", "/") + "/"]

    def walk(folder, prefix):
        entries = sorted([p for p in folder.iterdir() if p.is_dir()]) + \
            sorted([p for p in folder.iterdir() if p.suffix == ".java"])
        for i, p in enumerate(entries):
            last = i == len(entries) - 1
            lines.append(prefix + ("└── " if last else "├── ") + p.name + ("/" if p.is_dir() else ""))
            if p.is_dir():
                walk(p, prefix + ("    " if last else "│   "))

    walk(base, "")
    (BUILD / "code_tree_generated.txt").write_text("\n".join(lines) + "\n")


def main():
    shutil.rmtree(SRC, ignore_errors=True)
    BUILD.mkdir(exist_ok=True)
    sources = {}
    for c in model.DESIGN:
        if c["kind"] == "view":
            continue  # browser components live in demo/web/js
        text = render(c)
        target = path_of(c)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        sources[c["name"]] = text
    write_tree()
    print(f"Generated {len(sources)} Java files in {SRC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
