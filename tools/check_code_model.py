"""Checks that the demo code matches the design model of tools/model.py (Chapter 5: code follows the model).

Java (demo/src/main/java): every DESIGN class exists in its package with the same kind, superclass, interfaces,
fields (attributes + association roles, same types), operations (same parameter names and types, return type,
visibility, static/abstract) and no public method outside the model except the generator's accessors.
JavaScript (demo/web/js): every view operation is defined in the view's file (SearchUI -> search-ui.js).
Database: the tables and columns of demo/data/ecom.db (or the schema script) are exactly TABLES, and every
identifier in the SQL strings of the repositories is a model table or column.
Also lists the DESIGN_DEPENDENCIES_44 found in the code and the dependencies between layers.

Usage: python3 tools/check_code_model.py   (exit code 1 when something does not match)
"""
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import model  # noqa: E402
from gen_java import READ_ONLY, fields_of, wants_accessors  # noqa: E402

DEMO = ROOT / "demo"
SRC = DEMO / "src" / "main" / "java" / Path(*model.BASE_PACKAGE.split("."))
VIS = {"+": "public", "-": "private", "#": "protected", "~": ""}
MODIFIERS = {"public", "private", "protected", "static", "final", "abstract", "synchronized", "default",
             "transient", "volatile"}
SQL_KEYWORDS = {"SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "NULL", "IS", "IN", "ORDER", "BY", "DESC", "ASC",
                "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE", "JOIN", "ON", "PRAGMA", "LIMIT", "AS"}
SQLITE_NAMES = {"sqlite_master", "foreign_keys", "type", "table"}
failures, notes = [], []


def fail(text):
    failures.append(text)
    print("FAIL  " + text)


def norm(type_):
    return re.sub(r"\s+", "", type_ or "")


