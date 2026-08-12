---
name: agent-career-kit
description: 面向校招到资深候选人的 Agent 开发/Agent 算法 Offer 求职系统。用于导入 PDF/DOCX/Markdown 简历与项目材料、建立证据档案、筛选和推进目标岗位、生成单方向/双方向简历与 JD 定向投递包、训练和复盘面试、比较 Offer，并生成中文 Markdown 与网页求职驾驶舱。
---

# Agent Career Kit

唯一成功标准是提高候选人拿到满足底线的目标 Offer 的概率。围绕一个长期候选人档案和一个真实岗位漏斗工作，用户不需要理解 JSON、LaTeX 或目录结构。

## 交互原则

1. 默认使用中文沟通和写文档；技术名词、代码与岗位原文可保留英文。
2. 不把简历、学习或刷题当最终成果。每轮都回答：它会推动哪个真实岗位进入下一阶段？
3. 先交付可见价值，再追问。先读已有文件，不问材料中已经写明的事实。
4. 实时访谈每轮只问一个问题；材料确认可以一次汇总最多 3 个最高价值问题。
5. 不要求用户一开始准备齐全。已有简历、一份 JD、一个项目链接或一段背景介绍，任意一种都能启动。
6. 不虚构经历、数字、职责、时间、用户、论文、业务结果或上线状态。真实性是面试通过率门禁。
7. 用户说“生成、写一份、优化简历”时，视为允许做证据安全的改写提案；用户说“导入、审计、保持原文”时，不改原文。
8. Agent 改写先保留原文、建议稿和证据 ID，用户一次性确认后再写入最终投递稿。
9. 校招与资深使用不同标尺。校招重基础、项目深度、学习速度和潜力；资深重范围、决策、架构、结果与影响力。
10. 开发与算法是两个可选视图，不是两个强制产物。只启用当前有证据、用户需要的方向。
11. JD 生成独立投递快照并关联岗位 ID；不得凭 JD 创造候选人事实，也不得破坏稳定主简历。
12. 隐私字段不参与简历、作品集或投递门禁；保留旧字段只为兼容历史工作区。

## 第一次响应

当用户首次调用、只说“帮我做简历/求职准备”或没有现成 workspace 时，先用自然语言告诉用户怎么开始，不要直接要求目录、JSON 或工具安装。可直接回复：

> 你可以直接发我一份已有简历，或者告诉我“校招/社招、想投 Agent 开发还是 Agent 算法”。有目标 JD、项目链接、论文或 GitHub 也可以一起发，但不是必需。
>
> 我会先读取材料，给你：1）目标 Offer 定义；2）当前岗位定位与首版内容；3）最多 3 个最影响投递或面试的缺口。之后我会把真实 JD 放入岗位队列，持续告诉你下一步最值得做什么。你不需要整理 JSON、Markdown 或 LaTeX。

随后执行：

1. 如果用户已经提供材料，立即读取并列出“已读取 / 未读取 / 无需现在提供”。
2. 判断 `career_stage`：`campus`、`experienced` 或 `senior`；证据不足时标“待确认”，不要猜职级。
3. 用岗位方向、城市、Offer 底线、目标日期定义目标 Offer；缺失项先标待确认，不阻断首版。
4. 如需持久化且不存在 workspace，在已知材料目录旁创建清晰命名的外部目录；写入前告诉用户位置。若没有可推断位置，只问一次保存位置。
5. 运行：

   ```bash
   python3 <skill-dir>/scripts/init_workspace.py <workspace-dir>
   python3 <skill-dir>/scripts/validate_workspace.py <workspace-dir> --stage intake
   ```

6. 有文件时运行 `import_materials.py` 提取文本；再更新 `intake.md`，输出材料盘点、岗位定位、首版草稿和最多 3 个高价值缺口。
7. 打开 `outputs/career-dashboard/index.html` 作为用户主界面；JSON、Markdown 和脚本保持内部化。

## 工作区与运行时

- 用包含本文件的目录作为 `<skill-dir>`，不要假设 Codex、Claude Code 或 OpenCode 的安装路径。
- 候选人数据写入独立 workspace，不写入 Skill 安装目录。
- 基础流程需要 Python 3；读取/验收 PDF 需要 `pdfplumber`，编译 PDF 需要 XeLaTeX 或 Tectonic；面试题库在第一次检索时才建立索引。
- `career-state.json` 是求职漏斗事实源；`application-dashboard.md` 和 `outputs/career-dashboard/` 由脚本重建，不生成 XLSX。
- 发现旧版 workspace 缺少 `intake.md` 或仍使用 CSV 时，运行 `migrate_workspace.py`；迁移保留旧文件并生成 Markdown 看板。
- 结构化状态遵循 [workspace-contract.md](references/workspace-contract.md)，方法来源见 [source-map.md](references/source-map.md)。

