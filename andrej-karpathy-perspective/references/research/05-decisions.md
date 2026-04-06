# Andrej Karpathy Research 05: Decisions

- Owner: main agent
- Scope: 重大决策、职业转折、行动记录
- Status: completed

## Decision records

1. **2015-12-11: 作为 founding member 加入 OpenAI**
   - 背景：深度学习拐点期，研究与组织形态都在重组。
   - 信号：选择站在新实验室范式上，而不是只留在学术路径。
   - 揭示：他偏好“范式刚切换、杠杆很高”的位置。

2. **2017: 从 OpenAI 转去 Tesla，负责 Autopilot / 视觉团队**
   - 背景：从更偏研究环境转向现实世界、数据闭环、硬件部署。
   - 信号：愿意把模型能力扔进最脏、最难、反馈最真实的工业场景。
   - 揭示：他不满足于 benchmark 或 demo，更在意真实闭环与规模部署。

3. **2022-07-13: 离开 Tesla**
   - 公开表述偏温和，但后续路径清楚显示他在重新对齐个人重心：更多技术、开源、教学与个人项目。
   - 揭示：当组织角色开始偏离“亲手理解和构建系统”时，他会重新校准。

4. **2023-02 至 2024-02: 回到 OpenAI，建立新团队做 midtraining 和 synthetic data generation**
   - 截至 2026-03-16 的官网新版主页直接这样表述。
   - 这说明他回归后关注的不只是产品接口层，更是训练中段与数据生成这类“底层但高杠杆”的系统问题。
   - 揭示：他会在重要技术平台跃迁期回到一线。

5. **2024-02-13: 再次离开 OpenAI**
   - 路透系报道指出他离开去做 “personal projects”。
   - 随后 2024-07-16 推出 Eureka Labs，说明“personal projects”并非退场，而是转向更 personally meaningful 的教育/工具建设。

6. **2024-07-16: 创立 Eureka Labs**
   - 把长期的教学冲动、AI 工具判断、公开知识基础设施感合到一个新组织里。
   - 揭示：他把“前沿 AI 能力”与“学习系统重构”视为同一时代问题的两面。

7. **2025-10-13: 公开 `nanochat`，把 LLM 训练流程压成单机、低成本、可完整持有的实验 harness**
   - 不是做又一个大而全框架，而是刻意做 “the simplest experimental harness for training LLMs”。
   - 揭示：他在 2025-2026 的一个关键决策是继续压缩控制面，让更多人完整摸到训练链路。

8. **2026-03: 公开 `autoresearch`，把 agent 自治实验限制在单文件、单指标、固定 5 分钟 budget 的搜索循环里**
   - 这不是把研究完全交给 AI，而是把 autonomy 放到可测量、可回滚、可审计的边界里。
   - 揭示：他现在对 autonomy 的态度更精细了，不是“让 agent 乱跑”，而是“当 loop 足够紧时，把 agent 放进去”。

9. **2026-02-12 至 2026-04-06: 公开 `microgpt` 并持续更新 gist**
   - 这是一个明显的品味型决策：宁可反复提炼到 200 行，也不去堆一个更花哨的教学框架。
   - 揭示：他把“压缩解释成本”本身看成重要创作目标。

10. **2026-03 至 2026-04: 在 X 上系统推进 `org code`、`bigger IDE`、`LLM knowledge bases`、`idea files`、`file over app` 这一组观点**
   - 这些不是零散感想，而是围绕 agent 时代软件与知识控制面的重新定义。
   - 揭示：他最近一个非常明确的决策，是把人类从“编辑文件的人”进一步上移为“设计 artifact / loop / org code 的人”。

## Likely heuristics revealed

1. **去拐点处，而不是去稳定区。**
   - OpenAI 2015、Tesla 2017、OpenAI 2023、Eureka Labs 2024 都发生在技术与组织范式切换处。

2. **优先选择反馈最真实的环境。**
   - 学术 -> OpenAI -> Tesla -> OpenAI/ChatGPT -> Education tooling，路径都在逼近真实用户与真实闭环。

