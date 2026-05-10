# 4-Pass Rewrite Pipeline

Use this reference during Mode B (rewrite / de-AI polish). Run all four passes in order — never skip ahead, because language fixes on broken structure waste effort.

## Pass 1 — Structure Repair

**Goal**: fix logic flow before touching any words.

**Actions:**
- Convert inappropriately bulleted content into coherent prose paragraphs.
- Express causal / sequential logic with explicit connectives: "because", "therefore" at sentence start, "which in turn", "as a result".
- Reorder subsections if Method explains components out of dependency order (e.g., uses Module B before defining it).
- Remove redundant summary sentences at paragraph ends ("In summary, this section presented X" right before the section ends).
- Flag — but do not auto-fix — any notation issues you encounter; defer to Pass 2.

**Diagnostic**: after Pass 1, the section should read as a continuous argument, not a list of items.

## Pass 2 — Notation & Formula Cleanup

**Goal**: make math readable and rigorous.

**Actions:**
- Add a "Notation" paragraph or table at the start of Method if the section uses many symbols.
- Define every symbol before first use. No naked symbols.
- Replace fragmented formula sequences ("sentence → equation → sentence → equation") with derivation narratives:
  *"Starting from Eq. (1), we substitute X to obtain…"*
  *"This formulation has two consequences: first… Second…"*
- Remove pseudocode that duplicates prose. Keep pseudocode only when it adds genuine algorithmic clarity (non-obvious iteration order, complex control flow, or a parallel structure that's hard to express in prose).
- Standardize notation conventions across the section:
  - Matrices: bold uppercase (𝐀)
  - Vectors: bold lowercase (𝐱)
  - Scalars: italic (x)
  - Sets: calligraphic (𝓧)
- Standardize module abbreviations to one canonical form. If the paper has >4 named modules, add an abbreviation table.

**Diagnostic**: after Pass 2, a reader who reads only the equations (skipping prose) should still be able to reconstruct the method's structure.

## Pass 3 — Language De-AI

**Goal**: remove LLM fingerprints.

**Actions:**
- Apply ban lists from `banned-patterns.md` in this order: D4-residue → D1 → D2 → D3.
- Replace summary→next-topic transitions with direct topic sentences.
- Vary sentence length deliberately. LLM output drifts toward uniform medium length; introduce short punchy sentences and longer complex ones.
- Remove rhetorical Q+A patterns ("Why does this matter? Because…").
- If an earlier author voice is detectable (handwritten notes, prior draft version), restore it.

**Diagnostic**: after Pass 3, read the section aloud. If it sounds like a TED talk transcript, run another deflation pass. If it sounds like an experienced researcher explaining their work, you're done.

## Pass 4 — Consistency & Final Audit

**Goal**: catch anything the previous passes missed.

**Actions:**
- Verify module names are consistent across title, abstract, method, experiments, appendix.
- Confirm all figure / table references in text are present and correctly numbered.
- Confirm each contribution maps to a specific experiment or ablation row.
- Re-read the appendix; flag any section with markedly different quality from the main paper.
- Re-run D1 / D2 spot-check on the revised text (sometimes Pass 1 restructuring reintroduces banned phrases).
- Spot-check 5–10 citations against the in-text claim (catches hallucinated references that survived earlier passes).
- Search for direct-paste residue (`As an AI…`, `Certainly,`, `Sure! Here…`).
- Produce the **Change Summary** table per `output-templates.md` Mode B.

## When to ask the user before proceeding

If during any pass you encounter:
- A **factual claim** you suspect is wrong but cannot verify — flag it, do not silently rewrite.
- A **mathematical statement** that looks dimensionally inconsistent — flag, do not silently fix.
- A **citation** that may be hallucinated — flag, do not silently delete.
- An **author voice** decision (e.g., "should we keep the first-person plural?") — ask before defaulting.

Preserving the author's actual claims and ideas is more important than completing the polish quickly.

## Pass-skipping rules

You may skip passes only when the user explicitly asks for a narrow scope:

- "Fix only my notation" → Pass 2 only.
- "Just make it less AI-sounding" → Pass 3 only.
- "Check consistency" → Pass 4 only.

If the user asks broadly ("polish this", "de-AI this", "rewrite this"), run all four passes.
