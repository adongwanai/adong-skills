# Agent Development And Algorithm Learning Routes

Read this file when the candidate needs a durable learning plan rather than an immediate interview drill.

## Diagnose Before Sequencing

Use the capability map and one concrete artifact per claimed strength. Route a topic to:

- `learn`: the candidate cannot explain the mechanism or boundary;
- `build`: the mechanism is understood but no executable artifact exists;
- `verify`: an artifact exists without a fixed task set, baseline, trace, or failure analysis;
- `explain`: evidence exists but the candidate cannot present ownership, tradeoff, and limitation.

Do not schedule topics merely because they occur in a curriculum. Prioritize the smallest block that can change a target-role judgment.

## Development Route

| Stage | Dependency | Deliverable | Acceptance |
| --- | --- | --- | --- |
| Runtime core | Python/API/concurrency basics | minimal loop with typed state, stop, budget, tool result and trace | deterministic tests cover success, tool error, timeout and stop |
| Context and retrieval | runtime core | context packer plus hybrid retrieval/citation path | fixed retrieval set exposes recall, packing and citation failures |
| Memory and state | context policy | write/recall/conflict/forget rules | time changes, user corrections, cross-session conflicts and refusal cases pass defined checks |
| Safety and sandbox | tool boundary | permission policy and isolated execution | file/network/shell deny cases and approval transitions are executable |
| Harness and reliability | prior stages | checkpoint, replay, retry, idempotency and degradation | injected failures recover or stop without duplicate side effects |
| Evaluation and operations | trace schema | task set, outcome/trajectory/safety evaluators, dashboard and release gate | regression, latency, cost and unsafe action checks produce a Block/Caution/Pass/Improve verdict |
| Senior system design | complete harness | multi-tenant capacity and evolution proposal | candidate defends SLO, failure domains, cost, migration and organizational ownership |

## Algorithm Route

| Stage | Dependency | Deliverable | Acceptance |
| --- | --- | --- | --- |
| Model and optimization foundations | tensor/programming basics | hand-derived attention/training notes plus runnable small experiment | shapes, loss, optimizer, decoding and observed curve are explained without relying on framework names |
| Agent paradigms | model foundations | ReAct/workflow/search comparison on one task set | each method is tied to a failure mode, budget and stopping rule |
| Retrieval and data synthesis | evaluation basics | multi-hop task generator and reachability filter | answer leakage, unanswerable items, selection bias and split contamination are audited |
| Tool-use learning | trace format | SFT or preference dataset with valid/invalid trajectories | format accuracy, environment outcome and generalization are measured separately |
| Reward and verifier | fixed task set | rule/program/model/human verifier stack | gaming, judge variance, length bias and false-positive cases are measured |
| Agentic RL or search | verified baseline | bounded rollouts with reset, reward and credit assignment | same-budget baseline, seeds, mean/std, negative results and failure distribution are reported |
| Self-improvement | robust evaluator | holdout improvement loop | improvements survive frozen holdout and stop before evaluator or benchmark overfit |

## Weekly Loop

1. Pick one `gap` or `unknown` with high role value.
2. Produce one runnable artifact or one evidence repair, not a broad reading list.
3. Verify it with a fixed task, trace and failure note.
4. Run a 20-minute defense using the adaptive interview loop.
5. Update capability, weakness and progress state only from observed evidence.

The route is complete when the candidate can build, verify, defend and state the limitation. Time spent or content consumed is not an acceptance criterion.
