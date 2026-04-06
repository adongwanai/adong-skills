# Andrej Karpathy Research 01: Writings

- Owner: main agent
- Scope: 著作、长文、课程页、项目说明、系统化写作
- Status: completed

## Primary-source findings

1. **截至 2026-03-16 的官网自述，把他的身份稳定地压缩成三件事**：训练大模型、做清晰教学、做小而清楚的工具。`karpathy.ai` 首页第一句仍然是 “I like to train deep neural nets on large datasets”，并且新版主页把 2023-2024 在 OpenAI 的工作明确写成“built a new team working on midtraining and synthetic data generation”。

2. **《A Recipe for Training Neural Networks》反复强调“深度学习是高度泄漏的抽象”**。
   - 关键不是背最佳实践，而是接受训练过程会静默失败、指标会误导、bug 会藏在数据和配置里。
   - 他主张从最小基线开始，逐步增加复杂度，像侦探一样定位问题。
   - 这是 Karpathy 最稳定的工程世界观之一：复杂系统先做成可解释，再做成强大。

3. **《Software 2.0》体现了他最有辨识度的范式重构能力**。
   - 他把神经网络描述为“写不出来但能优化出来的程序”。
   - 这不是单点观点，而是他后来谈 LLM、提示词、agent、教育工具时的母框架：代码的“所在地”在迁移，工程师的工作也随之迁移。

4. **《The Unreasonable Effectiveness of Recurrent Neural Networks》体现了他解释新技术时的习惯动作**。
   - 他把 RNN 写成一种“可运行的程序性系统”，用样例和生成现象让抽象模型变成可感知对象。
   - 这和他后来做 `char-rnn`、`micrograd`、Zero to Hero 的路线一致：先把黑箱拆成一个能在脑中执行的小系统。

5. **《A Survival Guide to a PhD》把他的“技术思维”外溢到职业与制度层面**。
   - 他不只讲模型，也讲导师选择、课题选择、激励结构、野心与可攻击性之间的平衡。
   - 说明他的认知框架并不只服务于训练模型，也服务于选择“值得下注的问题”。

6. **Zero to Hero 和 `microgpt` 说明他偏爱“从零、从薄、从可执行样例出发”的教学方法。**
   - `zero-to-hero` 课程直接写明“building neural networks, from scratch, in code”。
   - 2026-02-12 的 `microgpt` guide 把它描述成“a single file of 200 lines of pure Python with no dependencies”，并明确说这是他“a decade-long obsession to simplify LLMs to their bare essentials”。
   - `microgpt` 页面与 2026-04-06 仍在更新的 gist 都重复同一句话：“This file is the complete algorithm. Everything else is just efficiency.”
   - 这不是单纯教学偏好，而是他的理解方法：先找到最小可运行核心，再回到工业规模。

7. **`nanochat` 把他的极简主义从“解释模型”推进到“解释整条 LLM 训练链”**。
   - README 直接称它是 “the simplest experimental harness for training LLMs”。
   - 它故意把控制面压成一个主要旋钮：`--depth`，并让其他超参自动按 compute-optimal 方式派生。
   - 这说明他不只喜欢“从零实现”，还喜欢把复杂工程压到一个能被人类完整持有的单一控制界面。

8. **`autoresearch` 说明他 2026 年开始把“最小可理解系统”进一步推到“最小可理解研究循环”**。
   - README 的核心思想不是让人手写所有 Python，而是让人写 `program.md`，让 agent 在受约束环境里改 `train.py`、训练 5 分钟、看指标、保留或回滚。
   - 这等于把“写程序”上移为“写研究组织和评估边界”。
   - 说明他最近的写作母题已经从“程序是什么”扩展到“研究循环应该如何被编程”。

9. **Eureka Labs 进一步把他的写作母题推向“AI-native 教育”**。
   - 官方页把产品定义成 “an AI-native school”，不是普通在线课平台。
   - 这和他长期的公开写作一脉相承：真正有价值的不是内容堆砌，而是把复杂系统教到可运行。

10. **他长期偏爱“小而清楚的个人软件”**。
   - 主页和 blog #3 都强调纯 HTML/CSS、无框架、无分析、无 RSS 的极简做法。
   - `ulogme` 的理由也不是“功能更多”，而是隐私和可控性。
   - 这表明他不仅推崇“更强”，也推崇“更薄、更透明、更能被单人完全理解”。

11. **2026 年 4 月的 X 长帖把他的写作母题从“简化模型”扩展到“简化知识系统”**。
   - 他提出用 LLM 把 `raw/` 目录中的 papers、repos、images、articles “compile” 成一个 markdown wiki。
   - 核心不是炫技式 RAG，而是让知识变成显式、可审计、可被 agent 继续操作的文件系统。
   - 这和他此前的 `microgpt` / `nanochat` 一样，本质都是把复杂系统压成 inspectable artifacts。

