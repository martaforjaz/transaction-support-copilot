"""Report response latency and retain model drafts for evidence review."""
import json
import os
from time import perf_counter

from copilot import DEMO, answer, explain
from evaluate import CASES


def main():
    if not os.getenv("OLLAMA_URL"):
        raise SystemExit("Set OLLAMA_URL to run the model evaluation.")
    runs = []
    for question, expected, *override in CASES:
        started = perf_counter()
        result = answer(question, fetch=lambda ref: override[0] if override else DEMO.get(ref))
        draft = explain(question, result)
        runs.append({"question": question, "expected_route": expected, "route": result["route"],
                     "evidence": result["evidence"], "action": result["action"],
                     "source": f"/playbook/{result['route']}", "draft": draft,
                     "latency_ms": round((perf_counter() - started) * 1000)})
    print(json.dumps({"model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"), "runs": runs}, indent=2))


if __name__ == "__main__":
    main()
