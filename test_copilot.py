import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from copilot import lookup, answer
from evaluate import evaluate

ID = "00000000-0000-0000-0000-000000000010"


class LookupHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200 if self.path == f"/transactions/{ID}" else 404)
        self.end_headers()
        if self.path == f"/transactions/{ID}":
            self.wfile.write(f'{{"id":"{ID}","status":"PENDING","attempts":0}}'.encode())


class Tests(unittest.TestCase):
    def test_grounded_cases(self):
        self.assertEqual(evaluate(True)["failures"], [])

    def test_ambiguous_reference_never_looked_up(self):
        def unexpected(reference):
            self.fail("Lookup must not run for an ambiguous reference")
        self.assertIsNone(answer("TX-104 and TX-107", unexpected)["reference"])

    def test_missing_and_invalid_evidence_requires_review(self):
        missing = answer("Why is it pending?")
        self.assertEqual(missing["route"], "missing")
        self.assertIn("Confirm the reference", missing["action"])
        unavailable = answer("TX-104", lambda reference: {})
        self.assertEqual(unavailable["route"], "unavailable")
        self.assertIn("human review", unavailable["action"])

    def test_http_contract(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), LookupHandler) as server:
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            try:
                with patch.dict("os.environ", {"RISK_SERVICE_URL": f"http://127.0.0.1:{server.server_port}"}):
                    self.assertEqual(answer(f"Look up {ID}")["route"], "queue")
                    self.assertIsNone(lookup("00000000-0000-0000-0000-000000000011"))
            finally:
                server.shutdown()
                worker.join()


if __name__ == "__main__":
    unittest.main()

