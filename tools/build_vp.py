"""Generate vp/diagrams.xml, run the VP Open API builder headless, validate the .vpp.

Needs Visual Paradigm 18.1 Community Edition ("Visual Paradigm CE.app") and, for the BPMN, DFD and ArchiMate
diagrams that the Community Edition cannot draw, the regular "Visual Paradigm.app" running as a trial.

    python3 tools/build_vp.py                       # build every diagram, export figures/vp/<id>.png/.svg/.pdf
    python3 tools/build_vp.py --check               # only the geometric self-check of the layouts (no VP run)
    python3 tools/build_vp.py --only a,b --out DIR  # test build of some diagrams into DIR (essay files untouched)

Diagrams marked edition="trial" are not exported (the trial stamps "evaluation copy" over every export):
tools/vp_shots.py saves a screenshot of the trial edition's window as figures/vp/<id>.png instead, and the
essay says so in the caption. Finally the trial edition saves the complete project with every diagram.
VP runs one at a time: every run holds vp/.vp.lock.
"""
from pathlib import Path
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import contextlib
import fcntl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

# The Community Edition build exports without the evaluation watermark of the regular (trial) build, so it is
# preferred when installed; VP_APP overrides the choice.
_CANDIDATES = [Path(os.environ["VP_APP"])] if os.environ.get("VP_APP") else []
_CANDIDATES += [Path("/Applications/Visual Paradigm CE.app"), Path("/Applications/Visual Paradigm.app")]
APP = next((c for c in _CANDIDATES if c.exists()), _CANDIDATES[-1]) / "Contents/Resources/app"
TRIAL_APP = Path("/Applications/Visual Paradigm.app/Contents/Resources/app")
VPS = Path.home() / "Library/Application Support/VisualParadigm"
LOCK = ROOT / "vp/.vp.lock"


