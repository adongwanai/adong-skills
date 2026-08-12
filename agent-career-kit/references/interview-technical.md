# Agent Technical Interview Bank

Read only the sections needed for the selected round. These are generated practice prompts, not claims about any company's real interview. Use [system-design-contracts.md](system-design-contracts.md) for concrete schemas/rubrics and [self-improving-agents.md](self-improving-agents.md) for improvement loops.

## Question Selection

Select questions in this order: resume evidence and unresolved weaknesses, exact JD signals, the indexed bundled aggregation, locally available AgentGuide practice material, then the concise practice prompts below.

The distributed Skill includes `assets/interview-bank/xiaohongshu-ai-interview-bank.md`. Treat “小红书” as the publishing platform, not the employer. New workspaces index it during initialization; index an older workspace once with:

```bash
python3 <skill-dir>/scripts/index_interview_bank.py <workspace-dir>
```

Query only the relevant domain/category/difficulty instead of loading the full bank:

```bash
python3 <skill-dir>/scripts/query_interview_bank.py <workspace-dir> --domain 大语言模型与NLP --category Agent与工具调用 --level L3 --level L4 --limit 12
```

The index retains the distributed source hash, line number, L0-L5 difficulty and reported company attributions. Exclude L0 by default because the source marks it as insufficient context. Treat every company label as an attribution reported by the aggregation, not independently verified company history. Label selected questions accordingly unless an original public post is separately verified.

Do not copy a company set wholesale. Connect fundamentals to terms the candidate used in the project answer. For a 45-60 minute full loop, select only the questions that fit the run sheet; retain the rest as an interviewer-only pool.

Use difficulty adaptively. Start a full-loop topic at L2 or L3. Move to L4/L5 only after a precise mechanism or implementation answer; move to L1 only when a prerequisite is missing. Never select L0 by default. For `focus`, walk one topic upward until the candidate gives a defensible boundary, repeats the same gap or reaches the time limit.

| Full-loop stage | Indexed-bank route |
| --- | --- |
| Self-introduction | `行为面试与HR / 自我介绍`, L1-L3, then one resume ownership probe |
| Project deep dive | `项目论文与经历`, L2-L4, filtered by the flagship project terms |
| Agent development fundamentals | `大语言模型与NLP / Agent与工具调用|RAG与知识库`, `系统设计与后端基础`, and `AI系统与训练推理工程`, L2-L4 |
| Agent algorithm fundamentals | `大语言模型与NLP`, `强化学习与对齐`, `机器学习基础`, `深度学习基础`, `数据与评测`, and `AI系统与训练推理工程`, L2-L5 |
| Coding | `编程与数据结构算法`, or an implementation question from the role domain, L2-L4 |

Do not select by reported company attribution alone. The candidate's evidence, role and unresolved weakness decide relevance; attribution is provenance metadata only.

## Role Foundations

Choose 2-4 foundations that connect to the resume project or JD:

- Agent development: Python async/concurrency, HTTP/API semantics, queue/backpressure, timeout/retry/idempotency, cache/database consistency, distributed failure, auth/sandbox and observability.
- Agent algorithm: Transformer/attention/KV Cache, decoding, SFT/DPO/RLHF, reward/verifier, data quality/contamination, metrics/uncertainty, retrieval/rerank and inference optimization.

Ask for the mechanism, applicable boundary and one project consequence. Do not run a disconnected trivia checklist.

## Agent Runtime And Harness

1. Hand-write a minimal observe-think-act loop. Where are state, stop, budget, and failure handled?
2. Design a tool registry. How are schemas, dispatch, permissions, timeouts, retries, and tool errors represented?
3. When should an Agent use a workflow instead of open-ended planning?
4. What makes a harness more production-ready than a prompt plus function calls?
5. How do checkpoint, replay, idempotency, and rollback interact on a long task?
6. Where should human approval sit, and how do you prevent approval fatigue?
7. When is multi-Agent coordination justified? Compare supervisor, peer, and fixed workflow designs.
8. How would you diagnose a trace that looks reasonable but did not actually complete the task?

## Context, Memory, RAG, And Search

1. What enters the context window, what stays out, and how do you measure that decision?
2. Design working, episodic, semantic, and procedural memory write/recall/forget policies.
3. How do you prevent memory pollution and resolve conflicting memories?
4. Hand-write a retrieval pipeline with parsing, chunking, sparse/dense recall, fusion, rerank, packing, and citations.
5. Decompose an Agentic RAG failure into retrieval, ranking, planning, synthesis, citation, and stopping errors.
6. When should an Agent search, what query should it issue, how many rounds should it run, and when should it stop?
7. How would you evaluate multi-hop retrieval without leaking the answer into generated data?
8. Compare GraphRAG, iterative search, and a conventional hybrid RAG pipeline for a concrete task.

