"""Screenshots of the Visual Paradigm window for the diagrams the Community Edition cannot draw.

BPMN, DFD and ArchiMate diagrams need the full (trial) edition, whose exports carry an "evaluation copy"
watermark. These figures are therefore real screenshots of the trial edition's window (its title bar says
"Visual Paradigm Enterprise (Evaluation Copy)"), and the essay labels them as such.

    python3 tools/vp_shots.py <out dir> <diagrams.xml> "<diagram name>|<file.png>" ...

The trial app starts with an empty project; vp/shots_plugin/TieuLuanShots builds the diagrams of the XML in it
with the essay's builder, opens each one, zooms it to the window and paints VP's own window (never the rest of
the screen) into a PNG. VP then quits without saving. The trial edition's marker file is restored only for this run (build_vp.trial_marker).
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TRIAL_APP = Path("/Applications/Visual Paradigm.app")
VPS = Path.home() / "Library/Application Support/VisualParadigm"
sys.path.insert(0, str(ROOT / "tools"))
PLUGIN = ROOT / "vp/shots_plugin"
LINK = VPS / "plugins/ptit.tieuluan.shots"


def compile_plugin():
    app = TRIAL_APP / "Contents/Resources/app"
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["unzip", "-q", str(app / "lib/openapi.jar"), "-d", f"{tmp}/api"], check=True)
        classes = PLUGIN / "classes"
        shutil.rmtree(classes, ignore_errors=True)
        classes.mkdir()
        subprocess.run([str(app.parent / "jre.bundle/Contents/Home/bin/javac"), "-nowarn", "-encoding", "UTF-8",
                        "-cp", f"{tmp}/api", "-d", str(classes), str(PLUGIN / "TieuLuanShots.java"),
                        str(ROOT / "vp/plugin/TieuLuanBuilder.java")], check=True)


def shoot(out_dir, wanted, xml, timeout=400):
    """Build the diagrams of xml in the trial edition's window and save a screenshot of the window for each
    (diagram name, file name) in wanted."""
    from build_vp import trial_marker, vp_lock
    with vp_lock(), trial_marker():
        return _shoot(out_dir, wanted, xml, timeout)


def _shoot(out_dir, wanted, xml, timeout):
    if subprocess.run(["pgrep", "-f", "Visual Paradigm.app/Contents/MacOS"], capture_output=True).stdout:
        raise SystemExit("Close Visual Paradigm first.")
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    compile_plugin()
    work = Path(tempfile.mkdtemp(prefix="vp_shots_"))
    # The builder saves its project next to the screenshots' work files, never over vp/tieuluan_design.vpp.
    tree = ET.parse(xml)
    tree.getroot().set("project", str(work / "trial_build.vpp"))
    tree.write(work / "trial.xml", encoding="utf-8", xml_declaration=True)
    request = PLUGIN / "shots.request"
    request.write_text("\n".join([str(work), f"xml={work / 'trial.xml'}"] + [f"{n}|{f}" for n, f in wanted]) + "\n",
                       encoding="utf-8")
    log = work / "shots.log"
    if LINK.is_symlink() or LINK.exists():
        LINK.unlink()
    LINK.symlink_to(PLUGIN, target_is_directory=True)
    vp = None
    try:
        vp = subprocess.Popen([str(TRIAL_APP / "Contents/MacOS/JavaApplicationStub")],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        start = time.time()
        lines = []
        while time.time() - start < timeout:
            time.sleep(1)
            lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
            if "exit" in lines:
                break
        else:
            raise SystemExit(f"Timed out; see {log}")
        if any(l.startswith(("error", "missing")) for l in lines):
            raise SystemExit("\n".join(lines))
        for _, f in wanted:
            shutil.copy2(work / f, out_dir / f)
            print("saved", out_dir / f)
    finally:
        if vp and vp.poll() is None:
            vp.kill()
        request.unlink(missing_ok=True)
        if LINK.is_symlink():
            LINK.unlink()
        time.sleep(2)
        shutil.rmtree(work, ignore_errors=True)
    return [out_dir / f for _, f in wanted]


if __name__ == "__main__":
    shoot(sys.argv[1], [tuple(a.split("|", 1)) for a in sys.argv[3:]], sys.argv[2])
