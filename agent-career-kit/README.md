# Agent Career Kit

面向 Agent 开发与 Agent 算法岗位的全流程求职 Skill。它把简历、GitHub、论文、项目、JD 和面试记录沉淀为一份长期候选人档案，并围绕真实 Offer 推进简历、项目、面试、作品集和投递复盘。

适用于校招、有经验候选人和资深候选人，可在 Codex、Claude Code 与 OpenCode 中使用。

## 能做什么

- **材料归档与事实抽取**：导入 PDF、DOCX、Markdown、TXT、JSON、HTML 或 LaTeX，保留原件与规范化文本，提取经历、项目、技能、数字和证据缺口。
- **候选人档案与能力画像**：按校招、社招或资深阶段，建立 Agent 开发 / Agent 算法能力画像，区分已证明能力、可表达事实和待补强项。
- **Agent 简历审计**：使用 30 秒筛选、整体结构、分段与逐条 bullet 审计，追问“所以呢”，检查角色、难点、行动、结果与证据，不改变用户指定的模板和版式。
- **按需生成主简历**：候选人可只启用 Agent 开发版、只启用 Agent 算法版，或同时维护两份稳定主简历；支持 LaTeX、PDF 与 Overleaf 包。
- **JD 投递包**：把 JD 拆成要求、证据、缺口和面试风险，生成独立投递快照。它可以调整已有事实的选择、排序与表达，但不会修改候选人主档案或虚构经历。
- **项目与学习补强**：根据目标岗位和证据缺口生成项目计划、实验方案、验收标准、README、Demo 与履历提升路径。
- **单点模拟面试**：围绕某个项目、知识点或简历疑点，一次只问一题，根据回答继续深挖，并给出证据化复盘。
- **45-60 分钟完整面试**：覆盖自我介绍、项目深挖、Agent 八股、算法或 Coding、系统设计与反问环节，支持压力追问和能力边界验证。
- **Agent 专项题库**：按领域、分类、L1-L5 难度和关键词检索题目；首次查询时自动建立索引，不要求用户预处理题库。
- **Story Bank 与讲解稿**：把项目和经历整理成可复用的 STAR 故事、项目讲解稿、技术决策与失败复盘。
- **作品集与个人求职页**：生成 GitHub README、项目 Demo 展示、可交互个人求职页和简历下载入口。
- **Offer 求职运营**：维护目标、岗位、投递、面试、Offer 和事件，生成漏斗、近期优先事项、下一最佳行动与本地网页驾驶舱。

所有对外事实都必须来自候选人材料或用户确认。Skill 可以优化表达，但不会编造学校、公司、角色、数字、论文、奖项或项目结果。

## 核心工作流

```text
任意候选人材料
      ↓
材料归档与事实抽取
      ↓
长期候选人档案 + 阶段/方向能力画像
      ↓
┌──────────────┬──────────────┬──────────────┐
│ 按需主简历   │ 项目与学习补强 │ 面试与题库训练 │
└──────────────┴──────────────┴──────────────┘
      ↓
作品集 / JD 投递快照 / 公司准备包
      ↓
投递 → 面试 → Offer → 面后复盘
      └──────────回写档案、弱项与下一行动
```

你不必从头跑完整流程。简历审计、项目深挖、题库检索、完整模拟面试、JD 分析、作品集和 Offer 跟踪都可以单独调用。

## Agent 与脚本各负责什么

| 工作 | Agent 负责 | 脚本负责 |
|---|---|---|
| 材料处理 | 识别事实、冲突与缺口 | 归档原件、抽取文本、维护清单 |
| 能力画像 | 判断证据强弱、岗位方向与补强优先级 | 校验候选人 workspace 的结构与状态 |
| 简历 | 审计、事实挖掘、表达提案和用户确认 | 渲染 LaTeX、编译 PDF、打包 Overleaf |
| JD 投递 | 拆解要求、映射证据、准备面试风险 | 固化 JD 哈希、生成独立投递快照 |
| 面试 | 单题追问、完整面试、评分与复盘 | 题库索引、检索和训练记录落盘 |
| 项目与作品集 | 设计项目、README、Demo 与讲解稿 | 渲染求职页并校验产物 |
| Offer 运营 | 判断优先级和下一行动 | 维护状态、计算漏斗、生成 Markdown 与网页驾驶舱 |

