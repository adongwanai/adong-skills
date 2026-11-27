---
name: adong-ai-daily
description: >-
  阿东的 AI 行业日报与前沿情报账本生成器。免登录、零 API Key、纯 Python 标准库并发聚合 6 大类一手与科技信源（X 建设者、建设者播客、HF Daily Papers、GitHub Trending & Hacker News、OpenAI/arXiv/精选 RSS、以及 ainav 9 大中文 AI 媒体），经并查集跨源共振去重后，生成「自包含交互式 HTML 日报页（内置自媒体分享卡片高清导出台）」与「社群一键转发纯文本版」。当用户说“生成今天的AI日报”、“跑一份阿东AI早报”、“输出今日AI情报账本”、“做一份今天社群转发的AI日报”时触发。
---

# 阿东 AI 日报生成器（`adong-ai-daily`）

以一线 Agent 工程师视角，从全球一手建设者动态与主流中文科技源中去重提炼每日高信噪比情报。核心流程**仅依赖 Python 3.10+ 标准库，免登录、零 API Key**，每次只交付两份干净产物：
1. **自包含交互式 HTML 日报页**（`YYYY-MM-DD_ai_daily_report.html`：含 30 秒主线判断、Top 4 Bento 必读、前置趋势判断与 `[N001]` 证据锚点跳转、多维筛选搜索、一键复制社群版、以及纯本地 HTML5 Canvas 自媒体分享卡片工作台）
2. **社群一键转发纯文本版**（`YYYY-MM-DD_community_brief.txt`：专为微信群 / 飞书群转发调优的零套话精简早报）

设当前 Skill 所在目录为 `{SKILL_DIR}`，目标日期（北京时间 `YYYY-MM-DD`）为 `{DATE}`。

---

## 标准执行流程（交互策展模式 · 首选）

### 第 1 步：并发采集多源动态并输出去重候选池
```bash
python3 "{SKILL_DIR}/scripts/collect_sources.py" --date "{DATE}" --dump-for-agent
```
- 自动并发直连 19 个公开信源（含 SSRF 内网地址防护、单源持久化缓存断网回退、`ainav` 当日未出时自动回退前一日），通过并查集将跨媒体同一事件合并为 `N001`、`N002`… 候选簇并按三维相关性打分排序。
- 原始候选池保存在 `{SKILL_DIR}/cache/{DATE}_candidates.json`，不污染当前项目工作区。

### 第 2 步：按阿东文风策展并写入 `curated.json`
动笔前先读取以下两份参考规范：
- [references/taxonomy_and_style.md](./references/taxonomy_and_style.md) — 9 大分类边界与阿东“去 AI 套话、讲人话、给判断”红线
- [references/ledger_schema.md](./references/ledger_schema.md) — `curated.json` 字段契约与数量标准

从候选池精选 **28–45 条** 高价值进展（Top 4 必填一线点评 `adong_note`）+ **4–6 条** 跨事件趋势判断（绑定 `evidence_ids`），保存至 `{SKILL_DIR}/cache/{DATE}_curated.json`。
- **防幻觉回填**：只需引用候选池短 ID（如 `"N001"`），无需手抄长 URL，渲染器会自动精确回填真实多源链接与点赞/Star 热度指标。

### 第 3 步：渲染 HTML 账本与社群一键转发版
```bash
python3 "{SKILL_DIR}/scripts/render_report.py" \
  --candidates "{SKILL_DIR}/cache/{DATE}_candidates.json" \
  --curated "{SKILL_DIR}/cache/{DATE}_curated.json"
```
- 默认输出到 `./output/ai-daily`（可通过 `--out-dir <路径>`、环境变量 `AI_DAILY_OUT_DIR` 或在 Skill 目录新建 `config.local.json` 覆盖本地默认目录）。
- **可选命令行批量导出 PNG 卡片**（需已安装 `playwright`，平时也可直接在 HTML 页面右上角零依赖在线导出）：
  ```bash
  python3 "{SKILL_DIR}/scripts/export_cards.py" --html "<生成的HTML路径>"
  ```

### 第 4 步：对话内精简反馈（禁止刷屏）
不要把整份日报全文贴进聊天框。仅回复：
1. **今日 1 段核心主线判断**
2. **Top 4 必读代表事件简表**（标题、共振源数/热度、一句话事实）
3. 生成好的 **交互式 HTML 页** 与 **社群一键转发 `.txt`** 点击链接。

---

## 无人值守快速兜底模式（可选）

当在定时脚本中无大模型交互时，可直接运行：
```bash
bash "{SKILL_DIR}/scripts/run_daily_report.sh" --auto
```
个性化关注方向词（`focus.topics`）、屏蔽词（`focus.blocked`）与作者署名可在 [config.json](./config.json)（或未纳入版本控制的 `config.local.json`）中配置。
