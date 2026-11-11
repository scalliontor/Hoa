#!/usr/bin/env python3
"""Builds showcase/index.html, the defense showcase of the essay "Họa." (served by GitHub Pages from the repo root).

The page is one static HTML file with inline CSS and JS. Everything it shows is read from the repository when it
is built, nothing is typed twice:
  tools/model.py                 requirements, use cases, classes, operations, tables, foreign keys
  figures/vp/README.md           the list of Visual Paradigm figures with their descriptions
  report/chapters/*.tex          sections, figure order and captions, problem/goal/scope/spec/rule tables
  build/report/tieuluan_V*.pdf   page of every section and figure (named destinations of the PDF)
  build/test_results.txt         test results; demo/tests/java for the line of every test
  build/eval/*.json              AI evaluation; build/sql_validation.txt; python3 tools/check_code_model.py
  demo/src, demo/web/js          line numbers of classes, methods, routes and view functions (GitHub #L links)
  demo/db/*.sql                  the schema and seed, loaded into an in-memory SQLite database

The generator fails (exit code 1) when a referenced file, figure, class, method, test, route or table is missing,
and it verifies every link it writes. Standard library only; the output is deterministic.

Usage: python3 tools/build_showcase.py
"""
import html
import json
import re
import sqlite3
import struct
import subprocess
import sys
import urllib.parse
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "showcase" / "index.html"
REPO = "https://github.com/scalliontor/Hoa"
BLOB = REPO + "/blob/main/"
TREE = REPO + "/tree/main/"
sys.path.insert(0, str(ROOT / "tools"))
import model  # noqa: E402

JAVA_ROOT = "demo/src/main/java/" + model.BASE_PACKAGE.replace(".", "/") + "/"
TEST_ROOT = "demo/tests/java"
JS_ROOT = "demo/web/js/"
SCHEMA = "demo/db/ecom_schema_sqlite.sql"
SEED = "demo/db/seed.sql"
WEBSERVER = JAVA_ROOT + "presentation/web/WebServer.java"
WARNINGS = []


class ShowcaseError(Exception):
    pass


def need(condition, message):
    if not condition:
        raise ShowcaseError(message)
    return condition


def warn(message):
    if message not in WARNINGS:
        WARNINGS.append(message)


def E(value):
    return html.escape(str(value), quote=True)


# ---------------------------------------------------------------------------------------------------- files, links
def repo_path(rel):
    path = ROOT / rel
    need(path.exists(), f"referenced file not found: {rel}")
    return path


def read(rel):
    return repo_path(rel).read_text(encoding="utf-8")


def lines_of(rel):
    return read(rel).split("\n")


class Links:
    """Every link the page contains, checked again after the page is written."""

    def __init__(self):
        self.rel = set()        # repository paths linked relatively (../path)
        self.blob = {}          # (path, start, end) -> text expected at the start line
        self.tree = set()       # directories linked on GitHub

    def file(self, rel):
        repo_path(rel)
        self.rel.add(rel)
        return "../" + urllib.parse.quote(rel)

    def code(self, rel, start, end=None, expect=None):
        lines = lines_of(rel)
        need(1 <= start <= len(lines), f"{rel}: line {start} out of range")
        if end is not None:
            need(start <= end <= len(lines), f"{rel}: lines {start}-{end} out of range")
        if expect is not None:
            need(expect in lines[start - 1], f"{rel}:{start} does not contain {expect!r}")
        self.blob[(rel, start, end)] = lines[start - 1]
        anchor = f"#L{start}" + (f"-L{end}" if end and end != start else "")
        return BLOB + urllib.parse.quote(rel) + anchor

    def whole(self, rel):
        repo_path(rel)
        self.blob[(rel, None, None)] = None
        return BLOB + urllib.parse.quote(rel)

    def directory(self, rel):
        need((ROOT / rel).is_dir(), f"referenced directory not found: {rel}")
        self.tree.add(rel)
        return TREE + urllib.parse.quote(rel)


LINKS = Links()


def find_line(rel, pattern, start=1, regex=False):
    """1-based number of the first line (from start) that contains pattern; fails loudly."""
    for number, line in enumerate(lines_of(rel), 1):
        if number < start:
            continue
        if (re.search(pattern, line) if regex else pattern in line):
            return number
    raise ShowcaseError(f"{rel}: {pattern!r} not found")


def png_size(rel):
    with open(repo_path(rel), "rb") as fh:
        head = fh.read(24)
    need(head[:8] == b"\x89PNG\r\n\x1a\n", f"{rel} is not a PNG file")
    return struct.unpack(">II", head[16:24])


def jpeg_size(rel):
    data = repo_path(rel).read_bytes()
    i = 2
    while i < len(data):
        need(data[i] == 0xFF, f"{rel}: bad JPEG marker")
        marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + length
    raise ShowcaseError(f"{rel}: no JPEG size found")


def git(*args):
    try:
        done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=False)
    except OSError:
        return None
    return done.stdout.decode("utf-8", "replace") if done.returncode == 0 else None


# ------------------------------------------------------------------------------------------------------ LaTeX
def brace(text, i):
    """Content of the {...} group starting at text[i] (spaces skipped) and the index after it."""
    while text[i] in " \t\n":
        i += 1
    need(text[i] == "{", f"expected '{{' in {text[i:i + 40]!r}")
    depth, j = 0, i
    while j < len(text):
        if text[j] == "\\":
            j += 2
            continue
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
        j += 1
    raise ShowcaseError(f"unbalanced braces in {text[i:i + 60]!r}")


def bracket(text, i):
    """Optional [..] argument at text[i]: (content or None, index after it)."""
    if i < len(text) and text[i] == "[":
        depth, j = 0, i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            elif text[j] == "]" and depth == 0:
                return text[i + 1:j], j + 1
            j += 1
    return None, i


def tex_macros():
    """Zero-argument macros defined by the generated files of the report (\\nFR, \\authorName, ...)."""
    macros = {}
    files = sorted((ROOT / "report" / "generated").glob("*.tex")) + [ROOT / "report" / "author.tex"]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\\(?:newcommand|renewcommand|providecommand)\*?\{?\\([A-Za-z]+)\}?(?=\{)", text):
            value, _ = brace(text, m.end())
            macros.setdefault(m.group(1), value)
    return macros


MACROS = tex_macros()
MATH = {r"\rightarrow": "→", r"\Rightarrow": "⇒", r"\ge": "≥", r"\le": "≤", r"\geq": "≥", r"\leq": "≤",
        r"\times": "×", r"\varnothing": "∅", r"\dots": "…", r"\ldots": "…", r"\cdot": "·", r"\alpha": "α",
        r"\beta": "β", r"\gamma": "γ", r"\infty": "∞", r"\boldsymbol": "", r"\mathrm": "", r"\text": ""}


class Essay:
    """Sections, labels and figures of report/main.tex, numbered as LaTeX numbers them."""

    def __init__(self):
        main = read("report/main.tex")
        self.inputs = re.findall(r"\\input\{chapters/([\w]+)\}", main)
        self.chapter_files = [f for f in self.inputs if re.match(r"ch\d", f)]
        self.sections = []          # dict(level, number, title, labels, file, line, dest)
        self.labels = {}            # label -> number
        self.figures = []           # every figure block in document order
        self.vp = {}                # vp id -> figure info
        self.demo = {}              # screenshot name -> figure info
        chapter = 0
        for name in self.inputs:
            rel = f"report/chapters/{name}.tex"
            numbered = name in self.chapter_files
            self._scan(rel, numbered and chapter + 1 or None)
            if numbered:
                chapter += 1

    def _scan(self, rel, chapter):
        text = read(rel)
        line_at = _line_index(text)
        if chapter is not None:          # equations are numbered per chapter, like figures
            eq = 0
            for m in re.finditer(r"\\begin\{(equation|align)\}(.*?)\\end\{\1\}", text, re.S):
                for part in (m.group(2).split("\\\\") if m.group(1) == "align" else [m.group(2)]):
                    if "\\nonumber" in part or "\\notag" in part:
                        continue
                    eq += 1
                    for label in re.findall(r"\\label\{([^}]*)\}", part):
                        self.labels[label] = f"{chapter}.{eq}"
        sec = sub = fig = 0
        current = None
        for m in re.finditer(r"\\(chapter|section|subsection)(\*?)\{|\\landscapefig\{|\\begin\{figure\}", text):
            kind = m.group(1)
            line = line_at(m.start())
            if kind and m.group(2) != "*" and chapter is not None:
                title, end = brace(text, m.end() - 1)
                labels = re.findall(r"\\label\{([^}]*)\}", text[end:text.find("\n", end)])
                if kind == "chapter":
                    number, dest = str(chapter), f"chapter.{chapter}"
                elif kind == "section":
                    sec, sub = sec + 1, 0
                    number, dest = f"{chapter}.{sec}", f"section.{chapter}.{sec}"
                else:
                    sub += 1
                    number, dest = f"{chapter}.{sec}.{sub}", f"subsection.{chapter}.{sec}.{sub}"
                info = dict(level=kind, number=number, title=clean_tex(title, plain=True), labels=labels,
                            file=rel, line=line, dest=dest)
                self.sections.append(info)
                for label in labels:
                    self.labels[label] = number
                current = info
            elif m.group(0).startswith("\\landscapefig"):
                fid, i = brace(text, m.end() - 1)
                short, i = brace(text, i)
                long_, i = brace(text, i)
                labels, i = brace(text, i)
                fig += 1
                self._figure(rel, chapter, fig, current, line, [("vp", fid, short, long_, labels)])
            elif m.group(0).startswith("\\begin{figure"):
                end = text.find("\\end{figure}", m.end())
                block = text[m.end():end]
                items, graphics = [], re.finditer(r"\\(vpfig|demofig)\{([^}]*)\}", block)
                pending = [(g.group(1), g.group(2)) for g in graphics]
                for c in re.finditer(r"\\caption", block):
                    short, i = bracket(block, c.end())
                    long_, i = brace(block, i)
                    rest = block[i:i + 400]
                    labels = " ".join(re.findall(r"\\label\{[^}]*\}", rest.split("\\caption")[0]))
                    need(pending, f"{rel}:{line}: caption without a figure")
                    kind_, fid = pending.pop(0)
                    items.append(("vp" if kind_ == "vpfig" else "demo", fid, short or long_, long_, labels))
                    fig += 1
                if items:
                    self._figure(rel, chapter, fig - len(items) + 1, current, line, items)

    def _figure(self, rel, chapter, first_number, section, line, items):
        block = len(self.figures)
        for k, (kind, fid, short, long_, labels) in enumerate(items):
            info = dict(kind=kind, id=fid, chapter=chapter, number=f"{chapter}.{first_number + k}" if chapter else None,
                        raw_short=short, raw_caption=_strip_src(long_), raw_caption_full=long_, section=section,
                        file=rel, line=line,
                        block=block)
            for label in re.findall(r"\\label\{([^}]*)\}", labels):
                self.labels[label] = info["number"]
            (self.vp if kind == "vp" else self.demo)[fid] = info
        self.figures.append(items)

    def finish(self):
        """Cleans the captions once every label of the essay is known (captions may contain \\ref)."""
        for info in list(self.vp.values()) + list(self.demo.values()):
            info["short"] = clean_tex(info["raw_short"], plain=True)
            info["caption"] = clean_tex(info["raw_caption"])

    def section(self, number):
        for s in self.sections:
            if s["number"] == number:
                return s
        raise ShowcaseError(f"section {number} not found in the essay")

    def section_titled(self, pattern, level="subsection"):
        for s in self.sections:
            if s["level"] == level and re.search(pattern, s["title"]):
                return s
        raise ShowcaseError(f"no {level} of the essay matches {pattern!r}")

    def chapter_title(self, number):
        return self.section(str(number))["title"]


def _line_index(text):
    starts = [0] + [m.end() for m in re.finditer("\n", text)]

    def line_at(offset):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1
    return line_at


def _strip_src(caption):
    """Removes the trailing 'Visual Paradigm diagram figures/vp/x.png.' / 'Screenshot ...' from a caption."""
    caption = re.sub(r"\s*(Visual Paradigm diagram|Diagram|Screenshot)\s*\\(vpsrc|demosrc)\{[^}]*\}\.?", "", caption)
    return re.sub(r"\s*\\trialshot\{[^}]*\}\.?", "", caption).strip()


ESSAY = None


def clean_tex(text, plain=False):
    """LaTeX of a table cell or caption -> HTML (or plain text). Unknown commands fail loudly."""
    s = " ".join(text.split())
    s = re.sub(r"\\(small|footnotesize|normalsize|centering|noindent|par)\b\s*", "", s)
    s = re.sub(r"\\(label|needspace)\{[^}]*\}", "", s)
    s = re.sub(r"~?\\cite\{[^}]*\}", "", s)
    for _ in range(3):
        s = re.sub(r"\\([A-Za-z]+)(\{\})?(?![A-Za-z])", lambda m: MACROS.get(m.group(1), m.group(0)), s)
    s = s.replace(r"\_", "_").replace(r"\%", "%").replace(r"\#", "#").replace(r"\$", "$")
    s = s.replace(r"\&", "\x00").replace(r"\,", "\u2009").replace(r"\'e", "é").replace(r"\'a", "á")
    s = s.replace("\\\\", " ")
    if not plain:
        s = html.escape(s, quote=False)
    s = s.replace("\x00", "&amp;" if not plain else "&")

    def math(m):
        body = m.group(1)
        for key in sorted(MATH, key=len, reverse=True):
            body = body.replace(key, MATH[key])
        body = re.sub(r"\^\{?\*\}?", "*", body)
        body = re.sub(r"_\{?(\w+)\}?", (lambda x: x.group(1)) if plain else (lambda x: f"<sub>{x.group(1)}</sub>"),
                      body)
        return body.replace("{", "").replace("}", "").strip()
    s = re.sub(r"\$([^$]*)\$", math, s)
    for key in sorted(MATH, key=len, reverse=True):
        s = re.sub(re.escape(key) + r"(?![A-Za-z])", MATH[key], s)

    def ref(m):
        label = m.group(1)
        need(ESSAY is not None and label in ESSAY.labels, f"unresolved essay reference \\ref{{{label}}}")
        return ESSAY.labels[label]
    s = re.sub(r"\\ref\{([^}]*)\}", ref, s)
    tags = {"code": "code", "codex": "code", "texttt": "code", "textbf": "strong", "emph": "em", "textit": "em",
            "mbox": "", "textsc": "", "detokenize": ""}
    for _ in range(4):
        s = re.sub(r"\\(" + "|".join(tags) + r")\{([^{}]*)\}",
                   lambda m: m.group(2) if plain or not tags[m.group(1)]
                   else f"<{tags[m.group(1)]}>{m.group(2)}</{tags[m.group(1)]}>", s)
    s = s.replace("---", "—").replace("--", "–").replace("``", "“").replace("''", "”").replace("~", "\u00a0")
    s = s.replace("\\{", "{").replace("\\}", "}")
    leftover = re.findall(r"\\[A-Za-z]+", s)
    need(not leftover, f"unknown LaTeX command(s) {sorted(set(leftover))} in {text[:80]!r}")
    return re.sub(r"(?<!\\)[{}]", "", s).strip()


def longtable(rel, label):
    """Rows of the longtable with \\label{label}: list of (cells as raw LaTeX, line number)."""
    text = read(rel)
    at = text.find("\\label{" + label + "}")
    need(at >= 0, f"table {label} not found in {rel}")
    start = text.rfind("\\begin{longtable}", 0, at)
    end = text.find("\\end{longtable}", at)
    body_start = max(text.rfind("\\endhead", start, end), text.rfind("\\endlastfoot", start, end))
    need(body_start > 0, f"{label}: no \\endhead")
    body_start = text.find("\n", body_start) + 1
    stop = text.find("\\bottomrule", body_start, end)
    stop = end if stop < 0 else stop
    line_at = _line_index(text)
    rows, pos = [], body_start
    for m in re.finditer(r"\\\\[ \t]*(?:\n|$)", text[body_start:stop]):
        chunk = text[pos:body_start + m.start()]
        offset = pos + len(chunk) - len(chunk.lstrip())
        pos = body_start + m.end()
        chunk = chunk.strip()
        if not chunk or chunk.startswith("\\midrule"):
            continue
        rows.append(([c.strip() for c in re.split(r"(?<!\\)&", chunk)], line_at(offset)))
    need(rows, f"table {label} has no rows")
    return rows


def spec_rows(rel, label):
    """Rows of a use case specification (\\specrow{key}{value}) as an ordered dict key -> (value, line)."""
    text = read(rel)
    at = text.find("\\label{" + label + "}")
    need(at >= 0, f"specification {label} not found in {rel}")
    end = text.find("\\end{longtable}", at)
    line_at = _line_index(text)
    rows = {}
    for m in re.finditer(r"\\specrow\{", text[at:end]):
        key, i = brace(text, at + m.end() - 1)
        value, _ = brace(text, i)
        rows[clean_tex(key, plain=True)] = (value, line_at(at + m.start()))
    return rows


def itemize_after(rel, section_label):
    """\\item \\textbf{Title.} text  entries of the first itemize after \\label{section_label}."""
    text = read(rel)
    at = text.find("\\label{" + section_label + "}")
    need(at >= 0, f"{section_label} not found in {rel}")
    start = text.find("\\begin{itemize}", at)
    end = text.find("\\end{itemize}", start)
    line_at = _line_index(text)
    items = []
    for chunk in re.finditer(r"\\item\s+(.*?)(?=\\item\s|$)", text[start + 15:end], re.S):
        body = chunk.group(1).strip()
        title = ""
        if body.startswith("\\textbf{"):
            title, i = brace(body, 7)
            body = body[i:].strip()
        items.append(dict(title=clean_tex(title, plain=True).rstrip("."), text=clean_tex(body),
                          line=line_at(start + 15 + chunk.start())))
    return items


# --------------------------------------------------------------------------------------------------------- PDF
class Pdf:
    """Named destinations and page labels of the essay PDF (xdvipdfmx output with object streams)."""

    def __init__(self, rel):
        data = repo_path(rel).read_bytes()
        objs = {}
        for m in re.finditer(rb"(?<![0-9])(\d+) 0 obj", data):
            end = data.find(b"endobj", m.end())
            objs.setdefault(int(m.group(1)), data[m.end():end])
        for body in list(objs.values()):
            if b"/ObjStm" not in body[:600] or b"stream" not in body:
                continue
            head, _, rest = body.partition(b"stream")
            rest = rest.lstrip(b"\r\n")
            raw = zlib.decompress(rest[:int(re.search(rb"/Length (\d+)", head).group(1))])
            n = int(re.search(rb"/N (\d+)", head).group(1))
            first = int(re.search(rb"/First (\d+)", head).group(1))
            nums = list(map(int, raw[:first].split()))
            pairs = [(nums[k], nums[k + 1]) for k in range(0, 2 * n, 2)]
            for k, (number, offset) in enumerate(pairs):
                stop = pairs[k + 1][1] if k + 1 < n else len(raw) - first
                objs[number] = raw[first + offset:first + stop]
        catalog = next((b for b in objs.values() if re.search(rb"/Type\s*/Catalog", b)), None)
        need(catalog is not None, f"{rel}: no PDF catalog")

        def ref(body, key):
            m = re.search(rb"/" + key + rb"\s+(\d+) 0 R", body)
            return int(m.group(1)) if m else None
        self.dests = {}

        def walk(number):
            body = objs[number]
            kids = re.search(rb"/Kids\s*\[([^\]]*)\]", body)
            if kids:
                for kid in re.findall(rb"(\d+) 0 R", kids.group(1)):
                    walk(int(kid))
            names = re.search(rb"/Names\s*\[(.*)\]", body, re.S)
            if names:
                for name, value in re.findall(rb"\(((?:\\.|[^\\)])*)\)\s*(\d+ 0 R|\[[^\]]*\])", names.group(1)):
                    self.dests[name.decode("latin-1")] = value
        names = ref(catalog, b"Names")
        need(names and ref(objs[names], b"Dests"), f"{rel}: no named destinations")
        walk(ref(objs[names], b"Dests"))
        pages = []

        def page_walk(number):
            body = objs[number]
            if re.search(rb"/Type\s*/Pages", body):
                for kid in re.findall(rb"(\d+) 0 R", re.search(rb"/Kids\s*\[([^\]]*)\]", body).group(1)):
                    page_walk(int(kid))
            else:
                pages.append(number)
        page_walk(ref(catalog, b"Pages"))
        self.page_index = {p: k for k, p in enumerate(pages)}
        self.count = len(pages)
        self.objs = objs
        self.labels = []
        nums = re.search(rb"/PageLabels\s*<<\s*/Nums\s*\[(.*?)\]\s*>>", catalog, re.S)
        if nums:
            for start, spec in re.findall(rb"(\d+)\s*<<(.*?)>>", nums.group(1)):
                style = re.search(rb"/S\s*/(\w)", spec)
                first = re.search(rb"/St\s+(\d+)", spec)
                self.labels.append((int(start), style.group(1).decode() if style else "", int(first.group(1)) if first else 1))

    def page(self, dest):
        """0-based physical page of a named destination (None, with a warning, when the PDF does not have it)."""
        if dest not in self.dests:
            warn(f"essay PDF has no destination {dest!r}; rebuild it with report/build.sh")
            return None
        value = self.dests[dest]
        if not value.startswith(b"["):
            target = self.objs[int(value.split()[0])]
            m = re.search(rb"/D\s*(\[[^\]]*\])", target)
            value = m.group(1) if m else target
        return self.page_index[int(re.search(rb"(\d+) 0 R", value).group(1))]

    def label(self, index):
        start, style, first = max((x for x in self.labels if x[0] <= index), default=(0, "D", 1))
        number = first + index - start
        if style == "r":
            return _roman(number).lower()
        if style == "R":
            return _roman(number)
        return str(number) if style == "D" else str(index + 1)

    def figure_dests(self):
        return sorted((d for d in self.dests if d.startswith("figure.")),
                      key=lambda d: [int(x) if x.isdigit() else x for x in d.split(".")])


def _roman(n):
    out = ""
    for value, sym in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"),
                       (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out, n = out + sym, n - value
    return out


# ------------------------------------------------------------------------------------------------ source code
def mask_java(src):
    """Same text with comments and the contents of string/char literals blanked (positions kept)."""
    out, n, i = list(src), len(src), 0

    def blank(a, b):
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "
    while i < n:
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
        elif src.startswith('"""', i):
            j = src.find('"""', i + 3)
            j = n if j < 0 else j
            blank(i + 3, j)
            i = j + 3
        elif src[i] in "\"'":
            q, j = src[i], i + 1
            while j < n and src[j] != q and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            blank(i + 1, j)
            i = j + 1
        else:
            i += 1
    return "".join(out)


def mask_js(src):
    """Comments, strings, template text and regex literals blanked; ${...} code inside templates kept."""
    out, n = list(src), len(src)

    def blank(a, b):
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    def template(i):
        start = i
        while i < n:
            if src[i] == "\\":
                i += 2
                continue
            if src[i] == "`":
                blank(start, i)
                return i + 1
            if src.startswith("${", i):
                blank(start, i)
                i = code(i + 2, True)
                start = i
                continue
            i += 1
        blank(start, n)
        return n

    def code(i, nested):
        depth, prev = 0, ""
        while i < n:
            c = src[i]
            if src.startswith("//", i):
                j = src.find("\n", i)
                j = n if j < 0 else j
                blank(i, j)
                i = j
                continue
            if src.startswith("/*", i):
                j = src.find("*/", i + 2)
                j = n if j < 0 else j + 2
                blank(i, j)
                i = j
                continue
            if c in "\"'":
                j = i + 1
                while j < n and src[j] != c and src[j] != "\n":
                    j += 2 if src[j] == "\\" else 1
                blank(i + 1, j)
                i, prev = j + 1, c
                continue
            if c == "`":
                i, prev = template(i + 1), "`"
                continue
            if c == "/" and (prev == "" or prev in "(,=:[!&|?{};+-*%<>~^"):
                j, in_class = i + 1, False
                while j < n and src[j] != "\n":
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == "[":
                        in_class = True
                    elif src[j] == "]":
                        in_class = False
                    elif src[j] == "/" and not in_class:
                        break
                    j += 1
                blank(i + 1, j)
                i, prev = j + 1, "/"
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                if nested and depth == 0:
                    return i + 1
                depth -= 1
            if not c.isspace():
                prev = c
            i += 1
        return i
    code(0, False)
    return "".join(out)


def match(masked, i, open_="(", close=")"):
    depth = 0
    for j in range(i, len(masked)):
        if masked[j] == open_:
            depth += 1
        elif masked[j] == close:
            depth -= 1
            if depth == 0:
                return j
    raise ShowcaseError("unbalanced brackets in source")


def depths(masked):
    out, d = [], 0
    for ch in masked:
        out.append(d)
        if ch == "{":
            d += 1
        elif ch == "}":
            d -= 1
    return out


JAVA_KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "new", "throw", "synchronized", "try", "else",
                 "super", "this", "do", "case", "assert"}
MODIFIERS = {"public", "private", "protected", "static", "final", "abstract", "synchronized", "default", "native",
             "transient", "volatile"}


class JavaFile:
    def __init__(self, rel):
        self.rel = rel
        self.src = read(rel)
        self.masked = mask_java(self.src)
        self.line_at = _line_index(self.src)
        depth = depths(self.masked)
        self.methods = []
        for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", self.masked):
            name = m.group(1)
            if depth[m.start()] != 1 or name in JAVA_KEYWORDS:
                continue
            k = max(self.masked.rfind(c, 0, m.start()) for c in ";{}")
            head = re.sub(r"@\w+(\s*\([^)]*\))?", "", self.masked[k + 1:m.start()])
            if "=" in head or "(" in head or "." in head:
                continue
            close = match(self.masked, m.end() - 1)
            after = self.masked[close + 1:].lstrip()
            if after.startswith("throws"):
                after = after[re.search(r"[{;]", after).start():]
            if not after or after[0] not in "{;":
                continue
            words = [w for w in re.sub(r"<[^<>]*(<[^<>]*>[^<>]*)*>", " ", head).split() if w not in MODIFIERS]
            params = self.masked[m.end():close].strip()
            count = 0 if not params else len(re.split(r",(?![^<]*>)", params))
            body = self.masked.find(after[0], close)
            end = match(self.masked, body, "{", "}") if after[0] == "{" else body
            self.methods.append(dict(name=name, start=m.start(), end=end, line=self.line_at(m.start()),
                                     end_line=self.line_at(end), params=count, ctor=not words,
                                     private="private" in head.split()))

    def constants(self):
        """static final String constants of the class: name -> source text of the declaration."""
        out = {}
        for m in re.finditer(r"\bstatic\s+final\s+String\s+([A-Z_][A-Z0-9_]*)\s*=", self.masked):
            end = self.masked.find(";", m.end())
            out[m.group(1)] = (self.src[m.end():end], self.masked[m.end():end])
        return out

    def method(self, name, params=None):
        found = [x for x in self.methods if x["name"] == name and (params is None or x["params"] == params)]
        need(found, f"{self.rel}: method {name}({'' if params is None else params} params) not found")
        return found[0]

    def has(self, name):
        return any(x["name"] == name for x in self.methods)

    def class_line(self, name):
        m = re.search(r"(?m)^\s*(?:public\s+)?(?:abstract\s+|final\s+)*(?:class|interface|enum)\s+" + name + r"\b",
                      self.masked)
        need(m, f"{self.rel}: declaration of {name} not found")
        return self.line_at(m.start() + len(m.group(0)) - len(name))

    def body(self, method, masked=False):
        return (self.masked if masked else self.src)[method["start"]:method["end"] + 1]


JAVA_CACHE = {}


def java_file_of(cls_name):
    c = model.DESIGN_BY_NAME.get(cls_name)
    need(c is not None and c["kind"] != "view", f"class {cls_name} is not a Java class of model.DESIGN")
    rel = JAVA_ROOT + c["package"].replace(".", "/") + f"/{cls_name}.java"
    if rel not in JAVA_CACHE:
        JAVA_CACHE[rel] = JavaFile(rel)
    return JAVA_CACHE[rel]


def model_op(cls_name, op_name):
    c = model.DESIGN_BY_NAME[cls_name]
    for o in c["ops"]:
        if o["name"] == op_name:
            return o
    raise ShowcaseError(f"operation {cls_name}.{op_name} not in tools/model.py")


def uml(o):
    params = ", ".join(f"{p}: {t}" for p, t in o["params"])
    return f"{o['name']}({params})" + (f": {o['ret']}" if o["ret"] else "")


class JsFile:
    def __init__(self, rel):
        self.rel = rel
        self.src = read(rel)
        self.masked = mask_js(self.src)
        self.line_at = _line_index(self.src)
        depth = depths(self.masked)
        self.functions = []      # dict(name, owner, start, end, line, end_line)
        for m in re.finditer(r"(?m)^[ \t]*(?:export\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(",
                             self.masked):
            self._add(m.group(1), None, m.start(1), m.end() - 1)
        for obj in re.finditer(r"(?m)^export\s+const\s+([A-Za-z_$][\w$]*)\s*=\s*\{", self.masked):
            open_ = obj.end() - 1
            close = match(self.masked, open_, "{", "}")
            level = depth[open_] + 1
            for m in re.finditer(r"(?m)^[ \t]*(?:async\s+)?([A-Za-z_$][\w$]*)\s*\(", self.masked[open_:close]):
                at = open_ + m.start(1)
                if depth[at] == level and m.group(1) not in JAVA_KEYWORDS:
                    self._add(m.group(1), obj.group(1), at, open_ + m.end() - 1)

    def _add(self, name, owner, at, paren):
        close = match(self.masked, paren)
        body = self.masked.find("{", close)
        end = match(self.masked, body, "{", "}")
        self.functions.append(dict(name=name, owner=owner, start=at, end=end, line=self.line_at(at),
                                   end_line=self.line_at(end)))

    def function(self, owner, name):
        for f in self.functions:
            if f["owner"] == owner and f["name"] == name:
                return f
        raise ShowcaseError(f"{self.rel}: {owner + '.' if owner else ''}{name}() not found")

    def enclosing(self, needle):
        at = self.src.find(needle)
        need(at >= 0, f"{self.rel}: {needle!r} not found")
        inside = [f for f in self.functions if f["start"] <= at <= f["end"]]
        need(inside, f"{self.rel}: {needle!r} is not inside a function")
        return min(inside, key=lambda f: f["end"] - f["start"]), self.line_at(at)


def kebab(name):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", name).lower()


JS_CACHE = {}


def js_file(rel):
    if rel not in JS_CACHE:
        JS_CACHE[rel] = JsFile(rel)
    return JS_CACHE[rel]


# ------------------------------------------------------------------------------------------- tests and checks
def java_unescape(s):
    return re.sub(r"\\(u[0-9a-fA-F]{4}|.)",
                  lambda m: chr(int(m.group(1)[1:], 16)) if m.group(1).startswith("u") and len(m.group(1)) == 5
                  else {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s)


class Tests:
    """build/test_results.txt and the line of every test(...) in demo/tests/java."""

    def __init__(self):
        lines = lines_of("build/test_results.txt")
        m = re.search(r"test run (.+)$", lines[0])
        self.date = m.group(1).strip() if m else ""
        self.groups, self.results, group = [], {}, None
        self.passed = self.failed = None
        for line in lines[1:]:
            if line.startswith("== Code versus model"):
                break
            if line.startswith("== "):
                group = dict(title=line[3:].strip(), tests=[])
                self.groups.append(group)
            elif line.startswith(("PASS  ", "FAIL  ")):
                name = line[6:].split(" -> ")[0].strip()
                self.results[name] = dict(name=name, ok=line.startswith("PASS"), group=group["title"])
                group["tests"].append(name)
            elif re.match(r"\d+ tests passed, \d+ failed", line):
                self.passed, self.failed = map(int, re.findall(r"\d+", line)[:2])
        need(self.passed is not None, "build/test_results.txt has no summary line")
        need(self.passed + self.failed == len(self.results), "test summary does not match the PASS/FAIL lines")
        self.source = {}
        for path in sorted((ROOT / TEST_ROOT).rglob("*.java")):
            rel = path.relative_to(ROOT).as_posix()
            src = read(rel)
            masked = mask_java(src)
            line_at = _line_index(src)
            for t in re.finditer(r'\btest\(\s*"((?:\\.|[^"\\])*)"', src):
                if masked[t.start()] != "t":
                    continue
                end = match(masked, src.find("(", t.start()))
                self.source[java_unescape(t.group(1))] = (rel, line_at(t.start()), line_at(end))
        for name in self.results:
            need(name in self.source, f"test {name!r} of build/test_results.txt not found in {TEST_ROOT}")

    def select(self, prefixes=(), groups=()):
        chosen = []
        for g in groups:
            hits = [x for x in self.groups if x["title"].startswith(g)]
            need(len(hits) == 1, f"test group {g!r} not found (or ambiguous) in build/test_results.txt")
            chosen += [n for n in hits[0]["tests"] if n not in chosen]
        for p in prefixes:
            hits = [n for n in self.results if n.startswith(p)]
            need(len(hits) == 1, f"test prefix {p!r} matches {len(hits)} tests in build/test_results.txt")
            if hits[0] not in chosen:
                chosen.append(hits[0])
        return chosen

    def link(self, name):
        rel, start, end = self.source[name]
        return LINKS.code(rel, start, end, expect="test(")

    def group_of(self, prefix):
        hits = [g for g in self.groups if g["title"].startswith(prefix)]
        need(len(hits) == 1, f"test group {prefix!r} not found")
        return hits[0]


def run_model_check():
    done = subprocess.run([sys.executable, "tools/check_code_model.py"], cwd=ROOT, capture_output=True, text=True)
    out = [line.rstrip() for line in done.stdout.splitlines()]
    summary = next((line for line in reversed(out) if line.startswith("Model check")), None)
    need(summary, "tools/check_code_model.py printed no 'Model check' line:\n" + done.stdout + done.stderr)
    count = lambda tag: sum(1 for line in out if line.startswith(tag))  # noqa: E731
    return dict(ok=done.returncode == 0, summary=summary, oks=count("OK "), notes=[line[6:] for line in out
                if line.startswith("NOTE")], fails=[line[6:] for line in out if line.startswith("FAIL")],
                sections=[line.strip("= ").strip() for line in out if line.startswith("== ")])


def sql_validation():
    lines = [line.rstrip() for line in lines_of("build/sql_validation.txt")]
    rejected = [line.strip() for line in lines if line.strip().startswith("Rejected")]
    final = next((line for line in lines if re.match(r"\s*\d+/\d+ statements", line)), "")
    created = next((line.strip() for line in lines if "tables created" in line), "")
    need(final and created, "build/sql_validation.txt has an unexpected format")
    return dict(engine=lines[0].strip(), created=created, rejected=rejected, final=final.strip())


class Database:
    """The schema and seed SQL of the demo loaded into an in-memory SQLite database, compared with model.TABLES."""

    def __init__(self):
        con = sqlite3.connect(":memory:")
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(read(SCHEMA))
        con.executescript(read(SEED))
        self.version = sqlite3.sqlite_version
        self.tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
        self.columns = {t: [r[1] for r in con.execute(f'PRAGMA table_info("{t}")')] for t in self.tables}
        self.fks = {(t, r[3], r[2], r[4]) for t in self.tables for r in con.execute(f'PRAGMA foreign_key_list("{t}")')}
        self.rows = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in self.tables}
        self.con = con
        self.model_tables = {t["name"]: [c["name"] for c in t["columns"]] for t in model.TABLES}
        self.model_fks = set(model.foreign_keys())
        self.match_tables = set(self.tables) == set(self.model_tables)
        self.match_columns = {t: self.columns.get(t) == cols for t, cols in self.model_tables.items()}
        self.match_fks = self.fks == self.model_fks
        self.n_columns = sum(len(c) for c in self.model_tables.values())

    def query(self, sql):
        return self.con.execute(sql).fetchall()


def svg_texts(fid):
    svg = read(f"figures/vp/{fid}.svg")
    return [html.unescape(re.sub(r"<[^>]+>", "", t)).strip() for t in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S)]


