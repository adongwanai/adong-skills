# Quality Gates

Read this file before declaring an artifact or cycle complete.

## Skill Package

- Official `quick_validate.py` passes.
- `agents/openai.yaml` uses valid metadata and a default prompt containing `$agent-career-kit`.
- No private candidate data, hard-coded personal paths, author branding, temp sync data, or secrets are present. Only the explicitly disclosed Adong template demo and anonymous synthetic acceptance fixture may be repository-local candidate profiles.
- Every reference in `SKILL.md` exists and is one level below it.

## Workspace And Evidence

- Candidate workspace is outside the public Agent Career Kit repository; initialized workspaces deny Git tracking by default.
- Private interview-bank indexes stay outside the repository, retain source hash/line/difficulty, exclude L0 by default, and label company fields as reported attributions.
- Claim and bullet IDs are unique and both resume views reference existing items.
- Resume artifacts reference only `provided` or `confirmed`, `visibility=resume|public`, public-safe claims. Portfolio artifacts use only explicit `visibility=public` claims and approved contact keys.
- All selected claims and bullets have valid structured source references.
- Facts and JD/company hypotheses are visibly separated.
- No per-JD primary resume exists.

## Resume

- `outputs/resumes/resume-audit.md` contains scope/role calibration, 30-second impression, holistic, language/terminology, summary, experience/project, bullet-level, revision-blueprint, Before/After, and unresolved-evidence sections.
- Every bullet selected by either stable resume view appears exactly once in the bullet-level audit with a verdict and `Critique -> Analysis -> Suggestion`; passing bullets remain visible instead of being silently skipped.
- Development and algorithm TeX files contain the current profile digest, come from the same profile, and differ only by stable view and bullet selection/emphasis.
- No `TODO`, `TBD`, `XX`, `[待确认]`, or unsupported example content remains.
- XeLaTeX or the bundled Tectonic XeTeX compilation exits successfully for both variants.
- PDFs are valid, searchable, contain the current profile digest, and have the configured A4 page count.
- Extract with the bundled parser and, for release QA, a second parser. Text must contain identity, role signal and a representative selected claim. A visually correct but garbled extraction is a Block.
- Render every page to PNG and inspect: no overlap, clipping, blank pages, broken glyphs, orphan headings, or unreadable density. Release QA uses PDFKit on macOS and Poppler on other platforms; do not accept a renderer that reports missing CJK maps or drops glyphs.
- Re-rendering an unchanged profile produces identical TeX and normalized extracted text.
- Each Overleaf ZIP contains current `main.tex`, `manifest.json` and a self-contained provenance `NOTICE.txt`; packaging fails after profile changes until TeX is regenerated.

## Interview And Growth

- A targeted reconnaissance pack contains an evidence-linked one-sentence risk assessment, exactly three core suspicions, the required priority table, and 15-20 main questions. Every question has a source type, 2-3 follow-ups, scoring anchors, verification evidence, and assessment purpose; 2-4 questions test non-JD-core breadth/honesty.
- A `focus` review names one project or knowledge point and records the mechanism, implementation, evidence, tradeoff, failure and boundary reached.
- A `full-loop` plan totals 45 or 60 minutes and preserves this order: self-introduction, project deep dive, Agent fundamentals, exactly one external-coding or hand-written-algorithm task, and candidate questions.
- In interview mode, the Agent never writes or patches the candidate's coding solution; it may inspect the submitted code and run its tests.
- A live mock reveals one question at a time and does not expose future questions, prepared follow-ups, scoring points, or an ideal answer before the candidate responds.
- Questions are labeled as simulated unless sourced as real public questions.
- Feedback cites the candidate answer or evidence, not personality guesses.
- Scores use anchored dimensions and are not converted into hiring probability.
- Every repair action has a validation question or artifact.
- `planned` project outcomes remain out of public claims.

## Portfolio

- First viewport exposes candidate identity and role signal.
- Projects include actual public-safe visuals from `public-assets/` and evidence references. Reject symlinks, non-image files and executable/external SVG content.
- Desktop and mobile screenshots show no overlap, horizontal overflow, or unreadable text.
- Links, downloadable resume paths, keyboard focus, alt text, and color contrast work.
- No private path, unapproved email/phone/location/link, hidden metadata, unsafe URL scheme, HTML injection, or placeholder leak.

## Application And Review

- Tracker IDs and statuses are valid; next actions are concrete.
- Company pack judgments quote the JD or cite a public source; hypotheses are labeled.
- Real interview feedback is separated from simulated practice.
- Progress records outputs, remaining gaps, next three actions, and how to validate them.

## Completion Report

Report passed commands, inspected artifacts, unresolved gaps, and anything that remains `planned`. A generated file is not proof until the relevant gate has been run.
