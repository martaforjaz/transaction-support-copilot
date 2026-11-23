"""Compare route accuracy and unsupported diagnoses on fixed synthetic scenarios."""
import json
from statistics import median
from time import perf_counter_ns

from copilot import DEMO, ROOT, answer

CASES = json.loads((ROOT / "cases.json").read_text())


def evaluate(grounded):
    failures = []
    unsupported = 0
    durations = []
    for question, expected, *override in CASES:
        def fetch(reference):
            return override[0] if override else DEMO.get(reference)

        for _ in range(100):
            start = perf_counter_ns()
            result = answer(question, fetch=fetch, grounded=grounded)
            durations.append(perf_counter_ns() - start)
        if result["route"] != expected:
            failures.append({"question": question, "expected": expected, "actual": result["route"]})
        unsupported += result["route"] in {"queue", "retry", "review", "decision"} and result["route"] != expected
    return {
        "cases": len(CASES), "correct_routes": len(CASES) - len(failures),
        "unsupported_diagnoses": unsupported, "median_local_us": round(median(durations) / 1000, 2),
        "failures": failures,
    }


if __name__ == "__main__":
    print(json.dumps({"playbook_only": evaluate(False), "state_and_playbook": evaluate(True)}, indent=2))
