# Evidence System

Read this file before promoting a project idea into a resume or portfolio claim.

## Evidence Ledger

For each important claim, capture:

```text
Claim ID:
Claim:
Status: provided | confirmed | planned
Source references:
Candidate contribution:
Problem and stakes:
Decision and rejected alternative:
Outcome:
Metric definition / denominator / window (if applicable):
Qualitative proof (if no metric):
Known limitation:
Public-safe: yes | no
Visibility: private | resume | public
Ship gate: Block | Caution | Pass | Improve
```

Candidate-provided facts do not require hostile verification. Source links make future reuse and conflict resolution reliable. Ask only when two sources disagree or the wording exceeds the supplied fact.

`status` answers whether a statement is a past fact; `visibility` answers who may see it. Never infer one from the other. Public contact and portfolio claims require explicit `public` selection.

## Claim Gate

Before public use, decide:

- `supported`: wording follows directly from a `provided` or `confirmed` claim.
- `narrow`: evidence supports a smaller wording; rewrite to that boundary.
- `planned`: useful future outcome but not completed; send to the project plan.
- `conflict`: sources disagree; ask one resolution question.

Use these as evidence verdicts, not replacements for the profile fact status.

Check six failure modes:

1. A new number, scale, date, publication status, or user outcome appeared without a source.
2. Participation became leadership or ownership.
3. Correlation became causal improvement.
4. Team output became individual contribution.
5. A demo became production deployment.
6. A case study or reproduced design became a completed personal project.

## Evidence Hierarchy

Use the strongest available form without forcing a metric:

1. Reproducible task set, baseline, metric, trace, code, and result.
2. Operational artifact such as logs, dashboard, incident record, deployment, merged change, or adoption.
3. Scope evidence such as system boundary, users, data, tasks, teams, or decision authority.
4. Qualitative transition such as unobservable to traceable, manual to repeatable, unsafe to gated, or ad hoc to standardized.
5. Candidate-stated decision or contribution with a clear boundary.

## Agent Project Proof

An interview-ready Agent project should answer:

- What fixed task set represents the real job?
- What baseline must it beat?
- Which outcome and trajectory metrics matter?
- What verifies success, and how can that verifier be gamed?
- Which traces prove the mechanism works?
- What are the top failure categories and their frequency?
- Which component removal changes the result?
- What are latency, cost, safety, and reproducibility limits?

Do not treat a polished architecture diagram as evidence of implementation.

For public project claims, store two proof layers:

- `proof`: bullet IDs that explain the claim in the resume or portfolio.
- `proof_refs`: source or artifact IDs for the task set, baseline, verification, trace, failure and result evidence.

`proof` without `proof_refs` is narration, not evidence. A case-study source may support `provided/improve`; promotion to `confirmed/pass` requires the stronger artifacts in the project promotion gate.

## Project Promotion

Project state and claim status are different:

- `planned`: question and intended artifact exist; claim remains `planned`, private, and Block.
- `running`: work has started; claim still remains `planned`.
- `evidenced`: applicable task set, baseline, verifier, trace, failure and raw result gates pass; claim may move to `provided` with source IDs.
- `confirmed`: a candidate or reviewer explicitly resolves a conflict and the resolution is logged.

Only after promotion run a separate publication review to set `visibility=resume|public`. Use Block for truth/privacy/correctness failure, Caution for narrow approved use, Pass for satisfied gates, and Improve for a valid current claim with a named non-blocking improvement.
