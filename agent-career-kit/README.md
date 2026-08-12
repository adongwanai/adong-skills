# Agent Career Kit

面向校招、有经验候选人和资深候选人的 Agent 开发 / Agent 算法 Offer 求职 Skill。它从一份简历、一个 JD、一个项目链接或一段自然语言介绍开始，持续推进目标岗位、定向投递、面试和 Offer。

产品原则是：**简历不是终点，拿到满足底线的目标 Offer 才是。先交付可审阅结果，再推动真实岗位进入下一阶段。**

## 第一次怎么用

不需要先建 JSON、学 LaTeX 或准备完整材料。直接对 Agent 说：

```text
$agent-career-kit 我是校招生，想投 Agent 开发。这是我的简历，请先给我岗位定位和一版可审阅的简历内容，最多问我 3 个最重要的问题。
```

也可以更简单：

```text
$agent-career-kit 我有 8 年后端经验，准备转资深 Agent 开发。先读取这些项目材料，判断哪些经历最有竞争力。
```

首次响应先告诉用户：可以提供什么、Agent 已经读了什么、首轮会交付什么。用户无需维护 JSON、Markdown 或 LaTeX。详见 [首次使用契约](references/onboarding.md)。

## 主要能力

1. **材料自动导入**：支持 PDF、DOCX、Markdown、文本、HTML、JSON 与 TeX，保留原件并生成规范文本。
2. **轻量冷启动**：任意一种材料即可开始，首轮输出目标 Offer、岗位定位、可审阅草稿和最多 3 个高价值缺口。
3. **校招到资深分层**：校招看基础、项目完整度、学习速度与潜力；资深看架构决策、范围、结果和影响力。
4. **按需简历方向**：Agent 开发版、Agent 算法版可以单独启用，也可以同时维护。
5. **JD 定向投递**：逐项映射岗位要求，生成定向 PDF，并关联真实岗位状态。
6. **岗位运营**：记录岗位优先级、匹配理由、缺口、投递、回复与下一步。
7. **转化漏斗**：计算目标岗位、投递、回复、面试和 Offer 的真实阶段转化。
8. **下一最佳动作**：优先处理 Offer 截止、临近面试和已回复岗位，不让低价值准备占满时间。
9. **模拟面试与复盘**：支持单项目或完整面试，结果回写岗位和弱点。
10. **Offer 比较**：集中记录职级、现金、股权、条件、截止日期与风险。
11. **中文网页驾驶舱**：用户主要看网页；Markdown 用于迁移和审阅，不使用 XLSX。

## 最短工作流

```text
起始材料
  -> 目标 Offer 与材料盘点
  -> 首版可审阅内容
  -> 最多 3 个关键问题
  -> 用户一次性确认
  -> 真实岗位队列与定向材料
  -> 投递 / 回复 / 面试 / Offer 状态回写
  -> 下一最佳动作与转化复盘
```

初始化外部工作区：

```bash
python3 scripts/init_workspace.py /path/to/career-workspace
python3 scripts/validate_workspace.py /path/to/career-workspace --stage intake
```

导入已有材料：

```bash
python3 scripts/import_materials.py /path/to/career-workspace /path/to/resume.pdf --kind resume
python3 scripts/import_materials.py /path/to/career-workspace /path/to/jd.docx --kind jd
```

初始化后可直接打开 `outputs/career-dashboard/index.html`。空状态会明确提示先添加 3-5 个目标岗位。

初始化是轻量的，不会预先生成庞大题库索引。第一次检索题库时才按需建立索引。
只做某个 Agent 主题训练时，到这里就可以直接查询题库，不需要先完成简历档案。

## 简历

只渲染开发方向：

```bash
python3 scripts/render_resumes.py /path/to/career-workspace --view development
python3 scripts/package_overleaf.py /path/to/career-workspace --view development
```

不传 `--view` 时，只渲染 `candidate-profile.json` 中已启用的方向。生成 PDF 需要 XeLaTeX 或 Tectonic；生成 `.tex` 不需要安装 LaTeX。

只验证简历产物：

```bash
python3 scripts/validate_workspace.py /path/to/career-workspace --require-resumes --view development
```

## JD 投递包

