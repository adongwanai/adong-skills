# kaggle-prior-art · 打比赛前先看别人怎么做过

一个面向 **Claude Code、OpenAI Codex、Antigravity、Cursor** 的数据科学竞赛先例研究 Skill。  
纯 Python 3.10+ 标准库实现，**零第三方 `pip` 依赖，不配 Kaggle Token 也能开箱即用**。

---

## 为什么要做这个

打 Kaggle（以及 DrivenData、天池等比赛）最浪费时间的，就是一上来闷头从零摸索。

绝大多数赛题——不管是带分组泄漏的医学影像、考 QWK 的文本评分、还是 9 小时禁网双 T4 的代码赛——往届早就有人拿过金牌了。真正管用的切分方式、Loss 改造和后处理全躺在历届的 Writeup、Discussion 和 GitHub 仓库里。但现实痛点也很明显：

1. **正在进行的比赛没有现成高分方案可抄**，有价值的线索全藏在名字完全不同的往届相似比赛里；
2. 直接问大模型“这个比赛怎么做”，十有八九给你背诵一套*“五折交叉验证 + LightGBM + 模型融合”*的万金油废话，顺带编几个根本打不开的 GitHub 链接，或者把别人占坑没传代码的空壳仓库推荐给你。

`kaggle-prior-art` 干的事很纯粹：**在你写第一行训练代码前（或者赛中卡分时），帮你把本赛和往届相似比赛摸个底朝天。**

---

## 它做什么，刻意不做什么

