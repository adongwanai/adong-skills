# JD 投递包

投递包连接“原始 JD”与“本次投递简历”，解决 JD 分析无法影响选材的问题，同时保留稳定主简历。

## 文件结构

```text
outputs/applications/<company-role>/
├── application-packet.md
├── application-request.json
├── resume-draft/main.tex
└── resume/main.tex
```

`application-request.json` 是事实源，`application-packet.md` 是每次渲染时确定性重建的中文审阅视图，不要直接编辑 Markdown。`resume-draft/` 可以在用户确认前生成；`resume/` 是最终投递稿，必须有 approval。
`render_application_resume.py --final --compile` 同时生成最终 `main.tex` 与 `main.pdf`。

## 必填内容

1. 公司、岗位、原始 JD 路径与 SHA256；
2. 使用的稳定母版方向；
3. JD 核心要求，保持原意，不把推断写成要求；
4. 每项要求对应的 claim IDs，或明确的未覆盖缺口；
5. 本次选中的 claim/bullet IDs 与排序理由；
6. 原文、改写提案、证据边界和风险；
7. 用户确认时间与确认记录。

## 状态

- `draft`：已完成或正在完成要求映射，可以生成审阅稿，不能标为最终投递稿。
- `approved`：用户已经确认要求映射、选材和最终措辞，可以生成最终投递快照。

批准不是 Agent 自行判断。“内容看起来合理”不能替代用户确认。

## 改写边界

- 可以调整标题、摘要、经历选择、bullet 顺序和证据安全的表达。
- 单次投递 bullet 改写写入 `bullet_overrides`，同时保存与当前 profile 完全一致的 `source_text`；原文变化后旧提案自动失效。
- 不得添加来源中没有的新职责、数字、结果、工具熟练度或上线状态。
- 未覆盖要求写入 gap，不用弱证据强行匹配。
- JD 更新后摘要哈希失效，必须重新确认映射。

## 最低验收

- 每项 JD 核心要求都有 claim IDs 或具体 gap；
- 所有选择项来自当前候选人档案，且不是 `planned`；
- 最终稿有可追溯 approval；
- 投递稿正文可见目标岗位标题；
- 投递包能解释“为什么选这些内容”和“哪些要求仍未覆盖”。