def vp_schema_evidence(fid):
    """How many tables and column names of model.TABLES the exported VP diagram shows (read from its SVG)."""
    texts = svg_texts(fid)
    names = set(texts) | {m.group(1) for t in texts for m in [re.match(r"^[+\-#~]?\s*(\w+)\s*:", t)] if m}
    tables = [t["name"] for t in model.TABLES]
    columns = sorted({c["name"] for t in model.TABLES for c in t["columns"]})
    missing_t = [t for t in tables if t not in names]
    missing_c = [c for c in columns if c not in names]
    return dict(id=fid, tables=len(tables) - len(missing_t), n_tables=len(tables), missing_tables=missing_t,
                columns=len(columns) - len(missing_c), n_columns=len(columns), missing_columns=missing_c)


# ------------------------------------------------------------------------------------------------ VP figures
def vp_figures(essay, pdf, pdf_rel):
    readme = read("figures/vp/README.md")
    rows = re.findall(r"(?m)^\| (\w+) \| ([^|]+?) \| (.+?) \|\s*$", readme)
    rows = [r for r in rows if r[0] != "id"]
    need(rows, "figures/vp/README.md: no figure table")
    figure_dests = pdf.figure_dests()
    by_block = len(figure_dests) == len(essay.figures)
    if not by_block:
        warn(f"essay has {len(essay.figures)} figure environments but the PDF {len(figure_dests)} figure "
             "destinations; figure links fall back to the page of their section")
    figures = {}
    for fid, chapter_col, desc in rows:
        png = f"figures/vp/{fid}.png"
        w, h = png_size(png)
        trial = "Trial screenshot" in desc
        desc_clean = re.sub(r"\*Trial screenshot\.\*\s*", "", desc).strip()
        desc_clean = re.sub(r"\*([^*]+)\*", r"\1", desc_clean)
        has_svg = (ROOT / f"figures/vp/{fid}.svg").exists()
        if trial:
            need(not has_svg, f"{fid} is marked as a trial screenshot in the README but has an SVG export")
        else:
            need(has_svg, f"{fid} is a Community Edition figure without its SVG export")
            svg = read(f"figures/vp/{fid}.svg")
            need("Community Edition" in svg, f"figures/vp/{fid}.svg has no 'Community Edition' footer")
            need("evaluation" not in svg.lower(), f"figures/vp/{fid}.svg carries an evaluation watermark")
        info = essay.vp.get(fid)
        readme_ch = int(re.match(r"\s*(\d)", chapter_col).group(1))
        fig = dict(id=fid, png=png, w=w, h=h, trial=trial, desc=desc_clean, readme_chapter=chapter_col.strip(),
                   in_essay=info is not None, chapter=info["chapter"] if info else readme_ch,
                   number=info["number"] if info else None,
                   title=info["short"] if info else desc_clean.split(":")[0].strip(),
                   caption=info["caption"] if info else "", section=info["section"] if info else None,
                   pdf=pdf_rel, page=None, essay_line=(info["file"], info["line"]) if info else None)
        if info:
            dest = figure_dests[info["block"]] if by_block else info["section"]["dest"]
            fig["page"] = pdf.page(dest)
        figures[fid] = fig
    for fid, info in essay.vp.items():
        if fid in figures:
            continue
        # A figure of the essay that the README does not describe yet: the image must exist; the essay caption is used.
        png = f"figures/vp/{fid}.png"
        w, h = png_size(png)
        trial = "\\trialshot" in info["raw_caption_full"]
        if not trial:
            svg = read(f"figures/vp/{fid}.svg")
            need("evaluation" not in svg.lower(), f"figures/vp/{fid}.svg carries an evaluation watermark")
        warn(f"figures/vp/README.md does not describe {fid} yet; the essay caption is used")
        dest = figure_dests[info["block"]] if by_block else info["section"]["dest"]
        figures[fid] = dict(id=fid, png=png, w=w, h=h, trial=trial, desc=re.sub(r"<[^>]+>", "", info["caption"]),
                            readme_chapter="", in_essay=True, chapter=info["chapter"], number=info["number"],
                            title=info["short"], caption=info["caption"], section=info["section"], pdf=pdf_rel,
                            page=pdf.page(dest), essay_line=(info["file"], info["line"]))
    order = [fid for fid in essay.vp] + [fid for fid in figures if fid not in essay.vp]
    ordered = sorted(order, key=lambda f: (figures[f]["chapter"], order.index(f)))
    return {fid: figures[fid] for fid in ordered}


def demo_figures(essay, pdf):
    shots = {}
    for path in sorted((ROOT / "figures" / "demo").glob("*.png")):
        name = path.stem
        info = essay.demo.get(name)
        w, h = png_size(f"figures/demo/{name}.png")
        shots[name] = dict(id=name, png=f"figures/demo/{name}.png", w=w, h=h, in_essay=info is not None,
                           title=info["short"] if info else name.replace("_", " "),
                           caption=info["caption"] if info else "", number=info["number"] if info else None,
                           section=info["section"] if info else None,
                           page=pdf.page(info["section"]["dest"]) if info else None)
    for name in essay.demo:
        need(name in shots, f"the essay uses figures/demo/{name}.png, which does not exist")
    return shots


# ----------------------------------------------------------------------------------------- code references
IMPLEMENTATIONS = {}
for _c in model.DESIGN:
    for _i in _c["implements"]:
        IMPLEMENTATIONS.setdefault(_i, []).append(_c["name"])


def model_line(cls_name, op_name=None):
    line = find_line("tools/model.py", f'cls("{cls_name}",')
    if op_name is None:
        return line
    return find_line("tools/model.py", rf'op\("[+\-#~]{op_name}\(', start=line, regex=True)


def code_ref(ref):
    """'Class.method' or 'Class' of model.DESIGN -> dict with GitHub links to the code and to tools/model.py."""
    cls_name, _, meth = ref.partition(".")
    c = model.DESIGN_BY_NAME.get(cls_name)
    need(c is not None, f"{cls_name} is not a class of tools/model.py")
    out = dict(ref=ref, cls=cls_name, meth=meth, kind=c["kind"])
    if c["kind"] == "view":
        rel = JS_ROOT + kebab(cls_name) + ".js"
        f = js_file(rel).function(cls_name, meth)
        out.update(rel=rel, line=f["line"], end=f["end_line"], url=LINKS.code(rel, f["line"], f["end_line"], meth))
        o = model_op(cls_name, meth)
    else:
        jf = java_file_of(cls_name)
        if not meth:
            line = jf.class_line(cls_name)
            out.update(rel=jf.rel, line=line, end=line, url=LINKS.code(jf.rel, line, expect=cls_name),
                       model_url=LINKS.code("tools/model.py", model_line(cls_name), expect=cls_name))
            return out
        o = model_op(cls_name, meth)
        m = jf.method(meth, len(o["params"]))
        out.update(rel=jf.rel, line=m["line"], end=m["end_line"], url=LINKS.code(jf.rel, m["line"], m["end_line"], meth))
    out["sig"] = uml(o)
    out["model_url"] = LINKS.code("tools/model.py", model_line(cls_name, meth), expect=meth)
    return out


def field_types(cls_name):
    c = model.DESIGN_BY_NAME[cls_name]
    types = {a["name"]: a["type"] for a in c["attrs"]}
    for a in model.DESIGN_ASSOCIATIONS:
        if a["src"] == cls_name:
            types[a["role"]] = a["dst"]
    return types


SQL_LITERAL = re.compile(r'"((?:\\.|[^"\\])*)"')


