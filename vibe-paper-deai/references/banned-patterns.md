# Banned Patterns — Language De-AI Reference

Use this reference during Pass 3 of a rewrite (Mode B) or when the user asks for a language-only check.

The lists below appear at statistically anomalous rates in LLM output of academic writing. Single occurrences are noise; clustering is the real signal. Flag and replace.

## D1 — Banned Sentence-Level Patterns

Flag any occurrence:

- `therefore` placed mid-sentence, e.g., *"The model, therefore, learns…"* — move to sentence start or restructure.
- `however` placed mid-sentence as a comma-spliced afterthought.
- Semicolons (`;`) overused to join independent clauses.
- Em dashes (— / ——) overused, especially in pairs as parenthetical inserts.
- `it is worth noting that` / `it is important to highlight that` / `it is important to note that` — delete; if worth noting, just say it.
- `this ensures that` / `this allows us to` — restructure to active voice.
- `building upon` / `drawing upon` / `leveraging` / `harnessing` — replace with `extending`, `following`, `using`.
- `in this regard` / `to this end` (when not preceded by a stated goal) — delete.
- `plays a crucial / pivotal role in` — replace with `is central to`, `determines`, `drives`.
- `shed light on` / `underscore` / `paradigm shift` — replace with concrete verbs.
- Tricolon "X, Y, and Z" structures repeated in adjacent sentences.
- Parallel negation "not X, but Y" used repeatedly.
- Paragraph openers stacking *Furthermore / Moreover / Additionally / Crucially / In addition* — vary or remove.
- Rhetorical Q + A pattern: *"Why does this matter? Because…"* — convert to direct topic sentence.

## D2 — Banned Vocabulary (AI Hallmark Words)

```
delve, delves, delving, delve into
leverage, leverages, leveraged (as verb)
pivotal, crucial, vital (as filler emphasis)
crucially (as paragraph opener)
seamlessly, elegantly, effectively, efficiently (as hollow adverbs)
theoretically (when no theory is presented)
robustly, comprehensively, holistically
groundbreaking, revolutionary, unprecedented, novel (self-applied)
nuanced, intricate, multifaceted
streamlined, optimized (without quantification)
landscape (as in "the landscape of X")
tapestry, ecosystem (metaphorical overuse)
interplay (as filler relational noun)
synergy, synergistic
paradigm shift, shed light on, underscore
state-of-the-art (SOTA used as adjective in prose)
principled, unified, holistic (when undefended)
```

### Replacement guide

| Banned | Human alternative |
|--------|-------------------|
| leverage (v.) | use, apply, exploit |
| delve into | examine, study, analyze |
| pivotal | key, central, critical (sparingly) |
| seamlessly | — (delete; show, don't tell) |
| elegantly | — (delete; let the method speak) |
| landscape of X | field of X, work on X |
| nuanced | specific, detailed (or rewrite) |
| therefore (mid-sentence) | move to sentence start, or restructure |
| it is worth noting | — (delete; if worth noting, just say it) |
| plays a crucial role | is central to, determines, drives |
| comprehensively addresses | addresses (and qualify scope) |
| building upon | extending, following |
| shed light on | clarify, reveal |
| underscore | show, demonstrate |
| paradigm shift | change, new approach |
| interplay | relationship, interaction |

## D3 — Overclaiming Language

Watch for these patterns; they signal the author let the LLM run unchecked:

- Method described with adjectives the user injected in their original prompt (user said "efficient method" → paper now says "our efficient and elegant method" everywhere).
- Abstract or intro claims broader impact than experiments demonstrate.
- "We propose a **novel** framework that **comprehensively** addresses…" — strip both adjectives.
- Contribution bullets opening with strong superlatives unsupported by ablations.
- Reviewers / co-authors asked for one specific change; the paper now treats that change as a central contribution.

**Fix principle**: deflate. Remove every adverb that isn't doing semantic work. The method should be impressive enough that you don't need to call it impressive.

## D4 — Structural AI Patterns

These are the harder-to-fix structural fingerprints — flag them in audit but require Pass 1 (structure) work to fix:

- Bullet points used in Method, Experiment Analysis, or Conclusion (not just lists of results).
- Appendix quality dramatically lower than main paper — common when authors wrote main paper but let LLM write appendix.
- Related Work text and citations semantically mismatched (hallucinated or wrong citations).
- Same idea paraphrased two or three times within one paragraph.
- "Double-wrapping" transitions: a sentence summarizes the just-concluded paragraph before introducing the next.
- AI-generated figures used unmodified (T7 in diagnostics).

### D4-residue — instant 🔴

These are direct-paste artifacts. Their presence alone justifies a major flag:

- `As an AI language model…`
- `Certainly, here is the…` / `Sure! Here's a…` / `Here is the…`
- `I cannot fulfill that request, but…` (rare but seen in submitted PDFs)
- Leftover LaTeX comment markers from prompt instructions (`% Now write a paragraph that…`)
- Stray instruction echoes (`In response to your query about…`)

Search the PDF text for these strings during every audit.

## Pass 3 application order

When running Pass 3 of a rewrite:

1. First, scan for **D4-residue** — if found, flag and remove immediately.
2. Then run **D1** sentence-level fixes (these often reveal D2 words).
3. Run **D2** vocabulary replacement using the table above.
4. Run **D3** deflation pass — remove hollow adverbs, qualify broad claims.
5. Final read: vary sentence length deliberately. LLM output drifts toward uniform medium length; introduce short punchy sentences and longer complex ones to break the rhythm.
