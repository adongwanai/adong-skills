# `curated.json` 策展输出契约（Schema v2）

Agent 读取 `collect_sources.py --dump-for-agent` 输出的候选事件池后，生成如下 JSON 文件传给 `render_report.py --curated <path>`。

> [!IMPORTANT]
> **防幻觉回填机制**：Agent 只需填写候选事件池中已存在的短 ID（如 `"N001"`），**无需手抄长 URL**。`render_report.py` 会自动根据 `id` 从候选池精确回填经过校验的多源 URL、点赞/Star 热度与共振媒体列表。

```json
{
  "date": "2026-11-27",
  "daily_take": "2-3句讲人话的当日核心主线判断（80-150字）：直接点出今天一手建设者、开源圈与产业界最集中的信号是什么。",
  "top_picks": ["N001", "N002", "N005", "N008"],
  "insights": [
    {
      "title": "简短有力的判断标题（10-20字，带明确结论）",
      "body": "150-240字具体拆解：串联2-4条当日真实新闻，讲清底层账本变化与工程启示，严禁公关套话。",
      "evidence_ids": ["N001", "N006", "N012"]
    }
  ],
  "items": [
    {
      "id": "N001",
      "category": "技术突破",
      "headline": "去震惊体后的清晰事实标题",
      "one_liner": "一句话讲清做了什么、核心数据或开源/商业细节（40-90字）",
      "adong_note": "可选（Top Picks 必填，其余有真知灼见再填，否则留空字符串）：一线工程师视角的简短点评"
    }
  ]
}
```

## 数量与质量自检清单
- `top_picks`：固定 **4 个** 最重磅/最高共振的条目 ID（且这 4 个 ID 必须包含在 `items` 中，并填写 `adong_note`）。
- `items`：总共精选 **28–45 条**（视当日有效信噪比而定，宁缺毋滥；每个有内容的分类精选 3–7 条，无内容分类直接留空不硬凑）。
- `insights`：**4–6 条** 深度趋势判断，每条 `evidence_ids` 中的 ID 必须存在于 `items` 列表内。
