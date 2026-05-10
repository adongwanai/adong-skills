# Output Templates

Use the template that matches the active mode.

## Mode A — Audit Report

```
## 🔥 Vibe Paper Audit Report

### AC Diagnosis
- Vibe Paper Probability: <0–100%>
- Risk Level: [LOW / MEDIUM / HIGH / CRITICAL]
- One-line verdict: <e.g., "A pipeline product using flashy adverbs to mask absent
  motivation logic.">

### 🎯 Triggered Signals (with evidence)
| ID | Signal | Location | Evidence (verbatim quote) | Severity |
|----|--------|----------|---------------------------|----------|
| S3 | Motivation shifts to minor detail | §3.2 ¶2 | "...which motivates our use of layer norm instead of batch norm" | 🔴 |
| E1 | Shallow ablation | §4.3 Tab.3 | "Removing M_A drops accuracy by 2.1%." (no analysis follows) | 🔴 |
| ...

### 📚 Citation Audit
- Sampled: <N> citations
- Suspicious / mismatched: <K>
- Examples: <citation strings + observed issue>

### 🖼️ Figure Audit
- AI-generated suspected: <yes / no>
- Reasoning: <e.g., generic pipeline style, arrow inconsistency>

### 🤖 Detector Score (optional, triage only)
- Fast-DetectGPT: <score / threshold>
- Binoculars: <score / threshold>

### 🔨 AC Meta-Review
- **Fatal flaw (beneath the AI polish)**: <the deepest real problem in motivation,
  method, or experiments — not a surface complaint>
- **Rebuttal-fixable in one round?** <yes / no, with reason>
- **Decision suggestion**: [Desk Reject / Reject / Borderline Reject / Major Revision / Normal Review]

### 🩹 Human-in-the-Loop Salvage Plan
If the underlying idea is real, ordered actions to rescue the paper:
1. <e.g., Re-derive §3 with a Notation table; re-write Eq. (3)–(7) with explicit derivation>
2. <e.g., Add ablation insight: explain *why* removing M_A hurts, with one failure-case figure>
3. <e.g., Replace template Limitations with one structural and one theoretical defect>
4. <e.g., Verify and replace 5 mismatched Related Work citations>
5. <e.g., Redraw pipeline figure manually; remove all bold module-name decoration>
```

**Key requirements:**
- Probability score is mandatory.
- Every triggered signal needs a verbatim quote and section/line reference.
- The Fatal Flaw must be the deepest real problem, not a surface complaint. If the only problems are surface-language, say so honestly and lower the probability.
- The Salvage Plan must be ordered concrete actions, not vague advice ("write better motivation" is not actionable; "rewrite the second paragraph of §1 to bridge between the open problem in [cite] and your specific contribution" is).

## Mode B — Rewrite Output

Return two artifacts in order:

### 1. Rewritten text

The rewritten section or paragraph as a continuous block. Do not interleave commentary inside the rewritten text. If the user asked for a section, return the whole section. If they asked for a paragraph, return only that paragraph.

### 2. Change Summary table

```
## Changes Made
| Pass | Location | Change Type | Before | After |
|------|----------|-------------|--------|-------|
| P1   | §3.1 ¶3 | Bullet → prose | "• First, we... • Then, we..." | "We first... This subsequently allows..." |
| P3   | §3.2     | Banned vocab   | "elegantly captures"           | "captures" |
| P2   | §3       | Notation       | undefined Φ                     | added definition before Eq. (3) |
| P4   | §3.4     | Naming         | "MHCA" / "MH-CA" inconsistent  | standardized to "MHCA" |
```

**Key requirements:**
- One row per substantive change. Do not list every comma-level edit.
- The "Pass" column lets the user audit which pass introduced which change.
- "Before" and "After" should be short verbatim excerpts, not paraphrases.

## Mode C — Targeted Single Check

Format:

```
## <What was checked> — Quick Check

**Verdict**: <one sentence>

**Top issues**:
1. <Location>: <issue>
   - Before: "<verbatim>"
   - After:  "<suggested fix>"
2. ...
3. ...

**Optional**: <one short recommendation about scope, e.g., "If you want a full audit, ask for one — this only covered §1.">
```

3–5 fixes is the sweet spot. Don't bury the user in 20 nitpicks during a targeted check.

## Mode D — Author Pre-Submission Self-Check

Output a personalized version of this checklist after a quick scan. Mark each item as ✅ pass / ⚠️ check / ❌ fail with a one-line note when relevant.

```
## Pre-Submission Self-Check

### Structure
- [ ] Intro has ≥3 paragraphs covering problem / challenge / contribution
- [ ] Each contribution maps to a specific experiment or ablation
- [ ] No motivation hijack (minor detail elevated to core claim)

### Notation & Method
- [ ] Every symbol denoted at first use
- [ ] Module abbreviations consistent throughout; ≤5 words per name
- [ ] No fragmented "sentence → equation → sentence" without derivation

### Language
- [ ] Bullets used only for true parallel content; sequential/causal logic in prose
- [ ] No banned vocabulary (`elegantly, seamlessly, theoretically, leverage, delve, pivotal, tapestry, …`)
- [ ] No mid-sentence `therefore` / `however`

### Citations & Figures
- [ ] Every cited paper read; citation context matches actual content
- [ ] All figures manually adjusted (arrows, spacing, fonts, colors) — no Midjourney pipelines pasted raw

### Experiments
- [ ] Every ablation row has at least one sentence of *why*, not just the percentage
- [ ] Limitations names at least one specific structural or theoretical defect
- [ ] Failure / edge case discussion present

### Final
- [ ] Appendix proofread end-to-end at the same standard as the main paper
- [ ] One co-author has done a final read without LLM assistance
- [ ] PDF searched for `As an AI`, `Certainly`, `Sure!`, `Here is the` direct-paste residue
```

## Output language

Match the user's input language. Diagnostic terminology may stay English where it's standard (ablation, denote, rebuttal, motivation), but explanations and salvage plans should be in the user's language.
