"""Generate vp/diagrams.xml, run the VP Open API builder headless, validate the .vpp.

Needs Visual Paradigm 18.1 in /Applications.

    python3 tools/build_vp.py            # build every diagram, export figures/vp/<id>.png/.svg
    python3 tools/build_vp.py --check    # only the geometric self-check of the layouts (no VP run)
"""
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

APP = Path("/Applications/Visual Paradigm.app/Contents/Resources/app")
JRE = APP.parent / "jre.bundle/Contents/Home/bin"
PLUGIN = ROOT / "vp/plugin"
PLUGIN_ID = "ptit.tieuluan.v1"
INSTALL = Path.home() / "Library/Application Support/VisualParadigm/plugins" / PLUGIN_ID
LOG = ROOT / "vp/vp_build.log"


def run_vp(xml_path, out_dir, log=LOG):
    """Compile the plugin and let VP build the project described by xml_path; exports go to out_dir."""
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


def main():
    import diagrams  # noqa: E402  (tools/diagrams.py aggregates tools/vp_diagrams/ch*.py)
    xml_path = ROOT / "vp/diagrams.xml"
    spec = diagrams.write_xml(xml_path)
    problems = diagrams.check()
    for line in problems:
        print("CHECK", line)
    if "--check" in sys.argv:
        return
    out_dir = ROOT / "figures/vp"
    run_vp(xml_path, out_dir)

    project = Path(ET.parse(xml_path).getroot().get("project"))
    project = project if project.is_absolute() else ROOT / project
    with sqlite3.connect(project) as db:
        names = {row[0] for row in db.execute("SELECT NAME FROM DIAGRAM")}
    expected = {d["name"] for d in spec}
    if names != expected:
        raise SystemExit(f"Diagram list mismatch.\nmissing={expected - names}\nextra={names - expected}")
    for d in spec:
        if not d.get("export", True):
            continue
        for ext in ("png", "svg"):
            if not (out_dir / f"{d['id']}.{ext}").is_file():
                raise SystemExit(f"Missing export {d['id']}.{ext}")
    print(f"Built {project.name}: {len(names)} editable diagrams, exports in figures/vp/")


if __name__ == "__main__":
    main()