| 维度 | 说明 |
|---|---|
| **它做的事** | 提取比赛指纹（任务、模态、指标、提交与外部数据限制）→ 跨 700+ 场往届比赛检索金牌方案帖与代码 → 自动体检 GitHub 仓库可复现性 → 输出**方案对比表、共识底座（标命中率）、高 ROI 差异化 Trick、避坑黑名单、开局前 48h 验证单** |
| **刻意不做 ①：不拍脑袋写最终方案** | 正式方案取决于你的真实数据分布和本地 CV 结果。没看数据就写出来的“四周冲金计划”只是往届 Trick 的拼贴。本 Skill 只把弹药库和 **EDA 必查假设** 交到你手上 |
| **刻意不做 ②：不重复单赛提交基建** | 下载数据、拉取复现公开 Kernel、提交预测交给 [`NVIDIA/nvidia-kaggle`](https://github.com/NVIDIA/nvidia-kaggle) 或 Kaggle MCP；本 Skill 专门补齐它们没有的**跨赛先例检索、正交拆解与方案排雷** |

---

## 用户体验：装好之后怎么用（3 种高频场景）

不用记任何命令行参数，装进 Agent 后直接说人话即可自动切换模式：

### 场景 1：刚进新比赛开荒（全景作战地图）
> **你直接说**：
> - `帮我摸一下这个比赛的底：https://www.kaggle.com/competitions/learning-agency-lab-automated-essay-scoring-2`
> - 或只描述赛题：`有个脑电信号分布预测比赛，指标是 KL 散度，禁网 9 小时双 T4 代码赛，往届类似比赛怎么打的？`

**你会拿到**：
- **30 秒速览卡**：比赛指纹 + **历史公私榜洗牌（Shake-up）风险灯** + 起步 Baseline + 头号避坑红线；
- **正交拼图检索**：就算赛题很新、找不到一模一样的往届赛，也会自动拆成 **A 路（同模态借特征与骨干）+ B 路（同指标借 Loss 与后处理）**；
- **去套话的硬核结论**：每条共识标明 `n/N` 金牌采用率（并区分“不过时的机制”与“需换代的旧模型底座”）；每条差异化 Trick 按 **预期涨分 ÷ 实现成本（ROI）** 排序；
- **开局前 48 小时验证单**：跑哪个公开 Baseline 对齐管线、EDA 必查哪 2–3 个防泄漏假设。

👉 完整输出效果可直接看真实样例：**[examples/automated-essay-scoring-2.md](./examples/automated-essay-scoring-2.md)**

### 场景 2：赛中卡分救急（单点瓶颈深挖）
> **你直接说**：
> - `我现在本地 CV 涨了 0.012 但公榜掉了 0.008，往届同类比赛怎么排查 CV-LB 不一致？`
> - `QWK / pAUC / Balanced LogLoss 这个指标有哪些不重训模型就能涨分的后处理？`
> - `双 T4 9 小时跑不完 4 个 DeBERTa 融合，往届代码赛怎么压推理时间？`

跳过基础科普，直接跨 5–8 场同指标/同约束比赛把这一个卡点的顶配做法、代码位置与涨分数字挖透。

### 场景 3：开源方案代码排雷（防空壳、查依赖、看协议）
> **你直接说**：
> - `帮我核验这几个往届冠军 GitHub 仓库能不能复现，许可证和本赛规则冲不冲突：<链接...>`

内置脚本自动过滤 `404` 幻觉链接、揪出只放了 README 写 `"Code coming soon"` 的**空壳占坑仓库（`PLACEHOLDER_NO_CODE`）**、检查是否包含训练脚本/推理脚本/环境依赖，并标记 `AGPL/GPL` 等强传染性协议风险。

---

## 一键安装

### 方式一：用 `skills` CLI 安装（推荐）

```bash
npx skills add adongwanai/kaggle-prior-art -g
```

*(若从合集仓库安装：`npx skills add adongwanai/adong-skills --skill kaggle-prior-art -g`)*

### 方式二：Git Clone 软链安装（方便随时 `git pull` 更新）

```bash
git clone https://github.com/adongwanai/kaggle-prior-art.git
cd kaggle-prior-art

# Claude Code
ln -sfn "$(pwd)" ~/.claude/skills/kaggle-prior-art

# OpenAI Codex
ln -sfn "$(pwd)" ~/.codex/skills/kaggle-prior-art

# Antigravity / Gemini CLI
ln -sfn "$(pwd)" ~/.gemini/config/skills/kaggle-prior-art
```

### 可选增强配置（不配也能用）
- `GITHUB_TOKEN`：可选环境变量，将 GitHub 仓库体检限额从 60 次/小时提升至 5000 次/小时；
- `kaggle` CLI / `NVIDIA/nvidia-kaggle` / Kaggle MCP：可选，用于读取实时榜单或下载官方 `Meta Kaggle` 全量 CSV 做深度离线检索。

---

## 独立命令行工具（不通过 Agent 也能单独跑）

仓库 `scripts/` 下的两个脚本均只用 Python 标准库，可以直接在终端当独立科研小工具跑：

### 1. 跨赛与金牌方案检索 `scripts/meta_kaggle_search.py`

```bash
# 零配置秒查（自动拉取并缓存 700+ 场整理好的赛事方案库到 ~/.cache/kaggle-prior-art/）
python3 scripts/meta_kaggle_search.py --keywords essay scoring --metric qwk --since-year 2021 --solutions

# 若本地下载了官方 Meta Kaggle 数据集（支持 .csv 与未解压的 .csv.zip），可开启双引擎合并与洗牌风险计算：
# kaggle datasets download kaggle/meta-kaggle -f Competitions.csv -p ~/.cache/kaggle-prior-art/meta
# kaggle datasets download kaggle/meta-kaggle -f ForumTopics.csv -p ~/.cache/kaggle-prior-art/meta
# kaggle datasets download kaggle/meta-kaggle -f Teams.csv -p ~/.cache/kaggle-prior-art/meta
python3 scripts/meta_kaggle_search.py --source both --data-dir ~/.cache/kaggle-prior-art/meta \
    --keywords brain eeg --metric kl --solutions --shakeup
```

### 2. 竞赛代码仓库体检 `scripts/github_check.py`

```bash
python3 scripts/github_check.py \
    nimashahbazi/optiver-trading-close \
    https://github.com/kentaroy47/Kaggle-PANDA-1st-place-solution
```

---

## 目录结构

```text
kaggle-prior-art/
├── SKILL.md                           # Agent 核心执行 SOP（三模式路由 + 五条铁律 + 输出模板）
├── scripts/
│   ├── meta_kaggle_search.py          # 免配置方案索引 + Meta Kaggle 双引擎检索与洗牌雷达
│   └── github_check.py                # 竞赛仓库真实性、许可证与可复现性文件树体检
├── references/
│   ├── metric-and-cv-playbook.md      # 常见竞赛指标 → Loss / OOF 后处理映射与防泄漏 CV 速查表
│   └── sources-and-ecosystem.md       # 全平台信源目录（Kaggle/DrivenData/顶会/天池）与 MCP 分工
├── examples/
│   └── automated-essay-scoring-2.md   # 真实比赛先例研究报告样例
└── tests/                             # 离线可跑的完整单元测试套件
```

## 运行测试

```bash
pytest -v
```

## License

[MIT License](./LICENSE)
