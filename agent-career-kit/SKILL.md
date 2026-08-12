---
name: agent-career-kit
description: Build and operate a persistent career system for senior Agent development or Agent algorithm roles. Use when an AI coding agent needs to organize candidate evidence, audit or render the two stable resumes, plan evidence-building projects, run single-project/topic drills or 45-60 minute resume-based Agent mock interviews, prepare a company pack from JDs, publish a portfolio, track applications, or turn interview feedback into a long-term improvement loop.
---

# Agent Career Kit

Build one durable candidate workspace. Do not treat each application as a new resume-writing task.

## Runtime Compatibility

- Use this directory containing `SKILL.md` as `<skill-dir>`; never assume a Codex-, Claude-, or OpenCode-specific home path.
- Run deterministic scripts through the host's shell with Python 3 and Node.js. Use any available XeLaTeX or Tectonic installation for PDF compilation.
- Treat `agents/openai.yaml` as optional Codex UI metadata. It does not change the workflow and is not required by Claude Code or OpenCode.
- Keep the same workspace contract, evidence gates, and output paths on every supported client.
- Read [source-map.md](references/source-map.md) when auditing provenance or extending the Skill from an upstream method.

## Operating Invariants

1. Maintain one candidate fact store and exactly two primary resume views: `development` and `algorithm`.
2. Never create a per-JD primary resume. Use a JD only for market-signal aggregation, fit analysis, company preparation, question selection, and referral context.
3. Use the resume template as a dynamic renderer, not a fixed resume. Keep the referenced GitHub resume template's visual format unchanged unless the user explicitly asks to redesign it; names, sections, bullets, projects, metrics and links still come only from the candidate workspace.
4. Preserve candidate-supplied resume wording by default. Audit and suggest improvements, but do not replace finished resume bullets unless the user explicitly approves a factual correction or rewrite.
5. Treat candidate-provided facts as usable unless sources explicitly conflict. Never invent experience, ownership, metrics, dates, users, publications, or business outcomes.
6. Keep fact status, publication visibility, and ship verdict separate. `planned` is private and blocked; portfolio content requires explicit `visibility=public` and public contact consent.
7. Store all candidate data in an explicit workspace outside this installed Skill. Never write resumes, JDs, stories, or application state into the Skill directory.
8. Distinguish facts, candidate statements, external public facts, and hypotheses. Do not report uncalibrated match percentages or interview probabilities.
9. During intake and mock interviews, ask at most one question per turn. Inspect available files before asking for facts already present.

## Start Or Resume

1. Find an existing workspace by locating `candidate-profile.json`. If more than one exists, ask which one to use.
2. If none exists, ask for or infer an explicit output directory outside this Skill, then run:

   ```bash
   python3 <skill-dir>/scripts/init_workspace.py <workspace-dir>
   ```

3. Read [workspace-contract.md](references/workspace-contract.md) before editing structured state.
4. Inventory resume files, repositories, papers, project notes, public profiles, JDs, and interview reviews. Copy only user-selected raw materials into `source-materials/`; otherwise record their paths in `evidence-ledger.md`.
5. Fill `candidate-profile.json` from available evidence. Preserve claim and bullet IDs across revisions. Default visibility and public contact to private until the user approves publication.
6. Run `validate_workspace.py` before producing public artifacts.

## Route The Request

| User intent | Required references | Result |
| --- | --- | --- |
| Start, import, organize, assess level, build a learning route | [workspace-contract.md](references/workspace-contract.md), [capability-models.md](references/capability-models.md), [evidence-system.md](references/evidence-system.md), [learning-routes.md](references/learning-routes.md) | profile, evidence ledger, capability map, staged route |
| Audit, rewrite, compile, or export resume | [resume-system.md](references/resume-system.md), [evidence-system.md](references/evidence-system.md), [quality-gates.md](references/quality-gates.md) | two stable `.tex`/`.pdf` resumes and Overleaf ZIPs |
| Strengthen a project, close a gap, or deliver an Agent system | [project-incubation.md](references/project-incubation.md), [agentic-engineering-delivery.md](references/agentic-engineering-delivery.md), [evidence-system.md](references/evidence-system.md) | bounded evidence plan and reviewed delivery |
| Design or defend a self-improving Agent | [self-improving-agents.md](references/self-improving-agents.md), [project-incubation.md](references/project-incubation.md), [interview-loop.md](references/interview-loop.md) | experiment contract, holdout gate, adaptive defense |
| Practice a single project/topic or a 45-60 minute resume-based Agent mock | [interview-loop.md](references/interview-loop.md), [interview-technical.md](references/interview-technical.md), [system-design-contracts.md](references/system-design-contracts.md) | focus drill or full-loop mock, coding evidence, review, weakness write-back |
| Analyze a JD or prepare a company | [company-prep.md](references/company-prep.md), [capability-models.md](references/capability-models.md) | company pack without resume mutation |
| Build README, Demo, portfolio, referral copy, tracker, or offer comparison | [portfolio-application.md](references/portfolio-application.md), [quality-gates.md](references/quality-gates.md) | public proof and application artifacts |
| Review progress or plan the next cycle | [quality-gates.md](references/quality-gates.md), [project-incubation.md](references/project-incubation.md) | prioritized next actions and updated weaknesses |

For an end-to-end request, execute the routes in table order. Do not ask the user to choose modules they already requested.

## Foundation Workflow

### Build The Evidence Ledger

