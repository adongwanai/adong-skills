# Adaptive Interview Loop

Read this file for behavioral, technical, project, manager, or pressure practice.

## Modes

- `reconnaissance`: build an interviewer-facing plan before a round; do not role-play yet.
- `interview`: do not coach until the candidate completes the answer.
- `practice`: allow a hint after the candidate asks or is stuck.
- `review`: analyze an existing transcript without role-play.

State the selected mode, role, round, and approximate scope. Label generated company questions as simulations, not verified real interview questions.

## Session Formats

Choose the session format separately from the interaction mode:

- `focus`: drill one named project or one knowledge point. Default to 20-30 minutes unless the user sets another duration. Stay on that target through mechanism, implementation, evidence, tradeoff, failure and boundary. Maintain at most 3-6 hidden probes and adapt them after each answer; do not require the 15-20 question reconnaissance pack. Do not force self-introduction, coding or candidate questions into this format.
- `full-loop`: simulate a resume-based interview lasting 45 or 60 minutes. Default to 60 minutes when the user does not choose. Run the fixed sequence `self-introduction -> project deep dive -> Agent fundamentals -> external coding or hand-written algorithm -> candidate questions`.

If the user asks for a resume mock without selecting a format, use `full-loop`. If the user names one project or topic, use `focus`. A JD can change selection and emphasis, but never changes either stable resume.

## Interviewer Reconnaissance Plan

Before a `full-loop` mock or when the user asks for an interviewer plan, cross-read the stable resume facts and the JD. The JD changes focus and priority, never the primary resume. Treat apparent exaggeration, contradiction, weak ownership, missing denominator, vague mechanism, or unsupported proficiency as an evidence-linked `疑点`, not deception or a personality judgment.

Write `outputs/interview/agent-question-pack.md` with:

1. `## Candidate Risk Profile`: one sentence describing the largest verification risk, followed by exactly three core suspicions. Each suspicion cites a resume claim/bullet and, when relevant, an exact JD signal; state what evidence would resolve it.
2. `## Interview Framework`: a Markdown table headed `考察领域 | 相关技术点 | 考察优先级`. Use only `重点考察` or `一般考察` for priority.
3. `## Interview Questions & Scoring Points`: 15-20 numbered main questions. About 80% must directly verify resume/JD evidence. Include 2-4 `广度/诚实度` questions for technologies the resume labels as familiar or understood but the JD does not make central.

For every main question include:

- a source label: `简历/JD` or `广度/诚实度`;
- 2-3 prepared follow-ups, ordered from implementation detail to decision/tradeoff, failure, boundary, or architecture;
- scoring points describing observable strong, partial, and weak signals rather than one memorized answer;
- verification evidence: stable claim/bullet IDs and the JD signal or `非JD核心`;
- the reason this question can change the hiring assessment.

When a question is selected or adapted from a private indexed bank, add its `bank-id`, level, original line and reported attributions to `验证依据`. Keep resume/JD evidence beside it; bank frequency never replaces candidate-specific relevance. Do not display a reported attribution as a verified company question.

Ask primarily about completed resume facts: `why`, `how`, alternatives, baseline, metric, failure, personal contribution, and scope. Use a hypothetical only as a direct extension of the candidate's answer or claimed system. Do not ask unrelated trivia or present generated questions as a real company's historical questions.

The plan is interviewer-facing. During a live mock, never reveal the remaining list, prepared follow-ups, scoring points, or recommended answer before the candidate responds.

The 15-20 questions are a selection pool, not a requirement to ask every question in one live round.

## Full-Loop Run Sheet

Use one of these complete budgets. Preserve the final coding and candidate-question segments instead of allowing project follow-ups to consume the whole round.

