"""Generate the SQLite database of the Họa. demo from model.TABLES and the painting catalogue.

Usage: python3 tools/gen_sql.py
Writes demo/db/ecom_schema_sqlite.sql (DDL, names exactly as in model.TABLES), demo/db/seed.sql (demo
data) and build/sql_validation.txt (the schema and seed run in an in-memory SQLite database).
"""
from pathlib import Path
import json
import sqlite3
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import model  # noqa: E402

DB = ROOT / "demo" / "db"
BUILD = ROOT / "build"
CATALOG = ROOT / "demo" / "data" / "catalog.json"
SHIPPING_FEE = 8  # USD, flat rate per order
# Composition parts and inheritance sub-tables disappear with their owner row.
CASCADE = {"cart_item.cart_id", "order_item.order_id", "customer_vip.customer_id", "customer_new.customer_id",
           "painting.product_id", "frame.product_id", "pay_cash.payment_id", "pay_credit.payment_id",
           "product_feature.product_id"}
SQLITE_TYPE = {}                  # model.TABLES already uses SQLite types
# The shop's two product lines. A category names the detail table that holds its products' own attributes;
# a new line with the same attributes (posters, canvas prints) is one more row, not one more table.
CATEGORIES = [
    dict(category_id="CAT-PRINTS", name="Fine-art prints", detail_kind="PAINTING",
         description="Museum-quality prints of public-domain paintings"),
    dict(category_id="CAT-FRAMES", name="Frames", detail_kind="FRAME",
         description="Frames sized for the prints of the shop"),
]
CATEGORY_OF = {c["detail_kind"]: c["category_id"] for c in CATEGORIES}
# Vocabulary of the attribute vectors; VectorIndex.java keeps the same lists (checked by the tests).
STYLES = ["Impressionism", "Post-Impressionism", "Ukiyo-e", "Art Nouveau", "Baroque", "Romanticism",
          "Expressionism", "Abstract", "Realism", "Naive art"]
SUBJECTS = ["landscape", "seascape", "flowers", "portrait", "still life", "cityscape", "everyday life", "abstract"]
COLORS = ["blue", "green", "yellow", "red", "orange", "brown", "white", "black", "purple", "pink"]


def sql_type(c):
    name = SQLITE_TYPE.get(c["type"], c["type"])
    if c["length"] is not None and c["scale"] is not None:
        return f"{name}({c['length']},{c['scale']})"
    if c["length"] is not None:
        return f"{name}({c['length']})"
    return name


def ordered_tables():
    """Tables with every referenced table first."""
    by_name = {t["name"]: t for t in model.TABLES}
    done, result = set(), []

    def visit(name):
        if name not in done:
            done.add(name)
            for c in by_name[name]["columns"]:
                if c["fk"]:
                    visit(c["fk"].split(".")[0])
            result.append(by_name[name])

    for t in model.TABLES:
        visit(t["name"])
    return result


def create_table(t):
    lines = []
    for c in t["columns"]:
        parts = [c["name"], sql_type(c)]
        if not c["nullable"]:
            parts.append("NOT NULL")
        if c["unique"]:
            parts.append("UNIQUE")
        if c["check"]:
            parts.append(f"CHECK ({c['check']})")
        lines.append("    " + " ".join(parts))
    keys = [c["name"] for c in t["columns"] if c["pk"]]
    lines.append(f"    PRIMARY KEY ({', '.join(keys)})")
    for c in t["columns"]:
        if c["fk"]:
            parent, parent_col = c["fk"].split(".")
            cascade = " ON DELETE CASCADE" if f"{t['name']}.{c['name']}" in CASCADE else ""
            lines.append(f"    FOREIGN KEY ({c['name']}) REFERENCES {parent} ({parent_col}){cascade}")
    return f"-- {t['source']}\nCREATE TABLE {t['name']} (\n" + ",\n".join(lines) + "\n);\n"


def literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def insert(table, **row):
    columns = ", ".join(row)
    values = ", ".join(literal(v) for v in row.values())
    return f"INSERT INTO {table} ({columns}) VALUES ({values});"


def one_hot(value, vocabulary):
    return [1.0 if value == v else 0.0 for v in vocabulary]


def feature_vector(painting):
    vector = one_hot(painting["style"], STYLES) + one_hot(painting["subject"], SUBJECTS) \
        + one_hot(painting["dominantColor"], COLORS)
    return struct.pack(f"<{len(vector)}f", *vector)


