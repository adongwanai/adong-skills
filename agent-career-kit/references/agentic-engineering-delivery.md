# Agentic Engineering Delivery Contract

Read this file when an Agent project must move from request to reviewed release.

## Delivery State Machine

| State | Required input | Artifact | Human decision | Failure recovery |
| --- | --- | --- | --- | --- |
| Clarify | request and repository context | confirmed goal, constraints, non-goals, risks | approve material scope or external side effects | return one unresolved decision; do not code through ambiguity |
| Plan | confirmed constraints | file-level plan, dependencies, tests and definition of done | approve architecture only when it changes boundaries or cost materially | revise plan from evidence, not preference |
| Implement | plan and ownership boundaries | bounded changes and atomic commits/checkpoints | approve privileged actions, deployments and irreversible data changes | isolate failed task; preserve unrelated work |
| Spec review | requirement and diff | coverage matrix of requirement to code/test | decide product ambiguity | reopen only uncovered requirement |
| Quality review | runnable change | correctness, security, maintainability and regression findings | accept explicit residual risk | fix by severity, rerun focused tests |
| Deploy | passing release candidate | deployment record, version and health checks | authorize production release | rollback to known version |
| Observe | deployed version | logs, traces, metrics and incident evidence | approve continued rollout if risk rises | pause, diagnose from trace, reproduce locally |
| MR fix loop | review/incident findings | minimal fix plus regression test | resolve disputed tradeoff | return to relevant prior state |
| Release gate | verified candidate | Block/Caution/Pass/Improve verdict | final release or hold | record gap and next validation |

## File-Level Plan Contract

For each task record owner, files, purpose, dependencies, acceptance command and prohibited overlap. Parallelize only independent tasks; express dependent work as a DAG. Agents are not a substitute for ownership boundaries. A task is complete only when its artifact and verification are visible to the integrator.

## Human Approval Boundaries

Require explicit approval for production deployment, paid or long-running compute, destructive data operations, secret/credential changes, external messages, publication of candidate data, and a material expansion of scope. Routine edits, local tests and read-only inspection do not need a checkpoint.

## Agent-Specific Artifacts

- request/constraint record;
- state and tool contracts;
- permission and sandbox policy;
- representative traces and failure taxonomy;
- task set, baseline and evaluator versions;
- deployment/rollback instructions;
- review findings and regression tests;
- release verdict and residual limitations.

## Release Verdict

- `Block`: truth, safety, privacy, correctness or required evidence fails.
- `Caution`: usable only with a stated narrow boundary and explicit reviewer approval.
- `Pass`: definition of done and release gates pass.
- `Improve`: safe to publish/use, with a named evidence or quality improvement that does not invalidate current claims.

Never convert a reviewer opinion into “independent verification” when the reviewer shares the same model family or evidence. Deterministic checks prove deterministic properties; semantic review remains provisional.
