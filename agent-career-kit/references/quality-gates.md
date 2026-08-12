# 质量门禁

生成文件不等于完成。只运行当前请求对应的门禁。

## Intake

```bash
python3 <skill-dir>/scripts/validate_workspace.py <workspace-dir> --stage intake
```

- `intake.md` 与空白档案存在；
- 空白求职状态与网页驾驶舱存在；
- 用户知道可以提供什么、首轮会得到什么、下一步是什么；
- 不要求简历、作品集、题库索引或完整 profile。

## 候选人档案

```bash
python3 <skill-dir>/scripts/validate_workspace.py <workspace-dir>
```

- 候选阶段有效，至少一个简历方向启用；
- claim/bullet/source ID 唯一且引用有效；
- 未启用方向为空，不阻断当前方向；
- 普通项目可以 `caution/improve`；`pass` 项目满足强工件门槛；
- Agent 改写有用户确认记录；
- 没有占位符伪装成最终事实。

## 简历

```bash
python3 <skill-dir>/scripts/validate_workspace.py <workspace-dir> --require-resumes --view development
```

- 传 `--view` 时只要求该方向的 TeX、PDF 和 Overleaf ZIP；不传时检查所有已启用方向；
- TeX 与当前 profile 完全一致；
- PDF 是 A4、页数正确、文本可搜索；
- 姓名、可见岗位标题和一个代表性 claim 能被抽取；
- 岗位标题不是注释，章节顺序符合该方向的 claim 优先级；
- 无重叠、裁切、空白页、乱码、孤立标题或不可读密度；
- ZIP 包含当前 `main.tex`、class、manifest 与许可证说明。

## JD 投递包

- JD 路径与 SHA256 对应当前原文；
- 每项要求映射 claim IDs 或写具体 gap；
- 选材只来自当前档案，不含 planned claim；
- 审阅稿与最终稿目录分开；
- 最终稿有 approval 时间与记录；
- 投递包能解释选材、排序和未覆盖风险。
- `--final --compile` 后 PDF 页数符合 view 配置且全部为 A4，正文有目标岗位标题，元数据含当前 request digest。

## 作品集

```bash
python3 <skill-dir>/scripts/validate_workspace.py <workspace-dir> --require-portfolio
```

- HTML/CSS/JS 与当前 profile digest 一致；
- 首屏有候选人和岗位信号；
- 项目详情、筛选、键盘焦点、图片和链接可用；
- 桌面与移动端无横向溢出或内容重叠；
- 简历按钮只显示 `portfolio.resume_downloads` 中配置的方向。

## 面试与成长

- `focus` 只围绕一个项目/主题；`full-loop` 总时长为 45 或 60 分钟；
- 实时只显示一道题，不提前泄露答案或评分点；
- 反馈引用候选人回答或证据，不做性格猜测；
- 每个修复动作都有验证问题或工件；
- 重复失败写回 `weaknesses.md`。

## 求职看板

- `career-state.json` 是唯一事实源，Markdown 和网页状态摘要与其 digest 一致；
- 每次投递、回复、面试和 Offer 追加事件或更新对应对象，不抹掉过去过程；
- 每个进行中事项有明确下一步，同一岗位只进入行动队列一次；
- Offer 截止、待面试与待复盘优先于普通准备动作；
- 漏斗按岗位去重，不把未投递拒绝计入已投递；
- 网页桌面与移动端无横向溢出、重叠、裁切或不可读文本；
- 不生成、不验证、不依赖 XLSX。

```bash
python3 <skill-dir>/scripts/validate_workspace.py <workspace-dir> --require-dashboard
```

## 完成报告

用中文报告：运行了哪些门禁、检查了哪些产物、哪些仍是草稿、哪些仍 planned、下一步最多 3 项。不要用一个总分掩盖具体失败。
