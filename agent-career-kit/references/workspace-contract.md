# 工作区契约

创建、导入或验证候选人状态时读取本文件。

## 目录

```text
career-workspace/
├── intake.md
├── candidate-profile.json
├── career-state.json
├── evidence-ledger.md
├── capability-map.md
├── application-dashboard.md
├── weaknesses.md
├── progress.md
├── source-materials/
├── public-assets/
├── jd-bank/
├── story-bank/
├── projects/
└── outputs/
    ├── resumes/{development,algorithm}/
    ├── applications/<company-role>/
    ├── portfolio/
    ├── career-dashboard/
    └── interview/companies/
```

`interview-bank/question-index.json` 是可选派生文件，只在第一次题库查询时创建。

`career-state.json` 是岗位、事件、面试和 Offer 的唯一事实源；`application-dashboard.md` 与 `outputs/career-dashboard/` 是派生产物。

## 阶段

- `intake`：要求 `candidate-profile.json`、`career-state.json` 与 `intake.md` 存在。用于新用户第一次成功，不要求档案已经完整。
- `profile`：要求事实档案、证据账本、能力画像、看板、弱点和进度文件完整。
- 产物阶段：按请求独立验证简历或作品集，不用一个“全家桶”门禁阻断单模块任务。

## 候选人档案

`candidate-profile.json` 是唯一机器可读事实源。

- `schema_version`：当前为 `2`。
- `sources`：带稳定 ID、访问日期和 `evidence_class` 的候选人陈述、工作区文件或 URL。
- `candidate`：姓名、岗位定位、`career_stage`、联系方式和链接。
- `career_stage`：`campus`、`experienced` 或 `senior`。
- `education`：带来源的教育记录。
- `claims`：经历、项目、研究、开源、论文、荣誉或领导力记录。
- `resume_views.development/algorithm`：可选方向；`active=false` 时 `claim_ids` 必须为空，不生成该方向。
- `portfolio.resume_downloads`：作品集需要显示下载按钮的已启用方向。

每个 claim 使用稳定 `id`，包含类别、名称、组织、角色、时间、来源、贡献、限制、状态、使用门槛和 bullet。每个 bullet 使用稳定 ID。

## 状态与证据等级

- `provided`：候选人或材料已经说明的过去事实。
- `confirmed`：候选人解决冲突或再次明确确认的事实。
- `planned`：未来工作，必须保持 `private + block`。
- `caution/improve`：可以窄化后用于简历，但存在明确非阻断缺口。
- `pass`：项目/研究具有完整 proof、至少两个不同来源，并至少包含一个强工件来源。

`pass` 项目还要用 `proof_notes.task_set/baseline/verification/trace/failure/result` 记录六类证据各自的实际内容，避免同一个 bullet 被形式化复用为全部证明。

`evidence_class` 支持：`statement`、`resume`、`repository`、`report`、`dataset`、`trace`、`benchmark`、`publication`、`public_profile`、`jd`。旧档案中的 `visibility`、`public_safe` 与 `contact_visibility` 字段继续兼容，但不参与简历、作品集或投递门禁。

## Agent 改写

原文导入的 bullet 默认为 `text_origin=source`。Agent 新写或实质改写的 bullet 使用：

```json
{
  "text_origin": "agent",
  "approval": {
    "status": "approved",
    "source_ref": "src-confirmation-01",
    "record": "用户确认了本轮最终措辞。"
  }
}
```

建议稿在确认前放入审计或投递包，不直接写进最终 fact store。

## 编辑规则

1. 保持 claim 和 bullet ID 稳定。
2. 先编辑事实源，再重新生成产物；不要把生成文件当事实源。
3. 不为改变重点复制 claim；方向和投递快照只选择、排序已有 ID。
4. 叙事、复盘与计划使用 Markdown；渲染所需结构化字段使用 JSON。
5. JD 投递的 `application-request.json` 是事实源；`application-packet.md` 由脚本重建，仅用于审阅。
6. 使用 UTF-8 和 `YYYY-MM` / `YYYY`；当前经历结束时间用 `Present`。
7. 首轮不要求用户自己编辑 JSON，Agent 负责把自然语言和材料转成结构化状态。
8. 使用 `career_ops.py` 更新求职状态；每次更新后同步生成 Markdown 和网页，不直接编辑派生产物。