脚本只处理确定性的归档、渲染和校验；涉及事实判断、表达取舍与面试追问的工作由 Agent 完成。

## 安装

先克隆仓库：

```bash
git clone https://github.com/adongwanai/adong-skills.git
cd adong-skills
```

推荐让三个客户端链接同一份源码，后续只需更新一次仓库：

```bash
mkdir -p ~/.agents/skills ~/.claude/skills ~/.config/opencode/skills
ln -s "$(pwd)/agent-career-kit" ~/.agents/skills/agent-career-kit
ln -s "$(pwd)/agent-career-kit" ~/.claude/skills/agent-career-kit
ln -s "$(pwd)/agent-career-kit" ~/.config/opencode/skills/agent-career-kit
```

调用方式：

- Codex：`$agent-career-kit`
- Claude Code：`/agent-career-kit`
- OpenCode：直接说“使用 agent-career-kit ……”

核心流程只依赖 Python 3。PDF 材料抽取需要 `pdfplumber`；正式 PDF 输出需要 XeLaTeX 或 Tectonic。题库按需索引，不依赖 Node 或 XLSX。

## 第一次使用

不需要先整理目录，也不需要先填写 JSON。上传现有材料，然后用自然语言说明目标即可：

```text
$agent-career-kit
我是有 3 年经验的后端工程师，准备投 Agent 开发岗位。
这是我的现有简历和两个项目链接。请先建立候选人档案，
给我一版可以审阅的能力画像和下一步行动，不要虚构缺失信息。
```

只有一份 JD、一段项目描述，甚至只有一句背景也可以启动。Skill 会先交付当前材料能支持的结果，再集中询问最多 3 个真正影响下一步的问题。

候选人 workspace 必须放在 Skill 仓库之外，例如：

```bash
python3 agent-career-kit/scripts/init_workspace.py /absolute/path/to/my-career-workspace
python3 agent-career-kit/scripts/import_materials.py \
  /absolute/path/to/my-career-workspace \
  /absolute/path/to/resume.pdf --kind resume
python3 agent-career-kit/scripts/import_materials.py \
  /absolute/path/to/my-career-workspace \
  /absolute/path/to/project.md --kind project
```

这样更新或开源 Skill 时，不会把候选人私有材料一起提交。

## 单独调用功能

### 1. 简历审计，不改格式

```text
使用 agent-career-kit 审计这份简历。保持我现有的 LaTeX 模板、章节、排版和基本经历不变；
按 30 秒筛选、整体、分段和逐条 bullet 给出问题、影响、修改建议与待确认事实。
```

### 2. 生成某个方向的简历

```text
基于已确认档案生成 Agent 开发版简历，突出工具调用、工作流、记忆、评估、可靠性与工程交付；
使用项目已有模板输出 LaTeX、PDF 和 Overleaf 包。
```

```text
基于同一份事实档案生成 Agent 算法版简历，突出模型、训练、推理、检索、实验设计与评估；
不要为了形成差异而新增事实。
```

### 3. 针对 JD 准备投递

```text
分析这个 JD，输出要求-证据-缺口映射、风险点和面试准备包。
基于稳定主简历生成一份独立投递快照，任何新表达先让我确认，不要修改主档案。
```

### 4. 单点项目深挖

```text
只针对我的多 Agent 调度项目做 grill-me 式深挖。一次只问一题，沿实现、故障、权衡、指标和个人贡献追问，直到找到真实能力边界，再复盘。
```