def seed_rows(catalog):
    rows = [
        "-- Demo customers: C001 is a VIP customer, C002 is a new customer.",
        insert("customer", customer_id="C001", first_name="An", middle_name="Minh", last_name="Nguyen",
               email="an.nguyen@example.com", phone="+84 912 345 678", date_of_birth="1998-04-12"),
        insert("customer", customer_id="C002", first_name="Binh", middle_name="Thu", last_name="Tran",
               email="binh.tran@example.com", phone="+84 987 654 321", date_of_birth="2003-09-02"),
        insert("customer_vip", customer_id="C001", vip_level=2, discount_rate=0.10, reward_points=1200),
        insert("customer_new", customer_id="C002", registered_date="2026-10-01", welcome_voucher="WELCOME10"),
        insert("address", address_id="A001", customer_id="C001", house_number="12", street="Trang Tien Street",
               district="Hoan Kiem", city="Hanoi"),
        insert("address", address_id="A002", customer_id="C001", house_number="45", street="Nguyen Chi Thanh Street",
               district="Dong Da", city="Hanoi"),
        insert("address", address_id="A003", customer_id="C002", house_number="96A", street="Tran Phu Street",
               district="Ha Dong", city="Hanoi"),
        "", "-- Categories: each one says which detail table holds the attributes of its products.",
    ]
    rows += [insert("category", **c) for c in CATEGORIES]
    rows += ["", "-- Artists and paintings (prints of public-domain works)."]
    for a in catalog["artists"]:
        rows.append(insert("artist", artist_id=a["artistId"], name=a["name"], nationality=a["nationality"],
                           life_years=a["lifeYears"]))
    for p in catalog["paintings"]:
        rows.append(insert("product", product_id=p["productId"], category_id=CATEGORY_OF["PAINTING"], name=p["name"],
                           price=p["price"], stock_quantity=p["stockQuantity"], image_url=p["imageUrl"],
                           description=p["description"]))
        rows.append(insert("painting", product_id=p["productId"], artist_id=p["artistId"], style=p["style"],
                           subject=p["subject"], dominant_color=p["dominantColor"], medium=p["medium"],
                           year_created=p["yearCreated"], width_cm=p["widthCm"], height_cm=p["heightCm"]))
        rows.append(insert("product_feature", product_id=p["productId"], model_version="style-subject-color/v1",
                           feature_vector=feature_vector(p), updated_at="2026-10-29 09:00:00"))
    rows += ["", "-- Frames."]
    for f in catalog["frames"]:
        rows.append(insert("product", product_id=f["productId"], category_id=CATEGORY_OF["FRAME"], name=f["name"],
                           price=f["price"], stock_quantity=f["stockQuantity"], image_url=f["imageUrl"],
                           description=f["description"]))
        rows.append(insert("frame", product_id=f["productId"], material=f["material"], color=f["color"],
                           size_label=f["sizeLabel"]))
    rows += ["", "-- Carts: at most one cart per customer."]
    rows.append(insert("cart", cart_id="CART-C001", customer_id="C001", created_date="2026-10-28 08:00:00",
                       updated_date="2026-10-28 08:05:00"))
    rows.append(insert("cart", cart_id="CART-C002", customer_id="C002", created_date="2026-10-28 08:00:00",
                       updated_date="2026-10-28 08:00:00"))
    rows.append(insert("cart_item", cart_id="CART-C001", product_id="P03", quantity=1, cart_price=89))
    rows += ["", "-- Sample orders of the A06 queries: find my order 20261001, where is my latest order?"]
    rows += order_rows("20261001", "C001", "2026-10-20 09:30:00", "SHIPPED", [("P10", 1, 75), ("F03", 1, 35)],
                       0.10, "A001", "IN_TRANSIT", "GHN26102001", None, ("CREDIT", "SUCCEEDED"))
    rows += order_rows("20261002", "C001", "2026-10-05 14:10:00", "DELIVERED", [("P06", 1, 119)],
                       0.10, "A002", "DELIVERED", "GHN26100502", "2026-10-08", ("CASH", "SUCCEEDED"))
    rows += order_rows("20261003", "C002", "2026-10-27 20:05:00", "PLACED", [("P26", 1, 139), ("F05", 1, 25)],
                       0.0, "A003", "PREPARING", None, None, ("CASH", "PENDING"))
    return rows


