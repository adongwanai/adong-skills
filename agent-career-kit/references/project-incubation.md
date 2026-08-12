# Project Incubation And Evidence Planning

Read this file when a capability gap needs real proof.

Also read [learning-routes.md](learning-routes.md) for staged learning, [agentic-engineering-delivery.md](agentic-engineering-delivery.md) for delivery, or [self-improving-agents.md](self-improving-agents.md) for improvement loops when relevant.

## Select The Work

Choose the smallest task most likely to change a high-priority capability judgment or resume claim. Prioritize:

1. Missing proof for an already completed, important project.
2. A bounded extension that closes one target-role gap.
3. A new flagship project only when existing work cannot prove the capability.

Prefer one project that survives 20-30 minutes of technical defense over several shallow demos.

## Project Card

```text
Question: what will this work prove?
Target capability:
Current baseline:
Task set / dataset:
System or method:
Success metrics:
Verifier and its failure modes:
Trace plan:
Failure taxonomy:
Ablation or alternative comparison:
Safety / cost / reproducibility constraints:
Public artifacts:
Definition of done:
Proposed resume claim (status=planned):
```

## Development Project Standard

Cover relevant layers: provider, loop, tools, context, memory, session, policy, permission, sandbox, trace, replay, evaluation, reliability, performance, deployment, and observability. Do not add layers irrelevant to the question.

Recommended flagship shapes from AgentGuide:

- minimal Agent harness;
- nano coding Agent with patch, shell policy, tests, rollback, and traces;
- enterprise or Agentic RAG with retrieval evaluation and citations;
- long-running Agent with state and memory governance;
- sandbox or workflow-evolution system with measurable gates.

## Algorithm Project Standard

Define environment, state, action, trajectory, reward/verifier, data, policy update, reset, and evaluation. Include leakage controls, baseline, holdout, ablation, failure distribution, compute budget, and reproducibility.

Relevant shapes include retrieval/search, tool-use learning, verifier/trajectory evaluation, memory evaluation, workflow optimization, or Agentic RL. Treat any AgentGuide case study as reference material only; never present it as personal completed evidence without code, traces, configs, and results.

## Claim-To-Evidence Order

1. Write the narrow claim the candidate wants to support.
2. List evidence that would prove it and evidence that would weaken it.
3. Separate `must`, `useful`, and `cut` experiments.
4. Run cheapest high-information checks first.
5. Define stop/go conditions before results exist.
6. After results, narrow the public claim to the observed boundary.

## Ablations

Every ablation must answer a question, such as whether gains come from retrieval, reranking, memory, planning, verifier, reward shaping, or more compute. Record expected evidence, cost, priority, and interpretation for positive, null, and negative results. Avoid combinatorial ablations with no decision consequence.

## Learning Plan

When the candidate needs learning rather than a project, use the staged development or algorithm route in [learning-routes.md](learning-routes.md). Each block ends with a runnable artifact, evaluation, failure note, and interview explanation.
