"""Build the class presentation slides/thuyettrinh_Hoa.pptx.

The talk (in English) follows the five chapters of the course (lectures 01-05
and the A06 assignment) and illustrates each idea with the demo shop Hoa. Every
name, ID and count shown is read from tools/model.py; a name missing from the
model stops the build, so the deck cannot drift from the code.

Figures come from figures/vp and figures/demo while other agents produce them:
a missing or stale image becomes a placeholder frame, so re-running fills it in.

    slides/.venv/bin/python slides/build_slides.py          # build the deck
    slides/.venv/bin/python slides/build_slides.py --qa     # also render slides/qa/*.png
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageOps
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "slides"
CACHE = HERE / ".cache"
OUT = HERE / "thuyettrinh_Hoa.pptx"
sys.path.insert(0, str(ROOT / "tools"))
import model  # noqa: E402

# Figures exported before the shop switched to paintings show the old book/clothes model.
CUTOFF = datetime(2026, 10, 29, 16, 28)

W, H, M = 13.333, 7.5, 0.6
SANS, MONO = "Arial", "Courier New"
BG, PANEL, LINE = "0B0B0B", "171717", "2E2E2E"
TEXT, BODY, MUTED, ACCENT = "F2F2EE", "CFCFCB", "8C8C88", "E5482E"
WHITE, WORDMARK = "FFFFFF", "222222"


def rgb(hex_):
    return RGBColor.from_string(hex_)


# ------------------------------------------------------------------ model names
class Names:
    """Exact names from model.py; unknown names are collected and stop the build."""

    def __init__(self):
        self.missing = []

    def cls(self, name):
        if name not in model.DESIGN_BY_NAME:
            self.missing.append(name)
        return name

    def op(self, ref, params=True):
        """'Class.method' -> 'Class.method(p1, p2)' with the parameter names of the model."""
        cls_name, op_name = ref.split(".")
        c = model.DESIGN_BY_NAME.get(cls_name)
        found = c and next((o for o in c["ops"] if o["name"] == op_name), None)
        if not found:
            self.missing.append(ref)
            return ref + ("()" if params else "")
        return ref + ("(" + ", ".join(p for p, _ in found["params"]) + ")" if params else "")

    def attr(self, ref):
        cls_name, attr_name = ref.split(".")
        c = model.DESIGN_BY_NAME.get(cls_name)
        if not c or attr_name not in [a["name"] for a in c["attrs"]]:
            self.missing.append(ref)
        return ref

    def req(self, rid):
        r = next((r for r in model.REQUIREMENTS if r[0] == rid), None)
        if not r:
            self.missing.append(rid)
        return r

    def uc(self, uid):
        u = next((u for u in model.USE_CASES if u[0] == uid), None)
        if not u:
            self.missing.append(uid)
            return (uid, "?", "?", "")
        return u


NAMES = Names()


def short_title(title, limit=46):
    """Short label of a requirement: the part before ':' ';' ' (', else the first clause."""
    head = re.split(r":|;| \(", title)[0].strip()
    if len(head) > limit:
        head = head.split(",")[0].strip()
    return head


def nfr_label(title):
    return title.split(":")[0].strip() if ":" in title else " ".join(title.split()[:3])


# ------------------------------------------------------------------- assets
class Assets:
    def __init__(self, allow_stale=False, dummies=False):
        self.allow_stale, self.dummies = allow_stale, dummies
        self.missing, self.stale = [], []

    def fresh(self, path):
        return path.exists() and (self.allow_stale or datetime.fromtimestamp(path.stat().st_mtime) >= CUTOFF)

    def figure(self, kind, name):
        """figures/<kind>/<name>.png if present and fresh, else None (recorded as missing)."""
        path = ROOT / "figures" / kind / f"{name}.png"
        if self.fresh(path):
            return path
        rel = f"figures/{kind}/{name}.png"
        (self.stale if path.exists() else self.missing).append(rel)
        return self.dummy(rel, 16 / 10 if kind == "demo" else 1.6) if self.dummies else None

    def file(self, rel):
        path = ROOT / rel
        return path if self.fresh(path) else None

    def dummy(self, rel, aspect):
        CACHE.mkdir(parents=True, exist_ok=True)
        path = CACHE / ("dummy_" + rel.replace("/", "_"))
        img = Image.new("RGB", (int(900 * aspect), 900), (190, 190, 186))
        ImageDraw.Draw(img).text((40, 40), "DUMMY " + rel, fill=(40, 40, 40))
        img.save(path)
        return path

    def painting(self, code):
        """demo/web/img/<code>.jpg and its caption from demo/data/ATTRIBUTION.md."""
        path = ROOT / "demo" / "web" / "img" / f"{code}.jpg"
        if not path.exists():
            return None, ""
        caption = ""
        attribution = ROOT / "demo" / "data" / "ATTRIBUTION.md"
        if attribution.exists():
            for line in attribution.read_text(encoding="utf-8").splitlines():
                cells = [c.strip() for c in line.strip("|").split("|")]
                if cells and cells[0] == code and len(cells) >= 5:
                    caption = f"{cells[1]} — {cells[2]} ▪ {cells[4]}".upper()
        return path, caption


ASSETS = Assets()


def cached(path, max_px=2600, aspect=None, trim=False):
    """Resized copy of an image under slides/.cache: paintings cover-cropped, diagrams trimmed of white margins."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(f"{path}|{path.stat().st_mtime}|{max_px}|{aspect}|{trim}".encode()).hexdigest()[:12]
    out = CACHE / f"{path.stem}_{key}{'.jpg' if aspect else path.suffix}"
    if out.exists():
        return out
    img = Image.open(path)
    if trim:
        rgba = img.convert("RGBA")
        img = Image.new("RGB", rgba.size, (255, 255, 255))
        img.paste(rgba, mask=rgba.split()[3])
        box = ImageOps.invert(img.convert("L")).point(lambda p: 255 if p > 16 else 0).getbbox()
        if box:
            m = 24
            img = img.crop((max(box[0] - m, 0), max(box[1] - m, 0), min(box[2] + m, img.width),
                            min(box[3] + m, img.height)))
    if aspect:
        img = img.convert("RGB")
        w, h = img.size
        if w / h > aspect:
            nw = int(h * aspect)
            img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = int(w / aspect)
            img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    if max(img.size) > max_px:
        img.thumbnail((max_px, max_px), Image.LANCZOS)
    if aspect or out.suffix.lower() in (".jpg", ".jpeg"):
        img.convert("RGB").save(out, quality=88)
    else:
        img.save(out, optimize=True)
    return out


def dot_grid():
    path = CACHE / "dotgrid.png"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (2667, 1500), (11, 11, 11))
        draw = ImageDraw.Draw(img)
        for x in range(15, 2667, 30):
            for y in range(15, 1500, 30):
                draw.ellipse((x - 1.6, y - 1.6, x + 1.6, y + 1.6), fill=(43, 43, 43))
        img.save(path, optimize=True)
    return path


def logo():
    """A dotted sphere, the Hoa. mark (after the fustic.studio logo)."""
    path = CACHE / "logo.png"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for i in range(9):
            for j in range(9):
                x, y = 28 + i * 25, 28 + j * 25
                d = ((x - 128) ** 2 + (y - 128) ** 2) ** 0.5
                if d <= 112:
                    r = 9 * (1 - d / 140)
                    draw.ellipse((x - r, y - r, x + r, y + r), fill=(237, 237, 233, 255))
        img.save(path)
    return path


# ------------------------------------------------------------------ drawing
def strip_style(shape):
    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)


def add_run(p, text, size, color, font, bold=False, italic=False, sub=False, tracking=None):
    run = p.add_run()
    run.text = text
    f = run.font
    f.size, f.name, f.bold, f.italic = Pt(size), font, bold, italic
    f.color.rgb = rgb(color)
    rpr = run._r.get_or_add_rPr()
    if sub:
        rpr.set("baseline", "-25000")
    if tracking:
        rpr.set("spc", str(tracking))
    return run