### 5. 完整模拟面试

```text
基于我的简历和目标岗位做一场 60 分钟 Agent 开发模拟面试：自我介绍、项目深挖、Agent 八股、Coding、系统设计和反问。一次只问一题，结束后输出评分、证据、弱点和复训任务。
```

### 6. 查询专项题库

```text
从题库中找 12 道 Agent Memory 与 RAG 题，L2-L4 难度，先只出题；我回答后再评分和追问。
```

### 7. 项目补强

```text
根据 Agent 算法岗位的能力缺口，为我设计一个 4 周可完成的项目补强计划。每周必须有可验证产物、实验或 Demo，不要把学习清单当项目成果。
```

### 8. Story Bank 与作品集

```text
把我现有项目整理成 Story Bank、项目讲解稿和 GitHub README，并生成个人求职页。所有公开内容先列出事实来源和待确认项。
```

### 9. 投递与 Offer 跟踪

```text
把这次投递、面试时间和面试结果加入求职驾驶舱，更新漏斗，并告诉我今天最应该推进的一个动作。
```

## 常用脚本

下列命令用于确定性生成与校验；正常使用时可以直接让 Agent 代为执行。

<details>
<summary>查看脚本命令</summary>

```bash
# 校验候选人 workspace
python3 agent-career-kit/scripts/validate_workspace.py /absolute/path/to/workspace --stage intake

# 渲染一个或两个简历方向
python3 agent-career-kit/scripts/render_resumes.py /absolute/path/to/workspace --view development
python3 agent-career-kit/scripts/render_resumes.py /absolute/path/to/workspace --view algorithm

# 查询题库
python3 agent-career-kit/scripts/query_interview_bank.py \
  /absolute/path/to/workspace \
  --domain 大语言模型与NLP --category Agent与工具调用 --level L3 --limit 10

# 生成作品集
python3 agent-career-kit/scripts/render_portfolio.py /absolute/path/to/workspace

# 刷新求职驾驶舱
python3 agent-career-kit/scripts/career_ops.py /absolute/path/to/workspace render
```

JD 投递快照分为审阅和批准两个阶段：

```bash
python3 agent-career-kit/scripts/init_application.py \
  /absolute/path/to/workspace \
  --jd /absolute/path/to/jd.md \
  --slug example-agent-engineer \
  --company Example --role "Agent Engineer" --view development

python3 agent-career-kit/scripts/render_application_resume.py \
  /absolute/path/to/workspace \
  /absolute/path/to/workspace/outputs/applications/example-agent-engineer/application-request.json
```

Agent 改写的 bullet 和本次投递选择必须在候选人档案与 `application-request.json` 中留下确认记录，之后才可使用 `--final --compile` 生成最终投递版本。

</details>

## 主要产物

```text
candidate-profile.json                 长期候选人事实档案
intake.md                              首轮材料与缺口摘要
story-bank/                            STAR 故事与项目讲解稿
weaknesses.md                          长期弱项与复训记录
outputs/resumes/                       主简历 LaTeX / PDF / Overleaf
outputs/applications/<application-id>/ JD 分析、审阅稿和投递快照
outputs/portfolio/                     个人求职页
outputs/career-dashboard/              投递漏斗与本地网页驾驶舱
```

## 边界

- 不承诺“从 0 自动拿到 Offer”；它提供的是可执行、可追踪、可复盘的求职系统。
- 不虚构事实、指标、学校、公司、论文、奖项或项目结果。
- 不为每个 JD 改写候选人的长期事实档案；JD 只生成独立投递快照和准备包。
- 不替用户自动海投，不提供面试中的隐蔽实时作弊。
- 不把普通学习 Demo 包装成生产级系统，也不把未验证计划写成已完成成果。
- 不在 Skill 仓库内保存真实候选人 workspace。

## 许可证与第三方材料

Skill 代码采用 MIT License。简历模板及其他第三方材料的来源、修改和许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
