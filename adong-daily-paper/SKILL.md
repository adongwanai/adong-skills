---
name: adong-daily-paper
description: 阿东的 HuggingFace 每日论文账本与站点生成 Skill。自动抓取 HuggingFace Daily Papers，提炼去套话的结构化中文要点（问题、方法、定量结果与可验证延伸实验），同步输出干净的 Markdown 归档文档（daily/YYYY-MM-DD.md）并构建或增量更新静态论文账本网页（支持直推 GitHub Pages）。当用户要求「HF 今日论文」「跑一份 HF 日报」「更新论文站」「总结 huggingface.co/papers/date/YYYY-MM-DD」时使用。
---

# Adong Daily Paper (Markdown + Static Ledger)

本 Skill 自包含抓取、总结、Markdown 渲染与零构建静态网页模板（`templates/site/`）。设当前 Skill 所在目录为 `SKILL_DIR`，目标数据存放目录（例如本地 `hf-daily-papers` 仓库目录或当前工作目录）为 `WORKSPACE`。

首次运行若缺少依赖，先安装：

```bash
pip install -r "{SKILL_DIR}/requirements.txt"
```

---

## 模式 A：配置了外部 LLM API Key 的一键流水线

当环境变量或 `{WORKSPACE}/.env` 中已配置 `HF_DAILY_LLM_API_KEY`（或 `DEEPSEEK_API_KEY`、`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`）时，直接执行：

```bash
python "{SKILL_DIR}/scripts/run_daily.py" --workspace "{WORKSPACE}" --date YYYY-MM-DD
```

- 省略 `--date` 时默认取北京时间昨日，若遇周末无更新会自动向前顺延查找最近一期有论文的日期。
- **双路产物**：
  1. `daily/{DATE}.md`（及 `out/{DATE}/report.md`）：带可点击目录锚点与折叠延伸笔记的干净 Markdown，可直接归档至飞书知识库或 Obsidian。
  2. `site/`：若目标目录尚无站点外壳，会自动从 `{SKILL_DIR}/templates/site/` 初始化，并编译 `site/data/manifest.json`、全库检索索引 `site/data/search.json` 与 `site/feed/atom.xml`。
- **增量续跑**：已成功总结的 `arxiv_id` 重跑时自动复用，不会重复消耗 Token。

---

## 模式 B：无外部 API Key 的交互代理模式

当未配置外部 API Key 时，由当前 Agent 直接完成论文提炼：

1. **抓取原始论文列表与摘要**：
   ```bash
   HF_PAPER_WORKSPACE="{WORKSPACE}" python "{SKILL_DIR}/scripts/fetch_papers.py" \
     --date {DATE} \
     --out "{WORKSPACE}/out/{DATE}/papers.json"
   ```
2. **按规范分批提炼结构化 JSON**：
   - 读取 `{SKILL_DIR}/prompts/summarize_paper.md` 与 `{SKILL_DIR}/references/topic_taxonomy.md`。
   - 当日论文若超过 10 篇，按每批 6–8 篇并行派发子 Agent（Subagents）处理，防止单次长输出截断或后半程套话化。
   - 汇总写入 `{WORKSPACE}/out/{DATE}/summaries.json`，顶层结构严格保持：
     ```json
     {
       "date": "YYYY-MM-DD",
       "summarized_at": "2026-11-27T08:00:00Z",
       "model": "interactive-agent",
       "daily_brief": "1-2句平实概括当日论文最集中的研究子问题与代表工作",
       "items": [
         { "arxiv_id": "...", "title_zh": "...", "topic": "...", "...": "..." }
       ]
     }
     ```
3. **生成 Markdown 文档并编译静态网页**：
   ```bash
   HF_PAPER_WORKSPACE="{WORKSPACE}" python "{SKILL_DIR}/scripts/build_site.py" \
     --data-dir "{WORKSPACE}/data" \
     --site-dir "{WORKSPACE}/site" \
     --ingest-papers "{WORKSPACE}/out/{DATE}/papers.json" \
     --ingest-summaries "{WORKSPACE}/out/{DATE}/summaries.json"

   HF_PAPER_WORKSPACE="{WORKSPACE}" python "{SKILL_DIR}/scripts/render_md.py" \
     --in-json "{WORKSPACE}/data/daily/{DATE}.json" \
     --out-md "{WORKSPACE}/daily/{DATE}.md"
   ```

---

## 推送上线与对话反馈规范

- 若 `{WORKSPACE}` 已关联 GitHub Pages 仓库（如 `hf-daily-papers`），在用户要求同步上线时提交 `data/daily/{DATE}.json`、`daily/{DATE}.md` 与 `site/` 并推送至远端分支。
- 在聊天窗口内不要全文刷屏整份 Markdown：仅输出 **1 段当日趋势概括 + Top 3–5 代表论文简表（含 `arXiv ID`、核心结论、代码链接）**，并给出生成的 `.md` 路径与网页预览方式。
