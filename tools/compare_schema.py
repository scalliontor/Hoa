"""Compare the DDL that Visual Paradigm generated from the physical model with the schema the demo runs on.

    python3 tools/compare_schema.py      # writes build/schema_comparison.txt, exits 1 on a real difference

demo/db/vp_generated_ddl.sql is written by VP's own SQL generator (DatabaseManager.generateCreateSQL, SQLite
dialect) from the tables of the ERD c42_erd during tools/build_vp.py. demo/db/ecom_schema_sqlite.sql is written by
tools/gen_sql.py from model.TABLES and is the schema of demo/data/ecom.db. Both scripts are loaded into SQLite and
compared table by table. VP's SQLite generator writes no FOREIGN KEY and no CHECK clause: those are reported
separately and are the only accepted differences.
"""
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
VP_DDL = ROOT / "demo/db/vp_generated_ddl.sql"
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


def main():
    vp, run = describe(load(VP_DDL)), describe(load(SCHEMA))
    lines = [f"VP generated DDL : {VP_DDL.relative_to(ROOT)} ({len(vp)} tables)",
             f"Running schema   : {SCHEMA.relative_to(ROOT)} ({len(run)} tables)", ""]
    problems = []
    if set(vp) != set(run):
        problems.append(f"tables only in VP: {sorted(set(vp) - set(run))}, only in schema: {sorted(set(run) - set(vp))}")
    n_cols = n_fk = n_check = 0
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
        if a["fks"] or a["checks"]:
            lines.append(f"  note: VP wrote {len(a['fks'])} FK and {a['checks']} CHECK for {name}")
    lines.append(f"Same tables, columns, types, NOT NULL, primary keys and UNIQUE: {not problems} "
                 f"({len(run)} tables, {n_cols} columns compared)")
    lines += [f"  DIFFERENCE {p}" for p in problems]
    lines += ["",
              f"Accepted differences: VP's SQLite generator writes no FOREIGN KEY ({n_fk} in the schema) and no CHECK "
              f"({n_check} in the schema).",
              "The foreign keys are the relationships drawn in the ERD c42_erd and the checks are the constraints of "
              "model.TABLES; tools/gen_sql.py writes both from the same physical model."]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