- Give each reusable claim and bullet a stable ID such as `work-routing-01` and `work-routing-01-b1`.
- Record the source, personal contribution, decision, outcome, metric definition if any, and current status.
- Use `provided` for a candidate-stated or source-backed past fact, `confirmed` for a fact the candidate explicitly reconfirmed, and `planned` for future work. Set visibility separately.
- When sources conflict, show the exact conflict and ask one resolution question.
- Convert missing evidence into `projects/` actions or `weaknesses.md`; do not strengthen the wording beyond the evidence.

### Build Capability Views

- Score using anchored labels `strong`, `usable`, `gap`, or `unknown`; include evidence IDs beside every judgment.
- Assess both role models even when one is primary. Senior candidates need technical depth, architecture judgment, production or research evidence, ownership, influence, and problem definition.
- Select a primary direction only for sequencing. Keep both resume views available.

## Resume Workflow

1. Audit the fact store before any edit. Report scope/role calibration and a 30-second hiring impression, then blocker/high/medium/low issues using `critique -> analysis -> suggestion`.
2. Follow the complete output contract in [resume-system.md](references/resume-system.md): whole-resume, language/terminology, summary, each selected experience/project, and every selected bullet. Run narrative, So What, technical decision, evidence, ownership/verb, scope, consistency, and contribution-boundary checks.
3. Produce a prioritized revision blueprint and at least one evidence-safe Before/After example. Ask only the highest-value unresolved evidence question in the current turn.
4. Default to preserving the candidate's supplied bullet text while rendering it in the template. Put rewrite proposals in `outputs/resumes/resume-audit.md`; update `candidate-profile.json` only when the user approves the change or supplies corrected evidence.
5. Render both variants:

   ```bash
   python3 <skill-dir>/scripts/render_resumes.py <workspace-dir>
   python3 <skill-dir>/scripts/package_overleaf.py <workspace-dir>
   ```

6. Compile each `main.tex` with the available LaTeX compile capability using XeLaTeX or the bundled Tectonic XeTeX engine. Then follow [quality-gates.md](references/quality-gates.md) for cross-tool text extraction and visual inspection.
7. Write `outputs/resumes/resume-audit.md` with accepted changes, unresolved conflicts, evidence gaps, and exact selected-bullet coverage.

## Project And Learning Workflow

- Turn each important gap into the smallest evidence-producing task.
- Require a question, baseline, task set or dataset, metrics, verifier, trace, failure analysis, alternative, and definition of done when relevant.
- Mark each proposed resume claim as `planned` until evidence exists.
- Prefer one flagship project defensible for 20-30 minutes over several shallow demos.
- Do not modify another project repository or start paid/long-running experiments unless the user asks.
- Use [learning-routes.md](references/learning-routes.md) when knowledge is missing, [self-improving-agents.md](references/self-improving-agents.md) for persistent improvement claims, and [agentic-engineering-delivery.md](references/agentic-engineering-delivery.md) when the work includes a release.

## Interview Workflow

1. Choose an interaction mode (`reconnaissance`, `interview`, `practice`, or `review`) and a session format (`focus` or `full-loop`). Use `focus` for one project/knowledge point and `full-loop` for a resume mock.
2. If the user provides a large interview-bank Markdown file, follow [interview-technical.md](references/interview-technical.md) to index it into the private workspace once and query only relevant categories. Do not copy the raw bank into the Skill repository.
3. For `focus`, maintain at most 3-6 hidden probes around the named project/topic and start with the highest-signal one. For `full-loop` or an explicit interviewer plan, follow [interview-loop.md](references/interview-loop.md) to create the interviewer-facing risk profile, framework, and 15-20 question selection pool from resume evidence, JD signals and relevant indexed-bank questions. State that generated or aggregated company-attributed questions are not verified company history unless an original public source proves otherwise.
4. Run a `full-loop` in 45 or 60 minutes: self-introduction, one project deep dive, project-connected Agent fundamentals, exactly one external-coding or hand-written-algorithm lane, then candidate questions. Do not attempt to ask all 15-20 pool questions.
5. During any live mock, do not expose the full plan. Ask exactly one question and follow the weakest or highest-signal branch of the answer, using prepared follow-ups only when they remain the best probe.
6. In `interview` mode, do not coach mid-answer or write the candidate's coding solution. Score after the answer; never provide an ideal answer in advance.
7. End a round with evidence-linked section reviews, exact breakdowns, a better answer structure, and at most three repair actions.
8. Append concrete breakdowns to `weaknesses.md` and save reusable stories in `story-bank/`.

## Portfolio And Application Workflow

- Render the static portfolio only from explicitly public, public-safe, non-`planned` claims and approved contact fields:

  ```bash
  python3 <skill-dir>/scripts/render_portfolio.py <workspace-dir>
  ```

- Lead with name, literal role signal, strongest evidence, and project visuals. Follow with projects, evidence, timeline, skills, publications/open source, and contact.
- Keep company analysis in `outputs/interview/companies/<company>/`; never merge it into primary resume facts.
- Maintain application and offer history in the provided CSV files. Preserve past states rather than overwriting the record.
- When a spreadsheet renderer is available, produce and inspect `outputs/application/career-tracker.xlsx`; CSV remains the canonical source.

  ```bash
  node <skill-dir>/scripts/build_tracker.mjs <workspace-dir>
  ```

## Finish A Work Session

1. Run `validate_workspace.py`; use `--require-artifacts` after generating resumes and portfolio.
2. Apply the relevant gates in [quality-gates.md](references/quality-gates.md).
3. Update `progress.md` with outputs created, unresolved evidence, next three actions, and the next validation condition.
4. Tell the user what is complete, what remains `planned`, and which claims changed. Do not hide failures behind a generic readiness score.
