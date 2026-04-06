# Andrej Karpathy Research 01: Writings

- Owner: main agent
- Scope: 著作、长文、课程页、项目说明、系统化写作
- Status: completed

## Primary-source findings

1. **官网自述把他的身份稳定地压缩成三件事**：训练大模型、做清晰教学、做小而清楚的工具。`karpathy.ai` 首页第一句就是 “I like to train deep neural nets on large datasets”，后面同时列出教学、pet projects、论文、课程与工具。

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
   - `microgpt` 页面写着 “The most atomic way to train and run inference for a GPT in pure, dependency-free Python.”
   - 这不是单纯教学偏好，而是他的理解方法：先找到最小可运行核心，再回到工业规模。

7. **Eureka Labs 进一步把他的写作母题推向“AI-native 教育”**。
   - 官方页把产品定义成 “an AI-native school”，不是普通在线课平台。
   - 这和他长期的公开写作一脉相承：真正有价值的不是内容堆砌，而是把复杂系统教到可运行。

8. **他长期偏爱“小而清楚的个人软件”**。
   - 主页和 blog #3 都强调纯 HTML/CSS、无框架、无分析、无 RSS 的极简做法。
   - `ulogme` 的理由也不是“功能更多”，而是隐私和可控性。
   - 这表明他不仅推崇“更强”，也推崇“更薄、更透明、更能被单人完全理解”。

## Secondary-source findings

- TIME 2024 的画像与一手材料高度一致：它把 Karpathy 定义为“可能最大的影响不来自研究，而来自教育”，并记录他“obsessed with coming to the core of things”。
- 这与官网、课程、from-scratch 项目、Eureka Labs 形成交叉验证。

## Candidate recurring ideas

1. **泄漏抽象优先级**：AI/NN 不是稳定黑箱，必须回到数据、损失、可视化和训练动态。
2. **从零构建以压缩理解**：真正理解一个系统，最好先亲手做一个小而完整的版本。
3. **范式重构能力**：他擅长把技术变化描述为软件栈迁移，而不是工具升级。
4. **工具化教学**：课程、demo、toy project、轻量软件，本质上都是“把复杂能力压缩成可学习结构”。
5. **极简可控工程审美**：偏好简单、私有、轻量、自己能完全看懂的系统。

## Sources

### Primary
- `https://karpathy.ai/` - 官网主页与个人时间线，高可信一手
- `https://karpathy.ai/blog/ai-tools-ecosystem-2025` - 官网聚合页，列出写作、演讲、项目、时间线
- `https://karpathy.ai/blog/index.html` - 主页式目录，补充最新 blog #3 入口
- `https://karpathy.ai/blog` - Blog #3，含 2023-12-27、2024-09-08、2024-12-16 的新帖
- `https://karpathy.ai/zero-to-hero.html` - Zero to Hero 课程页
- `https://karpathy.ai/microgpt.html` - `microgpt` 页面
- `https://karpathy.github.io/2019/04/25/recipe/` - A Recipe for Training Neural Networks
- `https://karpathy.medium.com/software-2-0-a64152b37c35` - Software 2.0
- `https://karpathy.github.io/2016/09/07/phd/` - A Survival Guide to a PhD
- `https://karpathy.github.io/2015/05/21/rnn-effectiveness/` - The Unreasonable Effectiveness of Recurrent Neural Networks
- `https://eurekalabs.ai/` - Eureka Labs 官方页

### Secondary
- `https://time.com/7012851/andrej-karpathy/` - TIME100 AI profile, 2024-09-05

## Confidence Notes

- 高置信：关于写作母题、技术审美、from-scratch 方法、教学取向，均有多篇一手材料交叉验证。
- 中置信：把这些材料进一步提炼成“工具化教学”与“极简可控工程审美”这两个候选模型，属于基于多源证据的归纳。
- 信息缺口：未发现公开、稳定、系统的“推荐书单”；不应编造其阅读谱系细节。