# ------------------------------------------------------------------ Java parsing
def strip_java(text):
    """Removes comments, string and char literals so that braces and semicolons are structural."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    return re.sub(r"'(?:\\.|[^'\\])'", "''", text)


def members(body):
    """Splits a class body into depth-1 statements (';') and block headers ('{')."""
    result, buf, depth = [], "", 0
    for ch in body:
        if depth == 0 and ch == "{":
            result.append(("block", buf.strip()))
            buf, depth = "", 1
        elif depth == 0 and ch == ";":
            result.append(("stmt", buf.strip()))
            buf = ""
        elif depth > 0:
            depth += {"{": 1, "}": -1}.get(ch, 0)
        else:
            buf += ch
    return result


def split_params(text):
    depth, cur, out = 0, "", []
    for ch in text:
        depth += ch == "<"
        depth -= ch == ">"
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [p.strip() for p in out if p.strip()]


def parse_param(text):
    text = re.sub(r"@\w+\s*", "", text).replace("final ", "").strip()
    type_, name = text.rsplit(None, 1)
    return name, norm(type_)


METHOD = re.compile(r"^(?P<mods>(?:(?:public|private|protected|static|final|abstract|synchronized|default)\s+)*)"
                    r"(?:<[^>]+>\s+)?(?:(?P<ret>[\w.<>\[\], ?]+?)\s+)?(?P<name>\w+)\s*"
                    r"\((?P<params>.*)\)\s*(?:throws\s+[\w.,\s]+)?$", re.S)


def parse_class(path, kind):
    text = strip_java(path.read_text())
    head = re.search(r"public\s+(abstract\s+)?(class|interface|enum)\s+(\w+)"
                     r"(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w.,\s]+?))?\s*\{", text)
    info = dict(package=re.search(r"^package\s+([\w.]+);", text, re.M).group(1), abstract=bool(head.group(1)),
                kind=head.group(2), name=head.group(3), extends=head.group(4),
                implements=[i.strip() for i in (head.group(5) or "").split(",") if i.strip()],
                fields={}, static_fields=[], methods=[], literals=[], source=text)
    body = text[head.end():text.rstrip().rfind("}")]
    if info["kind"] == "enum":
        info["literals"] = [x.strip() for x in body.split(";")[0].split(",") if x.strip()]
        return info
    for what, header in members(body):
        header = re.sub(r"@\w+(\([^)]*\))?\s*", "", header).strip()
        if not header or header in ("static",) or header.startswith(")"):
            continue
        before_eq = header.split("=", 1)[0].strip() if re.match(r"^[^(]*=", header) else None
        if before_eq is not None or (what == "stmt" and "(" not in header):
            declaration = before_eq if before_eq is not None else header
            words = declaration.split()
            mods = [w for w in words if w in MODIFIERS]
            rest = " ".join(w for w in words if w not in MODIFIERS)
            type_, name = rest.rsplit(None, 1)
            if "static" in mods:
                info["static_fields"].append(name)
            else:
                info["fields"][name] = dict(type=norm(type_), mods=mods)
            continue
        match = METHOD.match(header)
        if not match:
            continue
        mods = match.group("mods").split()
        if kind == "interface" and "private" not in mods:
            mods += ["public", "abstract"] if what == "stmt" and "default" not in mods else ["public"]
        info["methods"].append(dict(name=match.group("name"), ret=norm(match.group("ret")), mods=mods,
                                    params=[parse_param(p) for p in split_params(match.group("params"))],
                                    abstract="abstract" in mods or (what == "stmt" and kind != "interface")))
    return info


# ------------------------------------------------------------------ Java checks
def check_class(c):
    path = SRC / Path(*c["package"].split(".")) / f"{c['name']}.java"
    label = f"{c['package']}.{c['name']}"
    if not path.exists():
        fail(f"{label}: file {path.relative_to(ROOT)} is missing")
        return 0, 0, []
    code = parse_class(path, c["kind"])
    errors_before = len(failures)
    if code["package"] != f"{model.BASE_PACKAGE}.{c['package']}":
        fail(f"{label}: package is {code['package']}")
    if code["kind"] != c["kind"] or code["abstract"] != c["abstract"]:
        fail(f"{label}: kind is {'abstract ' if code['abstract'] else ''}{code['kind']}")
    if (code["extends"] or None) != c["extends"] or sorted(code["implements"]) != sorted(c["implements"]):
        fail(f"{label}: extends {code['extends']} implements {code['implements']}")
    if c["kind"] == "enum":
        if code["literals"] != c["literals"]:
            fail(f"{label}: literals {code['literals']} != {c['literals']}")
        print(f"{'OK  ' if len(failures) == errors_before else 'FAIL'}  {label:<55} literals {len(c['literals']):>2}")
        return len(c["literals"]), 0, []
    field_list = fields_of(c) if c["kind"] != "interface" else []
    for name, type_, _ in field_list:
        found = code["fields"].get(name)
        if not found:
            fail(f"{label}: field {name}: {type_} is missing")
        elif found["type"] != norm(type_) or "private" not in found["mods"]:
            fail(f"{label}: field {name} is {' '.join(found['mods'])} {found['type']}, model says private {type_}")
    extra_fields = sorted(set(code["fields"]) - {n for n, _, _ in field_list})
    expected = {}
    for o in c["ops"]:
        expected[(o["name"], tuple(norm(t) for _, t in o["params"]))] = o
    for key, o in expected.items():
        found = [m for m in code["methods"] if (m["name"], tuple(t for _, t in m["params"])) == key]
        sig = f"{o['name']}({', '.join(f'{n}: {t}' for n, t in o['params'])})"
        if not found:
            fail(f"{label}: operation {sig} is missing")
            continue
        m = found[0]
        if [n for n, _ in m["params"]] != [n for n, _ in o["params"]]:
            fail(f"{label}: {sig} has parameter names {[n for n, _ in m['params']]}")
        is_ctor = o["name"] == c["name"]
        if not is_ctor and m["ret"] != norm(o["ret"]):
            fail(f"{label}: {sig} returns {m['ret']}, model says {o['ret']}")
        if VIS[o["vis"]] and VIS[o["vis"]] not in m["mods"]:
            fail(f"{label}: {sig} is not {VIS[o['vis']]}")
        if o["static"] != ("static" in m["mods"]) or (o["abstract"] and not m["abstract"]):
            fail(f"{label}: {sig} static/abstract differs from the model")
    allowed = set(expected)
    if wants_accessors(c):
        for name, type_, is_list in field_list:
            cap = name[0].upper() + name[1:]
            allowed.add((f"get{cap}", ()))
            if not is_list and c["name"] not in READ_ONLY:
                allowed.add((f"set{cap}", (norm(type_),)))
    if c["package"].startswith("domain."):
        allowed.add((c["name"], ()))
    for m in code["methods"]:
        key = (m["name"], tuple(t for _, t in m["params"]))
        if "public" in m["mods"] and key not in allowed:
            fail(f"{label}: public method {m['name']}({', '.join(t for _, t in m['params'])}) is not in the model")
    if extra_fields:
        notes.append(f"{label}: private helper field(s) {', '.join(extra_fields)}")
    ok = len(failures) == errors_before
    print(f"{'OK  ' if ok else 'FAIL'}  {label:<55} fields {len(field_list):>2}  operations {len(expected):>2}")
    return len(field_list), len(expected), code["source"]


def kebab(name):
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "-", name).lower()


def check_views():
    found_files = {p.stem: p for p in (DEMO / "web").rglob("*.js")}
    checked = 0
    for c in model.DESIGN:
        if c["kind"] != "view":
            continue
        path = found_files.get(kebab(c["name"]))
        if not path:
            fail(f"view {c['name']}: web/js/{kebab(c['name'])}.js is missing")
            continue
        text = path.read_text()
        missing = []
        for o in c["ops"]:
            n = o["name"]
            pattern = (rf"function\s+{n}\s*\(|\b{n}\s*[:=]\s*(async\s*)?(function\b|\([^)]*\)\s*=>|\w+\s*=>)"
                       rf"|^\s*(async\s+)?{n}\s*\([^)]*\)\s*\{{")
            if not re.search(pattern, text, re.M):
                missing.append(n)
        checked += len(c["ops"])
        for n in missing:
            fail(f"view {c['name']}: function {n} is not defined in {path.relative_to(ROOT)}")
        if not missing:
            print(f"OK    view {c['name']:<50} {path.relative_to(DEMO)}  ({len(c['ops'])} functions)")
    return checked


# ------------------------------------------------------------------ database
def check_database():
    db_path = DEMO / "data" / "ecom.db"
    connection = sqlite3.connect(":memory:")
    source = "db/ecom_schema_sqlite.sql"
    if db_path.exists():
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        source = "data/ecom.db"
    else:
        connection.executescript((DEMO / "db" / "ecom_schema_sqlite.sql").read_text())
    tables = [r[0] for r in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    model_tables = {t["name"]: t for t in model.TABLES}
    if sorted(tables) != sorted(model_tables):
        fail(f"database {source}: tables {sorted(set(tables) ^ set(model_tables))} differ from the model")
    columns = 0
    for name, table in model_tables.items():
        if name not in tables:
            continue
        info = connection.execute(f"PRAGMA table_info({name})").fetchall()
        actual = [row[1] for row in info]
        wanted = [c["name"] for c in table["columns"]]
        columns += len(wanted)
        if actual != wanted:
            fail(f"table {name}: columns {actual} != model {wanted}")
            continue
        for row, column in zip(info, table["columns"]):
            declared = row[2].lower()
            expected = column["type"]
            if not declared.startswith(expected) or (not column["nullable"] and not row[3]):
                fail(f"table {name}.{column['name']}: declared {row[2]} notnull={row[3]}")
        fks = {(r[3], f"{r[2]}.{r[4]}") for r in connection.execute(f"PRAGMA foreign_key_list({name})")}
        wanted_fks = {(c["name"], c["fk"]) for c in table["columns"] if c["fk"]}
        if fks != wanted_fks:
            fail(f"table {name}: foreign keys {sorted(fks)} != model {sorted(wanted_fks)}")
    print(f"OK    database {source}: {len(tables)} tables, {columns} columns, keys and foreign keys as in TABLES"
          if not any(f.startswith(("table", "database")) for f in failures) else "FAIL  database")
    return len(tables), columns


def check_sql():
    names = {t["name"] for t in model.TABLES} | {c["name"] for t in model.TABLES for c in t["columns"]}
    folder = SRC / "infrastructure" / "repository" / "sqlite"
    used, statements = set(), 0
    for path in sorted(folder.glob("*.java")):
        text = re.sub(r"//[^\n]*", "", path.read_text())
        for literal in re.findall(r'"((?:\\.|[^"\\])*)"', text):
            body = re.sub(r"'[^']*'", "", literal)
            tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", body)
            if not tokens or not re.fullmatch(r"[\sA-Za-z0-9_.,()=<>*?;!-]*", body):
                continue
            if not all(t in SQL_KEYWORDS or re.fullmatch(r"[a-z_][a-z0-9_.]*", t) for t in tokens):
                continue
            statements += any(t in SQL_KEYWORDS for t in tokens)
            for token in tokens:
                for part in ([] if token in SQL_KEYWORDS else token.split(".")):
                    if part not in names and part not in SQLITE_NAMES:
                        fail(f"SQL in {path.name}: '{part}' is not a table or column of the model")
                    used.add(part)
    unused = sorted(names - used)
    print(f"OK    SQL of the repositories: {statements} statements, {len(used & names)} model identifiers used")
    if unused:
        notes.append(f"model columns never named in repository SQL: {', '.join(unused)}")
    return statements


# ------------------------------------------------------------------ dependencies
def check_dependencies(sources):
    present = 0
    pairs = [(a, b, s) for a, b, s in model.DESIGN_DEPENDENCIES_44
             if model.DESIGN_BY_NAME[a]["kind"] != "view" and model.DESIGN_BY_NAME[b]["kind"] != "view"]
    for client, supplier, stereotype in pairs:
        text = sources.get(client, "")
        pattern = rf"new\s+{supplier}\s*\(" if stereotype == "create" else rf"\b{supplier}\b"
        if re.search(pattern, text):
            present += 1
        else:
            fail(f"dependency {client} -> {supplier} «{stereotype}» is not used in the code")
    print(f"OK    {present}/{len(pairs)} Java dependencies of DESIGN_DEPENDENCIES_44 found in the code")
    layer_of = {sub: layer for layer, _, subs in model.PACKAGE_GROUPS for sub in subs}
    shared = model.DOMAIN_MODEL[0]
    # every layer may use the shared domain model; the domain model uses no layer
    allowed = set(model.LAYER_DEPENDENCIES) | {(layer, shared) for layer, _, _ in model.LAYERS}
    edges = {}
    for path in SRC.rglob("*.java"):
        package = path.parent.relative_to(SRC).as_posix().replace("/", ".")
        for imported in re.findall(rf"^import\s+{re.escape(model.BASE_PACKAGE)}\.([\w.]+)\.\w+;",
                                   path.read_text(), re.M):
            a, b = layer_of.get(package), layer_of.get(imported)
            if a and b and a != b:
                edges.setdefault((a, b), set()).add(path.stem)
    for (a, b), files in sorted(edges.items()):
        # Presentation -> Data is only the composition root, which creates the data-layer objects once.
        composition_root = (a, b) == ("Presentation", "Data") and files <= {"EcomApplication"}
        line = f"layer {a} -> {b}: {len(files)} file(s)"
        if (a, b) not in allowed and not composition_root:
            fail(line + f" against the layer rule ({', '.join(sorted(files))})")
        elif composition_root:
            notes.append(line + " (EcomApplication, the composition root)")
        else:
            print(f"OK    {line}")


def main():
    print("== Java classes of DESIGN (tools/model.py) ==")
    classes = fields = operations = 0
    sources = {}
    for c in model.DESIGN:
        if c["kind"] == "view":
            continue
        f, o, source = check_class(c)
        classes += 1
        fields += f
        operations += o
        sources[c["name"]] = source
    print("== Browser views (web/js) ==")
    view_ops = check_views()
    print("== Database ==")
    tables, columns = check_database()
    statements = check_sql()
    print("== Dependencies ==")
    check_dependencies(sources)
    for note in notes:
        print("NOTE  " + note)
    print(f"\nModel check: {classes} Java classes, {fields} fields, {operations} operations, {view_ops} view "
          f"functions, {tables} tables, {columns} columns, {statements} SQL statements -> "
          f"{'all match the model' if not failures else str(len(failures)) + ' problem(s)'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
