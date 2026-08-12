# Self-Improving Agent Systems

Read this file for learning, project design, or algorithm interview questions about Agents that improve from experience.

## Separate Four Improvement Boundaries

1. `inference_time`: repeated sampling, search, critique, verifier-guided retry, or test-time compute changes the current answer only.
2. `in_context`: the Agent updates notes, memory, strategies, or Skills used in later runs without changing model weights.
3. `system_evolution`: traces drive prompt, tool, workflow, evaluator, routing, memory, or policy updates that are versioned and released.
4. `weight_training`: SFT, preference optimization, RL, or another update changes model parameters.

Do not call repeated attempts “learning” unless state survives and affects a later independent task. State what persists, who approves it, how it is versioned, and how it can be rolled back.

## Generator-Verifier Gap

A generator can propose more candidates than a verifier can reliably distinguish. Repeated sampling increases coverage, not necessarily deployment accuracy. Measure:

- candidate diversity and pass@k under a fixed budget;
- verifier false-positive/false-negative behavior;
- correlation between verifier score and true task outcome;
- performance after selecting one output, not only oracle coverage;
- cost and latency added by search.

When the verifier is weaker than the generator, more search can amplify reward hacking. Use independent checks, adversarial cases, disagreement review, or a human gate for high-impact updates.

## Successful-Trajectory Feedback

Store successful trajectories only after checking outcome, policy compliance and contribution of the selected steps. Derive a reusable strategy at the right abstraction level, attach the source task and limitations, and test retrieval on a different task family. Also retain informative failures; a success-only memory creates survivorship bias.

## Improvement Experiment Contract

```text
Target behavior:
Frozen baseline and budget:
Improvement boundary:
State that persists:
Generator:
Verifier and known blind spots:
Training/development tasks:
Frozen holdout tasks:
Safety and regression tasks:
Update and rollback rule:
Stop conditions:
Supported claim if successful:
```

Use a three-way split: development for iteration, holdout for selection, and final/future tasks touched only at release. Track benchmark versions and every evaluator change. Never use the same model judgment both to optimize and to claim independent success without a second check.

## Benchmark Hill-Climb Controls

- freeze representative tasks before tuning;
- keep a challenge set from a different source or time window;
- inspect per-category changes, not only an aggregate;
- rerun a simple baseline whenever budget or evaluator changes;
- record negative results and alternative explanations;
- stop when gains vanish on holdout, safety regresses, cost exceeds the budget, or new changes only exploit evaluator quirks.

## High-Signal Interview Prompts

1. What exactly improved: current inference, memory/Skill state, workflow, or model weights?
2. How do you prove a stored strategy transfers beyond the task that created it?
3. Why can pass@k increase while deployed success@1 decreases?
4. How would you detect verifier overfitting without another perfect verifier?
5. Which update requires human approval, and what artifact supports that decision?
6. How do you version, audit and roll back self-modifications?
7. What evidence would show that improvement came only from more compute?
8. When should the loop stop even while the development benchmark still rises?
