# Offer 求职运营

本文件定义岗位发现、投递、面试和 Offer 的单一状态闭环。目标是推进真实岗位，不用准备动作替代结果。

## 唯一事实源

`career-state.json` 保存：

- 目标 Offer：岗位方向、城市、底线、目标日期；
- 岗位：公司、岗位、来源、优先级、匹配判断、缺口、状态和下一步；
- 事件：投递、回复、跟进、拒绝等历史；
- 面试：轮次、日期、状态、重点、结果和复盘；
- Offer：职级、现金、股权、奖金、条件、截止日期、风险和决策状态。

`application-dashboard.md` 与 `outputs/career-dashboard/index.html` 都是派生产物。只使用脚本更新，不直接维护三份状态。

## 定义目标 Offer

```bash
python3 <skill-dir>/scripts/career_ops.py <workspace-dir> set-target \
  --roles "Agent 开发工程师,Agent 平台工程师" \
  --locations "上海,杭州" \
  --minimum-offer "岗位方向匹配，薪资不低于当前总包" \
  --deadline 2026-09-30
```

## 添加与判断岗位

当用户要求找岗位时，Agent 先搜索当前有效的公司招聘页、官方职位页或可信招聘来源，再把 5-10 个真实 JD 保存到 `jd-bank/` 并写入岗位队列。每条岗位必须有可访问 URL、发现日期和来源；不要用过期聚合摘要或虚构职位填充岗位池。

选择顺序：满足硬门槛的岗位优先，然后比较证据匹配、成长价值、渠道强度、截止时间和准备成本。弱匹配岗位不因公司名气自动获得高优先级。

```bash
python3 <skill-dir>/scripts/career_ops.py <workspace-dir> add-job \
  --id company-agent-dev --company 公司名 --role "Agent 开发工程师" \
  --url https://example.com/job --source 内推 --priority high --fit strong \
  --fit-reasons "RAG 经验匹配,Python 工程能力" --gaps "生产监控经验"
```

- `priority`：`high / medium / low`，说明是否值得投入时间。
- `fit`：`strong / possible / weak / unknown`，必须由具体匹配和缺口支持。
- 没有真实 JD 时不要制造岗位；只有材料准备时不要假装已经投递。

## 记录真实进展

```bash
# 投递或回复
python3 <skill-dir>/scripts/career_ops.py <workspace-dir> record-event \
  --job-id company-agent-dev --type applied --date 2026-08-12 --note "官网投递"

# 面试安排
python3 <skill-dir>/scripts/career_ops.py <workspace-dir> add-interview \
  --id company-agent-dev-r1 --job-id company-agent-dev --round 技术一面 \
  --date 2026-08-16 --focus "项目深挖、Agent 评测与失败处理"

# 面试结果
python3 <skill-dir>/scripts/career_ops.py <workspace-dir> update-interview \
  --id company-agent-dev-r1 --status passed --result "通过，进入下一轮" \
  --review-path outputs/interview/company-agent-dev-r1.md

# Offer
python3 <skill-dir>/scripts/career_ops.py <workspace-dir> add-offer \
  --id company-agent-dev-offer --job-id company-agent-dev --level P6 \
  --cash "45k x 15" --deadline 2026-08-22 --risks "股权尚未写入书面 Offer"
```

事件类型支持：`sourced`、`materials_ready`、`referred`、`applied`、`response`、`interview_scheduled`、`interview_passed`、`interview_failed`、`offer`、`rejected`、`follow_up`、`withdrawn`、`note`。

## 下一最佳动作

优先级必须遵循：

1. 临近截止的 Offer 比较和谈判；
2. 待进行面试与尚未复盘的已结束面试；
3. 已收到回复、材料待投递或面试阶段待确认事项；
4. 已投递但需要跟进的岗位；
5. 新岗位适配判断和岗位池扩充。

同一岗位只占一个最高价值行动，避免低价值事项挤占今日队列。

## 转化口径

漏斗按不同岗位去重：目标岗位、已投递、有回复、进面试、Offer。拒绝本身不能证明发生过投递，必须有投递事件或后续阶段证据。没有样本时显示数量，不伪造成功概率。

## 验收

```bash
python3 <skill-dir>/scripts/career_ops.py <workspace-dir> render
python3 <skill-dir>/scripts/validate_workspace.py <workspace-dir> --require-dashboard
```

验收必须确认 JSON、Markdown 和网页属于同一状态快照；桌面与移动端无重叠、横向溢出或不可读文字。