def text(slide, x, y, w, h, paras, size=16, color=BODY, font=SANS, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, line=None, after=0, tracking=None, name=None):
    """paras: str (lines split on \\n) or a list of paragraphs; a paragraph is a str or a list of
    (text, opts) runs where opts may set size, color, font, bold, italic, sub."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap, tf.auto_size, tf.vertical_anchor = True, MSO_AUTO_SIZE.NONE, anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    if isinstance(paras, str):
        paras = paras.split("\n")
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line:
            p.line_spacing = line
        if after:
            p.space_after = Pt(after)
        for t, o in (para if isinstance(para, list) else [(para, {})]):
            add_run(p, t, o.get("size", size), o.get("color", color), o.get("font", font),
                    o.get("bold", bold), o.get("italic", False), o.get("sub", False), o.get("tracking", tracking))
    return box


def mono(slide, x, y, w, h, s, size=11, color=MUTED, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, after=0):
    return text(slide, x, y, w, h, s, size=size, color=color, font=MONO, align=align, anchor=anchor,
                tracking=60, after=after)


def bullets(slide, x, y, w, h, items, size=15, color=BODY, gap=7, char="▪", bullet_color=ACCENT, line=1.08):
    """items: str or list of runs; real bullets (a:buChar), not typed characters."""
    box = text(slide, x, y, w, h, [it if isinstance(it, list) else [(it, {})] for it in items],
               size=size, color=color, after=gap, line=line)
    for p in box.text_frame.paragraphs:
        ppr = p._p.get_or_add_pPr()
        ppr.set("marL", str(Inches(0.26)))
        ppr.set("indent", str(-Inches(0.26)))
        clr = etree.SubElement(ppr, qn("a:buClr"))
        etree.SubElement(clr, qn("a:srgbClr")).set("val", bullet_color)
        etree.SubElement(ppr, qn("a:buFont")).set("typeface", SANS)
        etree.SubElement(ppr, qn("a:buChar")).set("char", char)
    return box


def numbered(slide, x, y, w, h, items, size=14, gap=6, color=BODY):
    """Mono accent numbers on a hanging indent, so wrapped lines align with the text."""
    hang = Inches(0.44)
    paras = [[(f"{i:02d}", {"font": MONO, "color": ACCENT, "size": size - 2}), ("\t", {}), (t, {})]
             for i, t in enumerate(items, 1)]
    box = text(slide, x, y, w, h, paras, size=size, color=color, after=gap, line=1.08)
    for p in box.text_frame.paragraphs:
        ppr = p._p.get_or_add_pPr()
        ppr.set("marL", str(hang))
        ppr.set("indent", str(-hang))
        etree.SubElement(etree.SubElement(ppr, qn("a:tabLst")), qn("a:tab"), pos=str(hang), algn="l")
    return box


def rect(slide, x, y, w, h, fill=PANEL, line=None, radius=0.06, dash=False, name=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                   Inches(x), Inches(y), Inches(w), Inches(h))
    strip_style(shape)
    if name:
        shape.name = name
    if radius:
        shape.adjustments[0] = radius
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(fill)
    else:
        shape.fill.background()
    if line:
        shape.line.color.rgb = rgb(line)
        shape.line.width = Pt(1)
        if dash:
            shape.line.dash_style = MSO_LINE.DASH
    else:
        shape.line.fill.background()
    return shape


def alpha_fill(shape, hex_, alpha):
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(hex_)
    srgb = shape.fill._xPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
    etree.SubElement(srgb, qn("a:alpha")).set("val", str(int(alpha * 100000)))


def arrow(slide, x1, y1, x2, y2, color=MUTED):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    strip_style(c)
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(1.25)
    end = etree.SubElement(c.line._get_or_add_ln(), qn("a:tailEnd"))
    end.set("type", "triangle")
    end.set("w", "med")
    end.set("len", "med")
    return c


def picture(slide, path, x, y, w, h, alt, label, hint="", panel=False, frame=False, cover=False, fit=False):
    """Fit an image in the box (or cover it); a missing image becomes a dashed placeholder.
    fit=True shrinks a panel to the image, anchored at the top-left of the box."""
    if path is None:
        rect(slide, x, y, w, h, fill=None, line=MUTED, radius=0.02, dash=True, name="Placeholder " + label)
        mono(slide, x + 0.3, y + h / 2 - 0.35, w - 0.6, 0.3, "FIGURE PENDING ▪ " + label, size=10.5,
             color=BODY, align=PP_ALIGN.CENTER)
        if hint:
            text(slide, x + 0.4, y + h / 2 + 0.02, w - 0.8, 0.6, hint, size=12, color=MUTED, align=PP_ALIGN.CENTER)
        return None
    if cover:
        src = cached(path, 2000, aspect=w / h)
        pic = slide.shapes.add_picture(str(src), Inches(x), Inches(y), Inches(w), Inches(h))
    else:
        pad = 0.12 if panel else 0.0
        src = cached(path, trim=panel)
        iw, ih = Image.open(src).size
        bw, bh = w - 2 * pad, h - 2 * pad
        scale = min(bw / iw, bh / ih)
        pw, ph = iw * scale, ih * scale
        if fit:
            w, h = pw + 2 * pad, ph + 2 * pad
            bw, bh = pw, ph
        if panel:
            rect(slide, x, y, w, h, fill=WHITE, radius=0.015, name="Panel " + label)
        px, py = x + pad + (bw - pw) / 2, y + pad + (bh - ph) / 2
        pic = slide.shapes.add_picture(str(src), Inches(px), Inches(py), Inches(pw), Inches(ph))
        if frame:
            pic.line.color.rgb = rgb(LINE)
            pic.line.width = Pt(1)
    pic.name = label
    pic._element.nvPicPr.cNvPr.set("descr", alt)
    return pic


def set_cell(cell, paras, size, color, font, fill=None, bottom=LINE, bold=False):
    tc_pr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        ln = etree.SubElement(tc_pr, qn(tag))
        if tag == "a:lnB" and bottom:
            ln.set("w", "9525")
            etree.SubElement(etree.SubElement(ln, qn("a:solidFill")), qn("a:srgbClr")).set("val", bottom)
        else:
            ln.set("w", "0")
            etree.SubElement(ln, qn("a:noFill"))
    if fill:
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(fill)
    else:
        cell.fill.background()
    cell.margin_left = cell.margin_right = Inches(0.07)
    cell.margin_top = cell.margin_bottom = Inches(0.045)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf = cell.text_frame
    tf.word_wrap = True
    for i, para in enumerate(paras if isinstance(paras, list) else [paras]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        for t, o in (para if isinstance(para, list) else [(para, {})]):
            add_run(p, t, o.get("size", size), o.get("color", color), o.get("font", font), o.get("bold", bold))


def table(slide, x, y, widths, rows, size=13, header_size=10.5, mono_cols=(), row_h=0.4, accent_cols=()):
    """rows[0] is the header (mono, uppercase); hairlines under each row, no grid."""
    gf = slide.shapes.add_table(len(rows), len(widths), Inches(x), Inches(y),
                                Inches(sum(widths)), Inches(row_h * len(rows)))
    tbl = gf.table
    tbl_pr = tbl._tbl.tblPr
    tbl_pr.set("firstRow", "0")
    tbl_pr.set("bandRow", "0")
    style = tbl_pr.find(qn("a:tableStyleId"))
    if style is None:
        style = etree.SubElement(tbl_pr, qn("a:tableStyleId"))
    style.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # No Style, No Grid
    for i, wdt in enumerate(widths):
        tbl.columns[i].width = Inches(wdt)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h if r else 0.36)
        for c, value in enumerate(row):
            if r == 0:
                set_cell(tbl.cell(r, c), [brand_runs(str(value), upper=True)], header_size, MUTED, MONO, bottom=MUTED)
            else:
                font = MONO if c in mono_cols else SANS
                color = ACCENT if c in accent_cols else (TEXT if c == 0 else BODY)
                set_cell(tbl.cell(r, c), value if isinstance(value, list) else [[(str(value), {})]],
                         size - (1.5 if font == MONO else 0), color, font)
    return gf


def bar_chart(slide, x, y, w, h, labels, values):
    data = CategoryChartData()
    data.categories = labels
    data.add_series("Success rate", values)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), data)
    chart = gf.chart
    chart.has_legend = False
    chart.has_title = False
    chart.font.size = Pt(12)
    chart.font.name = SANS
    chart.font.color.rgb = rgb(BODY)
    plot = chart.plots[0]
    plot.gap_width = 70
    plot.has_data_labels = True
    labels_ = plot.data_labels
    labels_.number_format, labels_.number_format_is_linked = "0%", False
    labels_.position = XL_LABEL_POSITION.OUTSIDE_END
    labels_.font.size, labels_.font.color.rgb = Pt(16), rgb(TEXT)
    series = plot.series[0]
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = rgb(ACCENT)
    axis = chart.value_axis
    axis.minimum_scale, axis.maximum_scale = 0, 1
    axis.has_major_gridlines = True
    axis.major_gridlines.format.line.color.rgb = rgb(LINE)
    axis.tick_labels.number_format, axis.tick_labels.number_format_is_linked = "0%", False
    axis.format.line.fill.background()
    chart.category_axis.format.line.color.rgb = rgb(LINE)
    # Transparent chart and plot areas on the dark slide.
    space = chart._chartSpace
    sp = etree.Element(qn("c:spPr"))
    etree.SubElement(sp, qn("a:noFill"))
    etree.SubElement(etree.SubElement(sp, qn("a:ln")), qn("a:noFill"))
    space.find(qn("c:chart")).addnext(sp)
    plot_area = space.find(qn("c:chart")).find(qn("c:plotArea"))
    sp2 = etree.SubElement(plot_area, qn("c:spPr"))
    etree.SubElement(sp2, qn("a:noFill"))
    return gf


# ---------------------------------------------------------------- slide frame
class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(W), Inches(H)
        self.total = 0
        self.index = 0

    def slide(self, section, notes, dark_grid=False):
        self.index += 1
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(BG)
        if dark_grid:
            s.shapes.add_picture(str(dot_grid()), 0, 0, Inches(W), Inches(H)).name = "Dot grid"
        s.notes_slide.notes_text_frame.text = notes.strip()
        s.shapes.add_picture(str(logo()), Inches(M), Inches(0.31), Inches(0.22), Inches(0.22)).name = "Logo"
        mono(s, M + 0.32, 0.33, 7.5, 0.25, [[("Họa.", {"color": TEXT, "font": SANS, "bold": True, "size": 11.5,
                                                       "tracking": 0}), (f"   ▪   {section}", {})]], size=10.5)
        mono(s, W - M - 1.6, 0.33, 1.6, 0.25, f"{self.index:02d} / {self.total:02d}", size=10.5,
             align=PP_ALIGN.RIGHT)
        return s

    def title(self, s, t, size=30):
        return text(s, M, 0.78, W - 2 * M, 0.8, t, size=size, color=TEXT, name="Title")


def divider(d, number, title, subtitle, caption, painting, extra=None, notes=""):
    s = d.slide(f"CHAPTER {number}", notes, dark_grid=True)
    path, credit = ASSETS.painting(painting)
    if path:
        picture(s, path, 7.25, 0, W - 7.25, H, alt=credit or painting, label=f"Painting {painting}", cover=True)
        band = rect(s, 7.25, H - 0.55, W - 7.25, 0.55, radius=0)
        alpha_fill(band, "000000", 0.55)
        mono(s, 7.45, H - 0.42, W - 7.65, 0.3, credit, size=mono_fit(credit, W - 7.65, 9.5), color=BODY)
    mono(s, M, 1.45, 3, 0.5, f"CHAPTER {number}", size=12, color=ACCENT)
    text(s, M, 1.85, 6.3, 1.1, number, size=66, color=TEXT, font=MONO)
    text(s, M, 3.25, 6.4, 1.6, title, size=44, color=TEXT, line=0.95, anchor=MSO_ANCHOR.BOTTOM)
    text(s, M, 5.0, 6.2, 1.0, subtitle, size=19, color=BODY, line=1.1)
    if extra:
        extra(s)
    mono(s, M, 6.65, 6.4, 0.5, caption, size=mono_fit(caption, 6.4, 10), color=MUTED)
    return s


def mono_width(s, size):
    """Inches taken by one mono line: Courier New advance (0.6 em) plus tracking, sized for the wider
    Quick Look rendering so a fit there also fits in PowerPoint."""
    return len(s) * (0.6 * size + 1.0) / 72


def mono_fit(s, width, size, floor=8):
    """Largest size (0.5 pt steps, not below floor) that keeps s on one line."""
    while size > floor and mono_width(s, size) > width:
        size -= 0.5
    return size


def brand_runs(s, upper=False):
    """Runs for s with the brand "Họa." in the sans face: Courier New draws "Ọ" like a "Q"."""
    runs = []
    for i, part in enumerate(s.split("Họa.")):
        if i:
            runs.append(("Họa.", {"font": SANS, "tracking": 0}))
        if part:
            runs.append((part.upper() if upper else part, {}))
    return runs


def chips(s, x, y, items, h=0.36, size=10, gap=0.14, max_x=W - M):
    """Outlined mono labels in a row (like the outlined buttons of fustic.studio)."""
    cx = x
    for item in items:
        w = 0.3 + mono_width(item, size)
        if cx + w > max_x:
            cx, y = x, y + h + 0.1
        rect(s, cx, y, w, h, fill=None, line=MUTED, radius=0.0)
        mono(s, cx, y, w, h, item, size=size, color=BODY, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        cx += w + gap
    return y + h


# --------------------------------------------------------------- data helpers
def read_props(rel):
    path = ROOT / rel
    props = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()
    return props


def demo_port():
    props = read_props("demo/config/app.properties")
    for key in ("server.port", "http.port", "port", "web.port"):
        if props.get(key, "").isdigit():
            return props[key]
    return "8080"


MODE_LABELS = {"text": "Text", "voice": "Voice", "image": "Image", "room": "Room", "order": "Order",
               "multimodal": "Text + image", "assistant": "Assistant"}


def eval_rates():
    """Success rate per search mode from build/eval/eval_results.json, tolerant of its shape."""
    path = ASSETS.file("build/eval/eval_results.json")
    if not path:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    totals, oks = {}, {}

    def num(d, keys):
        return next((d[k] for k in keys if isinstance(d.get(k), (int, float)) and not isinstance(d.get(k), bool)),
                    None)

    def walk(obj):
        if isinstance(obj, dict):
            mode = str(obj.get("mode", obj.get("type", ""))).lower()
            flag = next((obj[k] for k in ("success", "correct", "passed", "ok", "hit") if isinstance(obj.get(k), bool)),
                        None)
            if mode in MODE_LABELS and flag is not None:
                totals[mode] = totals.get(mode, 0) + 1
                oks[mode] = oks.get(mode, 0) + int(flag)
                return
            for k, v in obj.items():
                if isinstance(v, dict) and str(k).lower() in MODE_LABELS:
                    t = num(v, ("total", "queries", "count", "n"))
                    o = num(v, ("success", "successes", "correct", "passed", "hits", "ok"))
                    if t and o is not None:
                        totals[k.lower()], oks[k.lower()] = t, o
                        continue
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(data)
    order = [m for m in MODE_LABELS if m in totals]
    return [(MODE_LABELS[m], oks[m] / totals[m], oks[m], totals[m]) for m in order] or None


def first_lines(rel, n, width=74):
    path = ASSETS.file(rel)
    if not path:
        return None
    lines = [ln.rstrip() for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    return [ln if len(ln) <= width else ln[: width - 1] + "…" for ln in lines[:n]]


def code_stats():
    path = ASSETS.file("build/code_stats5.tex")
    stats = {}
    if path:
        for name, value in re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", path.read_text(encoding="utf-8")):
            stats[name] = value
    return stats


def voice_summary():
    """English summary of build/eval/voice_eval.json (self-hosted Whisper), once the evaluation has run."""
    path = ASSETS.file("build/eval/voice_eval.json")
    if not path:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    summary = (data.get("en") or {}).get("summary") if isinstance(data, dict) else None
    keys = ("mean_seconds", "max_seconds", "wer", "exact_sentences", "n_utterances")
    return summary if isinstance(summary, dict) and all(k in summary for k in keys) else None


def java_methods(cls_name, methods):
    """Javadoc and body of the given methods from the demo source: the code slide's fallback excerpt."""
    src = next((ROOT / "demo/src").rglob(f"{cls_name}.java"), None) if (ROOT / "demo/src").exists() else None
    if not src:
        return None
    lines = src.read_text(encoding="utf-8").splitlines()
    out = []
    for method in methods:
        start = next((i for i, ln in enumerate(lines)
                      if re.match(rf"\s*(public|protected|private|static).*\b{method}\s*\(", ln)), None)
        if start is None:
            return None
        if start and lines[start - 1].strip().startswith("/**"):
            start -= 1
        depth = 0
        for end in range(start, len(lines)):
            depth += lines[end].count("{") - lines[end].count("}")
            if depth == 0 and "}" in lines[end]:
                break
        out += ([""] if out else []) + lines[start:end + 1]
    indent = min(len(ln) - len(ln.lstrip()) for ln in out if ln.strip())
    return src, [ln[indent:] for ln in out]


