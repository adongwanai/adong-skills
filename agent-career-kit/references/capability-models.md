# Capability Models

Read this file when diagnosing level, selecting resume evidence, or preparing a company pack.

## Anchors

- `strong`: multiple source-linked examples; can defend mechanism, tradeoff, failure, and outcome.
- `usable`: at least one credible example; some depth or scope is missing.
- `gap`: target role expects it, but current evidence is insufficient.
- `unknown`: materials do not answer the question.

Do not collapse these labels into a fake total score. Record evidence IDs and the next proof needed.

## Agent Development

| Dimension | Senior/high-level evidence |
| --- | --- |
| Agent loop and state | Explicit state/action/observation/done model, stop conditions, checkpoint and recovery |
| Tool system | Schema design, routing, error return, idempotency, permissions, MCP or equivalent protocol boundaries |
| Context and memory | Context selection, compression, write/recall/forget policy, conflict and pollution control |
| RAG and search | Parsing, retrieval, rerank, query planning, citations, failure decomposition and evaluation |
| Harness architecture | Provider, runner, tools, memory, channel, autonomy, session and policy boundaries |
| Sandbox and safety | File/shell/network isolation, prompt injection, approval gates, audit and data boundaries |
| Reliability | Timeout, retry, backoff, circuit breaking, replay, rollback, graceful degradation and SLO reasoning |
| Observability and eval | Logs, traces, task sets, outcome/transcript evaluation, verifier, regression and ship gates |
| Performance and cost | Latency, token, cache, batch, model routing, QPS, resource and cost tradeoffs |
| System design | API, worker, queue, storage, model gateway, capacity, failure domains and evolution path |
| Delivery and influence | 0-to-1 definition, cross-team alignment, standards, mentoring, rollout, incident learning |

## Agent Algorithm

| Dimension | Senior/high-level evidence |
| --- | --- |
| Model foundations | Transformer, attention, KV cache, decoding, training loop and optimization reasoning |
| Agent paradigms | ReAct, planning, search, reflection and multi-agent boundaries tied to failure modes |
| Retrieval algorithms | Sparse/dense/hybrid retrieval, rerank, multi-hop search, GraphRAG and attribution evaluation |
| Tool-use learning | Tool trajectory data, SFT/preference data, constrained outputs and failure correction |
| Agentic RL | State, action, environment, reward, policy, rollout, credit assignment and reset design |
| Reward and verifier | Rule, programmatic, model judge and human verification; gaming, bias and consistency controls |
| Evaluation science | Research question, dataset split, leakage, baseline, metric, holdout, ablation and reproducibility |
| Data synthesis | Seed tasks, evolution, rejection sampling, quality filtering, diversity and contamination controls |
| Memory/skill learning | Episodic/semantic/procedural memory, skill extraction, retrieval, forgetting and longitudinal eval |
| Research judgment | Hypothesis, alternative explanations, negative results, limitations and supported claims |
| Training systems | Data pipeline, distributed training, checkpointing, inference evaluation, cost and compute budget |
| Leadership and influence | Research direction, benchmark ownership, standards, mentoring and cross-functional adoption |

## High-Level Calibration

A high-level candidate must show more than framework usage. Require evidence of:

1. Defining an ambiguous problem and a measurable success condition.
2. Making a non-obvious technical choice and explaining the rejected alternative.
3. Owning a system or research loop beyond one module.
4. Handling failure, safety, cost, or reproducibility.
5. Influencing a team, platform, research direction, or business decision.
6. Knowing the contribution boundary between the candidate, team, framework, model, and AI coding tools.

Use representative JDs to adjust priority, never to fabricate a new identity.