12. **2026 年 4 月的 “idea file” 和 “file over app” 观点进一步揭示了他的新偏好：分享 idea 和 artifact 胜过分享封装好的 app。**
   - 他认为在 agent 时代，分享一个想法本身就足够，因为别人的 agent 可以按自己的上下文把它实现出来。
   - 这说明他最近越来越把“高层控制面”当作真正有价值的产物。

## Secondary-source findings

- TIME 2024 的画像与一手材料高度一致：它把 Karpathy 定义为“可能最大的影响不来自研究，而来自教育”，并记录他“obsessed with coming to the core of things”。
- 这与官网、课程、from-scratch 项目、Eureka Labs 形成交叉验证。

## Candidate recurring ideas

1. **泄漏抽象优先级**：AI/NN 不是稳定黑箱，必须回到数据、损失、可视化和训练动态。
2. **从零构建以压缩理解**：真正理解一个系统，最好先亲手做一个小而完整的版本。
3. **范式重构能力**：他擅长把技术变化描述为软件栈迁移，而不是工具升级。
4. **工具化教学**：课程、demo、toy project、轻量软件，本质上都是“把复杂能力压缩成可学习结构”。
5. **极简可控工程审美**：偏好简单、私有、轻量、自己能完全看懂的系统。
6. **编程循环高于编程文件**：当反馈足够快、指标足够清楚时，他倾向于把人类工作上移到“定义 loop / metric / control surface”，而不是反复亲写每个细节。
7. **显式 artifact 优先于隐式记忆**：如果知识、记忆、工作流能落到 markdown / files / inspectable repo 中，他会明显更偏爱这种形式。

## Sources

### Primary
- `https://karpathy.ai/` - 官网主页与个人时间线，高可信一手
- `https://karpathy.ai/blog/ai-tools-ecosystem-2025` - 官网聚合页，列出写作、演讲、项目、时间线
- `https://karpathy.ai/blog/index.html` - 主页式目录，补充最新 blog #3 入口
- `https://karpathy.ai/blog` - Blog #3，含 2023-12-27、2024-09-08、2024-12-16 的新帖
- `https://karpathy.ai/zero-to-hero.html` - Zero to Hero 课程页
- `https://karpathy.ai/microgpt.html` - `microgpt` 页面
- `https://karpathy.github.io/2026/02/12/microgpt/` - `microgpt` 长文导读，2026-02-12
- `https://gist.github.com/karpathy/8627fe009c40f57531cb18360106ce95` - `microgpt.py` gist，2026-04-06 仍在更新
- `https://karpathy.github.io/2019/04/25/recipe/` - A Recipe for Training Neural Networks
- `https://karpathy.medium.com/software-2-0-a64152b37c35` - Software 2.0
- `https://karpathy.github.io/2016/09/07/phd/` - A Survival Guide to a PhD
- `https://karpathy.github.io/2015/05/21/rnn-effectiveness/` - The Unreasonable Effectiveness of Recurrent Neural Networks
- `https://eurekalabs.ai/` - Eureka Labs 官方页
- `https://github.com/karpathy/nanochat` - `nanochat` README 与当前训练路线
- `https://github.com/karpathy/nanochat/discussions/481` - `Beating GPT-2 for <<$100: the nanochat journey`, 2026-02-01
- `https://github.com/karpathy/autoresearch` - `autoresearch` README，2026-03
- `https://github.com/karpathy` - GitHub profile，2026-04 快照
- `https://x.com/karpathy/status/2039805659525644595` - LLM Knowledge Bases, 2026-04-02
- `https://x.com/karpathy/status/2040572272944324650` - File over app / BYOAI thread, 2026-04-04
- `https://x.com/karpathy/status/2040470801506541998` - Idea file post, 2026-04-04

### Secondary
- `https://time.com/7012851/andrej-karpathy/` - TIME100 AI profile, 2024-09-05

## Confidence Notes

- 高置信：关于写作母题、技术审美、from-scratch 方法、教学取向，以及 2026 年新增的 loop-first / minimal-harness / explicit-artifact 取向，均有多篇一手材料交叉验证。
- 中置信：把这些材料进一步提炼成“编程循环高于编程文件”和“显式 artifact 优先于隐式记忆”这两个候选模型，属于基于 `microgpt`、`nanochat`、`autoresearch` 与 2026 X 长帖的归纳。
- 信息缺口：未发现公开、稳定、系统的“推荐书单”；不应编造其阅读谱系细节。
