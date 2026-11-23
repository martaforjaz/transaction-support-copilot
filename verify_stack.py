"""Exercise the copilot against the real Compose stack using disposable transactions."""
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

from copilot import answer

RISK = Path(os.environ.get("RISK_SERVICE_DIR", Path(__file__).resolve().parent.parent /
                           "transaction-risk-integration-service")).resolve()
BASE = "http://127.0.0.1:8080"


def compose(*args):
    subprocess.run(["docker", "compose", *args], cwd=RISK, check=True)


def post(path, payload):
    request = Request(BASE + path, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def wait_for(check):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError("Timed out waiting for the transaction service")


def main():
    os.environ["RISK_SERVICE_URL"] = BASE
    reference = str(uuid4())
    gateway = {"id": reference, "amountMinor": 1250, "currency": "EUR"}
    ledger = {"reference": reference, "total": "12.50", "ccy": "EUR"}
    question = f"Why is {reference} still pending?"
    # Keep Kafka down until the original app (and its consumer) has stopped.
    compose("stop", "kafka")
    try:
        first = post("/transactions/gateway", gateway)
        duplicate = post("/transactions/ledger", ledger)
        pending = answer(question)
        assert first == duplicate and pending["route"] == "queue", (first, duplicate, pending)
        compose("stop", "app")
    finally:
        compose("up", "-d", "app")

    def decided():
        result = answer(question)
        return result if result["route"] == "decision" else None

    recovered = wait_for(decided)
    assert recovered["snapshot"]["attempts"] == 1, recovered
    assert post("/transactions/ledger", ledger) == recovered["snapshot"], recovered
    print(json.dumps({"duplicate_before_restart": first == duplicate,
                      "pending": pending, "recovered": recovered,
                      "duplicate_after_restart": True}, indent=2))


if __name__ == "__main__":
    main()