def tables_touched(entry_refs):
    """Follows field calls (controller -> service -> repository interface -> SQLite class, and private helpers)
    from the entry methods and collects the tables named in the SQL strings: {table: {"R", "W"}} and the methods."""
    tables = {t["name"] for t in model.TABLES}
    access, via, seen = {}, {}, set()
    stack = [tuple(r.split(".", 1)) for r in entry_refs]
    while stack:
        cls_name, meth = stack.pop()
        if (cls_name, meth) in seen:
            continue
        seen.add((cls_name, meth))
        c = model.DESIGN_BY_NAME.get(cls_name)
        if c is None or c["kind"] in ("view", "enum"):
            continue
        if c["kind"] == "interface":
            stack += [(impl, meth) for impl in IMPLEMENTATIONS.get(cls_name, [])]
            continue
        jf = java_file_of(cls_name)
        types = field_types(cls_name)
        for m in [x for x in jf.methods if x["name"] == meth]:
            src, masked = jf.body(m), jf.body(m, True)
            for name, (c_src, c_masked) in jf.constants().items():
                if re.search(r"\b" + name + r"\b", masked):
                    src, masked = src + "\n" + c_src, masked + "\n" + c_masked
            for lit in SQL_LITERAL.finditer(src):
                if masked[lit.start()] != '"':
                    continue
                sql = lit.group(1)
                for _, table in re.findall(r"\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+(\w+)", sql, re.I):
                    if table in tables:
                        access.setdefault(table, set()).add("W")
                        via.setdefault(table, set()).add((cls_name, meth))
                for table in re.findall(r"\b(?:FROM|JOIN)\s+(\w+)", re.sub(r"\bDELETE\s+FROM\s+\w+", "", sql, flags=re.I), re.I):
                    if table in tables:
                        access.setdefault(table, set()).add("R")
                        via.setdefault(table, set()).add((cls_name, meth))
            for field, callee in re.findall(r"\b([a-z]\w*)\.([a-zA-Z]\w*)\s*\(", masked):
                base = re.sub(r"<.*", "", types.get(field, ""))
                if base in model.DESIGN_BY_NAME:
                    stack.append((base, callee))
            for callee in re.findall(r"(?<![\w.])([a-z]\w*)\s*\(", masked) + re.findall(r"\bthis\.([a-z]\w*)\s*\(", masked):
                if callee != meth and jf.has(callee):
                    stack.append((cls_name, callee))
    order = [t["name"] for t in model.TABLES]
    return [(t, "".join(sorted(access[t])), sorted(via[t])) for t in order if t in access]


def schema_lines(table):
    start = find_line(SCHEMA, f"CREATE TABLE {table} (")
    end = find_line(SCHEMA, ");", start=start)
    return start, end


def table_url(table):
    start, end = schema_lines(table)
    return LINKS.code(SCHEMA, start, end, expect=f"CREATE TABLE {table}")


def route(needle):
    line = find_line(WEBSERVER, needle)
    return dict(line=line, url=LINKS.code(WEBSERVER, line, expect=needle))


def js_caller(rel, needle):
    jf = js_file(JS_ROOT + rel)
    f, at = jf.enclosing(needle)
    label = f"{f['owner']}.{f['name']}" if f["owner"] else f"{f['name']}()"
    return dict(label=label, file=rel, url=LINKS.code(jf.rel, f["line"], f["end_line"], f["name"]), call_line=at,
                call_url=LINKS.code(jf.rel, at, expect=needle.strip('"')))


def expand_ids(text):
    """'FR01--FR04, FR14' -> ['FR01', 'FR02', 'FR03', 'FR04', 'FR14'] (also with an en dash)."""
    out = []
    for a, b in re.findall(r"([A-Z]+\d+)(?:\s*(?:--|–|-)\s*([A-Z]+\d+))?", text):
        if b:
            prefix, lo, hi = re.match(r"[A-Z]+", a).group(0), int(a[len(re.match(r'[A-Z]+', a).group(0)):]), int(b[len(re.match(r'[A-Z]+', b).group(0)):])
            out += [f"{prefix}{k:0{len(a) - len(prefix)}d}" for k in range(lo, hi + 1)]
        else:
            out.append(a)
    return out


def code_excerpt(rel, start, end):
    lines = lines_of(rel)[start - 1:end]
    width = len(str(end))
    rows = "".join(f'<span class="ln">{str(start + k).rjust(width)}</span>{E(line) or " "}\n'
                   for k, line in enumerate(lines))
    return f'<pre class="code"><code>{rows}</code></pre>'


# =================================================================================================== the page
# Curated choices (which use cases, diagrams, methods and tests to show). Every name is validated against the
# repository when the page is built; the facts themselves (signatures, lines, tables, results) are read, not typed.
THREAD_UC = "UC07"
TRACE = [
    dict(uc="UC02", analysis=["c2_activity_search", "c2_bce_search"], design=["c44_seq_search"],
         ops=["SearchService.searchText", "QueryService.textQuery", "QueryService.parseRules", "RankingService.rank"],
         entry="SearchController.search", route='"GET /api/search"', ui=("search-ui.js", "/api/search?q="),
         tests=dict(prefixes=["Gemma's JSON becomes a CommonQuery", "Keyword rules replace Gemma",
                              "Offline search keeps only Monet under", "Text search with Gemma", "RankingService: S"])),
    dict(uc="UC04", analysis=["c2_activity_image"], design=["c3_seq_image"],
         ops=["SearchService.searchImage", "ImageService.embed", "VectorIndex.toVector", "VectorIndex.cosineSimilarity"],
         entry="SearchController.searchImage", route='"POST /api/search/image"', ui=("search-ui.js", '"/api/search/image"'),
         ui_extra=["ImageUpload.validate"],
         tests=dict(prefixes=["Image search: Gemma", "Without Gemma the photo", "Uploads: only JPEG",
                              "cosineSimilarity follows", "toVector is one-hot"])),
    dict(uc="UC07", analysis=["c2_activity_checkout", "c2_bce_checkout"], design=["c44_checkout_seq", "c44_classes_backend"],
         ops=["CheckoutService.checkout", "OrderItem.fromCartItem", "Order.calculateTotal", "PayCredit.process"],
         entry="CheckoutController.checkout", route='"POST /api/checkout"', ui=("cart-view.js", '"/api/checkout"'),
         tests=dict(groups=["Checkout"], prefixes=["OrderItem.fromCartItem", "Order.calculateTotal"])),
    dict(uc="UC11", analysis=["c2_activity_cancel", "c2_bce_cancel", "c2_state_order"], design=["c44_seq_cancel"],
         ops=["OrderService.cancelOrder", "Order.isOwnedBy", "Order.cancel", "OrderRepository.updateStatus"],
         entry="OrderController.cancelOrder", route='"POST /api/orders/"', route_label="POST /api/orders/{orderId}/cancel",
         ui=("order-view.js", "/api/orders/${orderId}/cancel"),
         tests=dict(prefixes=["Order.cancel is allowed", "cancelOrder: only the owner", "Order.isOwnedBy",
                              "Another customer's order answers 404"])),
    dict(uc="UC13", analysis=["c2_activity_admin", "c2_state_order"], design=["c44_classes", "c43_design"],
         ops=["OrderService.updateStatus", "Order.advanceTo", "OrderRepository.updateStatus"],
         entry="AdminController.updateOrderStatus", route='"PUT /api/admin/orders/"',
         route_label="PUT /api/admin/orders/{orderId}", ui=("admin-view.js", "/api/admin/orders/${orderId}"),
         tests=dict(prefixes=["Order.advanceTo moves one step", "updateStatus moves one step", "Administrator routes need"])),
]
NAV = [("a", "A", "Overview"), ("b", "B", "Process"), ("c", "C", "Evolution"), ("d", "D", "Traceability"),
       ("e", "E", "Database"), ("f", "F", "Live demo"), ("g", "G", "Verification"), ("diagrams", "+", "All diagrams")]