3. **一旦角色离“亲手构建与理解系统”太远，就会重置。**
   - 两次离开大组织之后，他都转向更小、更能直接触碰核心的工作。

4. **教育不是副业，而是主策略。**
   - CS231n、Zero to Hero、Eureka Labs 不是零散输出，而是持续十年的同一条线。

5. **当评估函数清晰时，提高自治密度。**
   - `autoresearch` 说明他并不教条地坚持 human-in-the-loop；他会在“目标单一、反馈快、可回滚”的环境里主动把循环交给 agent。

6. **把复杂系统压成少数关键旋钮。**
   - `nanochat` 的单一 `--depth` 复杂度旋钮、`autoresearch` 的 `program.md` / `train.py` 双文件结构，都体现了这一点。

7. **把知识和记忆落成显式文件，而不是留在黑箱里。**
   - 2026-04 的 knowledge base / file-over-app 观点显示，他不仅对代码这样想，对个人化记忆与长期上下文也这样想。

## Action vs stated-belief alignment

- **对齐很强**：他说自己想来到底层、想把复杂东西讲清楚，实际产物就是课程、from-scratch demo、轻量项目。
- **对齐很强**：他说软件范式在变，实际既做前沿模型工作，也公开讲 Software 2.0 / 3.0。
- **对齐很强**：他说系统应该薄、可控、可理解，2026 的 `microgpt`、`nanochat`、`autoresearch` 都在继续压缩控制面。
- **对齐很强**：他说 personalization 应该 explicit / inspectable / file-based，实际就在公开推动 markdown wiki、idea file、BYOAI 这种 artifact-first 路线。
- **存在张力**：他一边强调 human-in-the-loop，一边又开始认真实验更高自治密度的 `autoresearch`；这不是矛盾消失，而是边界被重新划分。

## Sources

### Primary
- `https://openai.com/index/introducing-openai/` - OpenAI founding page, 2015-12-11
- `https://karpathy.ai/` - 个人主页时间线
- `https://karpathy.ai/blog/ai-tools-ecosystem-2025` - 官网聚合页，时间线更完整
- `https://karpathy.ai/microgpt.html` - `microgpt` 页面
- `https://karpathy.github.io/2026/02/12/microgpt/` - `microgpt` guide
- `https://eurekalabs.ai/` - Eureka Labs official, 2024-07-16
- `https://github.com/karpathy/nanochat` - `nanochat` README
- `https://github.com/karpathy/nanochat/discussions/481` - `nanochat journey`, 2026-02-01
- `https://github.com/karpathy/autoresearch` - `autoresearch` README
- `https://x.com/karpathy/status/2031767720933634100` - Bigger IDE, 2026-03-11
- `https://x.com/karpathy/status/2031770607466291393` - Org code, 2026-03-11
- `https://x.com/karpathy/status/2039805659525644595` - LLM Knowledge Bases, 2026-04-02
- `https://x.com/karpathy/status/2040572272944324650` - File over app / BYOAI, 2026-04-04
- `https://x.com/karpathy/status/2040470801506541998` - Idea file, 2026-04-04

### High-credibility reporting
- `https://www.cnbc.com/2022/07/13/tesla-ai-leader-andrej-karpathy-announces-hes-leaving-the-company.html` - Tesla departure, 2022-07-13
- `https://www.investing.com/news/stock-market-news/openai-researcher-andrej-karpathy-departs-firm-3302797` - Reuters syndication of OpenAI departure, 2024-02-13
- `https://time.com/7012851/andrej-karpathy/` - TIME100 AI profile, 2024-09-05
- `https://ossinsight.io/blog/autoresearch-overnight-ai-scientist` - 外部社区对 `autoresearch` 的时间线与影响分析

## Confidence Notes

- 高置信：职业时间线和 2025-2026 的公开项目节点。
- 中置信：把这些节点抽象为“优先选择拐点、反馈闭环、亲手构建、在清晰指标里提高自治密度、把知识显式落盘”属于基于动作记录和 2026 X 观点的提炼。
- 注意：关于离职时的主观动机，只能在他公开表述与后续动作一致的范围内推断，不能编造内部原因。
