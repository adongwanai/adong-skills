# Agent Career Kit

面向 Agent 开发与 Agent 算法岗位的长期求职工作流 Skill。它不是一次性的简历生成器，而是把候选人事实、两份稳定简历、项目证据、模拟面试、作品集、公司准备和投递复盘放进同一个可持续更新的 workspace。

## 能做什么

1. **材料归档与事实抽取**：读取简历、GitHub、论文、项目文档、JD 和面试记录，建立带来源的候选人档案、Evidence Ledger 和能力画像。
2. **两份稳定主简历**：从同一事实源生成 Agent 开发版与 Agent 算法版 LaTeX、可检索 PDF 和 Overleaf ZIP；保持 LLM-Resume-Template 的版式，不为每个 JD 反复改写。
3. **完整简历审计**：执行 30 秒印象、岗位/职级校准、整体/分段/逐 bullet 审计、So What、STAR/CAR、决策权衡、ownership、证据和一致性检查。默认只给修改建议，不擅自改候选人的成稿。
4. **能力差距与项目孵化**：分别评估 Agent Runtime、工具、记忆、RAG、Eval、Sandbox、可靠性，以及轨迹、Verifier、Reward、Post-training、实验与复现能力，把缺口变成最小可验证项目。
5. **专项训练**：围绕一个项目或知识点做 20-30 分钟 `focus` 深挖，每轮只问一道题，并沿最薄弱或最高信息量分支追问。
6. **完整模拟面试**：按 45 或 60 分钟运行自我介绍、项目深挖、Agent 八股/机制、一道外部 Coding 或手撕算法、反问和面后复盘。
7. **内置面试题库**：随 Skill 分发大体量 Markdown 面经，新 workspace 自动建立私有索引，并可按领域、分类、L1-L5 难度和关键词检索。
8. **Story Bank 与项目讲解**：沉淀 30 秒、2 分钟和深挖版本，记录个人动作、技术决策、失败、边界、结果和可复用能力标签。
9. **README、Demo 与作品集**：生成项目 README、Demo 讲解稿和响应式求职页；支持时间线筛选、项目/论文详情、STAR、证据链接和两份简历下载。
10. **公司准备与长期闭环**：JD 只用于能力信号、公司准备、问题选择和匹配说明；用 CSV/XLSX 跟踪投递、面试、Offer、弱点、下一步和验证条件。

## 哪些是脚本，哪些由 Agent 执行

| 能力 | 执行方式 |
| --- | --- |
| workspace 初始化、字段/证据/隐私校验 | Python 脚本 |
| 双 LaTeX、PDF、Overleaf、作品集渲染 | Python + XeLaTeX/Tectonic |
| 题库索引与筛选 | Python 脚本 |
| CSV/XLSX 投递看板 | Node.js；CSV 是事实源 |
| 简历审计、能力画像、项目计划、公司包 | Agent 按 Skill 契约执行 |
| `focus` / `full-loop` 模拟面试与复盘 | Agent 逐题交互执行 |
| Story Bank、弱点和进度回写 | Agent 更新候选人 workspace |

这意味着它是“Agent 可执行的工作流 + 确定性产物脚本”，不是一个脱离 Codex、Claude Code 或 OpenCode 独立运行的 SaaS。

## 安装

把本目录安装到你使用的客户端，三个客户端共用同一份 Skill：

```bash
# Codex
mkdir -p ~/.agents/skills
cp -R agent-career-kit ~/.agents/skills/

# Claude Code
mkdir -p ~/.claude/skills
cp -R agent-career-kit ~/.claude/skills/

# OpenCode
mkdir -p ~/.config/opencode/skills
cp -R agent-career-kit ~/.config/opencode/skills/
```

需要 Python 3。生成 PDF 需要 XeLaTeX 或 Tectonic。XLSX 是可选输出，需要 Codex bundled spreadsheet runtime 或一个可解析的 `@oai/artifact-tool` 路径；Claude Code/OpenCode 没有该运行时时继续使用 canonical CSV，不影响档案、简历、面试、项目、作品集和投递记录流程。

