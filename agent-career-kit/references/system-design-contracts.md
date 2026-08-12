# Agent System Design And Algorithm Answer Contracts

Read this with the technical question bank when a candidate needs a reusable design, coding or algorithm response structure.

## Minimal Agent State And Trace

```text
State: task_id, tenant_id, objective, constraints, messages, artifacts,
       step, budget, status, pending_approval, checkpoint, final_result
Trace event: trace_id, task_id, parent_id, timestamp, actor, action,
             arguments_digest, observation, outcome, latency_ms, cost,
             permission_decision, retry_count, evaluator_version
```

State must make stop, resume and replay semantics explicit. Trace arguments may be redacted or hashed; never log secrets by default.

## Tool Contract

```text
Request: call_id, tool_name, schema_version, arguments, idempotency_key, deadline, permission_context
Result:  call_id, status(ok|error|denied|timeout), output, error_code, retryable, side_effects, artifacts, latency_ms
```

Retries belong to policy, not a hidden tool loop. Denied and timed-out calls are observations the Agent can reason about. Side-effecting tools require idempotency or an explicit no-retry rule.

## Context Packing Priority

Pack in order: task and hard constraints, current state, latest tool observations, decision-relevant evidence, retrieved memory with provenance, compacted history, then optional examples. Define eviction by contribution to the next decision, not recency alone. A compaction summary records source span, unresolved decisions and lossy fields.

## Subagent Decision

Use a subagent when work is independently verifiable, has a clear artifact and reduces the critical path. Use a DAG with ownership and join conditions. Do not use one when the task is tiny, sequential, shares mutable files, lacks a verifier, or coordination/context cost exceeds the work.

## Multi-Tenant Platform Rubric

A senior design should cover tenant isolation, auth/policy, API and queue, worker pools, state/object/vector stores, model/tool gateways, rate limits, quotas, backpressure, noisy-neighbor controls, checkpoint/replay, regional or provider failure, observability, deletion/audit, and migration. Quantify representative QPS, concurrency, task duration, payload, model latency, storage growth, SLO and cost per successful task. Name the largest failure domain and degradation policy.

## Hand-Written Coding Acceptance

- Async tool executor: bounded concurrency, deadline propagation, cancellation, ordered trace events, idempotency and tests for error/timeout/denial.
- Trace evaluator: explicit outcome and trajectory checks, evaluator version, category counts, disagreement cases and deterministic tests.
- Context packer: token budget, priority, deduplication, provenance, stable output and overflow tests.
- Session store: atomic checkpoint, optimistic or explicit locking, resume semantics and duplicate-event prevention.

Require executable tests, complexity, edge cases and a post-solution design review.

## Algorithm Answer Contract

For a training or model question, answer in this order:

1. target behavior and failure mode;
2. variables, tensor shapes and the relevant objective/loss;
3. data source, split, ratio, negative examples and contamination control;
4. baseline, budget and implementation choice;
5. training curves or optimization diagnostics;
6. seeds, mean/std or another uncertainty report;
7. failure distribution, negative result and alternative explanation;
8. supported claim and limitation.

Do not present one run or a lower training loss as evidence of Agent task improvement.

## Memory Design Contract

Specify working, episodic, semantic and procedural stores only when the use case needs them. Define write, recall, update, conflict, expiry, deletion and provenance. Test time changes, explicit user corrections, cross-session conflicts, malicious or irrelevant writes, and “do not remember/refuse to recall” cases. External memory, model-internal memory and RL-trained behavior solve different persistence and governance problems; choose by update latency, auditability, privacy, capacity and evaluation needs. Benchmark names such as LOCOMO or LongMemEval are topic leads, not current ground truth; verify their current definitions and licenses before use.
