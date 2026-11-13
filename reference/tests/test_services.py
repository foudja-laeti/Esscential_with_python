import contextlib
import io
import os
import concurrent.futures
import http.client
import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import unittest
from services.http import create_server, MAX_BODY


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.servers = []
        self.addresses = {}
        for name in ("users", "products", "orders"):
            self.start(name)

    def start(self, name, **kwargs):
        server = create_server(name, **kwargs)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        thread.start()
        self.servers.append((server, thread))
        self.addresses[name] = server.server_port
        return server.server_port

    def tearDown(self):
        for server, thread in self.servers:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def request(self, name, method, suffix="", body=None, headers=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.addresses[name], timeout=3)
        payload = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        headers = dict(headers or {})
        if body is not None:
            headers.setdefault("Content-Type", "application/json")
        path = suffix if suffix.startswith("/health") else "/api/" + name + suffix
        try:
            conn.request(method, path, body=payload, headers=headers)
            res = conn.getresponse()
            status, response_headers = res.status, dict(res.getheaders())
            data = res.read()
            return status, json.loads(data) if data else None, response_headers
        finally:
            conn.close()

    def test_seed_and_service_identification(self):
        for name, count in [("users", 3), ("products", 3), ("orders", 2)]:
            with self.subTest(name=name):
                status, body, headers = self.request(name, "GET")
                self.assertEqual(status, 200)
                self.assertEqual(body["meta"], {"page": 1, "limit": 20, "total": count})
                self.assertEqual(headers["X-Service-Name"], name)
                self.assertIn("application/json", headers["Content-Type"])
                self.assertEqual(self.request(name, "GET", "/health")[1]["status"], "ok")

    def test_user_crud_normalization_and_conflicts(self):
        status, body, headers = self.request("users", "POST", body={"name": " Zoé ", "email": "ZOE@example.test"})
        self.assertEqual(status, 201)
        ident = body["data"]["id"]
        self.assertEqual(headers["Location"], f"/api/users/{ident}")
        self.assertEqual(body["data"]["name"], "Zoé")
        self.assertEqual(body["data"]["email"], "zoe@example.test")
        self.assertEqual(body["data"]["role"], "customer")
        self.assertEqual(self.request("users", "POST", body={"name": "Autre", "email": "zoe@example.test"})[0], 409)
        self.assertEqual(self.request("users", "PATCH", f"/{ident}", body={"role": "staff"})[1]["data"]["role"], "staff")
        self.assertEqual(self.request("users", "PATCH", f"/{ident}", body={"email": "alice@example.test"})[0], 409)
        self.assertEqual(self.request("users", "DELETE", f"/{ident}")[:2], (204, None))
        self.assertEqual(self.request("users", "GET", f"/{ident}")[0], 404)

    def test_product_crud_and_integer_money(self):
        status, body, _ = self.request("products", "POST", body={"name": "Support", "priceCents": 1250, "stock": 3})
        self.assertEqual(status, 201)
        ident = body["data"]["id"]
        self.assertEqual(self.request("products", "PATCH", f"/{ident}", body={"stock": 0})[1]["data"]["priceCents"], 1250)
        self.assertEqual(self.request("products", "DELETE", f"/{ident}")[0], 204)
        self.assertEqual(self.request("products", "GET", f"/{ident}")[0], 404)

    def test_order_lifecycle_and_independent_references(self):
        status, body, _ = self.request("orders", "POST", body={"userId": 999, "items": [{"productId": 888, "quantity": 2}]})
        self.assertEqual(status, 201)  # Références opaques, pas d'appel interservice.
        ident = body["data"]["id"]
        self.assertEqual(body["data"]["status"], "pending")
        self.assertEqual(self.request("orders", "PATCH", f"/{ident}", body={"status": "confirmed"})[0], 200)
        self.assertEqual(self.request("orders", "PATCH", f"/{ident}", body={"status": "confirmed"})[0], 200)
        self.assertEqual(self.request("orders", "PATCH", f"/{ident}", body={"status": "cancelled"})[0], 409)
        self.assertEqual(self.request("orders", "DELETE", f"/{ident}")[0], 204)
        self.assertEqual(self.request("orders", "GET", f"/{ident}")[0], 404)
        self.assertEqual(self.request("orders", "PATCH", "/1", body={"status": "cancelled"})[0], 200)

    def test_search_pagination_and_filters(self):
        self.assertEqual(self.request("products", "GET", "?q=%C3%89cran")[1]["data"][0]["id"], 3)
        self.assertEqual(self.request("users", "GET", "?q=ALICE")[1]["meta"]["total"], 1)
        body = self.request("products", "GET", "?page=2&limit=2")[1]
        self.assertEqual([r["id"] for r in body["data"]], [3])
        self.assertEqual(body["meta"]["total"], 3)
        self.assertEqual(self.request("orders", "GET", "?userId=1&status=pending")[1]["meta"]["total"], 1)
        self.assertEqual(self.request("orders", "GET", "?page=100")[1]["data"], [])
        for suffix in ("?limit=0", "?page=x", "?limit=101", "?page=1&page=2", "?unknown=x"):
            self.assertEqual(self.request("users", "GET", suffix)[0], 400, suffix)
        self.assertEqual(self.request("orders", "GET", "?status=invalid")[0], 400)

    def test_invalid_business_inputs_do_not_mutate(self):
        cases = [
            ("users", {"name": "", "email": "a@example.test"}),
            ("users", {"name": "X", "email": "invalid"}),
            ("users", {"id": 12, "name": "X", "email": "x@example.test"}),
            ("products", {"name": "X", "priceCents": 1.5, "stock": 1}),
            ("products", {"name": "X", "priceCents": True, "stock": 1}),
            ("products", {"name": "X", "priceCents": 20, "stock": -1}),
            ("orders", {"userId": 1, "items": []}),
            ("orders", {"userId": 1, "items": [{"productId": 1, "quantity": 0}]}),
            ("orders", {"userId": 1, "items": [{"productId": 1, "quantity": 1}] * 2}),
            ("orders", {"userId": 1, "items": [{"productId": 1, "quantity": 1}], "status": "confirmed"}),
        ]
        for name, body in cases:
            with self.subTest(service=name, body=body):
                before = self.request(name, "GET")[1]["meta"]["total"]
                self.assertEqual(self.request(name, "POST", body=body)[0], 400)
                self.assertEqual(self.request(name, "GET")[1]["meta"]["total"], before)
        self.assertEqual(self.request("orders", "PATCH", "/1", body={"userId": 2})[0], 400)

    def test_http_errors_and_empty_body(self):
        self.assertEqual(self.request("users", "POST", raw=b"{", headers={"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("users", "POST", raw=b"null", headers={"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("users", "POST", raw=b"{}", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("products", "POST", raw=b'{"name":"X","priceCents":NaN,"stock":1}', headers={"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("users", "POST", raw=b"x" * (MAX_BODY + 1), headers={"Content-Type": "application/json"})[0], 413)
        self.assertEqual(self.request("users", "PUT", "/1")[0], 405)
        self.assertEqual(self.request("users", "GET", "/999")[0], 404)
        self.assertEqual(self.request("users", "GET", "-old")[0], 404)
        self.assertEqual(self.request("users", "GET", "/")[0], 404)
        for name in self.addresses:
            self.assertEqual(self.request(name, "HEAD")[:2], (200, None))
            self.assertEqual(self.request(name, "HEAD", "/999")[:2], (404, None))
            status, data, headers = self.request(name, "OPTIONS")
            self.assertEqual((status, data), (204, None))
            self.assertIn("POST", headers["Allow"])

    def test_isolation_and_reset_on_restart(self):
        self.request("users", "DELETE", "/1")
        self.assertEqual(self.request("orders", "GET", "/1")[0], 200)
        self.start("users")
        self.assertEqual(self.request("users", "GET", "/1")[0], 200)

    def test_concurrent_creation_has_unique_identifiers(self):
        def create(i):
            return self.request("products", "POST", body={"name": f"Produit {i}", "priceCents": 100, "stock": 1})
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(create, range(18)))
        self.assertTrue(all(r[0] == 201 for r in results))
        self.assertEqual(len({r[1]["data"]["id"] for r in results}), 18)
        self.assertEqual(self.request("products", "GET")[1]["meta"]["total"], 21)

    def test_simulated_unavailability_and_health(self):
        self.start("products", mode="unavailable")
        status, body, headers = self.request("products", "GET")
        self.assertEqual(status, 503)
        self.assertEqual(headers["Retry-After"], "5")
        self.assertEqual(body["error"]["code"], "SERVICE_UNAVAILABLE")
        self.assertEqual(self.request("products", "GET", "/health")[0], 200)
        self.assertEqual(self.request("users", "GET")[0], 200)

    def test_delay_and_client_cancellation(self):
        port = self.start("orders", delay_ms=150)
        start = time.monotonic()
        self.assertEqual(self.request("orders", "GET")[0], 200)
        self.assertGreaterEqual(time.monotonic() - start, 0.13)
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=0.02)
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            conn.request("GET", "/api/orders")
            with self.assertRaises(TimeoutError):
                conn.getresponse()
            conn.close()
            time.sleep(0.2)
        self.assertEqual(captured.getvalue(), "")
        self.assertEqual(self.request("orders", "GET", "/health")[0], 200)


class LauncherTests(unittest.TestCase):
    def test_invalid_configuration_exits_cleanly(self):
        root = Path(__file__).resolve().parents[1]
        for args in (["--port", "9000"], ["--service", "users", "--delay-ms", "-1"]):
            result = subprocess.run([sys.executable, "run.py", *args], cwd=root, capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)


    def test_all_processes_start_and_stop_together(self):
        root = Path(__file__).resolve().parents[1]
        holders = []
        ports = []
        for _ in range(3):
            sock = socket.socket()
            sock.bind(("127.0.0.1", 0))
            holders.append(sock)
            ports.append(sock.getsockname()[1])
        for sock in holders:
            sock.close()
        env = dict(os.environ)
        for name, port in zip(("USERS", "PRODUCTS", "ORDERS"), ports):
            env[name + "_PORT"] = str(port)
            env[name + "_MODE"] = "normal"
            env[name + "_DELAY_MS"] = "0"
        env["HOST"] = "127.0.0.1"
        # SIGINT déclenché à l'intérieur du lanceur pour un arrêt portable,
        # y compris sous Windows sans console interactive.
        code = "import threading,signal,run; t=threading.Timer(3,lambda:signal.raise_signal(signal.SIGINT));t.daemon=True;t.start();raise SystemExit(run.main())"
        process = subprocess.Popen([sys.executable, "-c", code], cwd=root, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for name, port in zip(("users", "products", "orders"), ports):
                deadline = time.monotonic() + 2
                while True:
                    try:
                        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=0.2)
                        conn.request("GET", "/health")
                        response = conn.getresponse()
                        body = json.loads(response.read())
                        conn.close()
                        self.assertEqual(body["service"], name)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            self.fail(f"Le service {name} n'a pas démarré.")
                        time.sleep(0.05)
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr.decode(errors="replace"))
            for port in ports:
                with socket.socket() as sock:
                    sock.settimeout(0.2)
                    self.assertNotEqual(sock.connect_ex(("127.0.0.1", port)), 0)
        finally:
            if process.poll() is None:
                # L'arrêt programmé du lanceur assure le nettoyage des enfants.
                process.communicate(timeout=6)


if __name__ == "__main__":
    unittest.main()