## 第一次使用

真实候选人资料必须放在本 Skill 和公开仓库之外。先给 Agent 一个外部目录：

```text
$agent-career-kit 请在 /path/to/my-private-career-workspace 建立我的长期候选人档案。
读取我提供的简历、GitHub、项目和论文，先完成材料盘点与证据抽取。
不要改写我的简历；先给出 Agent 开发和 Agent 算法两条能力画像，以及最高优先级的一个补证问题。
```

Claude Code 将 `$agent-career-kit` 换成 `/agent-career-kit`；OpenCode 直接要求使用 `agent-career-kit`。

从 GitHub 安装到 Codex 时，也可以直接要求 `$skill-installer` 安装 `adongwanai/adong-skills` 仓库里的 `agent-career-kit` 目录。Codex 的当前官方用户级发现目录是 `$HOME/.agents/skills`；如果本地旧版 installer 使用 `$CODEX_HOME/skills`，以该 installer 的实际输出为准并重启 Codex。

## 单独调用某个功能

不必每次运行全流程。候选人档案建立后，可以直接调用任一模块：

```text
# 简历审计，不改原文
$agent-career-kit 审计我的两份稳定简历。严格保留当前模板和现有 bullet，只输出逐项问题、影响、最小修改建议和待补证据。

# 重新渲染两份稳定简历
$agent-career-kit 从当前候选人档案渲染 Agent 开发版和 Agent 算法版 LaTeX、PDF 与 Overleaf 包，不做 JD 定制。

# 单项目深挖
$agent-career-kit 用 interview + focus 模式，只拷打我的 Memory Agent 项目 25 分钟。一次只问一道题，结束后再复盘。

# 60 分钟完整模拟面试
$agent-career-kit 用 interview + full-loop 模式模拟 60 分钟 Agent 算法面试：自我介绍、一个项目、相关八股、一道手撕题、反问。不要提前泄露题目和评分点。

# 内置题库检索
$agent-career-kit 从内置题库筛选 Agent 工具调用的 L3-L4 问题，只返回与我的简历弱点相关的 12 道候选题。

# 项目补强
$agent-career-kit 针对我在 Agent Eval/Verifier 的缺口，设计一个最小证据项目。给 baseline、task set、metrics、trace、failure taxonomy、ablation 和 done condition。

# 公司准备
$agent-career-kit 读取这个 JD，生成公司准备包和面试重点，但不得修改两份主简历。

# 作品集
$agent-career-kit 只用 visibility=public 且通过证据门禁的内容生成求职页，并检查桌面、移动端、详情弹窗、链接和简历下载。

# 投递复盘
$agent-career-kit 汇总当前投递、面试和 Offer 漏斗，找出重复失败模式，更新 weaknesses.md 和下周三个可验证动作。
```

## 不能替你做什么

- 不保证面试、Offer、职级或薪酬结果。
- 不为每个 JD 生成一份新主简历。
- 不虚构经历、数字、论文、公司采用或项目结果。
- 不把聚合题库的公司标签说成已核验真题。
- 不在模拟面试时替候选人写 Coding 答案。
- 不自动海投，不做实时面试作弊。

它能做的是把真实能力变成可验证、可讲清、可持续改进的职业资产，并让每次训练和面试失败回流到下一轮行动。

## 隐私与许可证

候选人 workspace 默认 deny-all Git 跟踪，公开作品集只允许显式 `visibility=public` 的事实和联系人。许可证见 [LICENSE](LICENSE)，第三方来源见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)，完整方法追踪见 [references/source-map.md](references/source-map.md)。

`release_check.py` 是维护者的完整发布门禁，需要 PDF 双解析器、Tectonic/XeLaTeX、浏览器运行时和表格运行时。普通用户不需要运行它；日常使用以 `validate_workspace.py` 和当前请求对应的产物检查为准。
