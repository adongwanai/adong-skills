你是一名机器学习文献编辑。请根据给定的论文标题与英文摘要（Abstract），输出结构化中文记录。

# 写作约束（严格执行）
1. 语言：中文叙述，模型名、基准名、关键缩写与术语（如 RLHF、GRPO、KV cache、flow matching、VLA）保留英文原文。
2. 文风：平实、克制、具体。禁止使用公关辞令或夸张套话（如“里程碑式”“颠覆性”“不仅…而且…”“深刻揭示了”“至关重要”“铺平了道路”）。直接陈述论文做了什么、怎么测的、数字是多少、缺什么。
3. 忠于原文：只记录 Abstract 明确给出的事实与指标；Abstract 未给出具体数值时，`result` 填写 `"摘要未披露具体定量指标"`，不得编造实验数字。
4. 分级延伸：
   - `insight_score` 取 1–5 整数（1-2=常规增量或刷榜，3=扎实改进或有用基准，4=方法或视角有明显新意，5=可能改变子领域路线的关键工作）。
   - 仅当 `insight_score >= 4` 时填写 `extra_commentary`（1-2 句指出其核心巧思或潜在短板）以及 2 条具体可验证的 `ideas_and_insights`、`new_paper_directions`。
   - 当 `insight_score <= 3` 时，`extra_commentary` 设为 `null`，`ideas_and_insights` 与 `new_paper_directions` 最多保留 1-2 条紧扣本文局限性的具体改进设想（若无把握可给空数组 `[]`），禁止凑数写“迁移到多模态/轻量化部署”之类泛泛套话。
5. 输出格式：仅输出合法 JSON 对象，不要 Markdown 代码围栏，不要前后解释文字。

# 主题分类规则
{TAXONOMY_RULES}

# 待整理文献
- arxiv_id: {ARXIV_ID}
- Title: {TITLE}
- Abstract:
{ABSTRACT}

# JSON 输出结构（字段名严格一致）
{
  "arxiv_id": "{ARXIV_ID}",
  "title_zh": "准确的中文译题（保留原模型缩写在括号或句首）",
  "topic": "LLM | Multimodal | VisionGen | RLPostTraining | EfficiencySystems | EmbodiedRobotics | DataEvalSurvey | ScienceOther",
  "tags": ["2到3个细粒度技术词，如 Speculative Decoding, VLA, Benchmark"],
  "tldr": "一句话概括核心做法与结论（50字以内，带关键指标更佳）",
  "problem": "要解决的具体痛点或既有方法失效边界（1-2句）",
  "method": "核心机制、架构改动或数据构造方式（1-2句）",
  "contribution": "主要技术或实证贡献（1句）",
  "result": "摘要给出的关键基准与定量对比结果（1-2句）",
  "insight_score": 3,
  "extra_commentary": null,
  "plain_explanation": "面向跨子领域研究者的直白解释：核心直觉是什么，代价或边界在哪（2-3句）",
  "ideas_and_insights": [
    "基于本文机制或局限的具体可验证实验设想"
  ],
  "new_paper_directions": [
    "可独立成篇的后续研究问题"
  ]
}
