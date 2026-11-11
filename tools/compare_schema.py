"""Compare the DDL that Visual Paradigm generated from the physical model with the schema the demo runs on.

    python3 tools/compare_schema.py      # writes build/schema_comparison.txt, exits 1 on a real difference

Two scripts written by Visual Paradigm from the tables of the ERD c42_erd are compared:
  demo/db/vp_wizard_ddl.sql      VP's Generate Database wizard (Tools > DB > Generate Database, SQLite, Generate DDL),
                                 run in the window by tools/vp_generate_db.py
  demo/db/vp_generated_ddl.sql   VP's SQL generator called by the plugin in every build (DatabaseManager.generateCreateSQL)
with demo/db/ecom_schema_sqlite.sql, written by tools/gen_sql.py from model.TABLES (the schema of demo/data/ecom.db).
Each script is loaded into SQLite and compared table by table: columns, types, NOT NULL, primary keys, UNIQUE and,
when the script has them, foreign keys. Neither VP script has CHECK constraints (the ERD does not hold them), and the
plugin's call writes no FOREIGN KEY either: those are reported as the accepted differences.
"""
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
VP_DDL = ROOT / "demo/db/vp_generated_ddl.sql"
WIZARD_DDL = ROOT / "demo/db/vp_wizard_ddl.sql"
SOURCES = [("Generate Database wizard", WIZARD_DDL), ("SQL generator called in the build", VP_DDL)]
SCHEMA = ROOT / "demo/db/ecom_schema_sqlite.sql"
OUT = ROOT / "build/schema_comparison.txt"


def load(path):
    con = sqlite3.connect(":memory:")
    con.executescript(path.read_text(encoding="utf-8"))
    return con


def norm_type(t):
    """VP writes integer(10), numeric(12, 2) and varchar(4) for char(4); compare the SQLite meaning."""
    t = re.sub(r"\s+", "", t.lower())
    t = re.sub(r"^integer\(\d+\)$", "integer", t)
    return re.sub(r"^char\((\d+)\)$", r"varchar(\1)", t)


def describe(con):
    tables = {}
    for (name, sql) in con.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table' ORDER BY name"):
        cols = {r[1]: dict(type=norm_type(r[2]), notnull=bool(r[3]), pk=r[5] > 0)
                for r in con.execute(f"PRAGMA table_info({name})")}
        unique = set()
        for idx in con.execute(f"PRAGMA index_list({name})"):
            if idx[2] and idx[3] == "u":
                unique |= {r[2] for r in con.execute(f"PRAGMA index_info({idx[1]})")}
        fks = {(r[3], r[2], r[4]) for r in con.execute(f"PRAGMA foreign_key_list({name})")}
        checks = len(re.findall(r"\bCHECK\s*\(", sql, re.I))
        tables[name] = dict(cols=cols, unique=unique, fks=fks, checks=checks)
    return tables


def compare(path, run):
    """Lines of the report and the real differences for one script written by VP."""
    vp = describe(load(path))
    problems = []
    if set(vp) != set(run):
        problems.append(f"tables only in VP: {sorted(set(vp) - set(run))}, only in schema: {sorted(set(run) - set(vp))}")
    n_cols = n_fk = n_check = vp_fk = 0
    for name in sorted(set(vp) & set(run)):
        a, b = vp[name], run[name]
        if set(a["cols"]) != set(b["cols"]):
            problems.append(f"{name}: columns differ {sorted(set(a['cols']) ^ set(b['cols']))}")
            continue
        for col, spec in b["cols"].items():
            n_cols += 1
            for key in ("type", "notnull", "pk"):
                if a["cols"][col][key] != spec[key]:
                    problems.append(f"{name}.{col}: {key} VP={a['cols'][col][key]} schema={spec[key]}")
        if a["unique"] != b["unique"]:
            problems.append(f"{name}: UNIQUE VP={sorted(a['unique'])} schema={sorted(b['unique'])}")
        n_fk += len(b["fks"])
        n_check += b["checks"]
        vp_fk += len(a["fks"])
        if a["fks"] and a["fks"] != b["fks"]:
            problems.append(f"{name}: FOREIGN KEY VP={sorted(a['fks'])} schema={sorted(b['fks'])}")
        if a["checks"]:
            problems.append(f"{name}: VP wrote {a['checks']} CHECK")
    with_fk = vp_fk > 0
    if with_fk and vp_fk != n_fk:
        problems.append(f"VP wrote {vp_fk} foreign keys, the schema has {n_fk}")
    same = "columns, types, NOT NULL, primary keys, UNIQUE" + (" and foreign keys" if with_fk else "")
    lines = [f"{path.relative_to(ROOT)} ({len(vp)} tables)",
             f"  Same tables, {same}: {not problems} ({len(run)} tables, {n_cols} columns"
             + (f", {vp_fk} foreign keys" if with_fk else "") + " compared)"]
    lines += [f"  DIFFERENCE {p}" for p in problems]
    lines.append(f"  Accepted differences: no CHECK ({n_check} in the schema)"
                 + ("" if with_fk else f", no FOREIGN KEY ({n_fk} in the schema)") + ".")
    return lines, problems


def main():
    run = describe(load(SCHEMA))
    lines = [f"Running schema: {SCHEMA.relative_to(ROOT)} ({len(run)} tables), written by tools/gen_sql.py", ""]
    problems = []
    for title, path in SOURCES:
        if not path.exists():
            lines += [f"{title}: {path.relative_to(ROOT)} missing", ""]
            continue
        part, found = compare(path, run)
        lines += [f"{title}: " + part[0]] + part[1:] + [""]
        problems += found
    lines += ["The CHECK constraints are the constraints of model.TABLES (allowed values, positive amounts); the ERD does",
              "not hold them, so tools/gen_sql.py writes them from the same physical model."]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
