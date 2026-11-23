# Transaction Support Copilot

![Workflow and scenario evaluation](figures/workflow.svg)

A read-only support assistant for synthetic payment transactions. Ask why a payment is pending, check the recorded risk-processing state, and get a next step tied to the support playbook. An unresolved or ambiguous reference prompts clarification.

## Demo

![Browser replay showing a recorded decision, an unconfirmed delay, and a clarification request](figures/demo.gif)

[Download the 14-second MP4](figures/demo.mp4).

## Run the demo

Requires Python 3.11+ and uses only the standard library.

```sh
python app.py
```

Open [the local demo](http://127.0.0.1:8765/) and ask “Why is TX-104 still pending?” Try TX-106 to see how the assistant handles repeated failures. It recommends checking the dead-letter topic without claiming the transaction is on it.

## Connect the risk service

Start the companion [Transaction Risk Integration Service](https://github.com/martaforjaz/transaction-risk-integration-service) using its Compose instructions. Set `RISK_SERVICE_URL=http://127.0.0.1:8080` before launching the demo, then supply a UUID already created by the service. The adapter uses its existing GET endpoint. HTTP 404 produces a reference check, while connectivity and unsupported responses prompt manual review. The API permits a status lookup only and exposes no replay operation.

Optionally set `OLLAMA_URL=http://127.0.0.1:11434` to draft an explanation with a local Ollama model. Set `OLLAMA_MODEL` to an installed model (default `qwen2.5:3b`). The draft is labeled separately and is advisory. Keep this demo local and use synthetic records only.

## Evaluate

```sh
python -m unittest -v
python evaluate.py
```

| Approach | Correct support routes | Incorrect state-specific diagnoses |
| --- | ---: | ---: |
| Keyword search over the playbook | 8/20 | 12 |
| Transaction state and playbook | 20/20 | 0 |

The baseline chooses an entry from keywords alone. The grounded version routes using status and attempt count. For example, TX-107 is **decided** even if the question presupposes it is still pending. An incorrect state-specific diagnosis is an incorrect route that suggests a concrete queue, retry, review, or decision state. The state-aware version cannot distinguish broker downtime from other dispatch issues using the snapshot alone. The next step directs the operator to inspect telemetry.

The [fixed scenarios](cases.json) test routing on synthetic snapshots, including ambiguous references and incomplete or unavailable state. [Raw results](results.json) list baseline failures and median local runtime. Timings exclude network and model calls. The benchmark does not measure LLM answer quality or generalization to real support requests.

## Integration and model checks

Verified on the companion Spring Boot, Kafka, and PostgreSQL stack. Both ingress APIs returned the same pending transaction while Kafka was down. The copilot reported zero recorded attempts and left the cause unconfirmed. After Kafka and the consumer restarted, it reported an existing ALLOW decision with one recorded attempt. Replaying the same ingress request returned the existing result. [Integration recording](stack-results.json).

Run `python verify_stack.py` against an already running **local, disposable** companion Compose stack. This stops Kafka, sends the same synthetic transaction through both ingress APIs, then restarts the application consumer with Kafka available. It checks the pending answer before the restart and checks that the recovered transaction holds a single decision afterwards. Use `RISK_SERVICE_DIR` if the companion repository is in a different directory.

Run `python evaluate_model.py` with Ollama configured to capture explanations, attached evidence, and per-request latency on the fixed scenarios. Assess the drafts against the evidence and action in each row. The three browser captures in the demo show fixture mode with the optional draft disabled.