@contextlib.contextmanager
def vp_lock():
    """One VP run at a time (builds and screenshots share the plugin folder and the edition marker)."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


@contextlib.contextmanager
def trial_marker():
    """The trial edition wants ~/Library/Application Support/VisualParadigm/.eval; the Community Edition refuses
    the command line while it exists. Outside a trial run the file is kept as .eval.trial."""
    on, off = VPS / ".eval", VPS / ".eval.trial"
    if off.exists() and not on.exists():
        off.rename(on)
    try:
        yield
    finally:
        if on.exists():
            on.replace(off)
PLUGIN = ROOT / "vp/plugin"
PLUGIN_ID = "ptit.tieuluan.v1"
INSTALL = Path.home() / "Library/Application Support/VisualParadigm/plugins" / PLUGIN_ID
LOG = ROOT / "vp/vp_build.log"


def run_vp(xml_path, out_dir, log=LOG, app=None):
    """Compile the plugin and let VP build the project described by xml_path; exports go to out_dir."""
    with vp_lock():
        if app is not None and app != APP:
            with trial_marker():
                return _run_vp(xml_path, out_dir, log, app)
        return _run_vp(xml_path, out_dir, log, APP)


def _run_vp(xml_path, out_dir, log, APP):
    JRE = APP.parent / "jre.bundle/Contents/Home/bin"
    trial = INSTALL.parent.parent / ".eval"
    if "CE.app" in str(APP) and trial.exists():
        # Left by the regular (trial) VP app; with it the Community Edition refuses the command line
        # ("Feature not supported by current edition"). Close the regular VP app and move the file away.
        raise SystemExit(f"Remove {trial} (created by the trial edition of VP) before building with VP CE.")
    INSTALL.parent.mkdir(parents=True, exist_ok=True)
    if INSTALL.exists() and INSTALL.resolve() != PLUGIN.resolve():
        raise SystemExit(f"Plugin id already installed elsewhere: {INSTALL}")
    created = not INSTALL.exists()
    if created:
        INSTALL.symlink_to(PLUGIN, target_is_directory=True)
    try:
        with tempfile.TemporaryDirectory(prefix="tieuluan_vp_") as folder:
            temp = Path(folder)
            # The bundled javac has no ZIP file-system provider: compile against
            # the extracted Open API classes instead of the jar.
            with zipfile.ZipFile(APP / "lib/openapi.jar") as archive:
                archive.extractall(temp / "api")
            classes = PLUGIN / "classes"
            shutil.rmtree(classes, ignore_errors=True)
            classes.mkdir()
            subprocess.run([str(JRE / "javac"), "-nowarn", "-encoding", "UTF-8", "-cp", str(temp / "api"),
                            "-d", str(classes), str(PLUGIN / "TieuLuanBuilder.java")], check=True)
            seed = temp / "seed.vpp"
            shutil.copy2(APP / "resources/BaggageSchemas.vpp", seed)
            classpath = ":".join([str(classes)] + [str(p) for d in ("lib", "ormlib") for p in sorted((APP / d).glob("*.jar"))]
                                 + [str(APP / "bin")])
            cmd = [str(JRE / "java"), "-Xmx2048m", "-Dfile.encoding=UTF-8", "-Djava.awt.headless=true",
                   f"-Dtieuluan.root={ROOT}", f"-Dtieuluan.xml={xml_path}", f"-Dtieuluan.out={out_dir}",
                   "-cp", classpath, "com.vp.cmd.Plugin",
                   "-project", str(seed), "-upgrade-project", "-pluginid", PLUGIN_ID]
            with Path(log).open("w") as out:
                subprocess.run(cmd, cwd=APP / "bin", stdout=out, stderr=subprocess.STDOUT, check=False)
        text = Path(log).read_text(errors="replace")
        if "TIEULUAN_BUILD_SUCCESS" not in text:
            tail = "\n".join(line for line in text.splitlines()
                             if "Exception" in line or "at Tieu" in line or "BUILT" in line)
            raise SystemExit(f"VP build failed; see {log}\n" + tail[-3000:])
    finally:
        if created and INSTALL.is_symlink():
            INSTALL.unlink()


def subset(spec_xml, keep, project, path):
    """Copy of the XML with only the diagrams whose id is in keep, saving into project."""
    tree = ET.parse(spec_xml)
    root = tree.getroot()
    for d in list(root):
        if d.get("id") not in keep:
            root.remove(d)
    root.set("project", str(project))
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return [(d.get("id"), d.get("name")) for d in root]


def main():
    import diagrams  # noqa: E402  (tools/diagrams.py aggregates tools/vp_diagrams/ch*.py)
    import vp_shots  # noqa: E402
    xml_path = ROOT / "vp/diagrams.xml"
    spec = diagrams.write_xml(xml_path)
    trial_ids = {d["id"] for d in spec if d.get("edition") == "trial"}
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
        unknown = only - {d["id"] for d in spec}
        if unknown:
            raise SystemExit(f"Unknown diagram ids: {sorted(unknown)}")
    problems = diagrams.check()
    for line in problems:
        if only is None or line.split(":")[0].strip() in only:
            print("CHECK", line)
    if "--check" in sys.argv:
        return

    if only is not None:                     # test build: nothing of the essay is touched
        out_dir = Path(sys.argv[sys.argv.index("--out") + 1]).resolve() if "--out" in sys.argv else \
            Path(tempfile.mkdtemp(prefix="vp_test_"))
        out_dir.mkdir(parents=True, exist_ok=True)
        ce = only - trial_ids
        if ce:
            part = subset(xml_path, ce, out_dir / "test_ce.vpp", out_dir / "test_ce.xml")
            run_vp(out_dir / "test_ce.xml", out_dir, log=out_dir / "vp_build.log")
            for id_, _ in part:
                crop_pdf(out_dir / f"{id_}.pdf")
        if only & trial_ids:
            part = subset(xml_path, only & trial_ids, out_dir / "test_trial.vpp", out_dir / "test_trial.xml")
            vp_shots.shoot(out_dir, [(name, f"{id_}.png") for id_, name in part], out_dir / "test_trial.xml")
        print(f"Test build in {out_dir}")
        return

    out_dir = ROOT / "figures/vp"
    with tempfile.TemporaryDirectory(prefix="vp_parts_") as tmp:
        tmp = Path(tmp)
        # 1. Community Edition: every diagram it supports, with clean exports.
        subset(xml_path, {d["id"] for d in spec} - trial_ids, tmp / "ce.vpp", tmp / "ce.xml")
        run_vp(tmp / "ce.xml", out_dir)
        for d in spec:
            if d["id"] in trial_ids or not d.get("export", True):
                continue
            for ext in ("png", "svg", "pdf"):
                if not (out_dir / f"{d['id']}.{ext}").is_file():
                    raise SystemExit(f"Missing export {d['id']}.{ext}")
            crop_pdf(out_dir / f"{d['id']}.pdf")
        # 2. Trial edition: screenshots of the window for BPMN, DFD and ArchiMate.
        if trial_ids:
            part = subset(xml_path, trial_ids, tmp / "trial.vpp", tmp / "trial.xml")
            vp_shots.shoot(out_dir, [(name, f"{id_}.png") for id_, name in part], tmp / "trial.xml")
            for id_ in trial_ids:
                for ext in ("svg", "pdf"):
                    (out_dir / f"{id_}.{ext}").unlink(missing_ok=True)
        # 3. Trial edition, headless: the complete project with every diagram (its exports are discarded).
        project = Path(ET.parse(xml_path).getroot().get("project"))
        project = project if project.is_absolute() else ROOT / project
        if trial_ids:
            run_vp(xml_path, tmp / "trial_exports", log=ROOT / "vp/vp_build_full.log", app=TRIAL_APP)
        else:
            shutil.copy2(tmp / "ce.vpp", project)

    with sqlite3.connect(project) as db:
        names = {row[0] for row in db.execute("SELECT NAME FROM DIAGRAM")}
    expected = {d["name"] for d in spec}
    if names != expected:
        raise SystemExit(f"Diagram list mismatch.\nmissing={expected - names}\nextra={names - expected}")
    print(f"Built {project.name}: {len(names)} editable diagrams ({len(trial_ids)} as trial screenshots), "
          f"exports in figures/vp/")


WATERMARK = ("evaluation copy",)      # text VP stamps over the page when it runs as an evaluation copy


def crop_pdf(path, margin=4):
    """VP puts the vector diagram on an A4 page: keep only the diagram (shapes and their text, not the
    edition watermark) on a page of exactly that size, so the report can include it like an image."""
    import pymupdf
    src = pymupdf.open(path)
    page = src[0]
    box = pymupdf.Rect()
    for path_ in page.get_drawings():
        r = path_["rect"]
        if path_.get("fill") == (1.0, 1.0, 1.0) and path_.get("color") is None:
            continue                        # the white canvas behind the diagram
        if r.width < 2 and r.height < 2:
            continue                        # the corner spacers placed for the PNG export
        box |= r
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            if abs(line["dir"][1]) > 0.01:
                continue                    # the diagonal edition watermark
            for span in line["spans"]:
                if span["text"].strip() and not any(w in span["text"] for w in WATERMARK):
                    box |= span["bbox"]
    if box.is_empty:
        raise SystemExit(f"Empty PDF export: {path}")
    box = (box + (-margin, -margin, margin, margin)) & page.rect
    out = pymupdf.open()
    target = out.new_page(width=box.width, height=box.height)
    target.show_pdf_page(target.rect, src, 0, clip=box)
    data = out.tobytes(garbage=3, deflate=True)
    src.close()
    out.close()
    Path(path).write_bytes(data)


if __name__ == "__main__":
    main()