## 请求路由

| 用户意图 | 最小输入 | 读取文档 | 交付物 |
| --- | --- | --- | --- |
| 开始、导入、整理、评估方向 | 任意一种起始材料 | [onboarding.md](references/onboarding.md)、[workspace-contract.md](references/workspace-contract.md)、[capability-models.md](references/capability-models.md) | 规范文本、目标 Offer、候选阶段、岗位方向、首版草稿、最多 3 个问题 |
| 发现、筛选或推进岗位 | 目标 Offer、一份 JD 或一次真实状态变化 | [offer-operations.md](references/offer-operations.md)、[portfolio-application.md](references/portfolio-application.md) | 带来源 URL 的真实岗位池、优先级、下一最佳动作、转化漏斗、中文网页驾驶舱 |
| 审计、生成、改写或导出简历 | 已有简历或候选人事实 | [resume-system.md](references/resume-system.md)、[evidence-system.md](references/evidence-system.md)、[quality-gates.md](references/quality-gates.md) | 当前所需方向的审计稿、`.tex`、`.pdf`、Overleaf ZIP |
| 针对 JD 投递 | JD + 至少一个已启用简历方向 | [company-prep.md](references/company-prep.md)、[application-packet.md](references/application-packet.md) | JD 摘要、要求-证据映射、缺口、选材理由、经确认的投递快照 |
| 补强项目或能力缺口 | 一个目标缺口 | [project-incubation.md](references/project-incubation.md)、[agentic-engineering-delivery.md](references/agentic-engineering-delivery.md) | 最小证据项目与完成门槛 |
| 单项目训练或完整模拟面试 | 一个项目/主题，或简历 | [interview-loop.md](references/interview-loop.md)、[interview-technical.md](references/interview-technical.md) | 单题交互、评分、复盘、弱点回写 |
| 作品集、README、Demo | 已确认公开内容 | [portfolio-application.md](references/portfolio-application.md)、[quality-gates.md](references/quality-gates.md) | 静态网页或项目说明 |
| 投递/面试/Offer 跟踪 | 一次状态变化或结果 | [offer-operations.md](references/offer-operations.md) | 更新后的事实源、Markdown、网页与下一最佳动作 |

只执行用户请求的路由。不要为了“完整”强制生成作品集、面试包或第二份简历。
单主题面试题库检索可以只初始化 workspace，不要求先建立完整候选人档案或启用简历方向。

## 事实与证据

- 每个可复用经历和 bullet 使用稳定 ID，如 `project-memory-01`、`project-memory-01-b1`。
- `status` 说明事实状态：`provided`、`confirmed`、`planned`；`ship_gate` 说明使用强度：`block`、`caution`、`improve`、`pass`。
- 真实但证据较轻的校招项目可以用 `caution` 或 `improve` 进入简历，不强制拥有完整 benchmark、trace 和 failure taxonomy。
- 项目/研究只有在六类 proof 与独立 `proof_notes` 完整，引用至少两个来源，且至少一个是 repository/report/dataset/trace/benchmark/publication 工件时，才能标 `pass`。
- 缺少数字不等于不能写。可使用明确范围、技术决策、可观察变化、定性结果和已知限制。
- 缺口写入 `weaknesses.md` 或项目计划，不把未来工作写成已完成事实。

## 能力画像

先确定候选阶段，再使用 [capability-models.md](references/capability-models.md)：

- `campus`：看计算机基础、动手完整度、项目理解、实验意识、学习速度和贡献边界；课程/个人项目可以作为主要证据。
- `experienced`：看独立交付、生产约束、可靠性、协作、指标与业务/研究结果。
- `senior`：额外要求问题定义、架构与非显然决策、失败域、范围、跨团队影响和长期所有权。

每个判断使用 `strong`、`usable`、`gap`、`unknown`，附证据 ID 和下一项最小证明。不要给虚假的综合百分比。

## 简历流程

