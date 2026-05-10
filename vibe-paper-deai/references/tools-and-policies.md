# Detection Tools & Conference Policies

Use this reference when verifying citations, citing detection tools in an audit, or invoking conference policy in a recommendation.

## Background context

- **ICLR 2026 official policy**: Conference uses LLM detection tools to triage submissions; ACs/SACs verify with concrete evidence before any action. Authors and reviewers must disclose LLM use.
- **NeurIPS 2025 case**: 100+ submissions found with fabricated citations — professionally formatted, plausible venues, but corresponding to no real paper.
- **2025 review pollution**: ~20% of ICLR reviews and ~12% of Nature Communications reviews classified as AI-generated, up from near-zero before 2022.
- **Submission volume surge**: AAAI / ICML / NeurIPS face massive growth, partly driven by LLM-assisted vibe papers, increasing AC workload.

This context biases the skill: **strict** on structural and citation issues; **generous** on pure surface-language alone.

## LLM-detection tools (open source — use for triage)

| Tool | Type | Source | Use case |
|------|------|--------|----------|
| **Fast-DetectGPT** | Open source, conditional probability curvature | github.com/baoguangsheng/fast-detect-gpt | Used by ICLR 2025 evaluation framework; fast |
| **Binoculars** | Open source, zero-shot, dual-Falcon perplexity ratio | github.com/ahans30/Binoculars | 90%+ detection at 0.01% FPR; no ChatGPT training data needed |
| **DetectGPT** | Open source, perturbation + curvature | github.com/eric-mitchell/detect-gpt | Classic baseline |
| **ZipPy** | Open source (MIT), LZMA compression-ratio based | github.com/thinkst/zippy | <200 LoC; ~50× faster than RoBERTa |
| **LLMDet** | Open source, model-source attribution | arxiv.org/abs/2305.15004 | Identifies *which* LLM generated text |
| **Review Feedback Agent** | Open source (review-side, not detection) | github.com/zou-group/review_feedback_agent | ICLR 2025 official experiment; useful for understanding LLM-review style |

**Commercial alternatives** (mention only when relevant): GPTZero, Pangram, Copyleaks. Higher accuracy on humanized text but paid; not preferred for open academic use.

**Important caveat**: detector scores are triage only, not verdict. Action requires concrete evidence per ICLR 2026 guidance. Never base a reject recommendation solely on a detector score.

## Citation & content verification tools

When auditing Related Work for hallucinated or mismatched citations:

- **Semantic Scholar API** — cross-check that an in-text claim about a citation matches the cited paper's actual abstract.
- **Google Scholar / arXiv search** — verify a citation exists at all (catches fabricated venues).
- **CrossRef DOI lookup** — confirm DOIs resolve.
- **PDF text search** — find direct-paste residue (`As an AI`, `Certainly,`, etc.) and stray instruction echoes.

**Sampling protocol**: spot-check 5–10 citations per audit. Pick a mix of recent (post-2023, more likely hallucinated) and foundational (pre-2020, harder to fabricate). Read the abstract of each cited paper and compare to the in-text claim. Flag any of:
- Citation does not exist at the claimed venue/year.
- Citation exists but its abstract is irrelevant to the in-text claim.
- Citation exists and is relevant but the description distorts what the paper actually argues.

## Skill-design references (for the curious)

These open-source skills/projects informed parts of this skill's design:

- **blader/humanizer** — Original Claude Code skill for removing AI writing; source of D2 vocabulary list and voice-matching approach.
- **lguz/humanize-writing-skill** — Extended 3-pass system; 36 banned words, 10 structural patterns.
- **bahayonghang/academic-writing-skills** — LaTeX-aware academic polishing with `DEAI_GUIDE.md`; covers Chinglish, weak verbs, AXES coherence model.
- **OUBIGFA/De-AI-Prompt-Enhancer-Writer-Booster-SKILL** — Chinese-language de-AI skill with 24-item trace detector; useful for bilingual papers.
- **mumulin5/ARIS** — Autonomous research pipeline with integrated de-AI polish step.
- **Wikipedia: Signs of AI writing (WikiProject AI Cleanup)** — Empirically maintained list of statistical AI tells; ground truth for D1/D2.

## Official policy references

When recommending a decision in an audit report, you may cite:

- **ICLR 2026 Reviewer Guide & blog post (Nov 2025)** — Tools-triaged, AC-verified workflow; mandatory LLM-use disclosure.
- **NeurIPS / ICML CFP (recent)** — LLMs cannot be authors; authors fully accountable for LLM-generated content including hallucinated citations.
- **Nature, Science, Elsevier, Springer Nature editorials (2023–2025)** — Disclosure requirements; emphasis on accountability and transparency.

## How to phrase findings in a public review

Even when you are highly confident a paper is LLM-generated, do not name AI authorship in the public review text. Use neutral, evidence-based phrasing:

| Don't write | Do write |
|-------------|----------|
| "This paper appears to be AI-generated." | "The presentation has multiple consistency issues that obstruct evaluation of the technical contribution." |
| "The author let an LLM write the related work." | "Several citations in §2 do not match the content described — see specific examples below." |
| "This is a vibe paper." | "The method exposition is unclear in several places (§3.2 lacks symbol definitions; §3.3 mixes baseline comparison with method description)." |
| "The ablations are AI-fluff." | "The ablation analysis is shallow: percentage drops are reported without mechanistic explanation." |

Leave the AI-generation judgment to AC/SAC internal discussion. The neutral phrasing is both more defensible during rebuttal and more actionable for the author.