DEMO_PROPS = read_props("demo/config/app.properties")


def port_of(key, default):
    match = re.search(r":(\d+)", DEMO_PROPS.get(key, ""))
    return match.group(1) if match else default


# ===================================================================== slides
REQS = {r[0]: r for r in model.REQUIREMENTS}
DETAILS = getattr(model, "REQUIREMENT_DETAILS", {})
FRS = [r for r in model.REQUIREMENTS if r[1] == "FR"]
NFRS = [r for r in model.REQUIREMENTS if r[1] == "NFR"]
JAVA_CLASSES = [c for c in model.DESIGN if c["kind"] != "view"]
VIEWS = [c for c in model.DESIGN if c["kind"] == "view"]
PACKAGES = [p for _, _, subs in model.LAYERS for p in subs]
A06_QUERIES = ["black running shoes", "find Nike shoes under 100 dollars", "show me products similar to this image",
               "find my order 20261001", "where is my latest order?"]


def statement(rid):
    return DETAILS.get(rid, (None, None, REQS[rid][2]))[2]


def priority(rid):
    return DETAILS.get(rid, ("—",))[0]


def s_title(d):
    s = d.slide("TERM ESSAY", NOTES["title"], dark_grid=True)
    path, credit = ASSETS.painting("P10")
    if path:
        picture(s, path, 7.6, 0, W - 7.6, H, alt=credit, label="Painting P10", cover=True)
        band = rect(s, 7.6, H - 0.55, W - 7.6, 0.55, radius=0)
        alpha_fill(band, "000000", 0.55)
        mono(s, 7.8, H - 0.42, W - 8.0, 0.3, credit, size=mono_fit(credit, W - 8.0, 9.5), color=BODY)
    text(s, M, 1.55, 6.6, 1.2, "Họa.", size=72, color=TEXT)
    text(s, M, 3.05, 6.7, 1.5, "From requirements to running code.", size=40, color=TEXT, line=0.98)
    text(s, M, 4.6, 6.4, 1.0, "Analysis and design of a painting shop with multimodal search, Gemma 4 and Whisper",
         size=17, color=BODY, line=1.12)
    members = json.loads((HERE / "members.json").read_text(encoding="utf-8"))
    group = f" ▪ GROUP {members['group']}" if members.get("group") else ""
    people = "   ".join(f"{m['name']} — {m['id']}".upper() for m in members["members"])
    mono(s, M, 6.25, 6.7, 0.6, [f"INFORMATION SYSTEM ANALYSIS AND DESIGN ▪ CLASS {members['class']}{group}", people],
         size=10, after=4)


def s_agenda(d):
    s = d.slide("CONTENTS", NOTES["agenda"])
    d.title(s, "One system, five perspectives")
    cols = [("01", "Requirement Determination", "What must the system do, and for whom?", "LECTURES 01–02"),
            ("02", "Analysis", "How does it behave, which concepts does it manage?", "LECTURES 03–04"),
            ("03", "AI in e-commerce", "How does AI help a customer find the right painting?", "A06 ▪ GEMMA 4"),
            ("04", "Design", "How does the software realise the model?", "LECTURE 05"),
            ("05", "Code", "From model to running code, name for name", "LIVE DEMO")]
    cw, gap = 2.25, (W - 2 * M - 5 * 2.25) / 4
    for i, (num, name, question, ref) in enumerate(cols):
        x = M + i * (cw + gap)
        mono(s, x, 2.05, cw, 0.7, num, size=34, color=ACCENT)
        text(s, x, 2.95, cw, 0.9, name, size=19, color=TEXT, line=1.0)
        text(s, x, 3.95, cw, 1.2, question, size=14, color=BODY, line=1.1)
        mono(s, x, 5.2, cw, 0.3, ref, size=10)
    mono(s, M, 6.15, W - 2 * M, 0.3, "THE THREAD OF THE COURSE (LECTURE 01, SLIDE 32)", size=10)
    mono(s, M, 6.45, W - 2 * M, 0.4,
         "PROBLEM → NEED → REQUIREMENT → USE CASE → BEHAVIOUR → DOMAIN MODEL → DESIGN → CODE", size=12.5, color=TEXT)


def s_product(d):
    s = d.slide("PRODUCT", NOTES["product"])
    d.title(s, "Họa. — a painting shop that listens and sees")
    img_dir = ROOT / "demo/web/img"
    paintings = len(list(img_dir.glob("P*.jpg"))) if img_dir.exists() else 0
    intro = (f"Sells prints of {paintings} public-domain masterpieces and matching frames, priced in USD."
             if paintings else "Sells prints of public-domain masterpieces and matching frames, priced in USD.")
    text(s, M, 1.95, 4.9, 0.9, intro, size=16, color=TEXT, line=1.1)
    bullets(s, M, 2.95, 4.9, 2.6, ["Search by text, voice or photo",
                                    "Try a painting on a photo of your own room",
                                    "Curator assistant: ask about paintings and orders",
                                    "Cart → checkout → track or cancel orders",
                                    "Administration: paintings, prices, stock, order status"], size=15)
    mono(s, M, 5.75, 4.9, 0.3, "JAVA ▪ SQLITE ▪ HTML/CSS/JS ▪ GEMMA 4 ▪ WHISPER", size=10.5, color=BODY)
    mono(s, M, 6.15, 4.9, 0.6, [f"{len(model.REQUIREMENTS)} REQUIREMENTS ▪ {len(model.USE_CASES)} USE CASES",
                                f"{len(JAVA_CLASSES)} JAVA CLASSES ▪ {len(model.TABLES)} TABLES"], size=10.5,
         color=ACCENT, after=3)
    picture(s, ASSETS.figure("demo", "home"), 5.85, 1.95, 6.88, 4.3, alt="Họa. home page",
            label="figures/demo/home.png", hint="Screenshot of the demo home page", frame=True)
    mono(s, 5.85, 6.4, 6.88, 0.3, "DEMO SCREENSHOT ▪ HOME PAGE", size=10)


# --------------------------------------------------------------- chapter 01
def s_ch1(d):
    divider(d, "01", "Requirement\nDetermination", "Understand the business first, then write the requirements",
            "LECTURE 01 ▪ BUSINESS INVESTIGATION — LECTURE 02 ▪ REQUIREMENTS ENGINEERING", "P01", notes=NOTES["ch1"])