```bash
python3 scripts/init_application.py /path/to/career-workspace \
  --jd /path/to/career-workspace/jd-bank/company-role.md \
  --slug company-role --company 公司名 --role "Agent 开发工程师" \
  --view development --job-id company-role
```

Agent 完成要求-证据映射后，先生成审阅稿：

```bash
python3 scripts/render_application_resume.py /path/to/career-workspace \
  /path/to/career-workspace/outputs/applications/company-role/application-request.json
```

用户确认选材和措辞后，用 `--final --compile` 生成最终 TeX 与 PDF：

```bash
python3 scripts/render_application_resume.py /path/to/career-workspace \
  /path/to/career-workspace/outputs/applications/company-role/application-request.json \
  --final --compile
```

详细契约见 [JD 投递包](references/application-packet.md)。

## Offer 求职运营

```bash
# 定义目标 Offer
python3 scripts/career_ops.py /path/to/career-workspace set-target \
  --roles "Agent 开发工程师" --locations "上海,杭州" \
  --minimum-offer "岗位方向匹配，薪资不低于当前总包"

# 添加岗位
python3 scripts/career_ops.py /path/to/career-workspace add-job \
  --id company-role --company 公司名 --role "Agent 开发工程师" \
  --priority high --fit strong --source 内推

# 记录真实进展
python3 scripts/career_ops.py /path/to/career-workspace record-event \
  --job-id company-role --type applied --note "官网投递"
```

每次操作都会同步重建 `application-dashboard.md` 和 `outputs/career-dashboard/index.html`。完整命令见 [Offer 求职运营](references/offer-operations.md)。

## 作品集

作品集按需生成：

```bash
python3 scripts/render_portfolio.py /path/to/career-workspace
python3 scripts/validate_workspace.py /path/to/career-workspace --require-portfolio
```

仓库没有 XLSX 构建脚本，也不依赖表格专用运行时。

旧版 workspace 可一次性迁移，旧 CSV 会保留并转换进 Markdown 看板：

```bash
python3 scripts/migrate_workspace.py /path/to/old-career-workspace --career-stage experienced
```

## 安装

基础运行需要 Python 3；读取 PDF 与验收 PDF 需要 `pdfplumber`，DOCX 导入不需要额外 Python 包。建议让多个客户端链接到同一份安装目录，避免复制后版本漂移：

```bash
mkdir -p ~/.agents/skills
ln -s /absolute/path/to/agent-career-kit ~/.agents/skills/agent-career-kit
```

Claude Code 或 OpenCode 可将同一目录链接到各自的 Skills 发现目录。复制安装也可以，但升级时需要覆盖所有副本。

## 常用请求

```text
# 保持原文审计
$agent-career-kit 审计我的开发岗简历，保持原文。给 30 秒印象、逐 bullet 问题和最多 3 个补证问题。

# 生成一份开发岗简历
$agent-career-kit 根据这些材料生成一份 Agent 开发简历。允许证据安全改写，先给审阅稿，确认后再输出 PDF。

# 校招项目补强
$agent-career-kit 我是校招生，深挖这个 RAG 项目。先判断当前能写到什么程度，再设计一周内能完成的最小补强。

# 资深候选人校准
$agent-career-kit 按资深 Agent 开发标准审计我的经历，重点看问题定义、架构决策、范围、可靠性和跨团队影响。

# JD 投递
$agent-career-kit 读取这个 JD，逐项映射我的证据，生成投递包和审阅版简历。不要强行匹配未覆盖要求。

# 单项目模拟面试
$agent-career-kit 用 interview + focus 模式深挖我的 Memory Agent 项目 25 分钟，一次一道题，最后再复盘。

# 投递复盘
$agent-career-kit 更新 Markdown 求职看板，总结重复失败模式和下周最多 3 个可验证动作。
```

## 边界

- 不保证面试、Offer、职级或薪酬结果。
- 不虚构经历、数字、论文、公司采用或项目结果。
- 不把聚合题库的公司标签说成已核验真题。
- 不在模拟面试时替候选人完成 Coding 答案。
- 不自动海投，不做实时面试作弊。

完整 UX 问题与本次升级状态见 [UX-UPGRADE.md](UX-UPGRADE.md)。许可证见 [LICENSE](LICENSE)，第三方来源见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