class Page:
    def __init__(self):
        global ESSAY
        self.essay = ESSAY = Essay()
        self.essay.finish()
        author = read("report/author.tex")
        macro = lambda name: re.search(r"\\newcommand\{\\" + name + r"\}\{([^}]*)\}", author).group(1)  # noqa: E731
        self.author, self.student_id = macro("authorName"), macro("studentId")
        self.class_name, self.version = macro("className"), macro("essayVersion")
        subject = re.search(r"pdfsubject=\{([^}]*)\}", read("report/main.tex"))
        self.course = subject.group(1).split(" -- ")[0] if subject else "Information System Analysis and Design"
        pdfs = sorted((ROOT / "build" / "report").glob(f"tieuluan_V{self.version}_{self.class_name}_*.pdf"))
        need(len(pdfs) == 1, f"expected one essay PDF build/report/tieuluan_V{self.version}_{self.class_name}_*.pdf, "
             f"found {len(pdfs)}")
        self.pdf_rel = pdfs[0].relative_to(ROOT).as_posix()
        self.pdf = Pdf(self.pdf_rel)
        in_pdf = sum(1 for d in self.pdf.dests if re.match(r"(chapter|section|subsection)\.[1-5](\.|$)", d))
        if in_pdf != len(self.essay.sections):
            warn(f"the essay PDF has {in_pdf} sections in chapters 1-5 but the LaTeX sources {len(self.essay.sections)}: "
                 "the PDF is older than report/chapters; rebuild it with report/build.sh (page links may be off)")
        self.figs = vp_figures(self.essay, self.pdf, self.pdf_rel)
        self.shots = demo_figures(self.essay, self.pdf)
        self.tests = Tests()
        self.check = run_model_check()
        self.sqlv = sql_validation()
        self.db = Database()
        self.eval = json.loads(read("build/eval/eval_results.json"))
        self.voice = json.loads(read("build/eval/voice_eval.json"))
        self.vpp = "vp/tieuluan_design.vpp"
        repo_path(self.vpp)
        self.ch = {k: f"report/chapters/{f}.tex" for k, f in enumerate(self.essay.chapter_files, 1)}
        self.props = self._props("demo/config/app.properties")
        self.offline_props = self._props("demo/config/app.offline.properties")

    @staticmethod
    def _props(rel):
        return dict(re.findall(r"(?m)^([\w.]+)\s*=\s*(.*?)\s*$", read(rel)))

    # ------------------------------------------------------------------------------------------- small pieces
    def pdf_href(self, page):
        return LINKS.file(self.pdf_rel) + (f"#page={page + 1}" if page is not None else "")

    def sec(self, section, with_title=False):
        page = self.pdf.page(section["dest"])
        title = f" {E(section['title'])}" if with_title else ""
        if page is None:
            return f'<a class="sec" href="{self.pdf_href(None)}" title="Essay PDF">§{section["number"]}{title}</a>'
        return (f'<a class="sec" href="{self.pdf_href(page)}" title="Essay PDF, page {self.pdf.label(page)}">'
                f'§{section["number"]}{title}<span class="pg"> · p.&nbsp;{self.pdf.label(page)}</span></a>')

    def sec_label(self, label, with_title=True):
        number = self.essay.labels.get(label)
        need(number, f"essay label {label} not found")
        return self.sec(self.essay.section(number), with_title)

    def tex_line(self, rel, line, text="LaTeX source"):
        return f'<a class="src" href="{LINKS.code(rel, line)}">{E(text)}</a>'

    def fig(self, fid, label=None, cls="fig-link"):
        f = self.figs.get(fid) or self.shots.get(fid)
        need(f, f"figure {fid} not found in figures/vp or figures/demo")
        return f'<a class="{cls}" href="{LINKS.file(f["png"])}" data-fig="{E(fid)}">{E(label or f["title"])}</a>'

    def badge(self, f):
        if f["id"] in self.shots:
            return '<span class="badge shot"><i></i>Demo screenshot</span>'
        if f["trial"]:
            return '<span class="badge trial"><i></i>VP trial screenshot</span>'
        return '<span class="badge ce"><i></i>VP Community Edition</span>'

    def thumb(self, fid, note=None, size=""):
        f = self.figs.get(fid) or self.shots.get(fid)
        need(f, f"figure {fid} not found")
        number = f"Figure {f['number']}" if f["number"] else "Not in the essay"
        return (f'<a class="thumb {size}" href="{LINKS.file(f["png"])}" data-fig="{E(fid)}">'
                f'<span class="wall"><img src="{LINKS.file(f["png"])}" width="{f["w"]}" height="{f["h"]}" '
                f'loading="lazy" decoding="async" alt="{E(f["title"])}"></span>'
                f'<span class="thumb-meta">{self.badge(f)}<span class="mono">{E(number)}</span></span>'
                f'<span class="thumb-title">{E(f["title"])}</span>'
                + (f'<span class="thumb-note">{note}</span>' if note else "") + "</a>")

    def ref(self, ref, text=None):
        c = code_ref(ref)
        where = f"{c['rel'].split('/')[-1]}#L{c['line']}" + (f"-L{c['end']}" if c["end"] != c["line"] else "")
        return f'<a class="ref" href="{c["url"]}" title="{E(c["rel"])}, lines {c["line"]}–{c["end"]}">{E(text or ref)}</a>' \
               f'<span class="where">{E(where)}</span>'

    def ref_plain(self, ref, text=None):
        c = code_ref(ref)
        return f'<a class="ref" href="{c["url"]}" title="{E(c["rel"])}#L{c["line"]}">{E(text or ref)}</a>'

    def sig(self, ref):
        c = code_ref(ref)
        return f'<a class="sig" href="{c["model_url"]}" title="Declared in tools/model.py">{E(c["cls"])}.{E(c["sig"])}</a>'

    def table(self, name):
        return f'<a class="tbl" href="{table_url(name)}" title="CREATE TABLE {E(name)} in {SCHEMA}">{E(name)}</a>'

    def req(self, rid):
        line = find_line("tools/model.py", f'("{rid}",')
        title = next(r[2] for r in model.REQUIREMENTS if r[0] == rid)
        return f'<a class="req" href="{LINKS.code("tools/model.py", line, expect=rid)}" title="{E(title)}">{E(rid)}</a>'

    def uc_name(self, uc):
        return next(u[1] for u in model.USE_CASES if u[0] == uc)

    def test_li(self, name):
        r = self.tests.results[name]
        state = '<span class="ok">PASS</span>' if r["ok"] else '<span class="bad">FAIL</span>'
        return f'<li>{state}<a href="{self.tests.link(name)}">{E(name)}</a></li>'

    def file(self, rel, text=None, cls="file"):
        return f'<a class="{cls}" href="{LINKS.file(rel)}">{E(text or rel)}</a>'

    def blob(self, rel, needle, text, regex=False):
        line = find_line(rel, needle, regex=regex)
        return f'<a class="file" href="{LINKS.code(rel, line)}">{E(text)}</a>'

    def head(self, key, letter, title, lead):
        return (f'<div class="sec-head"><span class="letter" aria-hidden="true">{letter}</span>'
                f'<div><p class="label">Section {letter}</p><h2 class="h2">{title}</h2>'
                f'<p class="lead">{lead}</p></div></div>')

    # ------------------------------------------------------------------------------------------------ facts
    def counts(self):
        fr = [r for r in model.REQUIREMENTS if r[1] == "FR"]
        nfr = [r for r in model.REQUIREMENTS if r[1] == "NFR"]
        java = [c for c in model.DESIGN if c["kind"] != "view"]
        views = [c for c in model.DESIGN if c["kind"] == "view"]
        trial = [f for f in self.figs.values() if f["trial"]]
        return dict(fr=len(fr), nfr=len(nfr), uc=len(model.USE_CASES), figs=len(self.figs),
                    ce=len(self.figs) - len(trial), trial=len(trial), design=len(model.DESIGN), java=len(java),
                    views=len(views), tables=len(model.TABLES), fks=len(list(model.foreign_keys())),
                    analysis=len(model.ANALYSIS), passed=self.tests.passed, total=len(self.tests.results))

    def problems(self):
        rows = longtable(self.ch[1], "tab:pcin")
        return [dict(id=clean_tex(c[0], True), problem=clean_tex(c[1]), cause=clean_tex(c[2]), impact=clean_tex(c[3]),
                     need=clean_tex(c[4]), line=line) for c, line in rows]

    def derivation(self):
        rows = longtable(self.ch[2], "tab:derivation")
        return [dict(problem=clean_tex(c[0], True), need=clean_tex(c[1]), reqs=expand_ids(clean_tex(c[2], True)),
                     actors=clean_tex(c[3]), ucs=expand_ids(clean_tex(c[4], True)), line=line) for c, line in rows]

    def rules(self):
        return {clean_tex(c[0], True): dict(text=clean_tex(c[1]), decision=clean_tex(c[2]), line=line)
                for c, line in longtable(self.ch[2], "tab:rules")}

    def spec(self, uc):
        section = self.essay.section_titled(rf"\b{uc}\b")
        text = read(section["file"])
        label = re.search(r"\\caption\{Specification of " + uc + r"\b[^}]*\}\\label\{(tab:[^}]*)\}", text)
        need(label, f"specification table of {uc} not found")
        return section, spec_rows(section["file"], label.group(1))

    def priority(self, uc):
        order = ["Must", "Should", "Could", "Won't"]
        ps = [model.REQUIREMENT_DETAILS[r[0]][0] for r in model.REQUIREMENTS if uc in r[3] and r[1] == "FR"]
        return min(ps, key=order.index) if ps else ""

    # ----------------------------------------------------------------------------------------------- header
    def header(self):
        dots = "<i></i>" * 16
        links = "".join(f'<a href="#{k}" data-nav="{k}"><b>{E(letter)}</b>{E(name)}</a>' for k, letter, name in NAV)
        return (f'<a class="skip" href="#a">Skip to the overview</a>'
                f'<header class="top" id="top"><div class="top-in">'
                f'<a class="logo" href="#hero" aria-label="Họa. showcase, back to the top">'
                f'<span class="logo-mark" aria-hidden="true">{dots}</span>Họa.<span class="logo-sub">showcase</span></a>'
                f'<nav class="nav" aria-label="Sections">{links}</nav>'
                f'<button type="button" class="theme-toggle" id="theme-toggle" aria-label="Switch between dark and light">'
                f'</button></div></header>')

    def hero(self):
        n = self.counts()
        catalog = json.loads(read("demo/data/catalog.json"))
        art = next(p for p in catalog["paintings"] if p["productId"] == "P10")
        img = "demo/web" + art["imageUrl"]
        w, h = jpeg_size(img)
        stats = [
            (n["fr"], "functional requirements", f"+ {n['nfr']} non-functional", "a"),
            (n["uc"], "use cases", f"{len(model.ACTORS)} actors", "a"),
            (n["figs"], "Visual Paradigm diagrams", f"{n['ce']} Community Edition + {n['trial']} trial screenshots", "diagrams"),
            (n["design"], "design classes", f"{n['java']} Java + {n['views']} JS views", "c"),
            (n["tables"], "database tables", f"{n['fks']} foreign keys", "e"),
            (f"{n['passed']}/{n['total']}", "tests passed", f"run {self.tests.date}", "g"),
        ]
        tiles = "".join(f'<li><a href="#{a}"><span class="stat-n">{E(v)}</span><span class="stat-l">{E(l)}</span>'
                        f'<span class="stat-s">{E(s)}</span></a></li>' for v, l, s, a in stats)
        return f'''
<section class="hero wrap" id="hero">
  <div class="hero-grid">
    <div class="hero-text">
      <p class="label">{E(self.course)} · PTIT · Class {E(self.class_name)} · Individual essay</p>
      <h1 class="display">Họa. <span class="dash">—</span> <span class="display-2">from requirements to running code</span></h1>
      <p class="lead">An online gallery of public-domain prints, followed through five chapters — requirement
      determination, analysis, AI in e-commerce, design and code — until it runs as a Java&nbsp;17 shop on SQLite with
      multimodal search by Gemma&nbsp;4 and self-hosted Whisper. Every name below comes from one specification,
      <a class="ref" href="{LINKS.whole("tools/model.py")}">tools/model.py</a>, and every link opens the real artefact.</p>
      <dl class="who">
        <div><dt>Student</dt><dd>{E(self.author)}</dd></div>
        <div><dt>Student ID</dt><dd>{E(self.student_id)}</dd></div>
        <div><dt>Class</dt><dd>{E(self.class_name)}</dd></div>
        <div><dt>Essay</dt><dd>Version {E(self.version)}, {self.pdf.count} pages</dd></div>
      </dl>
      <div class="actions">
        <a class="btn solid" href="{LINKS.file(self.pdf_rel)}">Essay PDF</a>
        <a class="btn" href="{LINKS.file(self.vpp)}" download>VP project (.vpp)</a>
        <a class="btn" href="{REPO}">Source on GitHub</a>
        <a class="btn" href="#run">Run it locally ↓</a>
      </div>
    </div>
    <figure class="hero-art">
      <div class="art"><img src="{LINKS.file(img)}" width="{w}" height="{h}" alt="{E(art["name"])} by {E(art["artist"])}" decoding="async"></div>
      <figcaption><span>{E(art["name"])}</span><span class="mono">{E(art["artist"])}, {art["yearCreated"]} · {E(art["source"]["licence"])} ·
      {self.file("demo/data/ATTRIBUTION.md", "credits", "plain")}</span></figcaption>
    </figure>
  </div>
  <ul class="stats" aria-label="Key numbers, computed from the repository">{tiles}</ul>
</section>'''

    # --------------------------------------------------------------------------------------------- A overview
    def section_a(self):
        problems = self.problems()
        goals = [(clean_tex(c[0], True), clean_tex(c[1]), clean_tex(c[2])) for c, _ in longtable(self.ch[1], "tab:goals")]
        scope = [(clean_tex(c[0]), clean_tex(c[1])) for c, _ in longtable(self.ch[1], "tab:scope")]
        five = [[clean_tex(x) for x in c] for c, _ in longtable(self.ch[3], "tab:fiveai")]
        p_cards = "".join(f'''<article class="card problem"><p class="label">{E(p["id"])}</p><h3 class="h3">{p["problem"]}</h3>
          <p><span class="k">Cause</span>{p["cause"]}</p><p><span class="k">Impact</span>{p["impact"]}</p>
          <p class="need"><span class="k">Need</span>{p["need"]}</p></article>''' for p in problems)
        g_rows = "".join(f'<li><span class="mono">{E(i)}</span><span>{o}<small>{m}</small></span></li>' for i, o, m in goals)
        actors = []
        for name, desc in model.ACTORS:
            primary = [u for u in model.USE_CASES if u[2] == name]
            support = [uc for uc, acts in model.SUPPORTING_ACTORS.items() if name in acts]
            ucs = "".join(f'<span class="chip" title="{E(u[1])}">{E(u[0])}</span>' for u in primary) + \
                "".join(f'<span class="chip ghost" title="supports {E(self.uc_name(uc))}">{E(uc)}</span>' for uc in support)
            role = "primary actor" if primary else "supporting actor"
            actors.append(f'<li><strong>{E(name)}</strong><span class="muted">{E(desc)} · {role}</span><span class="chips">{ucs}</span></li>')
        ucs = "".join(f'<li><span class="mono">{E(u[0])}</span><span>{E(u[1])}</span>'
                      f'<span class="tag">{E(self.priority(u[0]) or ("abstract" if u[3] == "abstract" else ""))}</span></li>'
                      for u in model.USE_CASES)
        s_rows = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in scope)
        n = self.counts()
        feats = "".join(f'<li><strong>{f[0]}</strong> <span class="muted">{f[1]} · {f[2]}</span></li>' for f in five)
        highlights = f'''
          <li><strong>One specification.</strong> {self.blob("tools/model.py", "REQUIREMENTS = [", "tools/model.py")} declares
          the {n["fr"] + n["nfr"]} requirements, {n["uc"]} use cases, {n["analysis"]} analysis classes, {n["design"]} design classes and
          {n["tables"]} tables; the VP diagrams, the SQL, the Java skeleton and the essay tables are generated from it,
          and {self.blob("tools/check_code_model.py", "def ", "tools/check_code_model.py")} compares the finished code with it.</li>
          <li><strong>{len(five)} AI features with a way back.</strong> Each one has a path without AI (NFR02), so the
          shop keeps working when the Gemma&nbsp;4 server does not answer.<ul class="feat">{feats}</ul></li>
          <li><strong>Three layers and a shared domain.</strong> Presentation → Application → Data, rules inside the domain
          classes, AI behind the <code>LlmClient</code> and <code>SpeechClient</code> interfaces ({self.fig("c44_layers", "layers diagram")}).</li>
          <li><strong>Privacy by design.</strong> The customer id comes from the session, another customer's order is
          answered like a missing one (NFR01), card numbers are never stored (NFR05), audio never leaves the laptop (NFR08).</li>'''
        return f'''
<section class="block wrap" id="a">
  {self.head("a", "A", "Project overview", "What the shop is for, who uses it, and what the essay delivers.")}
  <h3 class="h3 sub">The problem it solves</h3>
  <p class="muted narrow">Before Họa. had a system, paintings were sold through social-media messages, a picture folder
  and two spreadsheets. Chapter&nbsp;1 traces five problems to their root causes and the need behind each
  ({self.sec_label("sec:1.6", False)}, {self.fig("c1_problems", "problem tree")}); every requirement of the essay
  attacks one of these causes.</p>
  <div class="problems">{p_cards}</div>
  <div class="grid-3 top-gap">
    <div>
      <h3 class="h3 sub">System goals</h3>
      <ul class="goals">{g_rows}</ul>
    </div>
    <div>
      <h3 class="h3 sub">Users</h3>
      <ul class="actors">{"".join(actors)}</ul>
      <p class="muted small">Stakeholders who do not use the system directly (owner, warehouse, support) are analysed in
      {self.sec_label("sec:1.3", False)} and drawn in the {self.fig("c1_stakeholders", "stakeholder map")}.</p>
    </div>
    <div>
      <h3 class="h3 sub">Functional scope</h3>
      <ul class="ucs">{ucs}</ul>
      <p class="muted small">Priority = the highest MoSCoW priority of the requirements the use case realises
      ({self.fig("c1_usecase", "use case diagram")}).</p>
    </div>
  </div>
  <h3 class="h3 sub top-gap">Highlights of the solution</h3>
  <ul class="highlights">{highlights}</ul>
  <details class="more"><summary>In and out of scope of the demo release ({self.sec_label("sec:1.7.3", False)})</summary>
    <div class="table-wrap"><table class="plain"><thead><tr><th>In scope</th><th>Out of scope (recorded for later)</th></tr></thead>
    <tbody>{s_rows}</tbody></table></div></details>
</section>'''

    # ---------------------------------------------------------------------------------------------- B process
    def thread(self):
        """The thread of THREAD_UC: problem -> need -> requirement -> use case (all read from the essay and model)."""
        row = next((d for d in self.derivation() if THREAD_UC in d["ucs"]), None)
        need(row, f"no problem of tab:derivation leads to {THREAD_UC}")
        pid = row["problem"].split()[0]
        problem = next(p for p in self.problems() if p["id"] == pid)
        frs = [r for r in model.REQUIREMENTS if THREAD_UC in r[3]]
        section, spec = self.spec(THREAD_UC)
        return dict(problem=problem, derivation=row, reqs=frs, section=section, spec=spec)

    def section_b(self):
        t = self.thread()
        uc = THREAD_UC
        p = t["problem"]
        rules = self.rules()
        rule_ids = re.findall(r"BR\d+", t["spec"].get("Rules", ("", 0))[0])
        rule_list = ", ".join(f'<abbr title="{E(re.sub("<[^>]+>", "", rules[r]["text"]))}">{r}</abbr>' for r in rule_ids if r in rules)
        trace = next(x for x in TRACE if x["uc"] == uc)
        touched = tables_touched([trace["entry"]])
        writes = [x[0] for x in touched if "W" in x[1]]
        chosen = self.tests.select(**trace["tests"])
        passed = sum(1 for x in chosen if self.tests.results[x]["ok"])
        rt = route(trace["route"])
        caller = js_caller(*trace["ui"])
        phases = [
            ("Requirements", [1, 2], "What hurts, who is involved, and what the system shall do.",
             [self.fig("c1_stakeholders", "Stakeholder map"), self.fig("c1_process", "Business process (BPMN)"),
              self.fig("c1_problems", "Problem tree"), self.fig("c1_dfd0", "Context diagram (DFD 0)"),
              self.sec_label("sec:frnfr"), self.blob("tools/model.py", "REQUIREMENTS = [", "Requirements in tools/model.py"),
              self.fig("c1_usecase", "Use case diagram")],
             f'Problem {E(p["id"])} — {p["problem"]} → need: {p["need"]} → {" ".join(self.req(r[0]) for r in t["reqs"])} → '
             f'<strong>{uc} {E(self.uc_name(uc))}</strong>'),
            ("Analysis", [2], "Specify each use case, then draw its behaviour and the domain it needs.",
             [self.sec_label("sec:2.2"), self.fig("c2_activity_checkout", "Activity diagrams"),
              self.fig("c2_bce_checkout", "Boundary–control–entity sequences"), self.fig("c2_state_order", "Order state machine"),
              self.sec_label("sec:2.3"), self.fig("c2_domain", "Domain model"), self.fig("c42_orm", "Logical data model"),
              self.fig("c2_dfd1", "DFD level 1")],
             f'Specification {self.sec(t["section"])} with rules {rule_list} → {self.fig("c2_activity_checkout", "activity")} → '
             f'{self.fig("c2_bce_checkout", "analysis sequence")}'),
            ("Design", [3, 4], "Types, methods, layers and tables — the how.",
             [self.fig("c3_ai_architecture", "AI architecture"), self.fig("c42_tables", "Physical data model"),
              self.fig("c42_erd", "Database (ERD)"), self.fig("c43_design", "Design class diagram"),
              self.fig("c44_layers", "Three layers"), self.fig("c44_packages", "Packages"),
              self.blob("tools/model.py", "DESIGN = [", "Design classes in tools/model.py")],
             f'{self.fig("c44_checkout_seq", "Design sequence")} → {self.sig("CheckoutService.checkout")}'),
            ("Implementation", [4, 5], "Generate the skeleton, implement it, keep every name.",
             [self.blob("tools/gen_java.py", "def ", "tools/gen_java.py"), self.blob("tools/gen_sql.py", "def ", "tools/gen_sql.py"),
              f'<a class="file" href="{LINKS.directory(JAVA_ROOT.rstrip("/"))}">demo/src (Java)</a>',
              f'<a class="file" href="{LINKS.directory("demo/web/js")}">demo/web/js (views)</a>',
              self.file(SCHEMA, "Generated SQL schema"), self.fig("c5_deployment", "Deployment")],
             f'{self.ref_plain("CheckoutService.checkout")} ← <code>{E(trace["route"].strip(chr(34)))}</code> '
             f'(<a class="ref" href="{rt["url"]}">WebServer</a>) ← <a class="ref" href="{caller["url"]}">{E(caller["label"])}</a>; '
             f'writes {", ".join(self.table(x) for x in writes)}'),
            ("Verification", [3, 5], "Tests, the code–model check, SQL constraints and the AI evaluation.",
             [self.file("build/test_results.txt", "Test results"), self.blob("tools/check_code_model.py", "def ", "Code–model check"),
              self.file("build/sql_validation.txt", "SQL validation"), self.file("build/eval/eval_summary.txt", "AI evaluation"),
              self.sec_label("sec:5.10")],
             f'{passed}/{len(chosen)} {uc} tests pass — <a href="#trace-{uc.lower()}">see them in D</a>'),
        ]
        cols = []
        for k, (name, chapters, purpose, artefacts, thread) in enumerate(phases, 1):
            chs = " ".join(self.sec(self.essay.section(str(c))) for c in chapters)
            items = "".join(f"<li>{a}</li>" for a in artefacts)
            cols.append(f'''<li class="phase"><p class="label">{k:02d} · Chapter {", ".join(map(str, chapters))}</p>
              <h3 class="h3">{name}</h3><p class="muted small">{purpose}</p><p class="chs">{chs}</p>
              <ul class="artefacts">{items}</ul>
              <div class="thread"><p class="label">{uc} {E(self.uc_name(uc))} here</p><p>{thread}</p></div></li>''')
        pipeline = [("tools/model.py", "the specification"), ("tools/build_vp.py", f"{len(self.figs)}-figure VP project"),
                    ("tools/gen_sql.py", "schema + seed"), ("tools/gen_java.py", "Java skeleton"),
                    ("report/gen_tables.py", "essay tables"), ("tools/check_code_model.py", "code = model?")]
        pipe = "".join(f'<li><a class="ref" href="{LINKS.whole(r)}">{E(r)}</a><span>{E(s)}</span></li>' for r, s in pipeline)
        return f'''
<section class="block wrap" id="b">
  {self.head("b", "B", "Development process", f"Requirements → analysis → design → implementation → verification: the key artefacts of each phase, with {uc} {E(self.uc_name(uc))} followed through all five.")}
  <ol class="phases">{"".join(cols)}</ol>
  <div class="pipeline"><p class="label">One specification drives every phase</p><ol>{pipe}</ol></div>
  <p class="muted small">Every diagram of the essay, in essay order, is in the <a href="#diagrams">diagram gallery</a> after section G.</p>
</section>'''

    # -------------------------------------------------------------------------------------------- C evolution
    def chain(self, key, title, intro, nodes, steps, code_html):
        """nodes: list of (figure id or None, stage label); steps: list of (what, why, benefit) between nodes."""
        need(len(steps) == len(nodes) - 1, f"chain {key}: {len(nodes)} nodes need {len(nodes) - 1} transitions")
        track = []
        for k, (fid, stage) in enumerate(nodes, 1):
            if fid:
                f = self.figs[fid]
                where = self.sec(f["section"]) if f["section"] else ""
                track.append(f'<li><p class="label">{k} · {E(stage)}</p>{self.thumb(fid, size="small")}<p class="node-sec">{where}</p></li>')
            else:
                track.append(f'<li class="code-node"><p class="label">{k} · {E(stage)}</p><a class="code-card" href="#{key}-code">'
                             f'<span class="mono">{{ }}</span><span>Running code</span></a></li>')
        rows = []
        for k, (what, why, benefit) in enumerate(steps, 1):
            a, b = nodes[k - 1][1], nodes[k][1]
            rows.append(f'''<li class="step"><p class="step-head"><span class="mono">{k} → {k + 1}</span>{E(a)} → {E(b)}</p>
              <div class="wwb"><div><p class="label">What changed</p><p>{what}</p></div>
              <div><p class="label">Why</p><p>{why}</p></div>
              <div><p class="label">Benefit</p><p>{benefit}</p></div></div></li>''')
        return f'''<article class="chain" id="{key}">
          <h3 class="h3 chain-title">{title}</h3><p class="muted chain-intro">{intro}</p>
          <ol class="track">{"".join(track)}</ol>
          <ol class="steps">{"".join(rows)}</ol>
          <div class="code-block" id="{key}-code">{code_html}</div></article>'''

    def section_c(self):
        n = self.counts()
        orm, design, dom = self.figs["c42_orm"], self.figs["c43_design"], self.figs["c2_domain"]
        enums = [c["name"] for c in model.DESIGN if c["kind"] == "enum" and c["package"].startswith("domain")]
        order = model.DESIGN_BY_NAME["Order"]
        order_ops = [o["name"] for o in order["ops"]]
        roles = [a["role"] for a in model.DESIGN_ASSOCIATIONS if a["src"] == "Order"]
        domain_attrs = [a for c in model.DESIGN if c["package"].startswith("domain") for a in c["attrs"]]
        money = sorted({a["name"] for a in domain_attrs if a["type"] == "BigDecimal"})
        domain_tests = self.tests.group_of("Domain rules")
        jf = java_file_of("Order")
        cls_line = jf.class_line("Order")
        first_method = min(m["line"] for m in jf.methods)
        last_field = max(k for k in range(cls_line, first_method) if lines_of(jf.rel)[k - 1].strip())
        cancel, advance = jf.method("cancel"), jf.method("advanceTo")
        code_a = (f'<p class="label">The real code · <a class="ref" href="{LINKS.code(jf.rel, cls_line, last_field, "Order")}">'
                  f'{E(jf.rel)}#L{cls_line}-L{last_field}</a></p>{code_excerpt(jf.rel, cls_line, last_field)}'
                  f'<p class="label">… <a class="ref" href="{LINKS.code(jf.rel, cancel["line"], advance["end_line"], "cancel")}">'
                  f'#L{cancel["line"]}-L{advance["end_line"]}</a></p>{code_excerpt(jf.rel, cancel["line"], advance["end_line"])}')
        chain_a = self.chain(
            "chain-classes", "1 · Classes: analysis → design → code",
            f"The {E(model.DESIGN_BY_NAME['Order']['name'])} class at four levels of detail. Each diagram adds exactly one "
            f"kind of information, as the lecturer's rule asks: analysis = attributes and kind of relationship, data model = names and multiplicities, design = types, methods and directions.",
            [("c2_domain", "Analysis"), ("c42_orm", "Logical data model"), ("c43_design", "Design"), (None, "Order.java")],
            [(f"Every class becomes «ORM-Persistable»; each relationship gets a name that reads as a sentence and a "
              f"multiplicity at both ends; each generalization becomes an <em>is a</em> link 1 – 0..1; the «create» "
              f"dependency of checkout is left out.",
              f"The analysis diagram ({self.sec(dom['section'])}) deliberately shows only the kind of each relationship. "
              f"Before anything can be stored the analyst must say how many objects take part on each side, and the "
              f"relational model has neither inheritance nor operations ({self.sec(orm['section'])}).",
              "Every line now carries what a foreign key needs, so the tables can later be derived by rule instead of by taste."),
             (f"Attributes become private and typed — money ({', '.join(f'<code>{m}</code>' for m in money[:4])}…) becomes "
              f"<code>BigDecimal</code>, dates <code>LocalDate</code>/<code>LocalDateTime</code>, free-text states the "
              f"enumerations {', '.join(f'<code>{e}</code>' for e in enums)}. Associations get a direction and a role "
              f"name ({', '.join(f'<code>{r}</code>' for r in roles)} on Order). Behaviour arrives: "
              f"{', '.join(f'<code>{o}()</code>' for o in order_ops)}.",
              f"Design answers what each class holds, with which type, and which rule it owns ({self.sec(design['section'])}). "
              f"Binary floating point cannot hold cents; an enumeration makes an impossible state unwritable; a direction "
              f"is kept only where the code must ask the question.",
              f"The rules live in the domain classes, not in one large service, and each rule is one method a test can "
              f"call: the {len(domain_tests['tests'])} “{E(domain_tests['title'])}” tests do exactly that."),
             (f"{self.blob('tools/gen_java.py', 'def ', 'tools/gen_java.py')} writes one Java file per design class into "
              f"demo/generated; the running code started from that skeleton and keeps every name. Role names become fields, "
              f"operations become the methods below.",
              f"The code is generated from the layered model, not written from memory "
              f"({self.sec_label('sec:4.5.1', False)}), so a renamed class or a missing method is a modelling decision, not an accident.",
              f"{self.blob('tools/check_code_model.py', 'def ', 'check_code_model.py')} re-reads code, views and database on every "
              f"build: <span class=\"quote\">{E(self.check['summary'])}</span>")],
            code_a)

        db = self.db
        fk_rows = list(model.foreign_keys())
        is_a = [(c, col, p) for c, col, p, _ in fk_rows if model.FK_LABELS.get(f"{c}.{col}", ("",))[0] == "is a"]
        unique_fk = [(t["name"], c["name"]) for t in model.TABLES for c in t["columns"] if c["fk"] and c["unique"] and not c["pk"]]
        composite = [t["name"] for t in model.TABLES if sum(1 for c in t["columns"] if c["pk"]) > 1]
        renamed = [(t["source"], t["name"]) for t in model.TABLES
                   if re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", t["source"].split()[0]).lower() != t["name"]
                   and model.DESIGN_BY_NAME.get(t["source"].split()[0], {}).get("package", "").startswith("domain")]
        ev_t, ev_e = vp_schema_evidence("c42_tables"), vp_schema_evidence("c42_erd")
        rejected = re.match(r"(\d+)/(\d+)", self.sqlv["final"])
        fam = self.product_family()
        excerpt_tables = [fam["product"]] + fam["details"][:1]
        code_b = "".join(
            f'<p class="label">Generated schema · <a class="ref" href="{table_url(t)}">{SCHEMA}#L{schema_lines(t)[0]}-L{schema_lines(t)[1]}</a></p>'
            f'{code_excerpt(SCHEMA, *schema_lines(t))}' for t in excerpt_tables)

        def missing(ev):
            if not ev["missing_tables"] and not ev["missing_columns"]:
                return ""
            return (f' <span class="warn-text">Not yet in the diagram: {", ".join(f"<code>{x}</code>" for x in ev["missing_tables"] + ev["missing_columns"])} '
                    f'— the VP figures must be rebuilt after the last model change.</span>')
        chain_b = self.chain(
            "chain-data", "2 · Data: conceptual → logical → physical → database",
            "The data model is drawn at three levels in the essay — conceptual and logical in the analysis, physical in the "
            "design — and then becomes a real SQLite database.",
            [("c42_conceptual", "Conceptual"), ("c42_orm", "Logical"), ("c42_tables", "Physical"), ("c42_erd", "Database (VP ERD)"),
             (None, "Generated SQLite schema")],
            [("The entities gain their attributes and the «ORM-Persistable» stereotype; every named link gains "
              "multiplicities at both ends; generalizations become <em>is a</em> links.",
              "The conceptual level only fixes which things the shop must remember and how they relate; the logical level "
              "must say how many, before storage can be decided.",
              "Each multiplicity becomes something the database can enforce: a foreign key, a UNIQUE column or a composite key."),
             (f"Each persistent class becomes a «table» with SQL types and {{PK, FK, U, NULL}} markers"
              + (f"; {', '.join(f'<code>{s}</code> → <code>{t}</code>' for s, t in renamed)} (SQL keyword)" if renamed else "")
              + (f"; generalization becomes class-table inheritance ({', '.join(f'<code>{c}.{col}</code> → <code>{p}</code>' for c, col, p in is_a[:2])})" if is_a else "")
              + (f"; 1 – 0..1 links become a foreign key with UNIQUE ({', '.join(f'<code>{t}.{c}</code>' for t, c in unique_fk)})" if unique_fk else "")
              + (f"; composed lines get a composite key ({', '.join(f'<code>{t}</code>' for t in composite)})" if composite else "") + ".",
              f"The physical level is a design decision ({self.sec(self.figs['c42_tables']['section'])}): column types follow the "
              f"typed design classes (BigDecimal → numeric) and the rules are applied mechanically by "
              f"{self.blob('tools/gen_sql.py', 'def ', 'gen_sql.py')}.",
              f"The database itself refuses impossible values: {rejected.group(1)} of {rejected.group(2)} statements that break a "
              f"constraint were rejected in {self.file('build/sql_validation.txt', 'sql_validation.txt')}."),
             ("The same tables, on the same grid, as a Visual Paradigm entity–relationship diagram: key icons, N and U markers, "
              "crow's-foot ends with the foreign-key names, solid identifying and dashed non-identifying relationships.",
              f"The outline asks for the database to be generated in the modelling tool ({self.sec(self.figs['c42_erd']['section'])}); "
              "the ERD is Visual Paradigm's database view of the physical model.",
              f"Cardinalities and identifying keys are visible at a glance and can be checked against the model: the "
              f"exported SVG shows {ev_e['tables']}/{ev_e['n_tables']} tables and {ev_e['columns']}/{ev_e['n_columns']} column names "
              f"of <code>model.TABLES</code>.{missing(ev_e)}"),
             (f"{self.blob('tools/gen_sql.py', 'def ', 'gen_sql.py')} reads <code>model.TABLES</code> and writes the "
              f"CREATE TABLE statements in foreign-key order ({self.file(SCHEMA, 'ecom_schema_sqlite.sql')}) and the seed "
              f"({self.file(SEED, 'seed.sql')}); <code>Database.initialize</code> creates demo/data/ecom.db at the first start.",
              "Generated, not typed by hand, so the schema cannot drift away from the model.",
              f"Loaded into SQLite {E(db.version)} while this page was built: {len(db.tables)} tables, "
              f"{sum(len(v) for v in db.columns.values())} columns and {len(db.fks)} foreign keys — "
              + ("<strong>identical to the model</strong>" if db.match_tables and all(db.match_columns.values()) and db.match_fks
                 else '<span class="warn-text">different from the model</span>')
              + f"; the seed fills {sum(db.rows.values())} rows.")],
            code_b)

        uc = THREAD_UC
        trace = next(x for x in TRACE if x["uc"] == uc)
        chk = code_ref("CheckoutService.checkout")
        rt = route(trace["route"])
        caller = js_caller(*trace["ui"])
        touched = tables_touched([trace["entry"]])
        group = self.tests.group_of("Checkout")
        ok = all(self.tests.results[x]["ok"] for x in group["tests"])
        code_c = (f'<p class="label">The real code · <a class="ref" href="{chk["url"]}">{E(chk["rel"])}#L{chk["line"]}-L{chk["end"]}</a></p>'
                  f'{code_excerpt(chk["rel"], chk["line"], chk["end"])}')
        chain_c = self.chain(
            "chain-behaviour", f"3 · Behaviour: {uc} {E(self.uc_name(uc))} from activity to running code",
            "One scenario told four times, each time by a more concrete actor: swimlanes, analysis objects, design classes, "
            "and finally the method that runs.",
            [("c2_activity_checkout", "Activity"), ("c2_bce_checkout", "Analysis sequence (BCE)"),
             ("c44_checkout_seq", "Design sequence"), (None, "Runtime")],
            [("The swimlanes (customer, Họa. system, database) become messages between objects with one responsibility each: "
              "a checkout page «boundary», a checkout control «control» and the entities; a loop checks every cart line and an "
              "alt fragment separates “out of stock” from “order created”.",
              "Lecture 03: decide which object is responsible for each step before any class of code exists, without "
              "technology.",
              "It already shows that the Order — not the control — creates its lines at the frozen price and computes its "
              "own total: the rule placement the design keeps."),
             (f"The boundary becomes <code>CheckoutController</code> (customer id from the session), the control becomes "
              f"{self.sig('CheckoutService.checkout')}, the entities answer with domain methods, and storage appears as "
              f"repository interfaces.",
              f"Lecture 05 gives four roles: the controller lets a request in, the service coordinates, the domain keeps the "
              f"rules, the repository persists ({self.sec_label('sec:4.4.3', False)}).",
              "Every arrow is a method declared in tools/model.py; because the service depends on interfaces, the tests run "
              "it against a fresh SQLite database."),
             (f"The body of {self.ref_plain('CheckoutService.checkout')} follows the sequence step by step. "
              f"<code>{E(trace['route'].strip(chr(34)))}</code> in <a class=\"ref\" href=\"{rt['url']}\">WebServer</a> calls "
              f"{self.ref_plain(trace['entry'])}, which the browser reaches from "
              f"<a class=\"ref\" href=\"{caller['url']}\">{E(caller['label'])}</a>. At run time it touches "
              f"{', '.join(self.table(t) + f'<sup>{m}</sup>' for t, m, _ in touched)}.",
              "The design sequence is the specification of the method; the essay walks through the same steps.",
              f"{len(group['tests'])} “{E(group['title'])}” tests run this exact path on a seeded database — "
              + ("all pass" if ok else '<span class="warn-text">not all pass</span>')
              + ". Known limit: the stock decrease and the emptying of the cart follow the order transaction as separate "
              f"statements ({self.sec_label('sec:5.12', False)}).")],
            code_c)
        return f'''
<section class="block wrap" id="c">
  {self.head("c", "C", "Diagram evolution", "Three chains, read left to right. For every step: what changed, why, and what it bought.")}
  {chain_a}{chain_b}{chain_c}
</section>'''

    def product_family(self):
        """The product table, the tables it points to (its category), its detail tables (is a) and its other users."""
        product = next((t for t in model.TABLES if t["source"].split()[0] == "Product"), None)
        need(product, "model.TABLES has no table for the class Product")
        name = product["name"]
        fks = list(model.foreign_keys())
        parents = [(col, p, pc, model.FK_LABELS[f"{c}.{col}"]) for c, col, p, pc in fks if c == name]
        details = [c for c, col, p, _ in fks if p == name and model.FK_LABELS[f"{c}.{col}"][0] == "is a"]
        others = [(c, col, model.FK_LABELS[f"{c}.{col}"]) for c, col, p, _ in fks
                  if p == name and model.FK_LABELS[f"{c}.{col}"][0] != "is a"]
        tables = {t["name"]: t for t in model.TABLES}
        kinds = []
        for tname in [name] + [p for _, p, _, _ in parents]:
            for col in tables[tname]["columns"]:
                m = re.match(r"\s*(\w+)\s+IN\s*\((.*)\)\s*$", col["check"] or "")
                if m:
                    values = re.findall(r"'([^']*)'", m.group(2))
                    if values and {v.lower() for v in values} <= set(details) | {v.lower() for v in values if v.lower() in tables}:
                        if {v.lower() for v in values} & set(details):
                            kinds.append((tname, col["name"], values))
        return dict(product=name, parents=parents, details=details, others=others, kinds=kinds, tables=tables)

    # ----------------------------------------------------------------------------------------- D traceability
    def section_d(self):
        cards = []
        for t in TRACE:
            uc = t["uc"]
            name = self.uc_name(uc)
            reqs = [r for r in model.REQUIREMENTS if uc in r[3]]
            req_html = "".join(
                f'<li>{self.req(r[0])} <span class="tag">{E(model.REQUIREMENT_DETAILS[r[0]][0])}</span>'
                f'<span class="muted">{E(r[2])}</span></li>' for r in reqs)
            section, spec = self.spec(uc)
            goal = clean_tex(spec["Goal"][0]) if "Goal" in spec else ""
            alts = [k for k in spec if re.match(r"A\d", k)]
            rules = sorted(set(re.findall(r"BR\d+", spec.get("Rules", ("", 0))[0])))
            ana = "".join(f"<li>{self.fig(f)}</li>" for f in t["analysis"])
            des = "".join(f"<li>{self.fig(f)}</li>" for f in t["design"])
            sigs = "".join(f"<li>{self.sig(op)}</li>" for op in [t["entry"]] + t["ops"])
            impl = "".join(f"<li>{self.ref(op)}</li>" for op in [t["entry"]] + t["ops"])
            rt = route(t["route"])
            label = t.get("route_label") or t["route"].strip('"')
            caller = js_caller(*t["ui"])
            extra = "".join(f"<li>{self.ref(v)}</li>" for v in t.get("ui_extra", []))
            touched = tables_touched([t["entry"]])
            tables = "".join(f'<li title="via {E(", ".join(c + "." + mm for c, mm in via))}">{self.table(tb)}'
                             f'<span class="rw">{E(m)}</span></li>' for tb, m, via in touched)
            chosen = self.tests.select(**t["tests"])
            passed = sum(1 for x in chosen if self.tests.results[x]["ok"])
            tests = "".join(self.test_li(x) for x in chosen)
            cards.append(f'''
<article class="trace" id="trace-{uc.lower()}">
  <header class="trace-head"><p class="label">{E(uc)} · {E(next(u[2] for u in model.USE_CASES if u[0] == uc))}{E("".join(" · supported by " + a for a in model.SUPPORTING_ACTORS.get(uc, [])))}</p>
    <h3 class="h3">{E(name)}</h3><p class="muted">{goal}</p></header>
  <div class="trace-grid">
    <div><p class="col-h">1 · Requirement</p><ul class="list">{req_html}</ul></div>
    <div><p class="col-h">2 · Analysis</p>
      <p>Specification {self.sec(section)} · {len(alts)} alternative flows · rules {", ".join(rules) or "—"}
      · {self.tex_line(section["file"], section["line"])}</p><ul class="list">{ana}</ul></div>
    <div><p class="col-h">3 · Design</p><ul class="list">{des}</ul>
      <p class="mini">Signatures in tools/model.py</p><ul class="list sigs">{sigs}</ul></div>
    <div><p class="col-h">4 · Implementation</p>
      <p class="mini">HTTP endpoint</p><p><a class="route" href="{rt["url"]}">{E(label)}</a><span class="where">WebServer.java#L{rt["line"]}</span></p>
      <p class="mini">Browser (view → request)</p><ul class="list"><li><a class="ref" href="{caller["url"]}">{E(caller["label"])}</a>
        <span class="where">{E(caller["file"])}#L{caller["call_line"]}</span></li>{extra}</ul>
      <p class="mini">Java (controller → service → domain)</p><ul class="list">{impl}</ul>
      <p class="mini">Tables reached from {E(t["entry"])} <span class="muted">(R read, W write)</span></p><ul class="list tables">{tables}</ul></div>
    <div><p class="col-h">5 · Test <span class="{'ok' if passed == len(chosen) else 'bad'}">{passed}/{len(chosen)} pass</span></p>
      <ul class="tests">{tests}</ul></div>
  </div>
</article>''')
        ucs = ", ".join(t["uc"] for t in TRACE)
        return f'''
<section class="block wrap" id="d">
  {self.head("d", "D", "Design-to-code traceability", f"For {ucs}: requirement → analysis → design → implementation → test, each step a link to the exact artefact or line.")}
  <p class="muted small how">How this table is built: requirements, signatures and test results are read from tools/model.py and
  build/test_results.txt; method, route and view lines are found by searching the sources; the tables are found by
  following the calls from the controller method through the services and repository interfaces to the SQL of the
  SQLite repositories (a static scan, so it lists every table the path can reach).</p>
  {"".join(cards)}
</section>'''

    # ---------------------------------------------------------------------------------------------- E database
    def col_html(self, table, col, fk_label=True):
        marks = []
        if col["pk"]:
            marks.append("PK")
        if col["fk"]:
            marks.append("FK")
        if col["unique"]:
            marks.append("U")
        if col["nullable"]:
            marks.append("NULL")
        t = col["type"] + (f"({col['length']}" + (f",{col['scale']}" if col["scale"] else "") + ")" if col["length"] else "")
        fk = ""
        if col["fk"] and fk_label:
            name = model.FK_LABELS.get(f"{table}.{col['name']}", ("",))[0]
            fk = f'<span class="fk">→ {E(col["fk"])}{(" · " + E(name)) if name else ""}</span>'
        check = f'<span class="check">CHECK {E(col["check"])}</span>' if col["check"] else ""
        return (f'<li><span class="cname">{E(col["name"])}</span><span class="ctype">{E(t)}</span>'
                f'<span class="marks">{" ".join(marks)}</span>{fk}{check}</li>')

    def table_box(self, name, highlight=""):
        t = next(x for x in model.TABLES if x["name"] == name)
        cols = "".join(self.col_html(name, c) for c in t["columns"])
        return (f'<div class="tbox {highlight}"><p class="tbox-h">{self.table(name)}<span class="mono">{E(t["source"])} · '
                f'{self.db.rows.get(name, 0)} rows</span></p><ul class="cols">{cols}</ul></div>')

    def section_e(self):
        db = self.db
        fam = self.product_family()
        prod = fam["product"]
        tables = fam["tables"]
        # key structures, grouped by the package of the class each table stores
        groups = {}
        for t in model.TABLES:
            cls_name = t["source"].split()[0]
            c = model.DESIGN_BY_NAME.get(cls_name)
            pkg = c["package"] if c else "technical (" + t["source"] + ")"
            groups.setdefault(pkg, []).append(t)
        cards = []
        for pkg, ts in groups.items():
            items = "".join(
                f'<li>{self.table(t["name"])}<span class="muted">{E(t["source"])}</span>'
                f'<span class="mono">{len(t["columns"])} col · {db.rows.get(t["name"], 0)} rows</span></li>' for t in ts)
            cards.append(f'<div class="group"><p class="label">{E(pkg)}</p><ul class="tlist">{items}</ul></div>')
        # category / product / detail tables
        parent_boxes = "".join(self.table_box(p, "parent") for _, p, _, _ in fam["parents"])
        detail_boxes = "".join(self.table_box(d, "detail") for d in fam["details"])
        others = ", ".join(f"{self.table(c)} ({E(lbl[0])})" for c, _, lbl in fam["others"])
        story = []
        for col, parent, pcol, (lbl, pm, cm) in fam["parents"]:
            story.append(f"Every row of {self.table(prod)} points to exactly one {self.table(parent)} through "
                         f"<code>{prod}.{col}</code> → <code>{parent}.{pcol}</code> (“{E(lbl)}”, {E(pm)} – {E(cm)}).")
        for tname, col, values in fam["kinds"]:
            pairs = ", ".join(f"<code>{v}</code> → {self.table(v.lower())}" for v in values if v.lower() in fam["details"])
            where = "its category" if tname != prod else "the product row itself"
            story.append(f"<code>{tname}.{col}</code> names the detail table that holds the specific attributes, so "
                         f"{where} decides where the rest of a product lives: {pairs}.")
        if fam["details"]:
            story.append(f"The detail tables use class-table inheritance: their primary key is also the foreign key to "
                         f"{self.table(prod)} (“is a”, 1 – 0..1), so a painting or a frame is one product row plus one detail row.")
        if fam["others"]:
            story.append(f"Other tables point at a product without being a kind of product: {others}.")
        seed_parent = ""
        for _, parent, _, _ in fam["parents"]:
            cols = db.columns[parent]
            rows = db.query(f'SELECT * FROM "{parent}" ORDER BY 1')
            counts = dict(db.query(f'SELECT "{fam["parents"][0][0]}", COUNT(*) FROM "{prod}" GROUP BY 1'))
            head = "".join(f"<th>{E(c)}</th>" for c in cols) + f"<th>{E(prod)} rows</th>"
            body = "".join("<tr>" + "".join(f"<td>{E(v)}</td>" for v in r) + f"<td>{counts.get(r[0], 0)}</td></tr>" for r in rows)
            seed_parent += (f'<p class="label">Rows of {E(parent)} in the seed data</p><div class="table-wrap">'
                            f'<table class="plain small"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
        design_cls = [model.DESIGN_BY_NAME.get(tables[p]["source"].split()[0]) for _, p, _, _ in fam["parents"]]
        design_note = ""
        for c in [x for x in design_cls if x]:
            ops = ", ".join(self.ref_plain(f"{c['name']}.{o['name']}") for o in c["ops"])
            enums = [a["type"] for a in c["attrs"] if model.DESIGN_BY_NAME.get(a["type"], {}).get("kind") == "enum"]
            lits = "; ".join(f"<code>{e}</code> = {', '.join(model.DESIGN_BY_NAME[e]['literals'])}" for e in enums)
            design_note += (f'<p class="muted small">In the design model the class {self.ref_plain(c["name"])} '
                            f'({E(c["package"])}) carries it{(" with the enumeration " + lits) if lits else ""}'
                            f'{(" and the operation " + ops) if ops else ""}.</p>')
        # mapping rules applied (computed from the model)
        fks = list(model.foreign_keys())
        embedded = [t for t in model.TABLES if "+" in t["source"]]
        is_a = [(c, col, p) for c, col, p, _ in fks if model.FK_LABELS[f"{c}.{col}"][0] == "is a"]
        one_many = [(c, col, p) for c, col, p, _ in fks if model.FK_LABELS[f"{c}.{col}"][2].endswith("*")]
        unique_fk = [(t["name"], c["name"]) for t in model.TABLES for c in t["columns"] if c["fk"] and c["unique"] and not c["pk"]]
        composite = [t["name"] for t in model.TABLES if sum(1 for c in t["columns"] if c["pk"]) > 1]
        money = [(t["name"], c["name"]) for t in model.TABLES for c in t["columns"] if c["type"] == "numeric" and c["scale"] == 2]
        checks = [(t["name"], c["name"]) for t in model.TABLES for c in t["columns"] if c["check"]]
        technical = [t["name"] for t in model.TABLES
                     if not model.DESIGN_BY_NAME.get(t["source"].split()[0], {}).get("package", "").startswith("domain")]
        renamed = [(t["source"], t["name"]) for t in model.TABLES
                   if re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", t["source"].split()[0]).lower() != t["name"]
                   and model.DESIGN_BY_NAME.get(t["source"].split()[0], {}).get("package", "").startswith("domain")]
        code = lambda xs: ", ".join(f"<code>{E(x)}</code>" for x in xs)  # noqa: E731
        rules = [
            ("Persistent class → table", "lower case with underscores",
             code([f"{s} → {t}" for s, t in renamed]) + " (SQL keyword)" if renamed else "—", len(model.TABLES)),
            ("Value object 1 – 1", "embedded as columns of the owner", code([t["source"] + " → " + t["name"] for t in embedded]), len(embedded)),
            ("Generalization", "child table reuses the parent key as PK and FK", code([f"{c}.{col} → {p}" for c, col, p in is_a[:3]]), len(is_a)),
            ("Kind of detail", "a CHECK column names the detail table", code([f"{t}.{c}" for t, c, _ in fam["kinds"]]) or "—", len(fam["kinds"])),
            ("Association 1 – *", "foreign key on the many side", code([f"{c}.{col} → {p}" for c, col, p in one_many[:3]]), len(one_many)),
            ("Association 1 – 0..1", "foreign key with UNIQUE", code([f"{t}.{c}" for t, c in unique_fk]), len(unique_fk)),
            ("Composition with lines", "composite primary key", code(composite), len(composite)),
            ("Money", "numeric(12,2) in US dollars", code([f"{t}.{c}" for t, c in money[:3]]), len(money)),
            ("Rules in the data", "CHECK constraints (ranges, allowed states)", code([f"{t}.{c}" for t, c in checks[:3]]), len(checks)),
            ("Technical table", "data for a non-domain class (search index)", code(technical) or "—", len(technical)),
        ]
        rule_rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td class='num'>{n}</td></tr>" for a, b, c, n in rules)
        # design class -> table -> schema, compared with the generated schema
        map_rows = []
        for t in model.TABLES:
            sources = [s.strip() for s in t["source"].split("+")]
            attrs = {}
            for s in sources:
                c = model.DESIGN_BY_NAME.get(s.split()[0])
                for a in (c["attrs"] if c else []):
                    attrs[re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", a["name"]).lower()] = f"{s.split()[0]}.{a['name']}"
            cols = []
            for col in t["columns"]:
                origin = attrs.get(col["name"])
                if not origin and col["fk"]:
                    roles = [a for a in model.DESIGN_ASSOCIATIONS if a["src"] == sources[0].split()[0]]
                    origin = next((f"{a['src']}.{a['role']}" for a in roles
                                   if model.DESIGN_BY_NAME.get(a["dst"]) and col["fk"].split(".")[0] in
                                   [x["name"] for x in model.TABLES if x["source"].split()[0] == a["dst"]]), "")
                    origin = origin or ("inherited key" if col["pk"] else "")
                cols.append(f'<li><code>{E(col["name"])}</code><span class="muted">{E(origin or "—")}</span></li>')
            ok_cols = db.match_columns.get(t["name"])
            ok_fk = {f for f in db.fks if f[0] == t["name"]} == {f for f in db.model_fks if f[0] == t["name"]}
            state = '<span class="ok">✓ same</span>' if ok_cols and ok_fk else '<span class="bad">differs</span>'
            map_rows.append(f'<tr><td>{E(t["source"])}</td><td>{self.table(t["name"])}</td>'
                            f'<td class="num">{len(t["columns"])}</td><td class="num">{sum(1 for f in db.model_fks if f[0] == t["name"])}</td>'
                            f'<td>{state}</td><td><details><summary>columns</summary><ul class="colmap">{"".join(cols)}</ul></details></td></tr>')
        ev = [vp_schema_evidence("c42_tables"), vp_schema_evidence("c42_erd")]
        ev_html = "".join(
            f'<li>{self.thumb(e["id"], size="small")}<p><strong>{e["tables"]}/{e["n_tables"]}</strong> tables and '
            f'<strong>{e["columns"]}/{e["n_columns"]}</strong> column names of <code>model.TABLES</code> appear in '
            f'{self.file("figures/vp/" + e["id"] + ".svg", e["id"] + ".svg")}.'
            + (f' <span class="warn-text">Missing: {", ".join(f"<code>{x}</code>" for x in e["missing_tables"] + e["missing_columns"])}'
               f' — rebuild the VP figures after the model change.</span>' if e["missing_tables"] or e["missing_columns"] else "")
            + "</p></li>" for e in ev)
        steps = [("Conceptual", self.fig("c42_conceptual", "c42_conceptual")), ("Logical", self.fig("c42_orm", "c42_orm")),
                 ("Physical", self.fig("c42_tables", "c42_tables")), ("VP database", self.fig("c42_erd", "c42_erd")),
                 ("Generator", self.blob("tools/gen_sql.py", "def ", "tools/gen_sql.py")),
                 ("Schema", self.file(SCHEMA, "ecom_schema_sqlite.sql")), ("Seed", self.file(SEED, "seed.sql")),
                 ("At start", self.ref_plain("Database.initialize", "Database.initialize"))]
        path = "".join(f'<li><p class="label">{E(a)}</p>{b}</li>' for a, b in steps)
        same = db.match_tables and all(db.match_columns.values()) and db.match_fks
        return f'''
<section class="block wrap" id="e">
  {self.head("e", "E", "Database design &amp; generation", f"{len(model.TABLES)} tables and {len(list(model.foreign_keys()))} foreign keys, generated from <code>model.TABLES</code> and checked against it.")}
  <div class="groups">{"".join(cards)}</div>

  <h3 class="h3 sub top-gap">Products, their {E(", ".join(p for _, p, _, _ in fam["parents"]) or "kinds")} and the detail tables</h3>
  <div class="family">
    <div class="family-text">{"".join(f"<p>{s}</p>" for s in story)}{design_note}{seed_parent}</div>
    <div class="family-boxes">
      <div class="fam-row">{parent_boxes}</div>
      <div class="fam-row">{self.table_box(prod, "main")}</div>
      <div class="fam-row details">{detail_boxes}</div>
    </div>
  </div>

  <h3 class="h3 sub top-gap">From the data models to the database</h3>
  <ol class="dbpath">{path}</ol>
  <div class="table-wrap"><table class="plain">
    <thead><tr><th>Case</th><th>Rule applied by gen_sql.py</th><th>Examples in the model</th><th class="num">How many</th></tr></thead>
    <tbody>{rule_rows}</tbody></table></div>

  <h3 class="h3 sub top-gap">Design classes ↔ the real schema</h3>
  <p class="muted">Each table, the class it stores, and a comparison with the schema SQL loaded into SQLite {E(db.version)}
  while this page was built: {"<strong>all tables, columns and foreign keys are the same as in the model</strong>" if same else '<span class="warn-text">the schema differs from the model</span>'}.
  The live database file is compared by {self.blob("tools/check_code_model.py", "def ", "check_code_model.py")} as well.</p>
  <div class="table-wrap"><table class="plain map">
    <thead><tr><th>Design class</th><th>Table</th><th class="num">Columns</th><th class="num">FKs</th><th>Schema</th><th>Column ← attribute</th></tr></thead>
    <tbody>{"".join(map_rows)}</tbody></table></div>

  <h3 class="h3 sub top-gap">Visual Paradigm evidence</h3>
  <ul class="evidence">{ev_html}</ul>
  <p class="muted small">Both diagrams are in the VP project {self.file(self.vpp, "vp/tieuluan_design.vpp")}; their text was read from the SVG export.</p>
</section>'''

    # --------------------------------------------------------------------------------------------- F live demo
    def accounts(self):
        db = self.db
        out = []
        for cid, first, middle, last in db.query("SELECT customer_id, first_name, middle_name, last_name FROM customer ORDER BY 1"):
            name = " ".join(x for x in (last, middle, first) if x)
            vip = db.query(f"SELECT discount_rate FROM customer_vip WHERE customer_id = '{cid}'")
            new = db.query(f"SELECT 1 FROM customer_new WHERE customer_id = '{cid}'")
            kind = f"VIP, {float(vip[0][0]) * 100:g} % discount" if vip else ("new customer" if new else "customer")
            orders = [r[0] for r in db.query(f"SELECT order_id FROM orders WHERE customer_id = '{cid}' ORDER BY 1")]
            out.append((cid, name, kind, orders))
        session = JAVA_ROOT + "presentation/web/SessionManager.java"
        need('"ADMIN"' in read(session), "SessionManager has no ADMIN account")
        out.append(("ADMIN", "Gallery administrator", "back office: paintings and order status", []))
        return out

    def section_f(self):
        port, off_port = self.props.get("server.port"), self.offline_props.get("server.port")
        need(port and off_port, "server.port missing in demo/config/*.properties")
        q = model.DEMO_QUERIES
        order_id = re.search(r"\d{6,}", q[3]).group(0)
        owner = self.db.query(f"SELECT customer_id FROM orders WHERE order_id = '{order_id}'")
        need(owner, f"demo order {order_id} is not in the seed data")
        owner = owner[0][0]
        other = next(c for c, *_ in self.db.query("SELECT customer_id FROM customer ORDER BY 1") if c != owner)
        placed = self.db.query(f"SELECT order_id FROM orders WHERE customer_id = '{other}' AND status = 'PLACED' ORDER BY 1")
        cancel_hint = f"cancel your own order {placed[0][0]}" if placed else "cancel one of your orders that is not shipped"
        flows = [
            ("Describe it — or say it", ["UC02", "UC03"], ["search_text", "search_voice"],
             [f"Type “{q[0]}” in the search box and press Search.",
              f"Press the microphone and say “{q[1]}”; correct the transcript if needed, then search."],
             "Gemma 4 turns the sentence into filters and every card says why it was chosen; the transcript stays editable "
             "and the audio goes only to the Whisper server on the same laptop.",
             ["QueryService.textQuery", "SpeechService.transcribe", "WhisperClient.transcribe"]),
            ("Show a photo, then hang it on your wall", ["UC04", "UC14"], ["search_image", "room_preview"],
             ["Choose “find paintings similar to a photo” and upload a photo of a painting.",
              "Open “Find for my room”, upload a room photo, pick one of the suggestions and place it on the wall."],
             "A similarity on every result; for the room, the palette and mood Gemma 4 read and one concrete reason per painting.",
             ["ImageService.embed", "SearchService.searchRoom", "RoomPreview.placePainting"]),
            ("Buy it, then ship it", ["UC06", "UC07", "UC13"], ["cart", "checkout", "admin_orders"],
             [f"As {owner}, add a print and a frame to the cart.",
              "Check out: choose a saved address or type a new one, pay cash or by card.",
              "Switch to ADMIN and move the new order one status forward."],
             "The VIP discount and the shipping fee in the total; stock goes down and the cart empties; the back office "
             "offers only the next valid status.",
             ["CheckoutService.checkout", "Order.calculateTotal", "Order.advanceTo"]),
            ("Ask the curator — and try to peek", ["UC10", "UC09", "UC11"], ["assistant", "order_forbidden", "order_cancel"],
             [f"Open the assistant and ask “{q[4]}”.",
              f"Switch to {other} and look up order {order_id} (it belongs to {owner}).",
              f"Still as {other}, {cancel_hint}."],
             "The assistant calls a read-only tool for the signed-in customer; another customer's order is answered exactly "
             "like a missing one; only orders that are not shipped can be cancelled.",
             ["AssistantService.ask", "Order.isOwnedBy", "Order.cancel"]),
            ("Pull the plug on Gemma", ["UC02", "UC10"], ["ai_fallback"],
             [f"Start the second copy whose Gemma address leads nowhere: <code>./run.sh config/app.offline.properties</code> "
              f"(port {E(off_port)}).", f"Search “{q[1]}” and ask “{q[4]}” again."],
             "Keyword rules and rule-based tools answer instead, the page says so, and nothing breaks (NFR02).",
             ["QueryService.parseRules", "AssistantService.ask"]),
        ]
        cards = []
        for k, (title, ucs, shots, steps, notice, refs) in enumerate(flows, 1):
            shots_html = "".join(self.thumb(s, size="shot") for s in shots)
            steps_html = "".join(f"<li>{s if '<code>' in s else E(s)}</li>" for s in steps)
            refs_html = " · ".join(self.ref_plain(r) for r in refs)
            uc_html = " ".join(f'<a class="chip" href="#trace-{u.lower()}" title="{E(self.uc_name(u))}">{u}</a>'
                               if any(t["uc"] == u for t in TRACE) else f'<span class="chip" title="{E(self.uc_name(u))}">{u}</span>' for u in ucs)
            cards.append(f'''<article class="flow"><div class="flow-text"><p class="label">Flow {k} · {uc_html}</p>
              <h3 class="h3">{E(title)}</h3><ol class="steps-list">{steps_html}</ol>
              <p class="notice-line"><span class="k">Notice</span>{E(notice)}</p><p class="small muted">Behind it: {refs_html}</p></div>
              <div class="flow-shots n{len(shots)}">{shots_html}</div></article>''')
        accounts = "".join(f'<tr><td><code>{E(c)}</code></td><td>{E(n)}</td><td>{E(k)}</td><td>{E(", ".join(o)) or "—"}</td></tr>'
                           for c, n, k, o in self.accounts())
        url = f"http://127.0.0.1:{port}"
        return f'''
<section class="block wrap" id="f">
  {self.head("f", "F", "Live demo", "The shop itself runs on the presenter's laptop. Start it, then show these five flows.")}
  <div class="run" id="run">
    <div class="run-steps">
      <p class="label">Run it locally</p>
      <pre class="cmd"><code>git clone {REPO}.git
cd Hoa/demo
./run.sh          # Whisper on {E(self.props.get("whisper.baseUrl", "").replace("http://", ""))}, then the shop on :{E(port)}
./test.sh         # the tests and the code–model check</code></pre>
      <p class="small muted">JDK&nbsp;17+ and Python&nbsp;3; the first start downloads the Whisper model once. Gemma&nbsp;4 needs the
      key in <code>demo/config/app.local.properties</code> (not in git); without it every AI feature uses its fallback.
      Details: {self.file("demo/README.md", "demo/README.md")}, {self.file("demo/run.sh", "run.sh")},
      {self.file("demo/config/app.properties", "app.properties")}.</p>
      <a class="btn solid" href="{url}/" rel="nofollow">Open the shop · {E(url.replace("http://", ""))}</a>
      <p class="notice-box"><strong>Not on GitHub Pages.</strong> This page is static; the shop needs the local Java server
      (and the Whisper server) started with <code>./run.sh</code>. The button only works on the machine where it runs.</p>
    </div>
    <div class="accounts"><p class="label">Demo accounts (switcher in the top bar)</p>
      <div class="table-wrap"><table class="plain"><thead><tr><th>Account</th><th>Name</th><th>Kind</th><th>Orders in the seed</th></tr></thead>
      <tbody>{accounts}</tbody></table></div>
      {self.thumb("home", size="shot")}</div>
  </div>
  <div class="flows">{"".join(cards)}</div>
</section>'''

    # ------------------------------------------------------------------------------------------ G verification
    def requirement_evidence(self):
        stories = {}
        for c, _ in longtable(self.ch[2], "tab:stories"):
            sid = clean_tex(c[0], True)
            stories[sid] = expand_ids(" ".join(re.findall(r"\(([^)]*)\)", clean_tex(c[1], True))))
        groups = []
        for c, _ in longtable(self.ch[5], "tab:tests"):
            name = clean_tex(c[0], True)
            ids = expand_ids(clean_tex(c[2], True))
            covered = set(ids) | {r for s in ids if s.startswith("US") for r in stories.get(s, [])}
            hits = [g for g in self.tests.groups if g["title"].split(" (")[0].split(":")[0].startswith(name.split()[0])]
            need(hits, f"test group {name!r} of the essay table tab:tests not found in build/test_results.txt")
            groups.append((name, hits[0], covered))
        nfr = {}
        for c, _ in longtable("report/generated/nfr_check.tex", "tab:nfrcheck"):
            nfr[clean_tex(c[0], True)] = clean_tex(c[2])
        flows_ucs = {"UC02", "UC03", "UC04", "UC14", "UC06", "UC07", "UC13", "UC10", "UC09", "UC11"}
        rows = []
        for rid, kind, title, ucs in model.REQUIREMENTS:
            by_group = [g for name, g, cov in groups if rid in cov]
            named = [n for n in self.tests.results if f"({rid})" in n or f" {rid})" in n or f"({rid}," in n]
            tests = sorted({t for g in by_group for t in g["tests"]} | set(named))
            ok = all(self.tests.results[t]["ok"] for t in tests)
            prio = model.REQUIREMENT_DETAILS[rid][0]
            evidence = []
            if tests:
                evidence.append(f'<span class="{"ok" if ok else "bad"}">{len(tests)} tests {"pass" if ok else "— some fail"}</span>'
                                f' <span class="muted">({E(", ".join(g["title"].split(" (")[0] for g in by_group) or "named in the test")})</span>')
            if rid in nfr:
                evidence.append(f'<span class="muted">{nfr[rid]}</span>')
            if not tests and set(ucs) & flows_ucs:
                evidence.append('<span class="muted">shown in the <a href="#f">live demo</a></span>')
            if not evidence:
                evidence.append(f'<span class="muted">specified in the essay; no automated test ({E(", ".join(ucs))})</span>')
            status = "tested" if tests and ok else ("failing" if tests else "demo")
            rows.append(f'<tr class="{status}"><td>{self.req(rid)}</td><td>{E(title)}</td><td>{E(prio)}</td>'
                        f'<td>{E(", ".join(ucs))}</td><td>{"<br>".join(evidence)}</td></tr>')
        return rows

    def section_g(self):
        n = self.counts()
        rows = self.requirement_evidence()
        tested = sum(1 for r in rows if r.startswith('<tr class="tested"'))
        ev = self.eval["summary"]
        sv = self.voice["en"]["summary"]

        def pct(x):
            return f"{x:.2f}"

        def bar(value, label):
            return (f'<span class="meter" title="{E(label)}: {value:.2f}"><span style="width:{max(0.0, min(1.0, value)) * 100:.0f}%"></span></span>'
                    f'<span class="num">{value:.2f}</span>')
        search_rows = []
        for key, label in [("text/Gemma 4/direct", "Text, Gemma 4"), ("text/keyword rules/direct", "Text, keyword rules (offline)"),
                           ("text/Gemma 4/paraphrased", "Paraphrases, Gemma 4"), ("text/keyword rules/paraphrased", "Paraphrases, keyword rules"),
                           ("voice/Whisper + Gemma 4", "Voice, Whisper + Gemma 4"), ("image/Gemma 4 vision", "Image, Gemma 4 vision"),
                           ("image/local colour", "Image, local colour (offline)")]:
            need(key in ev, f"build/eval/eval_results.json has no summary {key!r}")
            s = ev[key]
            search_rows.append(f'<tr><td>{E(label)}</td><td class="num">{s["n"]}</td><td class="bar">{bar(s["hit1"], label + " Hit@1")}</td>'
                               f'<td class="num">{pct(s["mrr"])}</td><td class="num">{s["seconds"]:.2f}</td></tr>')
        asst = [(k, ev[k]) for k in ev if k.startswith("assistant/")]
        asst_rows = "".join(f'<tr><td>{E(k.split("/", 1)[1])}</td><td class="num">{v["n"]}</td><td class="num">{v["correct"]}/{v["n"]}</td>'
                            f'<td class="num">{v["tool_ok"]}/{v["n"]}</td><td class="num">{v["leaks"]}</td></tr>' for k, v in asst)
        five = [[clean_tex(x) for x in c] for c, _ in longtable(self.ch[3], "tab:fiveai")]
        fallback = [[clean_tex(x) for x in c] for c, _ in longtable(self.ch[3], "tab:fallback")]
        fb_rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in fallback)
        strip_number = re.compile(r"^\d+\.\s*")
        five_html = "".join(f'<li><p class="label">Feature {k}</p><strong>{strip_number.sub("", f[0])}</strong>'
                            f'<span class="muted">{f[1]} · {f[2]}</span><span class="small">{f[3]}</span></li>'
                            for k, f in enumerate(five, 1))
        limits = itemize_after(self.ch[5], "sec:5.12")
        lim_html = "".join(f'<li><strong>{E(x["title"])}.</strong> {x["text"]}</li>' for x in limits)
        chk = self.check
        sqlv = self.sqlv
        db = self.db
        ce = [f for f in self.figs.values() if not f["trial"]]
        trial = [f for f in self.figs.values() if f["trial"]]
        rejected_ratio = re.match(r"(\d+/\d+)", sqlv["final"]).group(1)
        decisions = [
            ("Declare every name once", f'{self.blob("tools/model.py", "REQUIREMENTS = [", "tools/model.py")} is the only place where '
             "requirements, use cases, classes, methods and tables are written; diagrams, SQL, Java skeleton and essay tables "
             "are generated from it, so a change is made once and appears everywhere."),
            ("Three layers, one shared domain", f"Presentation → Application → Data with dependencies pointing down only; "
             f"the domain classes are shared by all three ({self.fig('c44_packages', 'packages')}). The checker verifies the imports of every file."),
            ("Rules live in the domain", f"{self.ref_plain('Order.cancel')}, {self.ref_plain('Order.advanceTo')}, "
             f"{self.ref_plain('Order.isOwnedBy')} and {self.ref_plain('OrderItem.fromCartItem')} hold the business rules; "
             "services only coordinate."),
            ("AI behind interfaces, always with a way back", f"{self.ref_plain('LlmClient')} and {self.ref_plain('SpeechClient')} "
             "hide Gemma 4 and Whisper; every AI feature has a rule-based path, so the shop works when the model does not."),
            ("Privacy as a requirement", f"The identity comes from {self.ref_plain('SessionManager')}, never from the request; "
             "another customer's order looks exactly like a missing one; Whisper runs on the laptop so audio never leaves it."),
            ("Generated database with constraints", f"Class-table inheritance, foreign keys, UNIQUE and CHECK constraints "
             f"generated by {self.blob('tools/gen_sql.py', 'def ', 'gen_sql.py')}, so the database itself refuses impossible data."),
        ]
        dec_html = "".join(f"<li><strong>{E(a)}.</strong> {b}</li>" for a, b in decisions)
        return f'''
<section class="block wrap" id="g">
  {self.head("g", "G", "Verification &amp; conclusion", "What is met, the technical evidence, what is still missing, and the decisions that made it consistent.")}
  <ul class="evidence-tiles">
    <li><span class="stat-n">{self.tests.passed}/{len(self.tests.results)}</span><span class="stat-l">tests pass</span>
      <span class="stat-s">{len(self.tests.groups)} groups · run {E(self.tests.date)} · {self.file("build/test_results.txt", "output", "plain")}</span></li>
    <li><span class="stat-n">{"OK" if chk["ok"] and not chk["fails"] else "FAIL"}</span><span class="stat-l">code = model</span>
      <span class="stat-s">{chk["oks"]} checks OK, {len(chk["notes"])} notes, {len(chk["fails"])} failures · run while building this page</span></li>
    <li><span class="stat-n">{E(rejected_ratio)}</span><span class="stat-l">bad SQL rejected</span>
      <span class="stat-s">{E(sqlv["created"])} · {self.file("build/sql_validation.txt", "output", "plain")}</span></li>
    <li><span class="stat-n">{len(db.tables)}/{len(model.TABLES)}</span><span class="stat-l">tables as modelled</span>
      <span class="stat-s">{db.n_columns} columns, {len(db.model_fks)} foreign keys compared</span></li>
    <li><span class="stat-n">{len(ce)} + {len(trial)}</span><span class="stat-l">VP figures</span>
      <span class="stat-s">CE exports checked for the CE footer and no watermark; {len(trial)} trial screenshots</span></li>
    <li><span class="stat-n" id="link-count">—</span><span class="stat-l">links verified</span>
      <span class="stat-s">files, GitHub lines and anchors, checked by the generator</span></li>
  </ul>
  <p class="quote-line"><span class="label">check_code_model.py</span> {E(chk["summary"])}</p>

  <h3 class="h3 sub top-gap">Requirements met <span class="muted">— {tested} of {len(rows)} backed by passing tests, the rest shown in the demo or the essay</span></h3>
  <div class="table-wrap"><table class="plain reqs"><thead><tr><th>ID</th><th>Requirement</th><th>Priority</th><th>Use cases</th><th>Evidence</th></tr></thead>
  <tbody>{"".join(rows)}</tbody></table></div>
  <p class="muted small">Tests are matched to requirements through the essay's table of test groups and user stories
  ({self.sec_label("sec:5.10", False)}) and through requirement ids named in the test names.</p>

  <h3 class="h3 sub top-gap" id="ai">AI: five features, one fallback principle, measured</h3>
  <ul class="five">{five_html}</ul>
  <div class="grid-2">
    <div><p class="label">Search quality (evaluation of {E(self.eval["date"])}, {self.file("build/eval/eval_summary.txt", "summary", "plain")})</p>
      <div class="table-wrap"><table class="plain"><thead><tr><th>Input</th><th class="num">n</th><th>Hit@1</th><th class="num">MRR</th><th class="num">s/query</th></tr></thead>
      <tbody>{"".join(search_rows)}</tbody></table></div>
      <p class="small muted">Whisper (model {E(sv["model"])}, {E(sv["device"])}): WER {sv["wer"] * 100:.1f}% on {sv["n_utterances"]} English
      sentences, mean {sv["mean_seconds"]:.2f} s per sentence (max {sv["max_seconds"]:.2f} s) — NFR08's 3 s limit
      {"met" if sv["nfr08_met"] else "not met"}. Synthetic voices: an upper bound.</p></div>
    <div><p class="label">Assistant with tool calling</p>
      <div class="table-wrap"><table class="plain"><thead><tr><th>Mode</th><th class="num">n</th><th class="num">correct</th><th class="num">right tool</th><th class="num">leaked words</th></tr></thead>
      <tbody>{asst_rows}</tbody></table></div>
      <p class="label top-gap">When an AI component fails ({self.sec_label("sec:3.11", False)})</p>
      <div class="table-wrap"><table class="plain small"><thead><tr><th>Failure</th><th>Behaviour</th><th>Customer sees</th><th>Req.</th></tr></thead>
      <tbody>{fb_rows}</tbody></table></div></div>
  </div>

  <div class="grid-2 top-gap">
    <div><h3 class="h3 sub">Limitations ({self.sec_label("sec:5.12", False)})</h3><ul class="limits">{lim_html}</ul></div>
    <div><h3 class="h3 sub">Key design decisions</h3><ul class="limits">{dec_html}</ul></div>
  </div>
  <div class="conclusion">
    <p class="label">Conclusion</p>
    <p>The essay follows one product through the five steps of the course, and this page shows that the steps are
    connected: each requirement has a use case, each use case its diagrams, each diagram the classes and tables it
    became, and each of those the lines of code and the tests that run them. The figures, the database and the code are
    generated from the same specification and checked against it on every build, the AI features are measured and
    can fail without breaking the shop, and the limits that remain are written down rather than hidden.</p>
    <p class="small muted">The essay's own conclusion: {self.file(self.pdf_rel, "essay PDF")}, chapter “Conclusion”.</p>
  </div>
</section>'''

    # ---------------------------------------------------------------------------------------------- gallery
    def gallery(self):
        chapters = []
        chips = []
        for ch in range(1, 6):
            figs = [f for f in self.figs.values() if f["chapter"] == ch]
            if not figs:
                continue
            title = self.essay.chapter_title(ch)
            chips.append(f'<a class="chip" href="#ch{ch}">Chapter {ch} · {len(figs)}</a>')
            cards = []
            for f in figs:
                where = self.sec(f["section"], with_title=True) if f["section"] else '<span class="muted">not in the essay — kept for the slides</span>'
                cards.append(f'<li>{self.thumb(f["id"], note=E(f["desc"]))}<p class="card-sec">{where}</p></li>')
            chapters.append(f'''<div class="chapter" id="ch{ch}"><div class="chapter-head"><p class="label">Chapter {ch}</p>
              <h3 class="h3">{E(title)}</h3>{self.sec(self.essay.section(str(ch)))}</div>
              <ul class="cards">{"".join(cards)}</ul></div>''')
        n = self.counts()
        return f'''
<section class="block wrap" id="diagrams">
  <div class="sec-head"><span class="letter" aria-hidden="true">+</span><div><p class="label">Appendix</p>
  <h2 class="h2">All {n["figs"]} diagrams, in essay order</h2>
  <p class="lead">{n["ce"]} exported from Visual Paradigm Community Edition; {n["trial"]} are screenshots of the VP window in
  the Enterprise edition's 30-day trial, because Community Edition cannot draw BPMN, ArchiMate or DFD diagrams.
  Click a card for the full figure; ← and → move through all of them.</p></div></div>
  <nav class="chips chapter-chips" aria-label="Chapters">{"".join(chips)}</nav>
  {"".join(chapters)}
</section>'''

    def footer(self):
        sources = ["tools/model.py", "figures/vp/README.md", "build/test_results.txt", "build/eval/eval_results.json",
                   "build/sql_validation.txt", self.pdf_rel]
        return f'''
<footer class="footer">
  <div class="wrap footer-in">
    <div><p class="label">Built from the repository</p>
    <p>Generated by {self.blob("tools/build_showcase.py", "def main", "tools/build_showcase.py")} from
    {", ".join(self.file(s, s.split("/")[-1], "plain") for s in sources)}, the essay sources and the demo code.
    Rebuild: <code>python3 tools/build_showcase.py</code>.</p></div>
    <div><p class="label">Essay</p><p>{E(self.author)} · {E(self.student_id)} · Class {E(self.class_name)}<br>
    {E(self.course)} · PTIT · individual essay</p></div>
  </div>
  <div class="wordmark" aria-hidden="true">Họa.</div>
  <div class="wrap footer-note"><span>Paintings: Wikimedia Commons · public domain</span><span>Diagrams: Visual Paradigm 18.1</span></div>
</footer>'''

    def lightbox_data(self):
        items = []
        for group, source in (("diagrams", self.figs), ("screens", self.shots)):
            for f in source.values():
                kind = "screen" if group == "screens" else ("trial" if f["trial"] else "ce")
                sec = f["section"]
                page = f.get("page")
                vector = None
                if kind == "ce" and (ROOT / f"figures/vp/{f['id']}.pdf").exists():
                    vector = LINKS.file(f"figures/vp/{f['id']}.pdf")
                items.append(dict(id=f["id"], group=group, src=LINKS.file(f["png"]), w=f["w"], h=f["h"], title=f["title"],
                                  desc=f.get("desc") or re.sub(r"<[^>]+>", "", f.get("caption", "")),
                                  kind=kind, fig=f"Figure {f['number']}" if f["number"] else "",
                                  sec=f"§{sec['number']} {sec['title']}" if sec else "",
                                  pdf=self.pdf_href(page) if page is not None else "",
                                  page=self.pdf.label(page) if page is not None else "", vector=vector or ""))
        return items

    def render(self):
        body = (self.header() + "<main>" + self.hero() + self.section_a() + self.section_b() + self.section_c()
                + self.section_d() + self.section_e() + self.section_f() + self.section_g() + self.gallery() + "</main>"
                + self.footer())
        data = json.dumps(self.lightbox_data(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        fonts = "".join(
            f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{wt};font-display:swap;"
            f"src:url({LINKS.file(f'demo/web/fonts/{file}-{wt}-{sub}.woff2')}) format('woff2');unicode-range:{rng}}}"
            for fam, file, weights in (("Inter Tight", "InterTight", (300, 400, 500)), ("JetBrains Mono", "JetBrainsMono", (400, 500)))
            for wt in weights for sub, rng in FONT_RANGES)
        title = "Họa. — from requirements to running code"
        desc = (f"Defense showcase of the individual course essay of {self.author} ({self.student_id}): "
                "the painting shop Họa. from requirements to running code.")
        return f'''<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<meta name="generator" content="tools/build_showcase.py">
<link rel="icon" href="{FAVICON}">
<script>try{{var t=localStorage.getItem("hoa-showcase-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t;}}catch(e){{}}</script>
<style>{fonts}{CSS}</style>
</head>
<body>
{body}
<div class="lb" id="lb" role="dialog" aria-modal="true" aria-labelledby="lb-title" hidden>
  <div class="lb-bar"><span class="mono" id="lb-count"></span><span id="lb-badge"></span><span class="spacer"></span>
    <button type="button" class="btn small" id="lb-zoom" aria-pressed="false">Actual size</button>
    <a class="btn small" id="lb-png" href="#" target="_blank" rel="noopener">Full-size PNG</a>
    <a class="btn small" id="lb-vector" href="#" target="_blank" rel="noopener">Vector PDF</a>
    <button type="button" class="btn small" id="lb-close" aria-label="Close (Esc)">Close ✕</button></div>
  <div class="lb-stage" id="lb-stage"><img id="lb-img" alt=""></div>
  <button type="button" class="lb-nav prev" id="lb-prev" aria-label="Previous (←)">←</button>
  <button type="button" class="lb-nav next" id="lb-next" aria-label="Next (→)">→</button>
  <div class="lb-cap"><p class="label" id="lb-meta"></p><h3 class="h3" id="lb-title"></h3><p id="lb-desc"></p></div>
</div>
<script id="figs" type="application/json">{data}</script>
<script>{JS}</script>
</body>
</html>
'''


FONT_RANGES = [
    ("vietnamese", "U+0102-0103,U+0110-0111,U+0128-0129,U+0168-0169,U+01A0-01A1,U+01AF-01B0,U+0300-0301,U+0303-0304,"
                   "U+0308-0309,U+0323,U+0329,U+1EA0-1EF9,U+20AB"),
    ("latin-ext", "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,"
                  "U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C4,U+2113,U+2C60-2C7F,U+A720-A7FF"),
    ("latin", "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,"
              "U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"),
]
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' "
           "height='16' fill='%230b0b0b'/%3E%3Cg fill='%23f1f0ec'%3E%3Ccircle cx='4' cy='4' r='1.2'/%3E%3Ccircle cx='8' "
           "cy='4' r='1.2'/%3E%3Ccircle cx='12' cy='4' r='1.2'/%3E%3Ccircle cx='4' cy='8' r='1.2'/%3E%3Ccircle cx='8' "
           "cy='8' r='1.2'/%3E%3Ccircle cx='4' cy='12' r='1.2'/%3E%3C/g%3E%3C/svg%3E")

# ------------------------------------------------------------------------------------------------------- CSS
# The look of the shop (demo/web/css): dark gallery by default with a light switch, Inter Tight and JetBrains Mono
# from demo/web/fonts, monospaced upper-case labels, large image cards on a "wall", the Họa. word mark.
CSS = r"""
:root{--bg:#0b0b0b;--bg-2:#141414;--panel:#141413;--panel-2:#1b1a19;--text:#f1f0ec;--muted:#a3a19b;--faint:#5c5a56;
--line:rgba(255,255,255,.12);--line-strong:rgba(255,255,255,.32);--dot:rgba(255,255,255,.065);--wall:#1d1c1b;
--ok:#8be3a8;--warn:#f2bd5b;--err:#ff8a7a;--shadow:0 16px 36px rgba(0,0,0,.5);--sans:"Inter Tight","Helvetica Neue",Arial,sans-serif;
--mono:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;--gutter:clamp(16px,3.2vw,44px);--ease:cubic-bezier(.22,.61,.36,1);
--top:64px;color-scheme:dark}
:root[data-theme=light]{--bg:#f5f4f0;--bg-2:#ebe9e3;--panel:#fbfaf7;--panel-2:#efede7;--text:#121211;--muted:#5d5b56;
--faint:#a5a39d;--line:rgba(0,0,0,.12);--line-strong:rgba(0,0,0,.34);--dot:rgba(0,0,0,.07);--wall:#e3e0d9;--ok:#16703c;
--warn:#875400;--err:#b42318;--shadow:0 16px 36px rgba(0,0,0,.16);color-scheme:light}
*{box-sizing:border-box}
[hidden]{display:none!important}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{margin:0;background-color:var(--bg);background-image:radial-gradient(var(--dot) 1px,transparent 1.3px);
background-size:24px 24px;color:var(--text);font:400 16px/1.55 var(--sans);-webkit-font-smoothing:antialiased;overflow-x:hidden;
font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0}
img{max-width:100%;height:auto;display:block}
a{color:inherit;text-decoration:underline;text-decoration-color:var(--line-strong);text-underline-offset:3px}
a:hover{text-decoration-color:currentColor}
:focus-visible{outline:2px solid var(--text);outline-offset:2px}
code,pre,.mono,.label,.ref,.sig,.where,.tbl,.req,.route,.sec,.file,.src{font-family:var(--mono);font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0}
code{font-size:.86em;background:var(--panel-2);padding:.08em .35em;border-radius:3px;overflow-wrap:anywhere}
::selection{background:var(--text);color:var(--bg)}
h1,h2,h3{margin:0}
p{margin:0 0 .7em}
ul,ol{margin:0;padding:0;list-style:none}
.wrap{max-width:1360px;margin:0 auto;padding:0 var(--gutter)}
.label{font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 8px}
.mono{font-size:11px;letter-spacing:.05em}
.muted{color:var(--muted)}
.small{font-size:14px}
.top-gap{margin-top:48px}
.spacer{flex:1}
.skip{position:absolute;left:-999px;top:8px;z-index:100;background:var(--text);color:var(--bg);padding:8px 12px}
.skip:focus{left:8px}
/* header */
.top{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--bg) 84%,transparent);
-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.top-in{max-width:1360px;margin:0 auto;padding:0 var(--gutter);height:var(--top);display:flex;align-items:center;gap:22px}
.logo{display:flex;align-items:center;gap:10px;font-size:23px;letter-spacing:-.03em;text-decoration:none;white-space:nowrap}
.logo-mark{display:grid;grid-template-columns:repeat(4,3px);gap:2.5px}
.logo-mark i{width:3px;height:3px;border-radius:50%;background:currentColor;opacity:.9}
.logo-mark i:nth-child(3n){opacity:.35}
.logo-sub{font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-left:2px}
.nav{display:flex;gap:4px;margin-left:auto;overflow-x:auto;scrollbar-width:none}
.nav::-webkit-scrollbar{display:none}
.nav a{font-family:var(--mono);font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;text-decoration:none;
padding:7px 9px;border:1px solid transparent;border-radius:999px;white-space:nowrap;color:var(--muted)}
.nav a b{font-weight:500;color:var(--text);margin-right:6px}
.nav a:hover{color:var(--text)}
.nav a.active{border-color:var(--line-strong);color:var(--text)}
.theme-toggle{flex:none;width:18px;height:18px;border:1px solid currentColor;border-radius:3px;cursor:pointer;padding:0;
background:linear-gradient(90deg,currentColor 50%,transparent 50%);color:var(--text)}
section[id],article[id],div[id]{scroll-margin-top:calc(var(--top) + 12px)}
/* buttons, chips, badges */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 18px;border:1px solid var(--line-strong);
background:transparent;color:var(--text);font:400 11px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;
text-decoration:none;cursor:pointer;white-space:nowrap;transition:background .25s var(--ease),color .25s var(--ease)}
.btn:hover{background:var(--text);color:var(--bg);border-color:var(--text)}
.btn.solid{background:var(--text);color:var(--bg);border-color:var(--text)}
.btn.solid:hover{background:transparent;color:var(--text)}
.btn.small{padding:8px 11px;font-size:10px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{display:inline-block;font-family:var(--mono);font-size:10.5px;letter-spacing:.05em;border:1px solid var(--line-strong);
border-radius:999px;padding:3px 9px;text-decoration:none;color:var(--text);white-space:nowrap}
.chip.ghost{border-style:dashed;color:var(--muted)}
a.chip:hover{background:var(--text);color:var(--bg)}
.tag{font-family:var(--mono);font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.badge{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:9.5px;letter-spacing:.08em;
text-transform:uppercase;border:1px solid var(--line-strong);border-radius:999px;padding:4px 9px;white-space:nowrap;color:var(--text)}
.badge i{width:7px;height:7px;border-radius:50%;background:var(--ok);flex:none}
.badge.trial{color:var(--warn);border-color:color-mix(in srgb,var(--warn) 55%,transparent)}
.badge.trial i{background:var(--warn)}
.badge.shot i{background:var(--muted)}
.ok{color:var(--ok);font-family:var(--mono);font-size:11px;letter-spacing:.05em}
.bad{color:var(--err);font-family:var(--mono);font-size:11px;letter-spacing:.05em}
.warn-text{color:var(--warn)}
/* inline references */
.ref,.sig,.tbl,.req,.route,.file,.src{font-size:12.5px;overflow-wrap:anywhere}
.sec{font-size:11.5px;letter-spacing:.02em;text-decoration:none;border-bottom:1px solid var(--line-strong);overflow-wrap:anywhere}
.sec:hover{border-bottom-color:currentColor}
.sec .pg{color:var(--muted);white-space:nowrap}
.where{display:block;font-size:10px;color:var(--muted);letter-spacing:.03em;margin-top:1px;overflow-wrap:anywhere}
.fig-link{text-decoration-style:dotted}
.fig-link::before{content:"▣ ";font-size:.8em;color:var(--muted)}
.sig{display:inline-block;font-size:11.5px;line-height:1.45}
.rw{font-family:var(--mono);font-size:10px;margin-left:6px;color:var(--muted)}
sup{font-family:var(--mono);font-size:9px;color:var(--muted)}
abbr{text-decoration:underline dotted;cursor:help}
/* typography */
.display{font-weight:300;font-size:clamp(46px,7.2vw,104px);line-height:.98;letter-spacing:-.04em}
.display .dash{color:var(--muted)}
.display-2{display:block;font-size:.5em;line-height:1.08;letter-spacing:-.03em;color:var(--muted);margin-top:.18em}
.h2{font-weight:300;font-size:clamp(30px,3.6vw,50px);line-height:1.05;letter-spacing:-.03em}
.h3{font-weight:400;font-size:21px;line-height:1.25;letter-spacing:-.015em}
.h3.sub{font-size:19px;margin-bottom:14px}
.lead{font-size:clamp(16px,1.35vw,19px);color:var(--muted);max-width:760px;margin:14px 0 0}
/* hero */
.hero{padding-top:64px;padding-bottom:40px}
.hero-grid{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:56px;align-items:end}
.hero-text .lead{margin:22px 0 26px}
.who{display:flex;flex-wrap:wrap;gap:12px 32px;margin:0 0 26px}
.who dt{font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.who dd{margin:2px 0 0;font-size:17px}
.actions{display:flex;flex-wrap:wrap;gap:10px}
.hero-art{margin:0}
.art{background:var(--wall);display:flex;align-items:center;justify-content:center;aspect-ratio:4/3.3;padding:9%}
.art img{max-height:100%;width:auto;object-fit:contain;box-shadow:var(--shadow)}
.hero-art figcaption{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;padding-top:12px;font-size:15px}
.hero-art figcaption .mono{color:var(--muted)}
.plain{color:inherit}
.stats{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-top:56px}
.stats li{border-right:1px solid var(--line)}
.stats li:last-child{border-right:0}
.stats a{display:flex;flex-direction:column;gap:4px;padding:22px 16px;text-decoration:none;height:100%}
.stats a:hover{background:var(--panel)}
.stat-n{font-weight:300;font-size:clamp(34px,3.4vw,48px);line-height:1;letter-spacing:-.03em}
.stat-l{font-size:15px}
.stat-s{font-family:var(--mono);font-size:10px;letter-spacing:.04em;color:var(--muted)}
/* sections */
section.block{margin-top:96px;padding-bottom:8px}
.sec-head{display:grid;grid-template-columns:auto minmax(0,1fr);gap:28px;align-items:start;padding-top:28px;border-top:1px solid var(--line-strong);margin-bottom:40px}
.letter{font-weight:300;font-size:clamp(64px,8vw,120px);line-height:.8;letter-spacing:-.05em;color:var(--muted)}
.grid-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:40px}
.grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:40px}
.card{border:1px solid var(--line);background:color-mix(in srgb,var(--panel) 85%,transparent);padding:20px}
/* A */
.goals li{display:grid;grid-template-columns:54px 1fr;gap:10px;padding:10px 0;border-bottom:1px solid var(--line)}
.goals small{display:block;color:var(--muted);font-size:13.5px;margin-top:2px}
.problems{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-top:28px}
.problem p{font-size:14px;margin:8px 0 0}
.problem .h3{font-size:18px;min-height:2.5em}
.k{display:block;font-family:var(--mono);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.problem .need{border-top:1px solid var(--line);padding-top:10px;margin-top:12px}
.actors li{padding:12px 0;border-bottom:1px solid var(--line);display:flex;flex-direction:column;gap:4px}
.actors .muted{font-size:13.5px}
.ucs li{display:grid;grid-template-columns:48px 1fr auto;gap:8px;padding:6px 0;border-bottom:1px solid var(--line);font-size:14.5px;align-items:baseline}
.highlights{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 40px}
.highlights>li{padding:12px 0;font-size:14.5px;border-top:1px solid var(--line)}
.narrow{max-width:820px}
.feat{margin:8px 0 0 2px}
.feat li{font-size:13.5px;padding:3px 0}
.more{margin-top:36px;border:1px solid var(--line);padding:14px 18px}
.more summary{cursor:pointer;font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase}
.more[open] summary{margin-bottom:12px}
/* tables */
.table-wrap{overflow-x:auto;max-width:100%}
table.plain{width:100%;border-collapse:collapse;font-size:14px}
table.plain th{font-family:var(--mono);font-weight:400;font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);
text-align:left;padding:8px 10px 8px 0;border-bottom:1px solid var(--line-strong);vertical-align:bottom}
table.plain td{padding:9px 10px 9px 0;border-bottom:1px solid var(--line);vertical-align:top}
table.plain.small{font-size:13px}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
th.num{text-align:right}
/* B */
.phases{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.phase{padding:22px 18px 22px 0;margin-right:18px;border-right:1px solid var(--line);display:flex;flex-direction:column}
.phase:last-child{border-right:0;margin-right:0}
.phase .chs{display:flex;flex-wrap:wrap;gap:6px 12px;margin:4px 0 12px}
.artefacts li{font-size:14px;padding:5px 0;border-bottom:1px dotted var(--line)}
.thread{margin-top:auto;padding:14px 0 0 12px;border-left:2px solid var(--text);font-size:14px}
.thread p:last-child{margin:0}
.phase .h3{margin-bottom:6px}
.pipeline{margin-top:28px}
.pipeline ol{display:flex;flex-wrap:wrap;gap:10px}
.pipeline li{display:flex;flex-direction:column;gap:2px;border:1px solid var(--line);padding:10px 14px;position:relative}
.pipeline li span{font-size:13px;color:var(--muted)}
/* thumbnails */
.thumb{display:block;text-decoration:none;color:inherit}
.thumb .wall{display:flex;align-items:center;justify-content:center;background:var(--wall);aspect-ratio:4/3;padding:7%;overflow:hidden}
.thumb img{max-height:100%;width:auto;max-width:100%;object-fit:contain;background:#fff;box-shadow:var(--shadow);transition:transform .6s var(--ease)}
.thumb:hover img{transform:scale(1.03)}
.thumb-meta{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-top:12px}
.thumb-meta .mono{color:var(--muted)}
.thumb-title{display:block;font-size:17px;letter-spacing:-.01em;line-height:1.3;margin-top:8px}
.thumb-note{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;color:var(--muted);font-size:13.5px;margin-top:6px}
.thumb.small .wall{padding:6%}
.thumb.small .thumb-title{font-size:15px}
.thumb.shot .wall{aspect-ratio:16/10;padding:0}
.thumb.shot img{box-shadow:none;background:transparent}
/* C */
.chain{margin-top:56px;padding-top:28px;border-top:1px solid var(--line)}
.chain:first-of-type{border-top:0;margin-top:0;padding-top:0}
.chain-title{font-size:26px;font-weight:300;letter-spacing:-.02em}
.chain-intro{max-width:820px;margin:8px 0 24px}
.track{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:28px;counter-reset:n}
.track>li{position:relative;min-width:0}
.track>li:not(:last-child)::after{content:"→";position:absolute;right:-22px;top:42%;color:var(--muted);font-size:18px}
.node-sec{margin:6px 0 0}
.code-card{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;aspect-ratio:4/3;background:var(--panel-2);
border:1px dashed var(--line-strong);text-decoration:none}
.code-card .mono{font-size:26px}
.steps{margin-top:26px;display:flex;flex-direction:column;gap:14px}
.step{border:1px solid var(--line);background:color-mix(in srgb,var(--panel) 85%,transparent)}
.step-head{display:flex;gap:14px;align-items:baseline;padding:12px 18px;border-bottom:1px solid var(--line);margin:0;font-size:15px}
.step-head .mono{color:var(--muted)}
.wwb{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}
.wwb>div{padding:14px 18px;border-right:1px solid var(--line);font-size:14.5px}
.wwb>div:last-child{border-right:0}
.wwb p:last-child{margin:0}
.quote{font-family:var(--mono);font-size:12px}
.code-block{margin-top:18px}
pre.code,pre.cmd{margin:0 0 12px;padding:14px 16px;background:var(--panel-2);border:1px solid var(--line);overflow:auto;max-height:520px;
font-size:12.5px;line-height:1.55;tab-size:4}
pre.code code,pre.cmd code{background:none;padding:0;font-size:inherit}
.ln{display:inline-block;color:var(--faint);margin-right:16px;user-select:none;text-align:right}
:root[data-theme=light] .ln{color:#8a8882}
/* D */
.how{max-width:900px}
.trace{border:1px solid var(--line);margin-top:28px;background:color-mix(in srgb,var(--panel) 80%,transparent)}
.trace-head{padding:18px 20px;border-bottom:1px solid var(--line)}
.trace-head p.muted{margin:6px 0 0;font-size:14.5px}
.trace-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.05fr) minmax(0,1.1fr) minmax(0,1.45fr) minmax(0,1.35fr)}
.trace-grid>div{padding:16px 16px 18px;border-right:1px solid var(--line);font-size:14px;min-width:0}
.trace-grid>div:last-child{border-right:0}
.col-h{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;margin-bottom:10px;display:flex;justify-content:space-between;gap:8px}
.mini{font-family:var(--mono);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:14px 0 6px}
.list li{padding:4px 0;font-size:13.5px}
.list li .muted{display:block;font-size:12.5px}
.list.sigs li{padding:3px 0}
.list.tables{display:flex;flex-wrap:wrap;gap:2px 12px}
.list.tables li{padding:2px 0;white-space:nowrap}
.tests li{display:grid;grid-template-columns:40px 1fr;gap:6px;font-size:13px;padding:4px 0;border-bottom:1px dotted var(--line)}
/* E */
.groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}
.group{border-top:1px solid var(--line-strong);padding-top:10px}
.tlist li{display:flex;flex-wrap:wrap;gap:2px 8px;padding:5px 0;border-bottom:1px dotted var(--line);font-size:13px;align-items:baseline}
.tlist .mono{margin-left:auto;color:var(--muted);font-size:10px}
.family{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.25fr);gap:32px;align-items:start}
.family-text p{font-size:15px}
.fam-row{display:flex;flex-wrap:wrap;gap:12px;justify-content:center;position:relative}
.fam-row+.fam-row{margin-top:26px}
.fam-row+.fam-row::before{content:"↓";position:absolute;top:-24px;left:50%;color:var(--muted)}
.tbox{border:1px solid var(--line-strong);background:var(--panel);min-width:0;flex:1 1 240px;max-width:100%}
.tbox.main{border-color:var(--text)}
.tbox-h{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;padding:8px 12px;margin:0;border-bottom:1px solid var(--line);background:var(--panel-2)}
.tbox-h .mono{color:var(--muted);font-size:10px}
.cols li{display:flex;flex-wrap:wrap;gap:2px 10px;padding:5px 12px;border-bottom:1px dotted var(--line);font-family:var(--mono);font-size:11.5px}
.cname{min-width:0}
.ctype,.marks{color:var(--muted)}
.marks{margin-left:auto;font-size:10px}
.fk,.check{flex-basis:100%;color:var(--muted);font-size:10.5px}
.dbpath{display:flex;flex-wrap:wrap;gap:0;margin-bottom:22px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.dbpath li{padding:12px 16px 12px 0;margin-right:16px;font-size:13.5px;position:relative}
.dbpath li:not(:last-child)::after{content:"→";position:absolute;right:-12px;top:50%;color:var(--muted)}
.map details summary{cursor:pointer;font-family:var(--mono);font-size:10.5px;color:var(--muted)}
.colmap li{display:flex;gap:10px;justify-content:space-between;font-size:12.5px;padding:2px 0}
.evidence{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px}
.evidence p{margin-top:10px;font-size:14.5px}
/* F */
.run{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:40px;align-items:start}
.run .btn{margin:6px 0 16px}
.notice-box{border-left:2px solid var(--warn);padding:10px 14px;background:var(--panel);font-size:14.5px}
.accounts .thumb{margin-top:18px}
.flows{margin-top:48px;display:flex;flex-direction:column;gap:20px}
.flow{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.5fr);gap:28px;border-top:1px solid var(--line);padding-top:22px}
.steps-list{list-style:decimal;padding-left:20px;margin:10px 0 12px}
.steps-list li{padding:3px 0;font-size:15px}
.notice-line{font-size:14.5px}
.flow-shots{display:grid;gap:14px;grid-template-columns:repeat(2,minmax(0,1fr))}
.flow-shots.n1{grid-template-columns:minmax(0,1fr);max-width:620px}
.flow-shots.n3{grid-template-columns:repeat(3,minmax(0,1fr))}
.flow-shots .thumb-title{font-size:14px}
/* G */
.evidence-tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid var(--line)}
.evidence-tiles li{display:flex;flex-direction:column;gap:4px;padding:20px 16px 20px 0;border-bottom:1px solid var(--line)}
.quote-line{font-family:var(--mono);font-size:12px;margin-top:16px;overflow-wrap:anywhere}
.quote-line .label{display:inline;margin-right:8px}
.reqs td:first-child{white-space:nowrap}
.reqs tr.demo td:first-child .req{color:var(--muted)}
.five{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-bottom:28px}
.five li{display:flex;flex-direction:column;gap:6px;border:1px solid var(--line);padding:14px;font-size:14px}
.five .small{font-size:12px;color:var(--muted);font-family:var(--mono);overflow-wrap:anywhere}
.five .small code{background:none;padding:0}
.meter{display:inline-block;width:110px;height:6px;background:var(--line);vertical-align:middle;margin-right:8px;border-radius:3px;overflow:hidden}
.meter span{display:block;height:100%;background:var(--text);border-radius:3px}
td.bar{white-space:nowrap}
.limits li{padding:8px 0;border-bottom:1px solid var(--line);font-size:14.5px}
.conclusion{margin-top:44px;border:1px solid var(--line-strong);padding:24px 26px;max-width:980px}
.conclusion p{font-size:17px}
/* gallery */
.chapter-chips{margin-bottom:12px}
.chapter{margin-top:44px}
.chapter-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 18px;border-top:1px solid var(--line);padding-top:16px;margin-bottom:22px}
.chapter-head .label{margin:0}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:36px 24px}
.card-sec{margin:8px 0 0;font-size:12px}
/* footer */
.footer{background:#050505;color:#e6e4de;margin-top:110px;padding-top:56px;overflow:hidden}
.footer a{color:#e6e4de}
.footer .label{color:#8d8b86}
.footer code{background:#1b1a19;color:#e6e4de}
.footer-in{display:grid;grid-template-columns:2fr 1fr;gap:32px;font-size:14.5px}
.wordmark{font-weight:300;font-size:clamp(110px,24vw,380px);line-height:.8;letter-spacing:-.06em;color:#1d1d1c;margin:56px 0 0 -.04em;white-space:nowrap;user-select:none}
.footer-note{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-family:var(--mono);font-size:10px;letter-spacing:.06em;
text-transform:uppercase;color:#77756f;padding-top:28px;padding-bottom:24px}
/* lightbox */
body.lb-open{overflow:hidden}
.lb{position:fixed;inset:0;z-index:90;display:grid;grid-template-rows:auto minmax(0,1fr) auto;background:#0a0a0a;color:#f1f0ec}
.lb[hidden]{display:none}
.lb .btn{color:#f1f0ec;border-color:rgba(255,255,255,.35)}
.lb .btn:hover{background:#f1f0ec;color:#0b0b0b}
.lb .label{color:#b3b1ab}
.lb .label a{color:#f1f0ec}
.lb-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:12px var(--gutter);border-bottom:1px solid rgba(255,255,255,.12)}
.lb-bar .badge{color:#f1f0ec;border-color:rgba(255,255,255,.35)}
.lb-bar .badge.trial{color:#f2bd5b}
.lb-bar .badge i{background:#8be3a8}
.lb-bar .badge.trial i{background:#f2bd5b}
.lb-bar .badge.shot i{background:#a3a19b}
.lb-stage{overflow:auto;display:flex;align-items:center;justify-content:center;padding:20px 64px;min-height:0}
.lb-stage img{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;background:#fff}
.lb-stage.zoomed{align-items:flex-start;justify-content:flex-start}
.lb-stage.zoomed img{max-width:none;max-height:none}
.lb-nav{position:absolute;top:50%;transform:translateY(-50%);width:46px;height:46px;border-radius:50%;border:1px solid rgba(255,255,255,.35);
background:rgba(8,8,8,.7);color:#f1f0ec;font-size:18px;cursor:pointer}
.lb-nav:hover{background:#f1f0ec;color:#0b0b0b}
.lb-nav.prev{left:12px}
.lb-nav.next{right:12px}
.lb-cap{padding:12px var(--gutter) 18px;border-top:1px solid rgba(255,255,255,.12);max-height:26vh;overflow:auto}
.lb-cap p{margin:6px 0 0;color:#c9c7c1;font-size:14.5px;max-width:1000px}
/* responsive */
@media (max-width:1240px){
.problems{grid-template-columns:repeat(3,minmax(0,1fr))}
.phases{grid-template-columns:repeat(2,minmax(0,1fr))}
.phase{margin-right:0;padding-right:18px;border-bottom:1px solid var(--line)}
.phase:nth-child(2n){border-right:0;padding-left:18px}
.phase:nth-child(2n+1){padding-right:18px}
.trace-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.trace-grid>div{border-bottom:1px solid var(--line)}
.trace-grid>div:nth-child(2n){border-right:0}
.five{grid-template-columns:repeat(3,minmax(0,1fr))}
.stats{grid-template-columns:repeat(3,minmax(0,1fr))}
.stats li:nth-child(3n){border-right:0}
.stats li:nth-child(-n+3){border-bottom:1px solid var(--line)}
}
@media (max-width:1060px){
:root{--top:auto}
.top-in{flex-wrap:wrap;height:auto;padding-top:10px;gap:8px 16px}
.logo{order:1}
.theme-toggle{order:2;margin-left:auto}
.nav{order:3;flex-basis:100%;margin:0 calc(var(--gutter) * -1);padding:0 var(--gutter) 8px}
section[id],article[id],div[id]{scroll-margin-top:112px}
.hero-grid{grid-template-columns:minmax(0,1fr);gap:36px}
.hero-art{max-width:560px}
.grid-3{grid-template-columns:repeat(2,minmax(0,1fr))}
.family,.run,.flow{grid-template-columns:minmax(0,1fr)}
.evidence-tiles{grid-template-columns:repeat(2,minmax(0,1fr))}
.track>li:not(:last-child)::after{display:none}
.track{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:760px){
.grid-2,.grid-3,.problems,.phases,.trace-grid,.wwb,.evidence,.five,.highlights{grid-template-columns:minmax(0,1fr)}
.phase,.phase:nth-child(2n){padding-left:0;padding-right:0;border-right:0}
.trace-grid>div{border-right:0}
.wwb>div{border-right:0;border-bottom:1px solid var(--line)}
.wwb>div:last-child{border-bottom:0}
.stats{grid-template-columns:repeat(2,minmax(0,1fr))}
.stats li{border-bottom:1px solid var(--line)}
.stats li:nth-child(3n){border-right:1px solid var(--line)}
.stats li:nth-child(2n){border-right:0}
.evidence-tiles{grid-template-columns:minmax(0,1fr)}
.flow-shots,.flow-shots.n3{grid-template-columns:repeat(2,minmax(0,1fr))}
.sec-head{grid-template-columns:minmax(0,1fr);gap:6px}
.letter{font-size:56px}
section.block{margin-top:64px}
.footer-in{grid-template-columns:minmax(0,1fr)}
.lb-stage{padding:12px 46px}
.lb-nav{width:36px;height:36px;font-size:15px}
.lb-nav.prev{left:5px}
.lb-nav.next{right:5px}
.logo-sub{display:none}
.track{grid-template-columns:repeat(2,minmax(0,1fr));gap:18px 12px}
.track .thumb-title{font-size:13.5px}
.cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:26px 12px}
.cards .thumb-note{display:none}
.cards .thumb-title{font-size:14px}
.cards .card-sec{font-size:10.5px}
.thumb-meta .mono{display:none}
.badge{font-size:8.5px;padding:3px 7px;gap:5px}
table.reqs,table.reqs tbody,table.reqs tr,table.reqs td{display:block;width:100%}
table.reqs thead{display:none}
table.reqs tr{padding:10px 0;border-bottom:1px solid var(--line)}
table.reqs td{border:0;padding:2px 0}
table.reqs td:nth-child(1),table.reqs td:nth-child(3),table.reqs td:nth-child(4){display:inline;width:auto;margin-right:10px;font-family:var(--mono);font-size:11px;color:var(--muted)}
.who dd{font-size:15px}
.ucs li{grid-template-columns:44px 1fr}
.ucs li .tag{grid-column:2}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.lb,.theme-toggle{display:none!important}body{background:#fff;color:#000}}
"""

# -------------------------------------------------------------------------------------------------------- JS
JS = r"""
(function () {
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");
  function setTheme(theme) {
    root.dataset.theme = theme;
    toggle.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
    try { localStorage.setItem("hoa-showcase-theme", theme); } catch (e) {}
  }
  toggle.addEventListener("click", function () { setTheme(root.dataset.theme === "light" ? "dark" : "light"); });
  toggle.setAttribute("aria-pressed", root.dataset.theme === "light" ? "true" : "false");

  // Section navigation: highlight the section on screen.
  var nav = document.querySelector(".nav");
  var links = Array.prototype.slice.call(document.querySelectorAll(".nav a[data-nav]"));
  var byKey = {};
  links.forEach(function (a) { byKey[a.getAttribute("data-nav")] = a; });
  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var link = byKey[entry.target.id];
        if (!link) return;
        links.forEach(function (a) { a.classList.remove("active"); a.removeAttribute("aria-current"); });
        link.classList.add("active");
        link.setAttribute("aria-current", "true");
        if (nav.scrollWidth > nav.clientWidth) nav.scrollTo({ left: link.offsetLeft - 24, behavior: "smooth" });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    Object.keys(byKey).forEach(function (key) {
      var section = document.getElementById(key);
      if (section) observer.observe(section);
    });
  }

  // Lightbox: every element with data-fig opens it; arrows move inside the group (diagrams or screenshots).
  var items = JSON.parse(document.getElementById("figs").textContent);
  var byId = {};
  items.forEach(function (item) { byId[item.id] = item; });
  var box = document.getElementById("lb"), img = document.getElementById("lb-img"), stage = document.getElementById("lb-stage");
  var el = function (id) { return document.getElementById(id); };
  var group = [], index = 0, opener = null;
  var badges = { ce: '<span class="badge ce"><i></i>VP Community Edition</span>',
                 trial: '<span class="badge trial"><i></i>VP trial screenshot</span>',
                 screen: '<span class="badge shot"><i></i>Demo screenshot</span>' };
  function zoom(on) {
    stage.classList.toggle("zoomed", on);
    el("lb-zoom").setAttribute("aria-pressed", on ? "true" : "false");
    el("lb-zoom").textContent = on ? "Fit to screen" : "Actual size";
  }
  function show() {
    var item = group[index];
    img.src = item.src;
    img.alt = item.title;
    img.width = item.w;
    img.height = item.h;
    el("lb-count").textContent = (index + 1) + " / " + group.length;
    el("lb-badge").innerHTML = badges[item.kind] || "";
    var meta = el("lb-meta");
    meta.textContent = [item.fig, item.sec].filter(Boolean).join(" · ");
    if (item.pdf) {
      var a = document.createElement("a");
      a.href = item.pdf;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = "essay p. " + item.page;
      meta.appendChild(document.createTextNode(meta.textContent ? " · " : ""));
      meta.appendChild(a);
    } else if (!item.fig) {
      meta.textContent = "Not in the essay";
    }
    el("lb-title").textContent = item.title;
    el("lb-desc").textContent = item.desc;
    el("lb-png").href = item.src;
    el("lb-vector").hidden = !item.vector;
    el("lb-vector").href = item.vector || "#";
    zoom(false);
    [index - 1, index + 1].forEach(function (k) {
      var next = group[(k + group.length) % group.length];
      if (next) { var pre = new Image(); pre.src = next.src; }
    });
  }
  function open(item, from) {
    opener = from;
    group = items.filter(function (x) { return x.group === item.group; });
    index = group.indexOf(item);
    box.hidden = false;
    document.body.classList.add("lb-open");
    show();
    el("lb-close").focus();
  }
  function close() {
    box.hidden = true;
    document.body.classList.remove("lb-open");
    img.removeAttribute("src");
    if (opener) opener.focus();
  }
  function step(d) { index = (index + d + group.length) % group.length; show(); }
  document.addEventListener("click", function (event) {
    var trigger = event.target.closest ? event.target.closest("[data-fig]") : null;
    if (!trigger || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var item = byId[trigger.getAttribute("data-fig")];
    if (!item) return;
    event.preventDefault();
    open(item, trigger);
  });
  el("lb-close").addEventListener("click", close);
  el("lb-prev").addEventListener("click", function () { step(-1); });
  el("lb-next").addEventListener("click", function () { step(1); });
  el("lb-zoom").addEventListener("click", function () { zoom(!stage.classList.contains("zoomed")); });
  stage.addEventListener("click", function (event) { if (event.target === stage) close(); });
  document.addEventListener("keydown", function (event) {
    if (box.hidden) return;
    if (event.key === "Escape") { event.preventDefault(); close(); }
    else if (event.key === "ArrowLeft") { event.preventDefault(); step(-1); }
    else if (event.key === "ArrowRight") { event.preventDefault(); step(1); }
    else if (event.key === "Tab") {
      var focusable = Array.prototype.filter.call(box.querySelectorAll("a[href],button"), function (x) { return !x.hidden && x.offsetParent !== null; });
      var first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
})();
"""


# ----------------------------------------------------------------------------------------------- verification
def verify(page_html):
    """Every link of the written page: anchors exist, repository files exist (and are in git), GitHub lines exist."""
    ids = set(re.findall(r'\sid="([^"]+)"', page_html))
    anchors = set(re.findall(r'href="#([^"]+)"', page_html))
    missing = sorted(a for a in anchors if a not in ids)
    need(not missing, f"anchors without a target: {missing}")
    rel = set(re.findall(r'(?:href|src)="\.\./([^"#]+)', page_html)) | set(re.findall(r"url\(\.\./([^)]+)\)", page_html))
    rel |= {json.loads(f'"{m}"') for m in re.findall(r'"(?:src|pdf|vector)":"\.\./([^"#]+)', page_html)}
    rel = {urllib.parse.unquote(r) for r in rel}
    for r in rel:
        repo_path(r)
    unknown = rel - LINKS.rel
    need(not unknown, f"relative links not registered by the generator: {sorted(unknown)}")
    blobs = set(re.findall(r'href="(https://github\.com/scalliontor/Hoa/blob/main/[^"]+)"', page_html))
    for url in blobs:
        path, _, frag = url[len(BLOB):].partition("#")
        path = urllib.parse.unquote(path)
        lines = lines_of(path)
        for a, b in re.findall(r"L(\d+)(?:-L(\d+))?", frag):
            need(1 <= int(a) <= len(lines) and (not b or int(a) <= int(b) <= len(lines)), f"bad line link {url}")
    externals = sorted(set(re.findall(r'href="(https?://[^"]+)"', page_html)) - blobs
                       - {TREE + urllib.parse.quote(t) for t in LINKS.tree})
    allowed = {REPO}
    local = [u for u in externals if u.startswith("http://127.0.0.1:")]
    other = [u for u in externals if u not in allowed and u not in local]
    need(not other, f"unexpected external links: {other}")
    # Compare with what GitHub serves (origin/main, else HEAD): a linked file must exist there, and a line link
    # must point at the same text there; differences disappear once the working tree is committed and pushed.
    ref = "origin/main" if git("rev-parse", "--verify", "--quiet", "origin/main") else "HEAD"
    listing = git("ls-tree", "-r", "--name-only", ref)
    report = dict(anchors=len(anchors), files=len(rel), blobs=len(blobs), trees=len(LINKS.tree), local=local,
                  ref=ref, missing_on_ref=[], changed={}, exact=0)
    if listing is not None:
        on_ref = set(listing.splitlines())
        report["missing_on_ref"] = sorted(r for r in rel | {k[0] for k in LINKS.blob} if r not in on_ref)
        heads = {}
        for (path, start, end), text in sorted(LINKS.blob.items(), key=lambda x: (x[0][0], x[0][1] or 0)):
            if start is None or path not in on_ref:
                continue
            if path not in heads:
                heads[path] = (git("show", f"{ref}:{path}") or "").split("\n")
            head = heads[path]
            if start > len(head) or head[start - 1] != text or (end and end > len(head)):
                report["changed"].setdefault(path, []).append(start)
            else:
                report["exact"] += 1
    return report


def main():
    try:
        page = Page()
        html_text = page.render()
        report = verify(html_text)
        total = report["anchors"] + report["files"] + report["blobs"] + report["trees"]
        html_text = html_text.replace('<span class="stat-n" id="link-count">—</span>',
                                      f'<span class="stat-n" id="link-count">{total}</span>')
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(html_text, encoding="utf-8")
    except ShowcaseError as error:
        print(f"build_showcase: ERROR: {error}", file=sys.stderr)
        return 1
    print(f"wrote {OUT.relative_to(ROOT)} ({len(html_text) // 1024} KB)")
    print(f"links verified: {report['anchors']} anchors, {report['files']} repository files, "
          f"{report['blobs']} GitHub line links, {report['trees']} GitHub folders; local shop link: {', '.join(report['local'])}")
    print(f"compared with {report['ref']}: {report['exact']} GitHub line links already exact there")
    if report["missing_on_ref"]:
        print(f"WARNING: {len(report['missing_on_ref'])} linked files are not on {report['ref']} yet "
              "(404 on GitHub / GitHub Pages until committed and pushed):")
        for r in report["missing_on_ref"]:
            print("  " + r)
    if report["changed"]:
        n = sum(len(v) for v in report["changed"].values())
        print(f"WARNING: {n} GitHub line links point at text that differs on {report['ref']} (exact after the push):")
        for path, starts in report["changed"].items():
            print(f"  {path}: lines {', '.join(map(str, starts[:8]))}{' …' if len(starts) > 8 else ''}")
    for w in WARNINGS:
        print("WARNING: " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
