# Stable Dual-Resume System

Read this file for resume intake, audit, rewriting, rendering, and QA.

## Non-Negotiable Model

Maintain one fact store and two views:

- Agent Development emphasizes architecture, tool/runtime engineering, reliability, evaluation, safety, performance, delivery, and influence.
- Agent Algorithm emphasizes problem formulation, data, baseline, reward/verifier, training, evaluation science, ablation, failure analysis, and research judgment.

Do not make a third primary resume for a JD. Update the shared facts only when the candidate gains or corrects evidence.

The default output is template-aligned rendering, not a fixed demo resume and not a freshly rewritten resume. Preserve the candidate's supplied content, render it cleanly, and keep critique, better phrasings, missing-evidence questions, and JD-facing emphasis notes in the audit file unless the user explicitly asks to apply them.

The schema-v2 views select stable claim and bullet IDs; text remains stored once. Fact maturity is not publication permission. A selected claim must be `provided|confirmed`, `visibility=resume|public`, `public_safe=true`, source-linked at claim and bullet level, and pass its ship gate. View summaries and skills cite selected claim IDs.

## Audit Sequence

### 0. Scope And Role Calibration

- State that PDF extraction may distort layout, so the content audit treats apparent spacing and line-wrap artifacts cautiously. Still report actual spelling, grammar, punctuation, capitalization, and technical-term errors as hard issues.
- Infer the target role and level from the resume. If a JD is present, use it to calibrate the review standard and record role signals or gaps, but do not create a JD-specific primary resume.
- Apply a higher bar to senior candidates: architecture, technical decisions, rejected alternatives, leadership, business or research impact, and scope of influence.
- Judge the candidate's evidence, not employer categories or personal-background stereotypes.

### 1. Thirty-Second Impression

Report:

- inferred role and level;
- `continue`, `borderline`, or `close` reading decision;
- the single strongest signal;
- the single reason the resume may be rejected.

This is a reviewer simulation, not a claim about a real hiring committee.

### 2. Whole-Resume Audit

Check career narrative, role signal, JD alignment when supplied, internal consistency, information hierarchy, noise, technical correctness, evidence density, ownership, scope, and high-level leadership. Separate technical errors from evidence gaps and writing weaknesses.

Audit the summary independently. Check that it is concise, avoids empty self-evaluation, and can be supported by selected claims. A useful drafting frame is `positioning + years or stage + technical domain + strongest evidenced achievement`; omit any component that the sources do not support.

Audit skills independently. Every claimed proficiency must point to project, work, research, or open-source evidence. Do not force proficiency tiers when the evidence only supports a categorized list.

### 3. Section And Bullet Audit

Audit every selected experience or project independently and every selected bullet exactly once, even when it passes. For each issue use:

```text
Critique: the exact weakness.
Analysis: the negative inference a reviewer could reasonably make.
Suggestion: the smallest factual change, rewrite, or evidence question that resolves it.
Severity: blocker | high | medium | low.
Evidence: claim/source ID.
```

Apply these tests to every selected bullet:

- So What: what technical, user, team, business, research, or risk value changed?
- Decision: what problem led to this method, what alternative existed, and why was it rejected?
- Mechanism: does the wording show how the result was achieved rather than list frameworks?
- Evidence: is there a metric, scope, artifact, qualitative transition, or risk avoided?
- Ownership: what did the candidate personally decide or implement?
- Influence: did impact reach a system, team, platform, research direction, or standard?
- Boundary: what belongs to the team, framework, model, or AI tool?
- Defensibility: can the candidate explain baseline, denominator, window, failure, and limitation?

Also check narrative completeness (`STAR`, `CAR`, or `PAR` as appropriate), verb strength against real ownership, implicit collaboration or leadership demonstrated through actions, and spelling/grammar/punctuation/terminology. A strong verb is a finding only when the evidence supports that ownership.

Use this required artifact structure in `outputs/resumes/resume-audit.md`:

```text
## Audit Scope
## Thirty-Second Impression
## Holistic Audit
## Language And Terminology
## Summary Audit
## Experience And Project Audit
## Bullet-Level Audit
## Strategic Revision Blueprint
### Before / After
## Unresolved Evidence
```

Under `Bullet-Level Audit`, include one table row beginning with the stable bullet ID for every bullet selected by either resume view. Each row records verdict, Critique, Analysis, Suggestion, and the relevant checks. `Pass` is allowed only when the statement answers So What, has a defensible mechanism or role, and has appropriate evidence for its claim.

## Strategic Revision Blueprint

After the audit:

1. Order fixes by `blocker`, `high`, `medium`, then `low`.
2. Recommend the fitting narrative tool: `STAR/CAR`, decision-tradeoff, problem-decision-implementation-evidence, or a qualitative impact pattern.
3. Provide at least one real `Before / After` example from the candidate's text. The `After` version may reorganize only supported facts; otherwise present a question instead of a fabricated rewrite.
4. List evidence-mining questions by information value, but ask the candidate only the single highest-value unresolved question in the current turn.
5. Keep spelling, grammar, punctuation, and terminology corrections separate from factual rewrites so formatting extraction noise is not confused with content defects.

## Writing Patterns

When the user asks for an applied rewrite, use the shortest truthful pattern that fits:

- `Problem -> decision -> implementation -> evidence`.
- `Constraint -> tradeoff -> mitigation -> outcome`.
- `Baseline -> intervention -> evaluation -> limitation`.
- `Failure -> diagnosis -> fix -> regression prevention`.
- `Ambiguity -> success definition -> alignment -> delivered scope`.

Prefer strong verbs only when ownership supports them. Do not force percentages. Valid qualitative outcomes include creating end-to-end traceability, establishing an evaluation gate, removing a permission risk, making a process reproducible, or turning an ambiguous task into an adopted standard.

## Section Order

For experienced candidates, default to:

1. identity and literal role signal;
2. concise summary;
3. role-specific skills supported by claims;
4. strongest work, project, or research evidence;
5. remaining experience and projects;
6. publications/open source/awards when material;
7. education.

Use the same visual template for both views to reinforce a stable identity.

Treat the user-selected GitHub template's class, section hierarchy, typography, spacing model, photo treatment, and visual structure as immutable by default. Auditing content or proposing wording must not alter the template, generated TeX/PDF, or approved resume text. Change any of them only after an explicit user request.

## Render And QA

`render_resumes.py` writes `outputs/resumes/development/main.tex` and `outputs/resumes/algorithm/main.tex` with the canonical profile digest. The renderer dynamically fills the candidate workspace through the upstream `resume-photo` template style from `LLM-Resume-Template`, using `\documentclass{resume-photo}`, `\ResumeName`, `\ResumeContacts`, `\ResumeTitle`, `\section`, and `\ResumeItem`. It contains no hard-coded sample achievements, schools, companies, projects, links, or metrics. It keeps only the compatibility settings needed for bundled Tectonic PDF extraction and Overleaf portability: TeX Live's Fandol Song CJK font and a text-extractable `\heiti` mapping.

Compile with XeLaTeX on Overleaf. In Codex, use the bundled LaTeX plugin's Tectonic compiler when its TeX Live runtime does not include `xelatex`. Package each directory for Overleaf only after the script confirms the current profile digest. Extract PDF text with two parsers at release time, render every page to PNG, and inspect margins, wrapping, density, hierarchy, glyphs, and blank pages. Search final sources and extracted text for unresolved placeholders.