def s_business(d):
    s = d.slide("01 REQUIREMENT DETERMINATION", NOTES["business"])
    d.title(s, "Understand the business before drawing diagrams")
    label = "INFORMATION SYSTEM = PEOPLE + PROCESSES + DATA + TECHNOLOGY"
    mono(s, M, 1.9, 5.9, 0.3, label, size=mono_fit(label, 5.9, 10))
    quad = [("PEOPLE", "Customers, administrator, warehouse and delivery"),
            ("PROCESSES", "Search → cart → checkout → delivery, cancellation"),
            ("DATA", "Paintings, artists, carts, orders, payments"),
            ("TECHNOLOGY", "Java, SQLite, Gemma 4, Whisper")]
    for i, (k, v) in enumerate(quad):
        x, y = M + (i % 2) * 2.9, 2.3 + (i // 2) * 1.0
        rect(s, x, y, 2.75, 0.85)
        mono(s, x + 0.15, y + 0.1, 2.5, 0.25, k, size=10, color=ACCENT)
        text(s, x + 0.15, y + 0.36, 2.5, 0.45, v, size=12.5, color=BODY, line=1.0)
    table(s, M, 4.45, [1.55, 2.0, 2.1], [
        ["Stakeholder", "Goal", "Information need"],
        ["Customer", "Find and buy paintings they like", "Paintings, prices, stock, order status"],
        ["Administrator", "Manage paintings and orders", "Prices, stock, pending orders"],
        ["Warehouse, delivery", "Ship the right painting to the right place", "Order details, addresses"],
        ["Support staff", "Answer customers quickly", "Customer order history"]], size=12, row_h=0.47)
    picture(s, ASSETS.figure("vp", "c1_context"), 6.55, 1.9, W - M - 6.55, 5.0,
            alt="Context view of the Họa. Gallery system", label="figures/vp/c1_context.png",
            hint="Context view: Họa. Gallery and its external entities", panel=True)


def s_chain(d):
    s = d.slide("01 REQUIREMENT DETERMINATION", NOTES["chain"])
    d.title(s, "From business problem to system requirement")
    fr3, uc4 = NAMES.req("FR03"), NAMES.uc("UC04")
    support = ", ".join(model.SUPPORTING_ACTORS.get("UC04", []))
    cards = [("01 ▪ PROBLEM", "Business problem", "Customers like a painting but do not know its title or artist."),
             ("02 ▪ ROOT CAUSE", "Root cause", "Search matches exact keywords only; images are hard to put into words."),
             ("03 ▪ NEED", "Stakeholder need", "Find a painting from a natural sentence, the voice or a photo."),
             ("04 ▪ REQUIREMENT", f"{fr3[0]} ▪ {priority('FR03')}", statement("FR03")),
             ("05 ▪ USE CASE", f"{uc4[0]} {uc4[1]}", f"Primary actor {uc4[2]}; supporting actor {support}.")]
    cw, gap = 2.15, (W - 2 * M - 5 * 2.15) / 4
    for i, (label, head, body) in enumerate(cards):
        x = M + i * (cw + gap)
        rect(s, x, 2.05, cw, 3.65)
        mono(s, x + 0.17, 2.22, cw - 0.3, 0.3, label, size=10, color=ACCENT)
        text(s, x + 0.17, 2.6, cw - 0.3, 0.8, head, size=16, color=TEXT, line=1.0)
        text(s, x + 0.17, 3.45, cw - 0.32, 2.2, body, size=13, color=BODY, line=1.1)
        if i < 4:
            arrow(s, x + cw + 0.04, 3.85, x + cw + gap - 0.04, 3.85)
    mono(s, M, 6.05, W - 2 * M, 0.3, "NEED ≠ SOLUTION — “USE GEMMA” IS A SOLUTION, NOT A REQUIREMENT", size=11,
         color=TEXT)
    mono(s, M, 6.45, W - 2 * M, 0.3, "PATTERN (LECTURE 02): THE SYSTEM SHALL + ACTION + OBJECT + CONDITION", size=10.5)


def s_fr(d):
    s = d.slide("01 REQUIREMENT DETERMINATION", NOTES["fr"])
    d.title(s, f"{len(FRS)} functional requirements, prioritised with MoSCoW")
    half = (len(FRS) + 1) // 2
    gap = 0.5
    tw = (W - 2 * M - gap) / 2 - 0.05
    widths = [0.8, tw - 0.8 - 0.92 - 0.92, 0.92, 0.92]
    for k, chunk in enumerate((FRS[:half], FRS[half:])):
        rows = [["ID", "Requirement", "MoSCoW", "Use case"]]
        for rid, _, title, ucs in chunk:
            rows.append([rid, short_title(title), priority(rid), ", ".join(ucs)])
        table(s, M + k * (tw + gap), 1.95, widths, rows, size=13, mono_cols=(0, 3), accent_cols=(0,), row_h=0.56)
    counts = {p: sum(1 for r in FRS if priority(r[0]) == p) for p in ("Must", "Should", "Could")}
    mono(s, M, 6.55, W - 2 * M, 0.3, f"FR: MUST {counts['Must']} ▪ SHOULD {counts['Should']} ▪ COULD {counts['Could']}"
                                     " ▪ WON'T (THIS RELEASE): REAL PAYMENTS — THE PAYMENT SERVICE IS SIMULATED",
         size=10.5)


def s_nfr(d):
    s = d.slide("01 REQUIREMENT DETERMINATION", NOTES["nfr"])
    d.title(s, "Non-functional requirements must be measurable")
    cw, gap, ch = 2.83, (W - 2 * M - 4 * 2.83) / 3, 2.0
    for i, (rid, _, title, ucs) in enumerate(NFRS[:8]):
        x, y = M + (i % 4) * (cw + gap), 1.95 + (i // 4) * (ch + 0.22)
        rect(s, x, y, cw, ch)
        mono(s, x + 0.16, y + 0.14, cw - 0.3, 0.25, f"{rid} ▪ {priority(rid).upper()}", size=10, color=ACCENT)
        label = nfr_label(title)
        text(s, x + 0.16, y + 0.43, cw - 0.3, 0.35, label, size=15 if len(label) <= 20 else 13, color=TEXT)
        text(s, x + 0.16, y + 0.8, cw - 0.3, ch - 0.9, statement(rid), size=11.5, color=BODY, line=1.05)
    perf = next((r for r in NFRS if re.search(r"\d+\s*seconds?", statement(r[0]))), None)
    if perf:
        mono(s, M, 6.55, W - 2 * M, 0.4, f"“THE SYSTEM SHALL BE FAST” → “{statement(perf[0]).rstrip('.')}” ({perf[0]})",
             size=10.5, color=TEXT)


def s_usecase(d):
    s = d.slide("01 REQUIREMENT DETERMINATION", NOTES["usecase"])
    d.title(s, "A use case is a goal, not a button")
    picture(s, ASSETS.figure("vp", "c1_usecase"), M, 1.9, 7.75, 5.0, alt="Use case diagram of Họa. Gallery",
            label="figures/vp/c1_usecase.png", hint=f"{len(model.USE_CASES)} use cases, {len(model.ACTORS)} actors",
            panel=True)
    x = 8.65
    primary = {u[2] for u in model.USE_CASES}
    mono(s, x, 1.95, W - M - x, 0.3, f"{len(model.ACTORS)} ACTORS", size=10.5, color=ACCENT)
    rows = [[(name, {"color": TEXT}), (f"  {'primary' if name in primary else 'supporting'}", {"size": 12,
                                                                                           "color": MUTED})]
            for name, _ in model.ACTORS]
    text(s, x, 2.3, W - M - x, 1.6, rows, size=14, after=5, line=1.05)
    mono(s, x, 3.95, W - M - x, 0.3, "STAKEHOLDER ≠ ACTOR", size=10.5, color=ACCENT)
    text(s, x, 4.25, W - M - x, 0.9, "Warehouse and support staff have a stake but do not use the system directly.",
         size=13, line=1.08)
    mono(s, x, 5.2, W - M - x, 0.3, "USE CASE = GOAL", size=10.5, color=ACCENT)
    text(s, x, 5.5, W - M - x, 0.6, [[("“Click Search” ", {"color": MUTED}), ("✗   ", {"color": ACCENT}),
                                      ("Search Product ", {"color": TEXT}), ("✓", {"color": ACCENT})]], size=14)
    mono(s, x, 6.2, W - M - x, 0.7, f"FR03 → UC04 → {NAMES.op('SearchService.searchImage')} → TEST", size=9.5)


# --------------------------------------------------------------- chapter 02
def s_ch2(d):
    divider(d, "02", "Analysis", "How the system behaves, and which concepts it manages",
            "LECTURE 03 ▪ FUNCTIONAL ANALYSIS — LECTURE 04 ▪ DOMAIN MODEL (A03)", "P05", notes=NOTES["ch2"])


def s_spec(d):
    s = d.slide("02 ANALYSIS", NOTES["spec"])
    uc = NAMES.uc("UC07")
    fr = next(r for r in model.REQUIREMENTS if "UC07" in r[3] and r[1] == "FR")
    d.title(s, f"Use case specification: {uc[1]} ({uc[0]})")
    support = ", ".join(model.SUPPORTING_ACTORS.get("UC07", [])) or "—"
    table(s, M, 1.95, [2.0, 5.4], [
        ["Element", "Description"],
        ["Requirement", f"{fr[0]} — {fr[2]}"],
        ["Primary actor", uc[2]],
        ["Supporting actor", support],
        ["Goal", "Create a valid order from the cart"],
        ["Trigger", "The customer clicks “Place order” in the cart"],
        ["Precondition", "The customer is signed in; the cart has at least one line"],
        ["Postcondition", "A PLACED order is saved, stock is reduced, the cart is empty"]], size=13, row_h=0.56)
    x = 8.35
    mono(s, x, 1.95, W - M - x, 0.3, "MAIN FLOW", size=10.5, color=ACCENT)
    numbered(s, x, 2.3, W - M - x, 2.6, ["The system shows the cart lines and the total",
                                         "The customer picks an address and a payment method",
                                         "The system re-reads prices and checks stock",
                                         "It creates the Order and OrderItems at frozen prices",
                                         "It records the payment, reduces stock, empties the cart"], size=13, gap=5)
    mono(s, x, 4.9, W - M - x, 0.3, "ALTERNATIVE FLOWS", size=10.5, color=ACCENT)
    bullets(s, x, 5.2, W - M - x, 1.8, ["Painting out of stock → name it, create no order",
                                        "Address not owned by the customer → choose again",
                                        "Payment rejected → choose another method"], size=13, gap=4)


def s_activity(d):
    s = d.slide("02 ANALYSIS", NOTES["activity"])
    d.title(s, "From scenario to activity: decisions follow rules")
    picture(s, ASSETS.figure("vp", "c2_activity_checkout"), M, 1.9, 7.9, 5.0, alt="Checkout activity diagram",
            label="figures/vp/c2_activity_checkout.png", hint="Swimlanes: Customer / Họa. system / Database",
            panel=True)
    x = 8.8
    mono(s, x, 1.95, W - M - x, 0.3, "FOUR QUESTIONS (LECTURE 03)", size=10.5, color=ACCENT)
    numbered(s, x, 2.3, W - M - x, 2.0, ["What is the actor's goal?", "What is the normal flow?",
                                         "What can go wrong?", "How does the system respond?"], size=13, gap=4)
    mono(s, x, 4.35, W - M - x, 0.3, "BUSINESS RULE → DECISION", size=10.5, color=ACCENT)
    bullets(s, x, 4.65, W - M - x, 1.6, ["No stock, no order", "The address must belong to the customer",
                                         "Cancel only before shipment"], size=13, gap=4)
    mono(s, x, 6.35, W - M - x, 0.5, "FR07 → UC07 → SCENARIO → ACTIVITY", size=10)


def s_consistency(d):
    s = d.slide("02 ANALYSIS", NOTES["consistency"])
    d.title(s, "Consistency check: cancel before shipment")
    fr = next(r for r in model.REQUIREMENTS if "UC11" in r[3])
    uc = NAMES.uc("UC11")
    link = next((l for l in model.USE_CASE_LINKS if l[0] == "UC11"), None)
    base = NAMES.uc(link[1]) if link else None
    table(s, M, 1.95, [1.55, 5.15], [
        ["Artefact", "What must agree"],
        ["Requirement", f"{fr[0]} — {fr[2]}"],
        ["Use case", f"{uc[0]} {uc[1]}" + (f" «{link[2].lower()}» {base[0]} {base[1]}" if link else "")],
        ["Decision", "Has the order been shipped yet?"],
        ["State machine", "Cancel only from PLACED or PROCESSING"],
        ["Design", f"{NAMES.op('OrderService.cancelOrder')} → {NAMES.op('Order.cancel')}"],
        ["Operations", f"{NAMES.op('AdminController.updateOrderStatus')} moves the order to SHIPPED"]],
          size=12.5, row_h=0.62)
    picture(s, ASSETS.figure("vp", "c2_state_order"), 7.6, 1.9, W - M - 7.6, 2.75, alt="Order state machine",
            label="figures/vp/c2_state_order.png", hint="PLACED → PROCESSING → SHIPPED → DELIVERED", panel=True)
    picture(s, ASSETS.figure("demo", "order_cancel"), 7.6, 4.85, W - M - 7.6, 2.05,
            alt="A customer cancels an order in the demo", label="figures/demo/order_cancel.png", frame=True)


def s_domain(d):
    s = d.slide("02 ANALYSIS", NOTES["domain"])
    d.title(s, "Domain concepts: CartItem ≠ OrderItem")
    picture(s, ASSETS.figure("vp", "c2_domain"), M, 1.9, 6.35, 5.0, alt="Domain model",
            label="figures/vp/c2_domain.png", hint=f"{len(model.ANALYSIS)} concepts and their associations", panel=True)
    x = 7.25
    cart_price = next(a.split(":")[0] for a in model.ANALYSIS["CartItem"] if "Price" in a)
    unit_price = next(a.split(":")[0] for a in model.ANALYSIS["OrderItem"] if "Price" in a)
    table(s, x, 1.95, [1.45, 2.0, W - M - x - 3.45], [
        ["", "CartItem", "OrderItem"],
        ["Purpose", "Shopping", "Transaction"],
        ["Lifetime", "Temporary", "Persistent"],
        ["Owned by", "Cart", "Order"],
        ["Price", f"{cart_price}: when added", f"{unit_price}: frozen at checkout"],
        ["After checkout", "Cart is emptied", "Stays in the order"]], size=12.5, row_h=0.46)
    mono(s, x, 4.95, W - M - x, 0.3, "CHECKOUT IS A TRANSFORMATION (A03)", size=10.5, color=ACCENT)
    text(s, x, 5.25, W - M - x, 0.4, [[("Cart ", {"color": TEXT}), ("—checkout «create»→ ", {"font": MONO, "size": 12}),
                                       ("Order", {"color": TEXT})]], size=15)
    wanted = [("Customer", "Cart"), ("Cart", "CartItem"), ("Order", "OrderItem"), ("CartItem", "Product")]
    mults = [f"{a['a']} {a['a_mult']} — {a['b_mult']} {a['b']}" for pair in wanted
             for a in model.ANALYSIS_ASSOCIATIONS if (a["a"], a["b"]) == pair]
    mono(s, x, 5.8, W - M - x, 1.0, "\n".join(mults), size=10.5, color=BODY, after=2)


# --------------------------------------------------------------- chapter 03
def s_ch3(d):
    def features(s):
        chips(s, M, 5.9, ["01 TEXT", "02 VOICE", "03 IMAGE", "04 ROOM", "05 ASSISTANT"], size=10, max_x=7.0)
    divider(d, "03", "AI in\ne-commerce", "Five ways AI helps a customer find the right painting",
            "ASSIGNMENT A06 ▪ MULTIMODAL SEARCH — GEMMA 4 (L40S SERVER) ▪ WHISPER (ON THE LAPTOP)", "P14",
            extra=features, notes=NOTES["ch3"])


def s_pipeline(d):
    s = d.slide("03 AI IN E-COMMERCE", NOTES["pipeline"])
    d.title(s, "Different inputs, one common query")
    inputs = [("TEXT", [NAMES.op("SearchUI.submitText", False), NAMES.op("QueryService.textQuery", False)]),
              ("VOICE", [NAMES.op("VoiceInput.upload", False), NAMES.op("SpeechService.transcribe", False),
                         NAMES.op("QueryService.voiceQuery", False)]),
              ("PAINTING PHOTO", [NAMES.op("ImageUpload.choose", False), NAMES.op("ImageService.embed", False),
                                  NAMES.op("QueryService.imageQuery", False)]),
              ("ROOM PHOTO", [NAMES.op("RoomPreview.chooseRoom", False), NAMES.op("ImageService.describe", False),
                              NAMES.op("SearchService.searchRoom", False)])]
    bw, bh, gap, top = 2.8, 1.0, 0.12, 1.95
    for i, (label, calls) in enumerate(inputs):
        y = top + i * (bh + gap)
        rect(s, M, y, bw, bh)
        mono(s, M + 0.14, y + 0.09, bw - 0.25, 0.25, label, size=10, color=ACCENT)
        mono(s, M + 0.14, y + 0.36, bw - 0.25, bh - 0.4, "\n".join(calls), size=9.5, color=BODY)
        arrow(s, M + bw + 0.03, y + bh / 2, 3.77, 3.95)

    def split(ref):
        cls_name, method = NAMES.op(ref).split(".", 1)
        return cls_name, "." + method

    retrieve, products, nearest = split("SearchService.retrieve"), split("ProductRepository.allProducts"), \
        split("VectorIndex.nearest")
    rank, render = split("RankingService.rank"), split("SearchResultView.render")
    stage_gap, x0 = 0.28, 3.8
    widths = [1.8, 2.55, 1.9]
    widths.append(W - M - x0 - sum(widths) - 3 * stage_gap)
    details = [("COMMON QUERY", NAMES.cls("CommonQuery"),
                ", ".join(a["name"] for a in model.DESIGN_BY_NAME["CommonQuery"]["attrs"])),
               ("RETRIEVAL", retrieve[0], "\n".join([retrieve[1], products[0], products[1], nearest[0], nearest[1]])),
               ("RANKING", rank[0], rank[1] + "\nS = α·Stext + β·Simage + γ·Sbusiness"),
               ("RESULTS", render[0], render[1])]
    x = x0
    for i, (w, (label, name, detail)) in enumerate(zip(widths, details)):
        rect(s, x, 2.6, w, 2.7)
        mono(s, x + 0.13, 2.71, w - 0.22, 0.3, label, size=10, color=ACCENT)
        text(s, x + 0.13, 3.03, w - 0.22, 0.35, name, size=11, color=TEXT, font=MONO)
        mono(s, x + 0.13, 3.42, w - 0.22, 1.85, detail, size=9, color=BODY)
        if i < len(widths) - 1:
            arrow(s, x + w + 0.03, 3.95, x + w + stage_gap - 0.03, 3.95)
        x += w + stage_gap
    chips(s, M, 6.6, ["DIFFERENT INPUTS → ONE COMMON REPRESENTATION", "RETRIEVAL ≠ RANKING",
                      "THE UI NEVER TOUCHES THE DATABASE", "START SIMPLE"], size=9.5, h=0.34)


def s_voice(d):
    v = voice_summary()
    privacy = next((r for r in NFRS if re.search(r"voice|audio|speech", r[2], re.I)), None)
    limit = re.search(r"within (\d+) seconds?", statement(privacy[0])) if privacy else None
    notes = NOTES["voice"]
    if v:
        notes += (f" We measured it on {v['n_utterances']} English test sentences: Whisper {v.get('model', '')} on the "
                  f"laptop's processor needs {v['mean_seconds']:.2f} seconds on average and at most "
                  f"{v['max_seconds']:.2f} seconds" + (f", well within the {limit.group(1)} seconds of {privacy[0]}"
                                                         if limit else "") +
                  f", with a word error rate of {v['wer'] * 100:.1f} percent.")
    s = d.slide("03 AI IN E-COMMERCE", notes)
    d.title(s, "Voice search: the audio never leaves the laptop")
    picture(s, ASSETS.figure("vp", "c2_seq_voice"), M, 1.9, 7.55, 4.35, alt="Voice search sequence of assignment A06",
            label="figures/vp/c2_seq_voice.png", hint="The 7 participants required by A06", panel=True)
    mono(s, M, 6.35, 7.55, 0.6, "THE 7 PARTICIPANTS OF A06: CUSTOMER ▪ SEARCHUI ▪ SPEECHSERVICE ▪ QUERYSERVICE ▪ "
                               "SEARCHSERVICE ▪ PRODUCTREPOSITORY ▪ RANKINGSERVICE", size=9.5)
    x = 8.45
    numbered(s, x, 1.95, W - M - x, 3.0, [
        f"{NAMES.op('VoiceInput.upload')} sends the recording",
        f"{NAMES.op('SpeechService.transcribe')} calls {NAMES.cls('WhisperClient')} on the laptop",
        "The customer reviews and edits the transcript",
        f"{NAMES.op('SearchService.searchVoice')} follows the text path",
        "Whisper down → null; the customer is asked to type"], size=12.5, gap=5)
    pw, py = W - M - x, 5.1
    rect(s, x, py, pw, 1.8)
    if v:
        mono(s, x + 0.18, py + 0.12, pw - 0.3, 0.3, f"MEASURED ON THE LAPTOP ▪ WHISPER {v.get('model', '').upper()}",
             size=9.5, color=ACCENT)
        cw = (pw - 0.36) / 3
        for i, (value, label) in enumerate([(f"{v['mean_seconds']:.2f} s", "MEAN TIME"),
                                            (f"{v['wer'] * 100:.1f} %", "WORD ERROR"),
                                            (f"{v['exact_sentences']}/{v['n_utterances']}", "EXACT")]):
            text(s, x + 0.18 + i * cw, py + 0.45, cw, 0.5, value, size=24, color=TEXT)
            mono(s, x + 0.18 + i * cw, py + 0.98, cw, 0.25, label, size=8.5)
        mono(s, x + 0.18, py + 1.35, pw - 0.3, 0.3,
             f"MAX {v['max_seconds']:.2f} S" + (f" ▪ {privacy[0]} LIMIT {limit.group(1)} S" if limit else "") +
             f" ▪ {v['n_utterances']} EN SENTENCES", size=8.5, color=BODY)
    else:
        mono(s, x + 0.18, py + 0.12, pw - 0.3, 0.3, "VOICE MEASUREMENTS", size=10, color=ACCENT)
        text(s, x + 0.18, py + 0.45, pw - 0.36, 1.25,
             f"{privacy[0]}: {statement(privacy[0])}" if privacy else "build/eval/voice_eval.json", size=11,
             color=BODY, line=1.05)


def s_image(d):
    s = d.slide("03 AI IN E-COMMERCE", NOTES["image"])
    d.title(s, "Search by image: vectors and cosine similarity")
    blocks = [
        ("IMAGE ENCODER (fθ)", [("z", {}), ("q", {"sub": True}), (" = f", {}), ("θ", {"sub": True}), ("(I", {}),
                                 ("q", {"sub": True}), (")", {})],
         f"Gemma 4 describes the photo → style, subject, colour → {NAMES.op('VectorIndex.toVector')}"),
        ("COSINE SIMILARITY", [("s(q, p) = z", {}), ("q", {"sub": True}), (" · z", {}), ("p", {"sub": True}),
                                (" / (‖z", {}), ("q", {"sub": True}), ("‖ ‖z", {}), ("p", {"sub": True}), ("‖)", {})],
         NAMES.op("VectorIndex.cosineSimilarity")),
        ("RANKING (ASSIGNMENT A06)", [("S(x|q) = α·S", {}), ("text", {"sub": True}), (" + β·S", {}),
                                       ("image", {"sub": True}), (" + γ·S", {}), ("business", {"sub": True})],
         f"{NAMES.cls('RankingService')}({', '.join(a['name'] for a in model.DESIGN_BY_NAME['RankingService']['attrs'])})"
         f".rank(...)")]
    y = 1.95
    for label, formula, mapping in blocks:
        mono(s, M, y, 5.9, 0.3, label, size=10.5, color=ACCENT)
        text(s, M, y + 0.3, 5.9, 0.55, [formula], size=21, color=TEXT)
        mono(s, M, y + 0.9, 5.9, 0.55, mapping, size=10, color=BODY)
        y += 1.55
    weights = [DEMO_PROPS.get(f"ranking.{k}") for k in ("alpha", "beta", "gamma")]
    if all(weights):
        mono(s, M, 6.3, 5.9, 0.3, "Họa. (app.properties): α = {} ▪ β = {} ▪ γ = {}".format(*weights), size=10,
             color=BODY)
    mono(s, M, 6.65, 5.9, 0.3, "MULTIMODAL: λt + λi = 1 (A06: λt = λi = 0.5)", size=10.5, color=TEXT)
    picture(s, ASSETS.figure("vp", "c3_seq_image"), 6.8, 1.9, W - M - 6.8, 5.0, alt="Image search sequence",
            label="figures/vp/c3_seq_image.png", hint="Customer → ImageUpload → … → RankingService", panel=True)


def s_room(d):
    s = d.slide("03 AI IN E-COMMERCE", NOTES["room"])
    uc = NAMES.uc("UC14")
    fr = next((r for r in model.REQUIREMENTS if "UC14" in r[3]), None)
    d.title(s, f"Try it in your room ({uc[0]} {uc[1]})", size=28)
    numbered(s, M, 1.95, 5.0, 3.9, [
        f"The customer uploads a photo of the room: {NAMES.op('RoomPreview.chooseRoom')}",
        f"Gemma 4 reads its palette, style and mood: {NAMES.op('SearchService.describeRoom')}",
        f"{NAMES.op('SearchService.searchRoom')} shortlists the 12 closest paintings by cosine",
        f"Gemma 4 picks 3–5 and writes one “why it fits” sentence each ({NAMES.attr('SearchResult.reason')})",
        f"{NAMES.op('RoomPreview.placePainting')} hangs the chosen painting on the wall"], size=13.5, gap=7)
    if fr:
        mono(s, M, 6.1, 5.0, 0.8, f"{fr[0]} ▪ {priority(fr[0]).upper()} ▪ {statement(fr[0]).upper()}", size=9.5,
             color=ACCENT)
    picture(s, ASSETS.figure("demo", "room_preview"), 5.95, 1.95, W - M - 5.95, 4.6,
            alt="A painting previewed on a photo of a room", label="figures/demo/room_preview.png",
            hint="The customer's room photo with the suggested painting on the wall", frame=True)
    mono(s, 5.95, 6.65, W - M - 5.95, 0.3, "DEMO SCREENSHOT ▪ TRY IT IN YOUR ROOM", size=10)


def s_architecture(d):
    timeout = DEMO_PROPS.get("gemma.timeoutSeconds", "15")
    s = d.slide("03 AI IN E-COMMERCE", NOTES["architecture"].format(timeout=timeout))
    d.title(s, "AI behind interfaces, always with a fallback")
    picture(s, ASSETS.figure("vp", "c3_ai_architecture"), M, 1.9, 6.85, 5.0, alt="AI class architecture",
            label="figures/vp/c3_ai_architecture.png", hint="LlmClient, SpeechClient and the services that use AI",
            panel=True)
    x = 7.75
    mono(s, x, 1.95, W - M - x, 0.3,
         f"{NAMES.cls('LlmClient')} ◁ {NAMES.cls('GemmaClient')} ▪ {NAMES.cls('SpeechClient')} ◁ "
         f"{NAMES.cls('WhisperClient')}", size=9.5, color=TEXT)
    table(s, x, 2.35, [2.3, W - M - x - 2.3], [
        ["When", "What Họa. does"],
        [f"Gemma fails or takes > {timeout} s", f"{NAMES.op('QueryService.parseRules', False)}: keyword rules"],
        ["Whisper is not running", "transcribe returns null; the customer types"],
        ["Image not JPEG/PNG/WebP or > 5 MB", "Rejected before Gemma is called"],
        ["Gemma misreads the request", "AI only builds filters; paintings, prices, stock come from the database"],
        ["Someone asks for another's order", "OrderService checks ownership against the session"]], size=11.5,
          row_h=0.55)
    picture(s, ASSETS.figure("demo", "ai_fallback"), x, 5.65, 2.0, 1.25, alt="Search with AI unavailable",
            label="figures/demo/ai_fallback.png", frame=True)
    mono(s, x + 2.15, 5.7, W - M - x - 2.15, 1.1, "SCREENSHOT: SEARCH STILL WORKS WITH GEMMA OFF", size=9.5)


def s_assistant(d):
    s = d.slide("03 AI IN E-COMMERCE", NOTES["assistant"])
    d.title(s, "Curator assistant: Gemma picks the tool")
    picture(s, ASSETS.figure("vp", "c3_seq_assistant"), M, 1.9, 6.9, 5.0, alt="Assistant tool-calling sequence",
            label="figures/vp/c3_seq_assistant.png", hint="Customer → AssistantView → … → OrderRepository",
            panel=True)
    x = 7.8
    picture(s, ASSETS.figure("demo", "assistant"), x, 1.9, W - M - x, 3.05, alt="The assistant answers about an order",
            label="figures/demo/assistant.png", frame=True)
    bullets(s, x, 5.15, W - M - x, 1.8, [
        f"{NAMES.op('AssistantService.ask')} sends the question with tools()",
        f"Gemma 4 picks a tool; {NAMES.op('AssistantService.runTool')} runs it for the session's customer",
        "Ask by text or by voice (Whisper); answers are text only"], size=12, gap=4)


def s_eval(d):
    s = d.slide("03 AI IN E-COMMERCE", NOTES["eval"])
    d.title(s, "Evaluation as required by A06")
    rates = eval_rates()
    if rates:
        bar_chart(s, M, 1.95, 6.6, 4.3, [f"{lab} ({ok}/{tot})" for lab, _, ok, tot in rates],
                  [r for _, r, _, _ in rates])
    else:
        summary = first_lines("build/eval/eval_summary.txt", 12, 70)
        if summary:
            rect(s, M, 1.95, 6.6, 4.3)
            mono(s, M + 0.2, 2.1, 6.2, 4.0, "\n".join(summary), size=10, color=BODY)
        else:
            picture(s, None, M, 1.95, 6.6, 4.3, alt="", label="build/eval/eval_results.json",
                    hint="Success rate per search mode")
    mono(s, M, 6.45, 6.6, 0.4, "SUCCESS RATE = SUCCESSFUL QUERIES / ALL QUERIES", size=10.5, color=TEXT)
    x = 7.6
    mono(s, x, 1.95, W - M - x, 0.3, "DEMO QUERIES (MATCHING A06)", size=10.5, color=ACCENT)
    rows = [[[[(q, {"color": TEXT})]], [[(a, {"font": MONO, "size": 10.5, "color": MUTED})]]]
            for q, a in zip(model.DEMO_QUERIES, A06_QUERIES)]
    table(s, x, 2.3, [2.75, W - M - x - 2.75], [["Họa.", "Assignment A06"]] + rows, size=12.5, row_h=0.62)
    mono(s, x, 6.0, W - M - x, 0.9, "REPORTED: QUERIES, SUCCESSES, RATE, FAILURE EXAMPLES (build/eval/)", size=9.5)


# --------------------------------------------------------------- chapter 04
def s_ch4(d):
    divider(d, "04", "Design", "Analysis says WHAT, design says HOW",
            "LECTURE 05 ▪ FROM ANALYSIS TO DESIGN — OUTLINE 4.1–4.6", "P16", notes=NOTES["ch4"])


def s_transform(d):
    s = d.slide("04 DESIGN", NOTES["transform"])
    d.title(s, "From analysis classes (A04) to design classes (A05)")
    table(s, M, 1.95, [1.85, 2.25, 3.0], [
        ["Analysis", "Design (lecture)", "Họa."],
        ["Cart, CartItem", "Domain class", f"{NAMES.op('Cart.addItem', False)}, {NAMES.op('Cart.calculateTotal', False)}"],
        ["CartItem → OrderItem", "Domain class", NAMES.op("OrderItem.fromCartItem")],
        ["checkout(Cart)", "CheckoutService.checkout(cartID)", NAMES.op("CheckoutService.checkout")],
        ["Business interaction", "Controller + Service", f"{NAMES.cls('CheckoutController')} → "
                                                         f"{NAMES.cls('CheckoutService')}"],
        ["Persistence need", "Repository", f"{NAMES.cls('CartRepository')}, {NAMES.cls('OrderRepository')}"],
        ["Analysis model", "Design class model", f"{len(model.ANALYSIS)} analysis → {len(JAVA_CLASSES)} Java classes"],
        ["Domain structure", "Layered architecture", f"{len(model.LAYERS)} layers, {len(PACKAGES)} packages"]],
          size=12, row_h=0.6, mono_cols=(2,))
    x = 7.95
    pic = picture(s, ASSETS.figure("vp", "c43_design"), x, 1.9, W - M - x, 2.9, alt="Design class diagram",
                  label="figures/vp/c43_design.png", hint="Domain classes with types, methods, navigability",
                  panel=True, fit=True)
    y = (pic.top + pic.height) / 914400 + 0.3 if pic else 4.95
    domain = [p for p in PACKAGES if p.startswith("domain.")]
    table(s, x, y, [1.05, W - M - x - 1.05], [["Package", "Domain classes"]] +
          [[p.split(".", 1)[1], ", ".join(c["name"] for c in model.DESIGN if c["package"] == p)] for p in domain],
          size=11, mono_cols=(0,), row_h=0.36)


def s_db(d):
    s = d.slide("04 DESIGN", NOTES["db"])
    d.title(s, "From data model to an SQLite database")
    picture(s, ASSETS.figure("vp", "c42_tables"), M, 1.9, 7.25, 5.0, alt="Physical database model",
            label="figures/vp/c42_tables.png", hint=f"{len(model.TABLES)} «table» classes with PK/FK", panel=True)
    x = 8.15
    picture(s, ASSETS.figure("demo", "db_tables"), x, 1.9, W - M - x, 2.85, alt="Screenshot of the ecom.db database",
            label="figures/demo/db_tables.png", frame=True)
    mono(s, x, 4.85, W - M - x, 0.3, "COPY SCREEN OF DB ▪ ecom.db", size=10, color=ACCENT)
    bullets(s, x, 5.25, W - M - x, 1.7, ["Inheritance → the subclass table's PK is also its FK",
                                         "1 – * → FK on the many side; 1 – 0..1 → add UNIQUE",
                                         "Composition → composite key, ON DELETE CASCADE"], size=12, gap=4)


def s_layers(d):
    s = d.slide("04 DESIGN", NOTES["layers"])
    d.title(s, "Four layers — a layer is not a package")
    picture(s, ASSETS.figure("vp", "c44_layers"), M, 1.9, 5.9, 5.0, alt="Four layers and their packages",
            label="figures/vp/c44_layers.png", hint="4 layers and their sub-packages", panel=True)
    duty = {"Presentation": "Receive requests, present results", "Application": "Coordinate use cases and workflows",
            "Domain": "Business concepts and rules", "Infrastructure": "SQLite, vector index, Gemma, Whisper"}
    x, y = 6.85, 1.95
    for title, _, subs in model.LAYERS:
        mono(s, x, y, W - M - x, 0.28, title.upper(), size=10.5, color=ACCENT)
        text(s, x, y + 0.28, W - M - x, 0.32, duty.get(title, ""), size=13, color=TEXT)
        mono(s, x, y + 0.62, W - M - x, 0.5, " ▪ ".join(subs), size=9, color=MUTED)
        y += 1.06
    for i, rule in enumerate(["THE UI NEVER TOUCHES THE DATABASE", "SERVICES DEPEND ON INTERFACES"]):
        chips(s, x, 6.2 + i * 0.42, [rule], size=9.5, h=0.32)


def s_checkout_seq(d):
    s = d.slide("04 DESIGN", NOTES["checkout_seq"])
    d.title(s, "Checkout across the layers (Lecture 05)")
    picture(s, ASSETS.figure("vp", "c44_checkout_seq"), M, 1.9, W - 2 * M, 4.2, alt="Checkout sequence across layers",
            label="figures/vp/c44_checkout_seq.png", hint="Controller → Service → Domain → Repository", panel=True)
    mono(s, M, 6.22, W - 2 * M, 0.5, [
        f"{NAMES.cls('CheckoutController')} → {NAMES.op('CheckoutService.checkout')} → Cart, Order (domain)",
        f"→ {NAMES.cls('CartRepository')}, {NAMES.cls('OrderRepository')}, {NAMES.cls('ProductRepository')}"],
         size=10, color=TEXT, after=2)
    mono(s, M, 6.75, W - 2 * M, 0.3,
         f"THE SERVICE COORDINATES; {NAMES.op('Cart.addItem', False).upper()} AND "
         f"{NAMES.op('Order.calculateTotal', False).upper()} LIVE IN THE DOMAIN — NO “GOD CLASS”", size=10)


# --------------------------------------------------------------- chapter 05
def s_ch5(d):
    divider(d, "05", "Code", "From model to running code, name for name",
            "JAVA ▪ SQLITE ▪ HTML/CSS/JS ▪ PYTHON (WHISPER SERVER)", "P26", notes=NOTES["ch5"])


def s_mapping(d):
    s = d.slide("05 CODE", NOTES["mapping"])
    d.title(s, "Course code ↔ Họa. code")
    rows = [["Lecture code (A05, A06)", "Họa. (Java)", "Package"]]
    pairs = [("product_repository.py: all_products()", "ProductRepository.allProducts"),
             ("query_service.py: text_query, voice_query", "QueryService.textQuery"),
             ("speech_service.py: transcribe(audio_input)", "SpeechService.transcribe"),
             ("search_service.py: search_text(query)", "SearchService.searchText"),
             ("cosine_similarity(a, b)", "VectorIndex.cosineSimilarity"),
             ("S = αStext + βSimage + γSbusiness", "RankingService.rank"),
             ("order_repository.py: find_order(order_id)", "OrderRepository.findOrder"),
             ("CheckoutService.checkout(cartID) : Order", "CheckoutService.checkout"),
             ("main.py", "EcomApplication.main")]
    for course_code, ref in pairs:
        cls_name = ref.split(".")[0]
        rows.append([course_code, NAMES.op(ref), model.DESIGN_BY_NAME.get(cls_name, {}).get("package", "?")])
    table(s, M, 1.9, [4.3, 5.1, W - 2 * M - 9.4], rows, size=11.5, mono_cols=(0, 1, 2), row_h=0.43)
    stats = code_stats()
    line = (f"{stats.get('javaFileCount', '?')} JAVA FILES ▪ {stats.get('javaLineCount', '?')} LINES ▪ "
            f"{stats.get('jsFileCount', '?')} JS FILES ▪ {stats.get('testCount', '?')} TESTS") if stats else \
        f"{len(JAVA_CLASSES)} JAVA CLASSES ▪ {len(VIEWS)} JS VIEWS ▪ {len(PACKAGES)} PACKAGES (FROM model.py)"
    mono(s, M, 6.45, W - 2 * M, 0.3, line, size=10.5, color=ACCENT)
    mono(s, M, 6.75, W - 2 * M, 0.3, "TECHNOLOGY MAPPING (LECTURE 05): CONTROLLER → JAVA HTTP HANDLER ▪ "
                                     "REPOSITORY → JDBC ON SQLITE ▪ DATABASE → ecom.db", size=9.5)


def s_code(d):
    s = d.slide("05 CODE", NOTES["code"])
    d.title(s, "Representative code and how it is verified")
    excerpt = None
    for name in ("VectorIndex.java", "SearchService.java", "QueryService.java"):
        path = ASSETS.file(f"build/excerpts5/{name}")
        if path:
            excerpt = (name, path)
            break
    rect(s, M, 1.9, 7.35, 5.0)
    source = None
    if excerpt:
        lines = [ln.rstrip() for ln in excerpt[1].read_text(encoding="utf-8").splitlines()]
        source = f"build/excerpts5/{excerpt[0]}"
    elif java_methods("VectorIndex", ["toVector", "cosineSimilarity"]):
        path, lines = java_methods("VectorIndex", ["toVector", "cosineSimilarity"])
        source = str(path.relative_to(ROOT / "demo/src/main/java"))
    if source:
        while lines and not lines[0].strip():
            lines.pop(0)
        lines = [(ln if len(ln) <= 82 else ln[:81] + "…") or " " for ln in lines[:23]]
        mono(s, M + 0.2, 2.02, 6.9, 0.3, source, size=mono_fit(source, 6.9, 9.5), color=ACCENT)
        text(s, M + 0.2, 2.35, 7.0, 4.45, "\n".join(lines), size=9.5, color=BODY, font=MONO, line=1.0)
    else:
        mono(s, M + 0.2, 2.02, 6.9, 0.3, "build/excerpts5/VectorIndex.java", size=9.5, color=ACCENT)
        text(s, M + 0.2, 2.4, 6.9, 1.0, f"The {NAMES.op('VectorIndex.cosineSimilarity')} excerpt is inserted "
                                        "once the demo exports it.", size=13, color=MUTED)
    x = 8.25
    tests = first_lines("build/test_results.txt", 40, 60)
    test_line = next((ln for ln in reversed(tests or []) if re.search(r"pass|ok|success", ln, re.I)), None)
    checks = [("01 ▪ MODEL ↔ CODE", "tools/check_code_model.py compares classes, methods, parameters, tables and "
                                    "columns with model.py"),
              ("02 ▪ TESTS", test_line or "Results in build/test_results.txt"),
              ("03 ▪ A06 EVALUATION", "build/eval/: success rate per search mode"),
              ("04 ▪ DATABASE", f"SQLite schema generated from the same specification: {len(model.TABLES)} tables")]
    y = 1.95
    for label, body in checks:
        mono(s, x, y, W - M - x, 0.28, label, size=10.5, color=ACCENT)
        text(s, x, y + 0.3, W - M - x, 0.8, body, size=12.5, color=BODY, line=1.05)
        y += 1.24


def s_demo(d):
    s = d.slide("05 CODE", NOTES["demo"])
    d.title(s, "Live demo script")
    q = model.DEMO_QUERIES
    run = next((r for r in ("demo/run.sh", "demo/scripts/run.sh") if (ROOT / r).exists()), "demo/run.sh")
    whisper = (ROOT / run).exists() and "voice-server" in (ROOT / run).read_text(encoding="utf-8")
    steps = [f"Run {run}{' (it also starts Whisper)' if whisper else ''}; open http://localhost:{demo_port()} as C001",
             f"Type “{q[0]}”",
             f"Click the microphone, say “{q[1]}”, fix the transcript if needed",
             f"Upload a photo: “{q[2]}”; then try a painting in a room",
             "Add a painting and a frame to the cart → checkout → order PLACED",
             f"Ask the assistant: “{q[3]}”, “{q[4]}”",
             "Cancel the new PLACED order; switch to C002, ask for order 20261001 → refused",
             "Switch to ADMIN: change price and stock; move an order to SHIPPED",
             "Set a wrong gemma.baseUrl and restart → search still works with keyword rules"]
    numbered(s, M, 1.95, W - 2 * M, 3.0, steps, size=13.5, gap=5)
    x = 6.1
    picture(s, ASSETS.figure("vp", "c5_deployment"), x, 4.95, W - M - x, 1.95, alt="Deployment diagram",
            label="figures/vp/c5_deployment.png", hint="Laptop ↔ L40S server", panel=True)
    db = Path(DEMO_PROPS.get("db.path", "ecom.db")).name
    mono(s, M, 5.05, x - M - 0.3, 1.8, [
        "DEPLOYMENT",
        f"LAPTOP: BROWSER ▪ JAVA :{demo_port()} ▪ {db} ▪ WHISPER :{port_of('whisper.baseUrl', '9000')}",
        f"L40S: NGINX :{port_of('gemma.baseUrl', '8000')} ▪ vLLM GEMMA 4",
        "ACCOUNTS: C001 (VIP) ▪ C002 ▪ ADMIN"], size=9.5, after=6)


# ------------------------------------------------------------------- closing
def s_conclusion(d):
    s = d.slide("CONCLUSION", NOTES["conclusion"])
    d.title(s, "Traceable from requirement to code")
    chain = ["FR03", "UC04", "ACTIVITY\nSEQUENCE", NAMES.op("ImageService.embed", False).replace(".", "\n."),
             NAMES.op("VectorIndex.cosineSimilarity", False).replace(".", "\n."), "product_feature", "TESTS\nEVALUATION"]
    x, y, h = M, 1.95, 0.62
    widths = [0.3 + max(mono_width(line, 9.5) for line in item.split("\n")) for item in chain]
    gap = (W - 2 * M - sum(widths)) / (len(widths) - 1)
    for i, (item, wdt) in enumerate(zip(chain, widths)):
        rect(s, x, y, wdt, h, fill=None, line=MUTED, radius=0)
        mono(s, x, y, wdt, h, item, size=9.5, color=TEXT, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        if i < len(chain) - 1:
            arrow(s, x + wdt + 0.02, y + h / 2, x + wdt + gap - 0.02, y + h / 2)
        x += wdt + gap
    cw = (W - 2 * M - 0.5) / 2
    mono(s, M, 3.0, cw, 0.3, "LESSONS", size=10.5, color=ACCENT)
    bullets(s, M, 3.35, cw, 3.4, ["Understand the problem and the stakeholders before choosing technology",
                                  "Analysis says what; design says how (A03 → A05)",
                                  "AI is a component behind an interface, with a fallback",
                                  "One shared specification keeps diagrams, database, code and report in sync"],
            size=15, gap=8)
    x2 = M + cw + 0.5
    mono(s, x2, 3.0, cw, 0.3, "LIMITATIONS AND NEXT STEPS", size=10.5, color=ACCENT)
    bullets(s, x2, 3.35, cw, 3.4, ["Payments are simulated; no real gateway yet",
                                   "Small evaluation set; needs more real queries and customer photos",
                                   "Personalised recommendations need interaction data and consent",
                                   "Several machines would need a server database instead of SQLite"], size=15, gap=8)


def s_qa(d):
    s = d.slide("Q&A", NOTES["qa"], dark_grid=True)
    text(s, M, 1.6, 9, 1.0, "Questions & answers", size=54, color=TEXT)
    mono(s, M, 2.75, 9, 0.4, "THANK YOU FOR LISTENING", size=12, color=BODY)
    text(s, M - 0.15, 3.55, W, 3.9, "Họa.", size=230, color=WORDMARK, line=0.8)


def s_folder_map(d):
    s = d.slide("APPENDIX ▪ BACKUP", NOTES["folders"])
    d.title(s, "Folder map of tieuluan/")
    entries = [("README.md", "Folder map: where each chapter's files are", "All"),
               ("tools/model.py", "Single specification: requirements, use cases, classes, tables", "Ch. 1–5"),
               ("vp/", "Visual Paradigm project and the diagram builder plugin", "Ch. 1–4"),
               ("figures/vp/", "Figures exported from VP (c1_… to c5_…)", "Report, slides"),
               ("demo/", "Họa. Java application: src, web, config, data", "Ch. 5, demo"),
               ("demo/voice-server/", "Self-hosted Whisper server (voice search)", "Ch. 3"),
               ("demo/db/", "SQLite schema and sample data", "Ch. 4.2"),
               ("figures/demo/", "Screenshots of the UI and the database", "Report, slides"),
               ("build/eval/", "A06 and voice evaluation results", "Ch. 3"),
               ("build/excerpts5/", "Code excerpts for Chapter 5", "Ch. 5"),
               ("report/", "LaTeX essay, five chapters", "Submission"),
               ("slides/", "Script that builds this deck", "Presentation")]
    rows = [["Path", "Contents", "Used in", "Exists"]]
    for path, what, where in entries:
        rows.append([path, what, where, "✓" if (ROOT / path).exists() else "—"])
    table(s, M, 1.85, [3.0, 6.0, 2.2, W - 2 * M - 11.2], rows, size=12, mono_cols=(0, 3), accent_cols=(3,),
          row_h=0.38)


SLIDES = [s_title, s_agenda, s_product,
          s_ch1, s_business, s_chain, s_fr, s_nfr, s_usecase,
          s_ch2, s_spec, s_activity, s_consistency, s_domain,
          s_ch3, s_pipeline, s_voice, s_image, s_room, s_architecture, s_assistant, s_eval,
          s_ch4, s_transform, s_db, s_layers, s_checkout_seq,
          s_ch5, s_mapping, s_code, s_demo,
          s_conclusion, s_qa, s_folder_map]

NOTES = {
    "title": """Good morning. Our group presents the term essay for Information System Analysis and Design, titled "From requirements to running code". Throughout the talk we use one concrete product, Họa., an online painting shop with multimodal search: customers find a painting by typing, by speaking or by uploading a photo. It has a shopping assistant powered by Gemma 4 and speech recognition by Whisper running on the laptop itself. The talk follows the content of the course, and every concept is illustrated with an example taken from Họa.""",
    "agenda": """The talk has five parts, matching the five chapters of the essay: requirement determination from Lectures 01 and 02, analysis from Lectures 03 and 04, AI in e-commerce from Assignment 06, design from Lecture 05, and finally the code with a live demo. The line at the bottom is the thread our lecturer draws in Lecture 01: from a business problem to a stakeholder need, a requirement, a use case, behaviour, a domain model, a design and finally code. Each part of the talk is one link of that chain.""",
    "product": """Họa. sells prints of public-domain masterpieces, with images from Wikimedia Commons, together with frames, priced in US dollars. Besides the usual e-commerce functions — cart, checkout, order tracking and cancellation — the shop has five AI features that we present in Chapter 3. The numbers at the bottom, requirements, use cases, Java classes and tables, are read directly from the shared specification file of the project, so they always match the report and the code.""",
    "ch1": """Chapter 1 answers the question: what must the system do, and for whom? Lecture 01 says we must understand the business first: its people, processes, information and problems. Lecture 02 turns that understanding into functional and non-functional requirements, actors and use cases.""",
    "business": """Lecture 01 stresses that an information system is not just software: it is people, processes, data and technology. For Họa., the people are customers, the administrator, the warehouse and support staff; the main process is search, cart, checkout, delivery and cancellation. The table on the left is the stakeholder analysis in the lecture's format: the goal of each stakeholder and the information they need. The diagram on the right is the context view: it fixes the boundary of the Họa. Gallery system and its external entities — customer, administrator, payment service and the Gemma 4 service.""",
    "chain": """This is the central chain of Lectures 01 and 02. The business problem: customers like a painting but do not know its title or artist. The root cause: the old search only matches exact keywords. The stakeholder need: find a painting from a natural sentence, the voice or a photo. Only then do we write the system requirement FR03, in the pattern "the system shall plus action plus object plus condition", and the use case UC04 Search by Image. Note that "use Gemma" is a solution, not a requirement: a need is not an implementation.""",
    "fr": """Here is the table of functional requirements in the format of Lecture 02: an identifier, a short description, a MoSCoW priority and the related use case. The Must requirements are the core of the shop: searching, viewing details, the cart, checkout, viewing and looking up orders, and administration. The advanced AI features, such as voice and image search or the assistant, are Should; trying a painting in your room and multimodal search are Could. Real payments are Won't for this release: the payment service is only simulated.""",
    "nfr": """Lecture 02 warns about requirements like "the system shall be fast": they cannot be verified. Every non-functional requirement of Họa. has a measurable condition: text search within two seconds on the demo data, images of at most five megabytes in three formats, audio processed only on the laptop, order ownership checked on the server. Each of these requirements can therefore become a test case.""",
    "usecase": """The use case diagram shows all use cases and four actors. Customer and Administrator are primary actors; the Gemma 4 Service and the Payment Service are supporting actors that the system calls. Two points from Lecture 02: a stakeholder is not an actor — the warehouse or support staff have a stake but do not interact directly; and a use case is a goal, not a button — "Search Product", not "click search". The three search modes specialise Search Product, exactly as in the structure of Assignment 06. The last line is a trace from a requirement to a method and its test.""",
    "ch2": """Chapter 2 turns requirements into models. Lecture 03 asks how the system behaves when an actor performs a use case: scenarios, alternative flows and activity diagrams. Lecture 04, which is Assignment 03, asks which concepts the system must manage: the domain model and the analysis class diagram.""",
    "spec": """This is the Checkout use case specified with the template of Lecture 03: primary and supporting actors, goal, trigger, pre- and postconditions. The main flow has five steps. Our lecturer insists that the normal flow is not enough, so we also list alternative flows: a painting out of stock, an address that does not belong to the customer, a rejected payment. Each alternative flow later becomes a decision in the activity diagram and a check in the code.""",
    "activity": """From the scenario we draw an activity diagram with swimlanes: the customer, the Họa. system and the database. Every decision node comes from a business rule: no stock means no order, the address must belong to the customer, and an order can only be cancelled before shipment. On the right are the four questions of functional analysis from Lecture 03. The trace FR07, UC07, scenario, activity answers the question "where is this requirement represented in our model?" """,
    "consistency": """Lecture 03 has an example of a consistency check for the requirement "a customer may cancel an order before shipment". We did exactly that exercise for Họa.: requirement FR11, the Cancel Order use case extending View Order, the decision "has the order been shipped", a state machine that allows cancellation only from PLACED or PROCESSING, and a design where cancelOrder calls Order.cancel. On the operations side, the administrator moves the order to SHIPPED, and from then on the customer can no longer cancel. The screenshot shows the cancellation in the demo.""",
    "domain": """This is the core of Lecture 04. On the left is the domain model with the concepts of Họa.: customers, paintings, artists, carts, orders, shipping and payments. The lecture stresses that CartItem is not OrderItem: one holds temporary shopping information with the price when the item was added; the other holds persistent transaction information with the price frozen at checkout. Checkout transforms a Cart into an Order, which is why it is drawn as a «create» dependency rather than a permanent association. The multiplicities below are read directly from the model.""",
    "ch3": """Chapter 3 covers AI in e-commerce. Họa. has five AI features: understanding natural text, voice search with Whisper running on the laptop, image search, trying a painting in your own room, and a curator assistant. The common principle: AI helps customers express what they want, while prices, stock and access rights stay under the control of business rules in the code.""",
    "pipeline": """The central principle of Assignment 06: different inputs are turned into one common representation, then candidates are retrieved, then ranked. Họa. has four inputs — text, voice, a photo of a painting and a photo of a room — and each one goes through exactly the classes and methods written in its box. They all meet in CommonQuery. SearchService retrieves candidates from ProductRepository and VectorIndex, and RankingService ranks them with the formula of the assignment. The four principles at the bottom also come from A06: one common representation, retrieval separate from ranking, the UI never touching the database, and starting simple.""",
    "voice": """Voice search. The sequence diagram on the left has exactly the seven participants required by Assignment 06. In Họa., the recording is sent to a self-hosted Whisper model running on the laptop, so the audio never leaves the machine — that is a privacy requirement. The transcript is shown so the customer can correct it, and then it follows the same path as a typed query. If the Whisper server is not running, the system asks the customer to type instead. We deliberately do not implement text-to-speech.""",
    "image": """Image search uses the formulas of Assignment 06. Here the encoder f-theta is Gemma 4 vision: the model describes the photo as a style, a subject and a colour, and VectorIndex.toVector turns that description into a vector. Similarity is the cosine between the query vector and the vector of each painting. The final score combines the text, image and business scores with the alpha, beta and gamma weights of RankingService. The sequence diagram on the right shows the order of calls from ImageUpload to RankingService.""",
    "room": """"Try it in your room" is use case UC14. The customer uploads a photo of their room, and Gemma 4 first reads it: the colours, the interior style, the mood and the light. SearchService.searchRoom then follows the two steps of Assignment 06. Retrieval: VectorIndex shortlists the twelve paintings closest to the suggested style, subject and colour by cosine similarity. Ranking: Gemma 4 sees the photo again with the shortlist, picks the three to five paintings that fit best and writes one sentence for each explaining why it fits, for example that its warm browns echo the wooden floor and the brick wall. If Gemma is unavailable, the vector ranking stays and the sentence is built from the painting's attributes. RoomPreview then hangs the chosen painting on the wall in the photo, so the customer can see how it would look. This requirement is a Could: it adds value to the experience but is not part of the core buying process.""",
    "architecture": """Architecturally, every use of AI goes through an interface: LlmClient for Gemma and SpeechClient for Whisper. This lets us swap the model, or use a fake one in tests. The table on the right lists how Họa. reacts when AI fails: if Gemma fails or takes more than {timeout} seconds, search falls back to keyword rules; if Whisper is down, the customer types; images of the wrong type or size are rejected before Gemma is called; AI only builds filters and never decides prices or stock; order access is always checked on the server.""",
    "assistant": """The curator assistant uses Gemma 4 tool calling. AssistantService sends the question together with the list of tools — search paintings and look up orders. Gemma chooses a tool and its arguments; runTool executes it with the customer id taken from the session, not from the question, so a customer can never retrieve someone else's order. The result goes back to Gemma, which writes the answer. Customers can ask by text or by voice through Whisper; the assistant answers in text.""",
    "eval": """Assignment 06 asks for an evaluation on a small set of queries: the number of queries, the number of successes, the success rate and examples of failures. The chart on the left shows the success rate per mode on our test set. The table on the right lists the demo queries of Họa. next to the example queries of the assignment: "black running shoes" becomes "blue landscape paintings", "Nike shoes under 100 dollars" becomes "Monet paintings under 100 dollars", and the order queries are kept unchanged.""",
    "ch4": """Chapter 4 is the design, following Lecture 05 and the outline 4.1 to 4.6 given by our lecturer. Analysis says what the system needs; design says how the software realises it: design classes, the database, layers and packages, and finally the code.""",
    "transform": """This transformation table follows slide 22 of Lecture 05. The analysis classes Cart, CartItem, Order and OrderItem become domain classes with behaviour; checkout of a Cart at analysis level becomes CheckoutService.checkout at design level; the business interaction becomes a controller plus a service; the need to persist data becomes repositories. Besides the cartId of the lecture, our method also receives the customer id from the session to check ownership, the address and the payment method. On the right is the design class diagram with types, methods and navigability.""",
    "db": """Section 4.2: from the data model we generate the database. The diagram on the left shows the tables with their primary keys, foreign keys and unique constraints. Three main mapping rules: inheritance becomes a subclass table whose primary key is also a foreign key; a one-to-many association puts the foreign key on the many side; composition, such as cart lines and order lines, uses a composite primary key. The screenshot on the right is the real SQLite database of the demo — the "copy screen of DB" our lecturer asked for.""",
    "layers": """Section 4.4: the four-layer architecture of Lecture 05 — presentation, application, domain and infrastructure. Each layer has its own responsibility, listed on the right together with the Java packages that implement it. The lecture points out that a layer is not a package: a layer is an architectural responsibility, a package is a way to organise code, so each layer is split into several packages. Two dependency rules: the UI never touches the database, and services depend only on the interfaces of the repositories and of the AI clients.""",
    "checkout_seq": """This is the checkout sequence across the layers — the central example of Lecture 05. The controller receives the request and CheckoutService coordinates: it reads the cart, checks stock, creates the Order and its OrderItems, saves the order, reduces stock and empties the cart. Business rules such as adding a cart line or computing the total live in the domain classes Cart and Order rather than in the service, which avoids the "God class" the lecture warns about.""",
    "ch5": """Chapter 5 is the code. The goal is not only that it runs, but that it matches the model name for name: classes, methods, parameters, tables and columns in the code are identical to the specification.""",
    "mapping": """This table maps the sample code of the course slides to the code of Họa. The Python code of Assignment 06 — all_products, text_query, transcribe, search_text, cosine_similarity, find_order — keeps its names following Java conventions, and so does CheckoutService.checkout from Lecture 05. The package column shows the layer of each class. The last line is the technology mapping of Lecture 05: a controller is a Java HTTP handler, a repository is JDBC on SQLite.""",
    "code": """On the left is a representative excerpt of the real code. On the right are the four ways we verify consistency: the check_code_model tool compares class, method, parameter, table and column names between the code and the specification; the test suite; the evaluation required by Assignment 06; and the SQLite schema generated from the same specification. This is how the report, the diagrams and the code stay aligned.""",
    "demo": """This is the script of the live demo. We search by text, by voice, by image and try a painting in a room; add a painting and a frame to the cart and check out; ask the assistant about orders; cancel an order; sign in as another customer to show that their order is refused; open the administration page to change price, stock and order status; and finally switch Gemma off to show that search still works. The diagram on the right is the deployment: everything runs on the laptop except Gemma 4, which runs on the L40S server.""",
    "conclusion": """To conclude, we kept one continuous trace: from requirement FR03 and use case UC04, through the activity and sequence diagrams, to the methods in the code, the database table and the test and evaluation results. The main lessons: understand the problem before choosing technology; analysis says what and design says how; AI is a component behind an interface with a fallback; and one shared specification keeps every artefact consistent. Limitations: payments are simulated and the evaluation set is still small.""",
    "qa": """Thank you for listening. We are happy to answer your questions.""",
    "folders": """Backup slide, for questions about where an artefact lives: each row is a folder of tieuluan, what it contains and the chapter that uses it. The last column shows whether the folder existed when the deck was built.""",
}


def strip_notes(prs):
    """Quick Look hangs on decks with notes slides, so the render copies drop them."""
    for slide in prs.slides:
        for rid, rel in list(slide.part.rels.items()):
            if rel.reltype.endswith("/notesSlide"):
                slide.part.drop_rel(rid)
    lst = prs.part._element.find(qn("p:notesMasterIdLst"))
    if lst is not None:
        for master in list(lst):
            rid = master.get(qn("r:id"))
            lst.remove(master)
            prs.part.drop_rel(rid)
        prs.part._element.remove(lst)


def render_qa(pptx, out):
    """Render each slide with Quick Look (one single-slide copy per slide) plus a contact sheet."""
    split = out / "_split"
    shutil.rmtree(split, ignore_errors=True)
    split.mkdir(parents=True)
    for old in out.glob("slide-*.png"):
        old.unlink()
    count = len(Presentation(pptx).slides)
    pngs = []
    for i in range(count):
        p = Presentation(pptx)
        lst = p.slides._sldIdLst
        for j, sid in enumerate(list(lst)):
            if j != i:
                rid = sid.get(qn("r:id"))
                lst.remove(sid)
                p.part.drop_rel(rid)
        strip_notes(p)
        f = split / f"slide-{i + 1:02d}.pptx"
        p.save(f)
        try:
            subprocess.run(["qlmanage", "-t", "-s", "1600", "-o", str(split), str(f)], capture_output=True,
                           check=False, timeout=30)
        except subprocess.TimeoutExpired:
            continue
        png = split / (f.name + ".png")
        if png.exists():
            target = out / f"{f.stem}.png"
            png.replace(target)
            pngs.append(target)
    thumbs = [Image.open(p).convert("RGB").resize((400, 225)) for p in pngs]
    cols = 4
    sheet = Image.new("RGB", (cols * 410 + 10, max(1, (len(thumbs) + cols - 1) // cols) * 245 + 10), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    for k, t in enumerate(thumbs):
        x, y = 10 + (k % cols) * 410, 10 + (k // cols) * 245
        sheet.paste(t, (x, y))
        draw.text((x + 4, y + 228), pngs[k].stem, fill=(230, 230, 230))
    sheet.save(out / "contact.png")
    shutil.rmtree(split, ignore_errors=True)
    return pngs


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--qa", action="store_true", help="render slides/qa/slide-NN.png with Quick Look")
    parser.add_argument("--allow-stale", action="store_true", help="also use figures exported before the cutoff")
    parser.add_argument("--dummies", action="store_true", help="grey stand-ins for missing figures (layout tests)")
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    global ASSETS
    ASSETS = Assets(args.allow_stale, args.dummies)
    deck = Deck()
    deck.total = len(SLIDES)
    for build in SLIDES:
        build(deck)
    if NAMES.missing:
        raise SystemExit("Names not in tools/model.py: " + ", ".join(sorted(set(NAMES.missing))))
    props = deck.prs.core_properties
    props.title = "Họa. — From requirements to running code"
    props.subject = "Term essay presentation, Information System Analysis and Design"
    props.author = "Họa. group — Class 04"
    out = Path(args.out)
    deck.prs.save(out)
    print(f"Saved {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}: {len(SLIDES)} slides")
    if ASSETS.missing or ASSETS.stale:
        print("Missing:", ", ".join(sorted(set(ASSETS.missing))) or "-")
        print("Stale (exported before the painting shop):", ", ".join(sorted(set(ASSETS.stale))) or "-")
    if args.qa:
        pngs = render_qa(out, HERE / "qa")
        print(f"Rendered {len(pngs)} slides to slides/qa/ (contact.png)")


if __name__ == "__main__":
    main()
