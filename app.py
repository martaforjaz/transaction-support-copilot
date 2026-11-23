import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from copilot import PLAYBOOK, ROOT, answer, explain


class Handler(BaseHTTPRequestHandler):
    def send(self, status, content, mime="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path == "/":
            self.send(200, (ROOT / "index.html").read_bytes(), "text/html")
        elif self.path == "/playbook":
            self.send(200, (ROOT / "playbook.json").read_bytes())
        elif self.path.startswith("/playbook/") and self.path[10:] in PLAYBOOK:
            self.send(200, json.dumps(PLAYBOOK[self.path[10:]], indent=2).encode())
        else:
            self.send(404, b"{}")

    def do_POST(self):
        if self.path != "/ask":
            self.send(404, b"{}")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                raise ValueError
            question = json.loads(self.rfile.read(length))["question"]
            if not isinstance(question, str) or not question.strip() or len(question) > 500:
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send(400, b'{"error":"Enter a question of up to 500 characters."}')
            return
        result = answer(question)
        result["draft"] = explain(question, result)
        self.send(200, json.dumps(result).encode())


if __name__ == "__main__":
    print("Transaction Support Copilot at http://127.0.0.1:8765")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()