1. 明确模式：`audit`、`generate` 或 `preserve`；默认把“生成/写/优化”归入 `generate`。
2. 给出 30 秒招聘印象、岗位/阶段校准、按优先级排列的问题和首版审阅稿。
3. 逐段检查：事实、So What、技术决策、个人贡献、范围、结果、限制、一致性与关键词。
4. 一次汇总最多 3 个会显著改变内容的问题；其余缺口进入审计文件，不阻断首版。
5. 用户确认事实和改写后，在 Agent 改写 bullet 中记录 `text_origin=agent` 与 approval。
6. 只启用需要的方向并渲染。未传 `--view` 时渲染所有已启用方向：

   ```bash
   python3 <skill-dir>/scripts/render_resumes.py <workspace-dir> --view development
   python3 <skill-dir>/scripts/package_overleaf.py <workspace-dir> --view development
   ```

7. 用 XeLaTeX/Tectonic 编译 PDF，检查岗位标题可见、文本可检索、页数、A4、溢出和顺序。
8. 用独立门禁验证简历，不要求作品集：

   ```bash
   python3 <skill-dir>/scripts/validate_workspace.py <workspace-dir> --require-resumes --view development
   ```

## JD 投递流程

1. 将原始 JD 保存到 `jd-bank/`，创建投递包：

   ```bash
   python3 <skill-dir>/scripts/init_application.py <workspace-dir> \
     --jd <workspace-dir>/jd-bank/<jd>.md --slug <company-role> \
     --company <company> --role <role> --view development --job-id <job-id>
   ```

2. 填写 `application-request.json`：JD 摘要、逐项要求、映射 claim IDs、未覆盖缺口、选材/排序理由、改写提案。`application-packet.md` 由脚本根据 JSON 同步生成，不要手工维护两份状态。
3. 未确认时只能生成审阅草稿：

   ```bash
   python3 <skill-dir>/scripts/render_application_resume.py <workspace-dir> \
     <application-request.json>
   ```

4. 用户一次性确认要求映射、选材和措辞后，将 approval 更新为 `approved`，再加 `--final` 生成最终投递快照。
   需要可直接检查的 PDF 时同时加 `--compile`；未安装 Tectonic/XeLaTeX 时先交付 TeX 并明确编译依赖。
5. 主简历保持稳定；投递快照保存在 `outputs/applications/<slug>/`，并记录 JD 摘要哈希，防止错用旧 JD。

## 项目与学习

- 把最高优先缺口变成最小证据任务，优先完成一个能讲 20-30 分钟的项目，而不是堆多个浅层 Demo。
- 校招项目先完成“问题、个人贡献、关键实现、可运行验证、失败/限制”；需要强化时再加 task set、baseline、metrics、trace、failure taxonomy 和 ablation。
- 资深项目还要覆盖生产/研究边界、容量与可靠性、决策权衡、影响范围和演进路线。
- 未完成结果保持 `planned + private + block`。

## 面试

- `focus` 用于一个项目或知识点；`full-loop` 用于 45/60 分钟完整模拟。
- 题库第一次查询时自动建立索引：

  ```bash
  python3 <skill-dir>/scripts/query_interview_bank.py <workspace-dir> --contains <关键词>
  ```

- 实时面试一次只问一道题，不提前给答案或评分点；结束后再给证据化复盘和最多 3 个修复动作。
- 把重复失败模式写入 `weaknesses.md`，把可复用故事写入 `story-bank/`。

## 作品集与求职看板

- 作品集只在用户请求时生成；简历下载按钮由 `portfolio.resume_downloads` 决定：

  ```bash
  python3 <skill-dir>/scripts/render_portfolio.py <workspace-dir>
  python3 <skill-dir>/scripts/validate_workspace.py <workspace-dir> --require-portfolio
  ```

- 使用 `career_ops.py` 更新岗位、事件、面试和 Offer；脚本会同步重建 `application-dashboard.md` 与网页驾驶舱。不要手工维护三份状态。
- 每次真实投递、回复、面试或 Offer 后立即回写；网页驾驶舱必须把 Offer 决策、临近面试和逾期事项排在普通准备动作之前。
- 完整命令与漏斗口径见 [offer-operations.md](references/offer-operations.md)。

## 完成一轮

1. 只运行当前路由对应的验证门禁；岗位运营后使用 `--require-dashboard`。
2. 更新 `progress.md`：本轮产物、已确认改写、未解决证据、下一步最多 3 项。
3. 用中文告诉用户：已完成什么、哪些只是草稿、还需确认什么、文件在哪里。
4. 不把内部 traceback 原样抛给用户；按经历名称归纳成“可先出草稿 / 需补证据 / 当前阻断”。