## Evaluation, Reliability, And Safety

1. Distinguish capability, task, trajectory, safety, and preference evaluation.
2. Compare outcome and transcript evaluation. When can each be gamed?
3. Design a fixed task set, baseline, metrics, verifier, and ship gate for a consumer Agent.
4. Compare rule, programmatic, LLM judge, and human verification. How do you test judge consistency?
5. Explain success@1, pass@k, repeated-attempt success, cost, latency, tool recovery, and unsafe-block tradeoffs.
6. Build a failure taxonomy from traces and decide which failure to fix first.
7. How do prompt injection, tool authorization, filesystem/network isolation, and data deletion change the architecture?
8. An Agent passes the test suite but violates the user's intent. How do you detect and prevent that failure?

## System Design

1. Design an enterprise Agent platform: API, worker, queue, state, object store, vector store, model gateway, policy, and observability.
2. Design a coding Agent that edits via patches, runs shell commands, tests changes, and recovers from failure.
3. Design a long-running research Agent with checkpoints, budgets, citations, replay, and human review.
4. Design a high-QPS customer-service Agent. Cover SLO, routing, cache, degradation, safety, and cost per task.
5. How would you migrate a prototype Agent into a multi-tenant platform without rewriting everything?
6. A provider model is degraded. Which functions fail, which degrade, and how do you detect recovery?

## Agent Algorithms

1. What failure mode does ReAct solve, and when does it add useless tokens?
2. Compare explicit planning, tree search, MCTS-like search, reflection, and verifier-guided retry.
3. Define state, action, reward, trajectory, reset, and credit assignment for a coding or search Agent.
4. Compare SFT, DPO, PPO-style RLHF, and verifier-guided RL for tool-use behavior.
5. Why is pass/fail reward insufficient for a coding Agent? Design a reward or verifier stack.
6. How would you synthesize hard tool-use or multi-hop tasks and prevent contamination or unreachable samples?
7. Design holdout and ablation experiments for a verifier-guided Agent.
8. How do reward hacking, judge bias, length bias, and data leakage appear in Agent evaluation?
9. How would you train a model to decide whether to search, what to search, and when to stop?
10. What evidence proves a self-improving workflow learned a reusable skill rather than overfit its evaluator?

## Coding Foundations

Use language-appropriate problems, then connect them to Agent work:

- LRU/cache and context or response caching;
- heap/top-k and retrieval/reranking;
- BFS/DFS and workflow or dependency traversal;
- trie/string matching and tool/command routing;
- producer-consumer queue and Agent workers;
- rate limiter and model gateway;
- timeout/retry/circuit breaker implementation;
- JSON schema validation and tool arguments;
- trace aggregation and failure statistics;
- concurrency-safe session or checkpoint store.

Require complexity, edge cases, executable tests, and post-solution review. AI assistance does not replace the candidate's ability to explain and verify the code.

## Coding Lanes

- `external-coding`: implement or debug one Agent-facing component in the candidate's editor or repository. Use the acceptance contracts in [system-design-contracts.md](system-design-contracts.md#hand-written-coding-acceptance).
- `algorithm`: solve one hand-written or LeetCode-style problem. Useful patterns from the AgentGuide practice bank include edit distance with path reconstruction, time-decayed top-k, evidence deduplication, LRU/cache, graph traversal and producer-consumer coordination.

Choose one lane per full-loop round. State inputs, outputs, constraints, examples and acceptance criteria. In interview mode, the interviewer must not edit the solution. Require the candidate to explain the approach and complexity before coding, then run or inspect the result and probe one hidden edge or design tradeoff.

## Project And Pressure Follow-Ups

- Are you only calling APIs? Point to the runtime, state, policy, evaluation, and failure logic you own.
- Is this a demo or a system? Show task set, trace, verifier, failure cases, deployment or adoption evidence.
- Are the metrics credible? Define denominator, baseline, window, dataset split, and limitation.
- Which part did you personally own? Separate team, framework, model, and AI coding contributions.
- Why not the obvious alternative? State the constraint and evidence behind the choice.
- What broke in production or experiment runs? Explain diagnosis, repair, and regression prevention.
- If budget or latency halves, what design changes first?
- What would invalidate your conclusion?

For deep topic study, generate L1 must-know, L2 advanced, and L3 top-lab questions with formulas or runnable code only when the topic requires them.
