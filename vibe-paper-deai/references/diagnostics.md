# Diagnostics — Vibe Paper Signal Checklist

Use this reference during Mode A (audit) and Mode C (targeted check).
Severity: 🔴 High (alone may justify reject) · 🟡 Medium · 🟢 Low.

For each triggered signal, record: **signal ID · location · verbatim quote · severity**.

## Section A — Structure & Narrative Logic

| ID | Signal | Severity |
|----|--------|----------|
| S1 | Intro ≤ 2 paragraphs; motivation introduced abruptly without context arc; second paragraph jumps straight to "Therefore, we propose…" | 🔴 |
| S2 | Background / Related Work appears before a clear problem statement | 🟡 |
| S3 | High-level motivation suddenly shifts mid-paper to a minor design detail (LLM "focus transfer" — e.g., user prompted "make this work for X", paper now hyper-emphasizes X everywhere) | 🔴 |
| S4 | Method section starts comparing baselines before fully describing the proposed method | 🔴 |
| S5 | Contributions list does not match what the method/experiments actually deliver | 🟡 |
| S6 | No clear story arc: Problem → Gap → Insight → Method → Validation | 🟡 |
| S7 | Conclusion merely restates the abstract via synonym substitution | 🟢 |
| S8 | Abstract / Intro / Method / Conclusion contain mutually inconsistent core claims | 🔴 |
| S9 | Conclusion fabricates "Future Work" items that were never grounded in the main paper | 🟡 |

## Section B — Notation, Formulas & Algorithms

| ID | Signal | Severity |
|----|--------|----------|
| F1 | Symbols used without prior definition / denotation ("naked symbols") | 🔴 |
| F2 | Formula fragmentation: "1–2 sentences → equation → 1–2 sentences → equation" with no derivation logic — equations as decoration, not argument | 🔴 |
| F3 | Algorithm pseudocode that adds no information beyond prose or formulas (filler "rigor") | 🟡 |
| F4 | Inconsistent bold / italic / hat notation for the same symbol across sections | 🟡 |
| F5 | Equations numbered but never referenced in text | 🟢 |
| F6 | Dimension mismatch or obvious type errors in matrix / vector notation | 🔴 |
| F7 | Method described in numbered "Step 1 / Step 2" how-to format instead of academic prose | 🟡 |

## Section C — Naming & Formatting

| ID | Signal | Severity |
|----|--------|----------|
| T1 | Module names verbose (>4 words) and / or abbreviated inconsistently — e.g., "MHCA" / "MH-CA" / "Multi-Head Cross-Attention Module" coexist; or *Dynamic Hierarchical Feature Extraction Module* with no clear short form | 🔴 |
| T2 | Bold used simultaneously for module names, bullet headers, and emphasis — visual hierarchy collapsed | 🟡 |
| T3 | Bullet points used for content with inherent causal / sequential logic (bullets flatten the logic) | 🔴 |
| T4 | Parallel bullet items that are actually causally related (A causes B, listed as `• A` `• B`) | 🔴 |
| T5 | Section headers in Method mirror a how-to guide rather than a research narrative | 🟡 |
| T6 | Figure captions are either one bare sentence or a full paragraph, neither matching venue norms | 🟢 |
| T7 | AI-generated pipeline / concept figures with no human edits — boxes mis-proportioned, arrows nonsensical, generic Midjourney / DALL·E / Nano-Banana style | 🔴 |

## Section D — Language & Style (AI Fingerprints)

For the full ban lists (D1 sentence patterns, D2 vocabulary, D3 overclaiming, D4 structural patterns), see `banned-patterns.md`. The audit only needs to record which sub-section triggered and how often.

Quick reference:
- **D1**: mid-sentence `therefore`/`however`, em-dash overuse, `it is worth noting`, `building upon`, `to this end`, `plays a crucial role`, `shed light on`, paragraph openers stacking *Furthermore/Moreover/Crucially*, rhetorical Q+A.
- **D2**: `delve, leverage, pivotal, seamlessly, elegantly, robustly, comprehensively, novel (self-applied), nuanced, landscape, tapestry, interplay, paradigm shift, underscore, synergy`, etc.
- **D3**: hollow adverbs the user injected in their prompt now appearing everywhere; broader-than-experiments claims.
- **D4**: bullets in Method/Conclusion; same idea paraphrased 2–3× in one paragraph; double-wrapping transitions; AI figures unmodified.
- **D4-residue (instant 🔴)**: `As an AI language model…`, `Certainly, here is the…`, `Sure! Here's a…`, leftover instruction echoes inside the PDF.

## Section E — Experiment Depth (AC-Specific)

| ID | Signal | Severity |
|----|--------|----------|
| E1 | **Shallow ablation**: "Removing module A drops performance by X%" with no analysis of *why* — no hypothesis, no failure case, no edge case | 🔴 |
| E2 | Ablation table without paired qualitative analysis or visualization | 🟡 |
| E3 | **Template-style Limitations**: only "needs more compute" / "future work on larger datasets" / "more diverse evaluation" — no real theoretical or structural defect named | 🔴 |
| E4 | Experiment analysis distorts the original motivation: results don't support the claimed insight, but prose pretends otherwise | 🔴 |
| E5 | Sub-section titles in Experiments do not map to sub-modules in Method | 🟡 |
| E6 | "We observe that …" followed by interpretation only loosely tied to the actual numbers in the table / figure | 🟡 |
| E7 | No failure / edge / out-of-distribution discussion at all | 🟡 |

## Section F — High-Risk Zones (spot-check these first)

| Zone | Why It's Risky | What to Check |
|------|---------------|---------------|
| **Appendix** | Authors often skip human review here | Formatting consistency, non-redundancy, citation accuracy, style continuity with main paper |
| **Related Work** | High hallucinated-citation rate | Verify 5–10 random citations match described content (see `tools-and-policies.md`) |
| **Experiment Analysis** | Bullet overuse, motivation distortion | Analysis must connect back to original research question |
| **Abstract** | Often LLM-polished last, picks up hedging and overclaiming | Check adverbs and contribution-experiment alignment |
| **Figure Captions** | Minimum-effort zone | Self-contained, concise, no AI filler |
| **Pipeline Figures** | AI-generated likely | Box proportions, arrow semantics, generic style |
| **Conclusion** | LLM tends to merely paraphrase the abstract | Check for fabricated Future Work and missing experimental insight |
| **PDF metadata / hidden text** | Direct-paste residue lingers here | Search PDF for `As an AI`, `Certainly`, `Sure! Here`, etc. |

## Calibration: how many flags to call it "vibe paper"

There is no hard threshold, but as guidance:
- **5+ 🔴 signals across at least 2 different sections** → high probability vibe paper.
- **Any direct-paste residue (D4)** → automatic high probability regardless of count.
- **3+ 🔴 in Section E (experiment depth)** → strong AC-level red flag even if language reads fine.
- **Only 🟡/🟢 signals from a single section** → likely just rough writing, not vibe. Lean charitable.
