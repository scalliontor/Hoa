"""End-to-end check of the Họa. demo through its HTTP API, on a fresh database.

    python3 tools/e2e_check.py      # writes build/e2e_results.txt, exits 1 if a step fails

Starts the real server (demo/build/classes) on port 8691 with a copy of config/app.properties whose database is a
new file created from the schema and seed, so the demo database is never touched. Each step names the use case or
rule it checks and compares the answer with a literal value from the specification. A second server with the
offline configuration (Gemma unreachable) checks the fallback of NFR02. Both servers are stopped at the end.
"""
from http.cookiejar import CookieJar
import base64
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"
OUT = ROOT / "build/e2e_results.txt"
SHIPPING_FEE = 8


class Client:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    def call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=60) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, json.loads(raw) if raw.startswith(b"{") else raw.decode()

    def login(self, customer_id):
        status, _ = self.call("POST", "/api/login", {"customerId": customer_id})
        assert status == 200, status
        return self


def start(config_lines, port, tmp):
    db = Path(tmp) / f"e2e_{port}.db"
    config = Path(tmp) / f"e2e_{port}.properties"
    lines = [l for l in config_lines if not l.startswith(("server.port=", "db.path="))]
    config.write_text("\n".join(lines + [f"server.port={port}", f"db.path={db}"]) + "\n")
    java = subprocess.run([str(DEMO / "scripts/java_home.sh")], capture_output=True, text=True).stdout.strip()
    proc = subprocess.Popen([f"{java}/java", "-Dfile.encoding=UTF-8", "-cp", "build/classes:lib/*",
                             "com.ptit.ecom.presentation.web.EcomApplication", str(config)], cwd=DEMO,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(80):
        try:
            urllib.request.urlopen(base + "/api/session", timeout=1)
            return proc, base
        except OSError:
            time.sleep(0.25)
    proc.kill()
    raise SystemExit(f"server on {port} did not start")


def main():
    subprocess.run([str(DEMO / "build.sh")], cwd=DEMO, check=True, stdout=subprocess.DEVNULL)
    results = []

    def step(name, check):
        try:
            detail = check()
            results.append(("PASS", name, detail or ""))
        except AssertionError as e:
            results.append(("FAIL", name, str(e)))
        except Exception as e:      # an unexpected error is a failure of the step, not of the script
            results.append(("FAIL", name, f"{type(e).__name__}: {e}"))

    procs = []
    with tempfile.TemporaryDirectory(prefix="hoa_e2e_") as tmp:
        online = (DEMO / "config/app.properties").read_text().splitlines()
        offline = (DEMO / "config/app.offline.properties").read_text().splitlines()
        try:
            proc, base = start(online, 8691, tmp)
            procs.append(proc)
            guest, an, binh, admin = Client(base), Client(base).login("C001"), Client(base).login("C002"), \
                Client(base).login("ADMIN")

            def catalogue():
                status, items = guest.call("GET", "/api/products")
                assert status == 200, status
                kinds = {}
                for r in items:
                    p = r["product"]
                    kinds.setdefault((p["kind"], p["category"]["name"]), []).append(p["productId"])
                got = {k: len(v) for k, v in kinds.items()}
                assert got == {("PAINTING", "Fine-art prints"): 32, ("FRAME", "Frames"): 5}, got
                return f"37 products: {got}"
            step("UC01/UC05 catalogue grouped by category (Category -> detail table)", catalogue)

            def monet():
                status, items = guest.call("GET", "/api/search?q=Monet%20paintings%20under%20100%20dollars")
                assert status == 200 and items, (status, items)
                bad = [r["product"]["productId"] for r in items
                       if r["product"]["artist"]["name"] != "Claude Monet" or r["product"]["price"] > 100]
                assert not bad, f"results that are not Monet under $100: {bad}"
                return f"{len(items)} results, all Claude Monet and <= $100; reason: {items[0]['reason']}"
            step("UC02 'Monet paintings under 100 dollars' (FR01: artist and maximum price respected)", monet)

            def blue():
                status, items = guest.call("GET", "/api/search?q=blue%20landscape%20paintings")
                assert status == 200 and items, status
                top = items[0]["product"]
                assert top["kind"] == "PAINTING", top["kind"]
                assert "landscape" in top["subject"] or top["dominantColor"] == "blue", top
                return f"top: {top['productId']} {top['name']} ({top['subject']}, {top['dominantColor']})"
            step("UC02 'blue landscape paintings' returns a blue or landscape painting first", blue)

            def checkout():
                _, cart = an.call("GET", "/api/cart")
                lines = {i["product"]["productId"]: (i["quantity"], i["cartPrice"]) for i in cart["items"]}
                assert lines == {"P03": (1, 89)}, lines
                status, cart = an.call("POST", "/api/cart/items", {"productId": "F01", "quantity": 1})
                assert status == 200, (status, cart)
                f01 = next(i for i in cart["items"] if i["product"]["productId"] == "F01")
                _, before = guest.call("GET", "/api/products")
                stock = {r["product"]["productId"]: r["product"]["stockQuantity"] for r in before}
                status, order = an.call("POST", "/api/checkout", {"addressId": "A001", "paymentMethod": "CASH"})
                assert status == 200, (status, order)
                subtotal = 89 + f01["cartPrice"]
                expected = round(subtotal * 0.9 + SHIPPING_FEE, 2)
                assert order["status"] == "PLACED", order["status"]
                assert abs(float(order["totalAmount"]) - expected) < 0.005, (order["totalAmount"], expected)
                _, after = guest.call("GET", "/api/products")
                left = {r["product"]["productId"]: r["product"]["stockQuantity"] for r in after}
                assert left["P03"] == stock["P03"] - 1 and left["F01"] == stock["F01"] - 1, (stock, left)
                _, cart = an.call("GET", "/api/cart")
                assert cart["items"] == [], cart["items"]
                step.order_id = order["orderId"]
                return (f"order {order['orderId']} PLACED, total {order['totalAmount']} = ({subtotal}) x 0.9 + "
                        f"{SHIPPING_FEE}; stock P03 {stock['P03']}->{left['P03']}, F01 {stock['F01']}->{left['F01']}; "
                        f"cart empty")
            step("UC06/UC07 VIP checkout: price frozen, 10% discount, stock decreased, cart emptied (FR07, BR04)",
                 checkout)

            def empty_cart():
                status, body = an.call("POST", "/api/checkout", {"addressId": "A001", "paymentMethod": "CASH"})
                assert status in (400, 409), (status, body)
                return f"{status}: {body}"
            step("UC07 A: checkout of an empty cart is refused (BR03)", empty_cart)

            def foreign_address():
                binh.call("POST", "/api/cart/items", {"productId": "P05", "quantity": 1})
                status, body = binh.call("POST", "/api/checkout", {"addressId": "A001", "paymentMethod": "CASH"})
                assert status in (400, 403, 404, 409), (status, body)
                return f"{status}: {body}"
            step("UC07 A: an address of another customer is refused", foreign_address)

            def others_order():
                status, body = binh.call("GET", "/api/orders/20261001")
                assert status == 404, (status, body)
                return f"{status}: {body}"
            step("UC08/NFR01: another customer's order is answered as not found (BR08)", others_order)

            def cancel_shipped():
                status, body = an.call("POST", "/api/orders/20261001/cancel")
                assert status == 409, (status, body)
                return f"{status}: {body}"
            step("UC11 A1: a SHIPPED order cannot be cancelled (BR06)", cancel_shipped)

            def cancel_placed():
                status, order = an.call("POST", f"/api/orders/{step.order_id}/cancel")
                assert status == 200 and order["status"] == "CANCELLED", (status, order)
                return f"order {step.order_id} -> CANCELLED"
            step("UC11: a PLACED order is cancelled (FR11)", cancel_placed)

            def admin_status():
                status, order = admin.call("PUT", "/api/admin/orders/20261003", {"status": "DELIVERED"})
                assert status in (400, 409), (status, order)
                status, order = admin.call("PUT", "/api/admin/orders/20261003", {"status": "PROCESSING"})
                assert status == 200 and order["status"] == "PROCESSING", (status, order)
                return "PLACED -> DELIVERED refused; PLACED -> PROCESSING accepted"
            step("UC13: only the next status is accepted (BR07)", admin_status)

            def admin_only():
                status, body = an.call("GET", "/api/admin/orders")
                assert status in (401, 403), (status, body)
                return f"customer gets {status}"
            step("UC12/UC13 A: back office refused to a customer (NFR01)", admin_only)

            def admin_price():
                status, p = admin.call("PUT", "/api/admin/products/P02", {"price": 72.5, "stockQuantity": 4})
                assert status == 200 and float(p["price"]) == 72.5 and p["stockQuantity"] == 4, (status, p)
                status, p = admin.call("PUT", "/api/admin/products/P02", {"price": -1, "stockQuantity": 4})
                assert status == 400, (status, p)
                return "P02 -> $72.50, stock 4; negative price refused"
            step("UC12: price and stock updated; invalid data refused (A1)", admin_price)

            def image_search():
                photo = "data:image/jpeg;base64," + base64.b64encode((DEMO / "web/img/P10.jpg").read_bytes()).decode()
                status, items = guest.call("POST", "/api/search/image", {"image": photo})
                assert status == 200 and items, (status, items)
                top = items[0]
                assert top["product"]["productId"] == "P10", [r["product"]["productId"] for r in items[:3]]
                return f"top: P10 The Great Wave; reason: {top['reason']}"
            step("UC04: a photo of The Great Wave finds P10 first (FR03)", image_search)

            def assistant():
                status, reply = an.call("POST", "/api/assistant", {"message": "Where is my order 20261001?"})
                assert status == 200 and "find_order" in reply["toolsUsed"], (status, reply)
                assert "20261001" in reply["answer"] or "GHN26102001" in reply["answer"], reply["answer"]
                return f"tools {reply['toolsUsed']}, aiUsed={reply['aiUsed']}: {reply['answer'][:110]}"
            step("UC10: the assistant looks the order up with a tool (FR10)", assistant)

            def assistant_ownership():
                status, reply = an.call("POST", "/api/assistant", {"message": "Show me the orders of customer C002"})
                assert status == 200, (status, reply)
                assert "20261003" not in reply["answer"], reply["answer"]
                return f"answer names only An's orders: {reply['answer'][:110]}"
            step("UC10/NFR01: asking for another customer's orders reveals nothing", assistant_ownership)
        finally:
            for p in procs:
                p.terminate()
        try:
            proc, base = start(offline, 8692, tmp)
            procs.append(proc)

            def fallback():
                status, items = Client(base).call("GET", "/api/search?q=blue%20landscape%20paintings")
                assert status == 200 and items, (status, items)
                assert "Keyword rules" in items[0]["reason"], items[0]["reason"]
                return f"{len(items)} results without Gemma; reason: {items[0]['reason']}"
            step("NFR02: search still answers when Gemma is unreachable (keyword rules)", fallback)

            def no_ai_checkout():
                binh = Client(base).login("C002")
                status, cart = binh.call("POST", "/api/cart/items", {"productId": "P05", "quantity": 1})
                assert status == 200, (status, cart)
                status, order = binh.call("POST", "/api/checkout", {"addressId": "A003", "paymentMethod": "CASH"})
                assert status == 200 and order["status"] == "PLACED", (status, order)
                status, orders = binh.call("GET", "/api/orders")
                assert status == 200 and orders[0]["orderId"] == order["orderId"], (status, orders)
                return f"order {order['orderId']} PLACED and listed while Gemma is unreachable"
            step("NFR12: cart, checkout and orders work without the AI services", no_ai_checkout)
        finally:
            for p in procs:
                p.terminate()

    passed = sum(1 for r in results if r[0] == "PASS")
    lines = [f"Họa. end-to-end check {time.strftime('%Y-%m-%d %H:%M')} (fresh database, HTTP API)", ""]
    lines += [f"{s}  {n}\n      {d}" for s, n, d in results]
    lines += ["", f"{passed}/{len(results)} steps passed"]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