def order_rows(order_id, customer_id, date, status, items, discount, address_id, ship_status, tracking,
               delivered, payment):
    subtotal = sum(q * price for _, q, price in items)
    total = round(subtotal - subtotal * discount + SHIPPING_FEE, 2)
    rows = [insert("orders", order_id=order_id, customer_id=customer_id, order_date=date, status=status,
                   total_amount=total)]
    rows += [insert("order_item", order_id=order_id, product_id=pid, quantity=q, unit_price=price)
             for pid, q, price in items]
    rows.append(insert("shipping", shipping_id="SH-" + order_id, order_id=order_id, address_id=address_id,
                       carrier="GHN Express", tracking_number=tracking, shipping_fee=SHIPPING_FEE,
                       status=ship_status, delivered_date=delivered))
    method, pay_status = payment
    paid_at = date if pay_status == "SUCCEEDED" else None
    rows.append(insert("payment", payment_id="PAY-" + order_id, order_id=order_id, method=method, amount=total,
                       payment_date=paid_at, status=pay_status))
    if method == "CASH":
        received = total if pay_status == "SUCCEEDED" else None
        rows.append(insert("pay_cash", payment_id="PAY-" + order_id, cash_received=received,
                           change_amount=0 if received else None))
    else:
        rows.append(insert("pay_credit", payment_id="PAY-" + order_id, card_holder="NGUYEN MINH AN",
                           bank_name="Vietcombank", card_last4="4242", authorization_code="AUTH-7731"))
    return rows


def validate(schema, seed):
    """Run schema + seed in memory and try three statements that must violate a constraint."""
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(schema)
    con.executescript(seed)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    bad = [
        ("quantity 0 in cart_item", "INSERT INTO cart_item VALUES ('CART-C002', 'P01', 0, 100)"),
        ("unknown product in order_item", "INSERT INTO order_item VALUES ('20261003', 'P999', 1, 100)"),
        ("second cart for C001", "INSERT INTO cart VALUES ('CART-X', 'C001', '2026-10-29', '2026-10-29')"),
        ("unknown order status", "UPDATE orders SET status = 'LOST' WHERE order_id = '20261001'"),
        ("product in an unknown category", "UPDATE product SET category_id = 'CAT-NONE' WHERE product_id = 'P01'"),
        ("category with an unknown detail kind", "INSERT INTO category VALUES ('CAT-X', 'Sculpture', 'STATUE', NULL)"),
    ]
    lines = [f"SQLite {sqlite3.sqlite_version}, PRAGMA foreign_keys = ON",
             f"{len(tables)} tables created; {sum(counts.values())} sample rows", ""]
    lines += [f"  {t:<16} {n:>3} rows" for t, n in counts.items()]
    lines.append("")
    rejected = 0
    for label, sql in bad:
        try:
            con.execute(sql)
            lines.append(f"  NOT rejected: {label}")
        except sqlite3.IntegrityError as error:
            rejected += 1
            lines.append(f"  Rejected as expected ({label}): {error}")
    lines.append(f"\n{rejected}/{len(bad)} statements that break a constraint were rejected")
    # Every product has exactly one detail row, in the table its category names.
    mismatched = con.execute("""
        SELECT p.product_id FROM product p JOIN category c ON c.category_id = p.category_id
        WHERE (c.detail_kind = 'PAINTING') != EXISTS (SELECT 1 FROM painting d WHERE d.product_id = p.product_id)
           OR (c.detail_kind = 'FRAME') != EXISTS (SELECT 1 FROM frame d WHERE d.product_id = p.product_id)""").fetchall()
    per_category = con.execute("""
        SELECT c.name, c.detail_kind, COUNT(p.product_id) FROM category c
        LEFT JOIN product p ON p.category_id = c.category_id GROUP BY c.category_id ORDER BY c.category_id""").fetchall()
    lines.append("")
    lines += [f"  category {name!r} ({kind}): {n} products" for name, kind, n in per_category]
    lines.append(f"  products whose detail row is not in the table of their category: {len(mismatched)}")
    return "\n".join(lines) + "\n", len(tables), rejected == len(bad) and not mismatched


def main():
    catalog = json.loads(CATALOG.read_text())
    DB.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    header = ("-- SQLite schema of the Họa. shop, generated from tools/model.py (TABLES).\n"
              "-- Table, column, key and constraint names are exactly those of the data model in section 4.2.\n\n")
    schema = header + "\n".join(create_table(t) for t in ordered_tables())
    seed = "-- Sample data, generated from demo/data/catalog.json.\n" + "\n".join(seed_rows(catalog)) + "\n"
    (DB / "ecom_schema_sqlite.sql").write_text(schema)
    (DB / "seed.sql").write_text(seed)

    report, n_tables, ok = validate(schema, seed)
    (BUILD / "sql_validation.txt").write_text(report)
    print(report)
    if n_tables != len(model.TABLES) or not ok:
        raise SystemExit("schema validation failed")


if __name__ == "__main__":
    main()
