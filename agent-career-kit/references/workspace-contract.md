# Workspace Contract

Read this file when creating, importing, or validating candidate state.

## Isolation

The workspace must be outside the installed Skill directory. Only schemas, scripts, templates, and public non-private fixtures belong in the open-source repository. Candidate resumes, names, contact details, private repositories, JDs, interview schedules, compensation, and reviews stay in the workspace.

## Required Layout

```text
career-workspace/
├── candidate-profile.json
├── evidence-ledger.md
├── capability-map.md
├── weaknesses.md
├── progress.md
├── source-materials/
├── public-assets/
├── jd-bank/
├── interview-bank/question-index.json  # optional private index; raw bank stays outside the repository
├── story-bank/
├── projects/
└── outputs/
    ├── resumes/{development,algorithm}/
    ├── portfolio/
    ├── interview/companies/
    └── application/
```

## Profile Model

`candidate-profile.json` is the single machine-readable fact store.

- `schema_version`: currently `2`; v1 is rejected so implicit publication fields cannot survive unnoticed.
- `fixture_notice`: optional visible disclosure for public template or synthetic acceptance cases; omit it from real candidate workspaces.
- `sources`: structured `candidate_statement`, workspace-relative `file`, or `url` records with stable IDs and access dates.
- `candidate`: name, headline, contacts, links, and explicit `contact_visibility.resume/public` lists. Public contact defaults to empty.
- `education`: source-linked education records.
- `claims`: source-linked experience, project, research, open-source, publication, award, or leadership records.
- `resume_views.development` and `resume_views.algorithm`: headline, expected page count, source-linked summary, ordered claim IDs, stable bullet selections, and evidence-linked skill groups. Views select and frame facts; they do not create separate facts.
- `portfolio`: source-linked public summary and metrics, ordered public claim IDs, optional per-claim detail panels, and visuals under `public-assets/` only. Every detail metric references a bullet from the same claim.

Every claim has:

- `id`: stable unique identifier.
- `category`: `experience`, `project`, `research`, `open_source`, `publication`, `award`, or `leadership`.
- `name`, `organization`, `role`, `start`, `end`, and stable bullet objects (`id`, `text`, `source_refs`).
- `tags`: role signals used for view selection.
- `source_refs`: IDs from the structured source registry.
- `status`: `provided`, `confirmed`, or `planned`.
- `visibility`: `private`, `resume`, or `public`; this is independent from fact status.
- `public_safe`, `contribution`, `limitation`, and `ship_gate`.
- completed project/research proof links for task set, baseline, verification, trace, failure, and result.

`provided` means the candidate supplied the past fact or a source states it. It is usable without repeated interrogation. `confirmed` means the candidate resolved a conflict or explicitly reconfirmed it. `planned` means future evidence and is always `private`, `public_safe=false`, and `ship_gate=block`.

Fact maturity never grants publication consent. Resume rendering accepts only `visibility=resume|public`; portfolio rendering accepts only `visibility=public`. Both require `public_safe=true` and a passing ship gate.

## Editing Rules

1. Preserve claim IDs so stories, resumes, and portfolio links remain stable.
2. Edit the profile before regenerating artifacts; never patch generated files as the source of truth.
3. Do not duplicate a claim to change its emphasis. Select and order stable bullet IDs in each view; bullet text remains stored once.
4. Keep narrative notes, interview answers, and project plans in Markdown. Keep machine-rendered fields in JSON.
5. Use UTF-8 and ISO-like dates (`YYYY-MM` or `YYYY`). Use `Present` for current work.
6. Copy only explicitly reviewed visual assets into `public-assets/`; the renderer rejects other paths, symlinks and executable SVG content.

## Intake Order

1. Existing resume and public profiles.
2. Work and project repositories, reports, papers, traces, and evaluation results.
3. Candidate explanations for ownership, decisions, outcomes, and conflicts.
4. Target role direction and representative JDs.

Do not ask for information that is already readable. When a decision is required, ask exactly one high-information question.
