"""Visual Paradigm's own Generate Database wizard on the ERD c42_erd, with screenshots of the window.

    python3 tools/vp_generate_db.py        # about 2 minutes; close Visual Paradigm first

The trial edition builds the ERD of tools/model.py in a new, unsaved project (the trial no longer reopens saved
projects: "Evaluation on this project has been expired"), sets the project's database to SQLite with the driver of
the demo, then does what a person does: Tools > DB > Generate Database, output folder, Generate DDL, OK.
It saves
    figures/vp/c42_generate_db.png        the wizard over the ERD (SQLite, Create Database, Generate DDL)
    figures/vp/c42_generate_db_done.png   "Generate Database - Finish" and VP's ORM messages
    demo/db/vp_wizard_ddl.sql             the DDL file the wizard wrote
and runs tools/compare_schema.py. Only Visual Paradigm's own window is painted, never the rest of the screen
(vp/shots_plugin/TieuLuanShots.java); VP then quits without saving anything.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_vp  # noqa: E402
import diagrams  # noqa: E402
import vp_shots  # noqa: E402

OUT = ROOT / "build/vp_wizard"
ERD = "4.2 Database - entity relationship diagram"
SHOTS = {"c42_generate_db.png": ROOT / "figures/vp/c42_generate_db.png",
         "c42_generate_db_done.png": ROOT / "figures/vp/c42_generate_db_done.png"}
DDL = ROOT / "demo/db/vp_wizard_ddl.sql"
# Clicks in VP's window: the message pane button sits 63, 13 pixels from the bottom right corner; every other
# control is found by its label. path= sets the wizard's output folder.
STEPS = ["unless:ORM Message@-63,-13", "Tools", "popup:DB", "Generate Database", f"path={OUT}",
         "shot:c42_generate_db.png", "OK", "shot:c42_generate_db_done.png"]


def main():
    if subprocess.run(["pgrep", "-f", "Visual Paradigm"], capture_output=True).stdout:
        raise SystemExit("Close Visual Paradigm first.")
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    diagrams.write_xml(OUT / "all.xml")
    build_vp.subset(OUT / "all.xml", {"c42_erd"}, OUT / "unused.vpp", OUT / "erd.xml")
    tree = ET.parse(OUT / "erd.xml")
    tree.getroot().set("project", "")          # kept unsaved
    tree.write(OUT / "erd.xml", encoding="utf-8", xml_declaration=True)
    request = vp_shots.PLUGIN / "shots.request"
    with build_vp.vp_lock(), build_vp.trial_marker():
        vp_shots.compile_plugin()
        request.write_text("\n".join([str(OUT), f"xml={OUT / 'erd.xml'}", f"ddl={OUT / 'api_ddl.sql'}", f"repo={ROOT}",
                                      "dbsetup", "steps=" + ">".join(STEPS) + "|end.png", f"{ERD}|erd.png"]) + "\n",
                           encoding="utf-8")
        if vp_shots.LINK.is_symlink() or vp_shots.LINK.exists():
            vp_shots.LINK.unlink()
        vp_shots.LINK.symlink_to(vp_shots.PLUGIN, target_is_directory=True)
        vp = subprocess.Popen([str(vp_shots.TRIAL_APP / "Contents/MacOS/JavaApplicationStub")],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log = OUT / "shots.log"
        try:
            for _ in range(400):
                time.sleep(1)
                if log.exists() and "exit" in log.read_text(encoding="utf-8").splitlines():
                    break
            else:
                raise SystemExit(f"Timed out; see {log}")
        finally:
            if vp.poll() is None:
                vp.kill()
            request.unlink(missing_ok=True)
            if vp_shots.LINK.is_symlink():
                vp_shots.LINK.unlink()
    lines = log.read_text(encoding="utf-8").splitlines()
    problems = [l for l in lines if l.startswith(("error", "not found", "missing", "click error", "call "))]
    written = sorted(OUT.glob("*.ddl"))
    if problems or not written:
        raise SystemExit("\n".join(problems or ["The wizard wrote no .ddl file"]) + f"\nsee {log}")
    for name, target in SHOTS.items():
        shutil.copy2(OUT / name, target)
        print("saved", target.relative_to(ROOT))
    DDL.write_text(f"-- Written by Visual Paradigm's Generate Database wizard (Tools > DB > Generate Database, SQLite,\n"
                   f"-- Generate DDL) from the ERD c42_erd; copied by tools/vp_generate_db.py.\n"
                   + written[0].read_text(encoding="utf-8"), encoding="utf-8")
    print("saved", DDL.relative_to(ROOT))
    subprocess.run([sys.executable, str(ROOT / "tools/compare_schema.py")], check=True)


if __name__ == "__main__":
    main()
