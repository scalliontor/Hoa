"""Every Visual Paradigm figure of the essay; the layouts live in tools/vp_diagrams/ch*.py.

write_xml(path) writes vp/diagrams.xml for the TieuLuanBuilder plugin and returns [{id, name}];
check() returns the problems found by the geometric self-check (labels touching shapes, lines or
other labels, lines through shapes, overlapping shapes, crossing lines). Run tools/build_vp.py.
"""
import xml.etree.ElementTree as ET

from vp_diagrams import common, ch1, ch2, ch3, ch4, ch5

CHAPTERS = [ch1, ch2, ch3, ch4, ch5]


def write_xml(path):
    root = common.new_root()
    for chapter in CHAPTERS:
        chapter.build(root)
    ET.indent(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return [dict(id=d.get("id"), name=d.get("name"), export=d.get("export") != "false")
            for d in root.findall("diagram")]


def check():
    return [problem for d in common.DIAGRAMS for problem in d.check()]


if __name__ == "__main__":
    from pathlib import Path
    out = Path(__file__).resolve().parents[1] / "vp/diagrams.xml"
    for d in write_xml(out):
        print(d["id"], "-", d["name"])
    for line in check():
        print("CHECK", line)
