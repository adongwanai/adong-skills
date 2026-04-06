# Andrej Karpathy Research 06: Timeline

- Owner: main agent
- Scope: 人物时间线、关键转折、最近 12 个月动态
- Status: completed

## Chronological timeline

- **2005 - 2009**: University of Toronto，本科双主修计算机科学与物理，辅修数学；在此接触 Geoff Hinton 的课程与读书会。
- **2009 - 2011**: University of British Columbia，MSc，研究物理模拟角色的控制器学习，偏向机器学习 + 机器人/控制。
- **2011 - 2015**: Stanford PhD，方向是 CNN/RNN 及其在视觉、NLP 与交叉领域的应用；导师 Fei-Fei Li。
- **2015**: 设计并主讲 Stanford 首门深度学习课 CS231n，之后迅速成为最受欢迎课程之一。
- **2015-12-11**: 作为 founding member 加入 OpenAI。
- **2017 - 2022**: Tesla Sr. Director of AI，负责 Autopilot 计算机视觉团队、数据标注、神经网络训练、生产部署。
- **2022-07-13**: 宣布离开 Tesla。
- **2023-02 至 2024-02**: 回到 OpenAI；截至 2026-03-16 的官网新版主页将这段经历表述为“built a new team working on midtraining and synthetic data generation”。
- **2024-02-13**: 再次离开 OpenAI，公开说去做个人项目。
- **2024-07-16**: 创立 Eureka Labs，定位为 AI-native school。
- **2024**: 公开内容重心明显转向 LLM 教学、实操、AI 工具与教育基础设施。
- **2025**: 继续以公开演讲和长对话方式讨论 Software 3.0、agent、AI coding 与人类监督问题。
- **2025-10-13**: 在 `nanochat` README 中将其定义为“the simplest experimental harness for training LLMs”，公开把训练 GPT-2 级别模型的成本和控制面压到更小。
- **2026-02-01**: 发布 `Beating GPT-2 for <<$100: the nanochat journey` 讨论串，系统公开当前训练路线和速度记录。
- **2026-02-12**: 发布 `microgpt` guide，把 GPT 压缩成单文件、约 200 行、无依赖的教学作品。
- **2026-03-06**: `autoresearch` 仓库上线；OSS Insight 后续分析以这一日期作为仓库创建时间。
- **2026-03-11**: 在 X 上连续发帖讨论 `bigger IDE`、`org code`、`intelligence brownouts`，把 agent 从“单工具”提升为“组织单元”和“新软件基本单位”。
- **2026-03-16**: `karpathy.ai` 首页快照显示其当下公开身份仍以 Eureka Labs 为主，同时加入了对 OpenAI 阶段“midtraining / synthetic data generation”的更精确表述。
- **2026-03-28**: 在 X 上强调 LLM 很擅长为任一方向论证，因此应主动要求它 `argue the opposite` 来帮助形成判断。
- **2026-03-31**: 针对 axios 供应链攻击发帖，公开表达对 package manager 默认策略和未 pin 依赖风险的强烈不满。
- **2026-04-02**: 发布 `LLM Knowledge Bases` 长帖，系统阐述 raw -> compiled markdown wiki -> Q&A -> linting 的知识工作流。
- **2026-04-04**: 连续发帖讨论 `file over app`、`BYOAI`、`idea file` 与 AI 辅助提升政府 legibility / accountability。
- **2026-04-06**: `microgpt.py` gist 仍在更新，显示这个“最原子 GPT”项目不是一次性演示而是持续打磨对象。

## Turning points and likely impact

1. **Toronto + Hinton**
   - 让他很早从物理/数学视角进入深度学习，而不是只从应用开发切入。

2. **Stanford + CS231n**
   - 奠定“研究 + 教学 +清晰表达”三位一体的公共形象。

3. **OpenAI 2015**
   - 进入 frontier lab 生态，开始更系统地参与范式切换本身。

4. **Tesla 2017**
   - 把思维重心进一步推向现实世界闭环、数据引擎和部署约束。

5. **OpenAI 回归 2023**
   - 进入 GPT-4 / ChatGPT 产品化核心层，强化对 LLM 时代软件栈迁移的判断。

6. **Eureka Labs 2024**
   - 把长期的教学冲动升级成组织级使命，说明教育在他心里不是 side quest。