| Stage | 45-minute round | 60-minute round | Live behavior |
| --- | ---: | ---: | --- |
| Self-introduction | 3 min | 3 min | Ask for a 60-90 second introduction, then at most one ownership or role-fit probe. |
| Project deep dive | 12 min | 16 min | Select one flagship resume project; probe mechanism, personal contribution, decision, evidence and one failure. |
| Agent fundamentals | 8 min | 12 min | Ask 2-4 project-connected Agent or role-foundation questions; do not jump to unrelated trivia. |
| External coding / hand-written algorithm | 15 min | 20 min | Run exactly one coding lane from [interview-technical.md](interview-technical.md#coding-lanes). |
| Candidate questions | 5 min | 7 min | Invite 2-3 questions, one at a time. |
| Transitions | 2 min | 2 min | State section changes and preserve the stop time. |
| Total | 45 min | 60 min | End on time and move unfinished probes to the review. |

Capture the start time and current stage. Use wall-clock time when the host exposes it; otherwise treat the section budgets as approximate and say so. Never claim exact timing without a clock. At a section boundary, finish the current answer, record the unasked probe, and move on.

## Coding Segment

Choose exactly one lane based on role, JD signals, demonstrated weaknesses and the user's preference:

1. `external-coding`: the candidate implements or debugs an Agent component in an external editor, repository or sandbox. Development examples include an Agent loop, tool router, async executor, trace evaluator, context packer or checkpoint store.
2. `algorithm`: the candidate solves one hand-written data-structure/algorithm or LeetCode-style problem in an external editor. Favor a problem connected to the role, such as LRU/cache, top-k, graph traversal, string DP or producer-consumer coordination, without pretending a generated problem came from a real company.

In `interview` mode, state the problem and acceptance criteria but do not write, patch or complete the candidate's solution. Ask for the approach and complexity, let the candidate code, then inspect the submitted path or pasted solution, run its tests when available, and ask one follow-up about correctness, edge cases, complexity or engineering tradeoffs. In `practice` mode, give at most one hint at a time after the candidate asks or is stuck. Score executable correctness, complexity, edge cases, tests and explanation.

## Candidate Questions

Switch roles explicitly after coding and invite 2-3 candidate questions, one at a time. Answer only from the supplied JD or sourced public company facts; label the rest as a simulation or an inference. Evaluate the specificity and seniority of the questions only in the final review, not while the candidate is still asking them.

## One-Question State Machine

1. Select the highest-signal unresolved question from the reconnaissance plan or workspace evidence.
2. Ask exactly one question.
3. Classify the answer: mechanism, evidence, ownership, tradeoff, failure, scope, or communication gap.
4. Follow the weakest important branch with one question. A prepared follow-up is optional; generate a sharper branch when the answer exposes a different weakness.
5. Stop the branch when the candidate provides a defensible answer, repeats the same gap, or needs offline evidence.
6. Continue to the next competency or end the round.

Do not ask for facts available in the workspace. Do not turn one answer into a long questionnaire.

This applies the `grill-me` discipline: inspect discoverable facts first, resolve one branch at a time, and keep pressure direct without abusive language. Unlike design grilling, do not give the recommended answer before an interview response; recommendations belong in practice feedback or the round review.

## Answer Depth

- 30 seconds: problem, decision, result.
- 2 minutes: context, candidate role, mechanism, key tradeoff, evidence, limitation.
- Deep defense: architecture/code or method/data, alternatives, baseline, metric definition, failure, safety/cost, contribution boundary, and next version.

## Scoring Rubric

Score each observed dimension from 1 to 5 with an anchor and quote/paraphrase from the answer:

| Dimension | 1 | 3 | 5 |
| --- | --- | --- | --- |
| Correctness | materially wrong | mostly correct, shallow edge cases | precise with boundaries |
| Mechanism | framework names only | describes main flow | explains internals and failure behavior |
| Evidence | unsupported claim | one credible artifact or result | baseline, metric, trace/failure and limitation |
| Judgment | no alternative | basic tradeoff | decision under constraints with rejected alternative |
| Ownership | vague `we` | personal module clear | decision and influence boundary clear |
| Communication | scattered | understandable structure | concise first, expands under follow-up |

Do not average this into interview probability.

## Behavioral Story Mining

Use one prompt at a time:

1. Counterfactual: what would have gone worse if the candidate had not acted?
2. Timeline scan: project, conflict, failure, or self-initiated leadership.
3. Lock personal responsibility: replace vague `we` with the candidate's actual scope.
4. Extract situation briefly, task and tension, decisions/actions, result, evidence, and reflection.
5. Tag the story for ownership, ambiguity, conflict, failure, influence, technical judgment, mentoring, or customer/business impact.

Save a reusable 60-90 second version plus deep follow-ups. A story may support several questions; do not manufacture a new story per company.

## Round Review

Write:

- session format, planned duration, approximate or clock-backed timing by section;
- for `full-loop`, separate reviews of self-introduction, project deep dive, Agent fundamentals, coding and candidate questions;
- for `focus`, the target plus mechanism, implementation, evidence, tradeoff, failure and boundary reached;
- strongest demonstrated signals and evidence IDs;
- exact breakdowns and the follow-up that exposed each;
- a stronger answer outline without adding facts;
- at most three repair actions;
- the next validation question.

Append each breakdown to `weaknesses.md` with date, context, root cause, action, destination, validation, and state. Do not delete resolved weaknesses; mark them `validated`.