7. **nanochat / microgpt / autoresearch 2025-2026**
   - 这组项目说明他的公开重心不只是“教别人理解 LLM”，而是“把训练、实验、研究循环都压缩成 hackable 系统”。

## Latest 12 months

- **2025-06-18**: Y Combinator 官方账号发布 `Andrej Karpathy: Software Is Changing (Again)`，视频说明写明这是他在 2025-06-17 AI Startup School 的 keynote。
- **2025-10-13**: `nanochat` 原始说明文将目标直接设为用极小控制面重现并超越 GPT-2 级别训练体验。
- **2025-10-17**: Dwarkesh 长访谈被官网列为 featured talk；内容集中在软件栈迁移、agent、世界模型、表征学习与人类监督。
- **2026-02-01**: `nanochat journey` 文档公开“<<$100 beating GPT-2”的路线与指标。
- **2026-02-12**: `microgpt` 长文上线，把 GPT 压成单文件教程。
- **2026-03-06**: `autoresearch` 启动，以单 GPU、单文件、单指标的 agent 自治实验循环切入研究自动化。
- **2026-03-11**: X 连续发帖提出 “the basic unit of interest is not one file but one agent” 和 `org code` 概念。
- **2026-03-28**: 用 “ask the LLM to argue the opposite” 总结自己当前使用 LLM 形成判断的方法。
- **2026-03-31**: 公开批评 npm / axios 供应链攻击暴露出的默认依赖管理问题。
- **2026-04-02**: `LLM Knowledge Bases` 长帖把他的新重心从 code manipulation 进一步推到 knowledge manipulation。
- **2026-04-04**: `file over app`、`BYOAI`、`idea file` 与政府 legibility 连续观点，显示他在 agent 时代越来越关注显式 artifact、控制面和社会可读性。
- **2026-03-16**: 官网快照更新了 OpenAI 阶段描述，并确认公开主线仍是 Eureka Labs + AI 教学 + hackable projects。
- **2026-04-06**: `microgpt.py` gist 仍在更新，说明其近期公开工作不仅是演讲，还有持续的最小实现迭代。

## Sources

### Primary
- `https://karpathy.ai/`
- `https://karpathy.ai/blog/ai-tools-ecosystem-2025`
- `https://karpathy.ai/microgpt.html`
- `https://karpathy.github.io/2026/02/12/microgpt/`
- `https://eurekalabs.ai/`
- `https://openai.com/index/introducing-openai/`
- `https://gist.github.com/karpathy/8627fe009c40f57531cb18360106ce95`
- `https://github.com/karpathy/nanochat`
- `https://github.com/karpathy/nanochat/discussions/481`
- `https://github.com/karpathy/autoresearch`
- `https://x.com/karpathy/status/2031767720933634100`
- `https://x.com/karpathy/status/2031770607466291393`
- `https://x.com/karpathy/status/2031792523187040643`
- `https://x.com/karpathy/status/2037921699824607591`
- `https://x.com/karpathy/status/2038849654423798197`
- `https://x.com/karpathy/status/2039805659525644595`
- `https://x.com/karpathy/status/2040572272944324650`
- `https://x.com/karpathy/status/2040470801506541998`
- `https://x.com/karpathy/status/2040549459193704852`

### High-credibility reporting / indexing
- `https://www.cnbc.com/2022/07/13/tesla-ai-leader-andrej-karpathy-announces-hes-leaving-the-company.html`
- `https://www.investing.com/news/stock-market-news/openai-researcher-andrej-karpathy-departs-firm-3302797`
- `https://www.youtube.com/watch?v=LCEmiRjPEtQ`
- `https://www.dwarkesh.com/p/andrej-karpathy`
- `https://ossinsight.io/blog/autoresearch-overnight-ai-scientist`

## Confidence Notes

- 高置信：2005-2026-04-06 的主线时间线，尤其是官网、gist、repo README 与 X 原帖明确记录的节点。
- 中置信：`nanochat` 原始说明文的“2025-10-13”作为项目起始公开节点，来自 repo 自述；不同镜像页面可能显示稍有差异。
- 明确边界：截至 2026-04-06，未发现 2026-04 之后的新重大公开节点；若之后有新创业、回归实验室或产品发布，此时间线未覆盖。
