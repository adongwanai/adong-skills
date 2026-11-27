## Learning Agency Lab - Automated Essay Scoring 2.0：先例研究作战地图（样例报告）

> **说明**：本文件展示当参赛者在比赛**进行中**输入比赛链接时，`kaggle-prior-art` 生成的标准先例研究报告样式（所有往届比赛与方案帖链接均经 `scripts/meta_kaggle_search.py` 实测检索核验）。

> **30 秒速览**
> - **比赛指纹**：文本评分（有序等级 1–6 分） / 长文本 NLP（学生议论文，部分超 512–1024 tokens） / 评估指标 **Quadratic Weighted Kappa (QWK)** / 约 1.7 万篇训练作文（含原 Persaude 语料与新增样本混合） / **禁网 9 小时代码赛（双 T4 GPU）** / 允许合规开源预训练模型与公开外部数据（需在官方帖报备）
> - **赛事假设视角**：开赛初期开荒 · **历史洗牌风险**：`🟡 中高波动`（QWK 阈值后处理在小测试集或新写作题目 `prompt_id` 切换时极易发生公私榜漂移，严禁对着公榜微调切分阈值）
> - **推荐起步 Baseline**：本赛 Code 区按票数靠前的 `DeBERTa-v3-small/large Regression + Nelder-Mead QWK Threshold` 公开推理管线（先跑通离线挂载权重 + 长度排序动态 Padding 提交流程）
> - **头号避坑提醒**：训练集混有旧竞赛语料（Persuade 2.0）与主办方新采集语料，**两批数据的评分尺度（分布均值）存在系统性偏移**，不区分来源直接随机 KFold 会导致本地 CV 失真且阈值搜偏。

---

### 1. 往届高价值方案对比表（双路检索：同任务 NLP + 同指标 QWK）

| 来源（往届比赛 + 年份） | 私榜名次 | 匹配维度与相似度 | CV 切分策略 | 模型底座（含换代建议） | 核心涨分 Trick | 后处理与集成 | 方案出处（已核验存在） | 本赛可迁移性 |
|---|---|---|---|---|---|---|---|---|
| **Feedback Prize - English Language Learning**（2022） | 金牌区前排共识 | 同任务（学生作文评分）9/12 | `MultilabelStratifiedKFold` / 按 `prompt` 留出验证 | `DeBERTa-v3-large` 多种池化头（Mean / Attention / Weighted Layer Pooling） | 长文本 `max_length=1024/1536` 不截断关键结尾段；AWP 对抗权重扰动防过拟合；多折伪标签 | 线性回归 / Nelder-Mead 融合多头特征输出 | [Competition Archive](https://www.kaggle.com/competitions/feedback-prize-english-language-learning) | `🟢 可直接迁移`（骨干仍是长文本中小规模首选，需控总折数适配 9h） |
| **Linking Writing Processes to Writing Quality**（2024） | 1st–4th | 同领域（议论文质量预测）8/12 | 5/10-Fold StratifiedKFold（多随机种子稳定 OOF） | `DeBERTa-v3` 文本语义提取 + `LightGBM / CatBoost / MLP` 统计特征融合 | **手工统计特征与深度表征互补**：段落数、句长方差、拼写错误率、高频连接词密度、TF-IDF n-gram 奇异值 | Ridge / ElasticNet 两层 Stacking（异构模型增益显著高于纯同构大模型） | [1st](https://www.kaggle.com/c/linking-writing-processes-to-writing-quality/discussion/466873) · [2nd](https://www.kaggle.com/c/linking-writing-processes-to-writing-quality/discussion/466775) · [3rd](https://www.kaggle.com/c/linking-writing-processes-to-writing-quality/discussion/466906) | `🟢 可直接迁移`（”DeBERTa OOF 分数 + 文本统计特征喂 GBDT”推理极快且稳） |
| **Child Mind Institute — Problematic Internet Use**（2024） | 1st–3rd | 同评估指标（**QWK**）7/12 | **Nested CV（嵌套验证）** 评估阈值泛化 | Tabular GBDT + MLP 异构集成 | 针对 QWK 离散分档特性的平滑回归目标与分布对齐 | **Nelder-Mead 优化阈值必须加正则或多次 Bootstrap 取中位数**，防止单次 OOF 搜索过拟合 | [1st](https://www.kaggle.com/c/child-mind-institute-problematic-internet-use/discussion/552638) · [2nd](https://www.kaggle.com/c/child-mind-institute-problematic-internet-use/discussion/552712) · [3rd](https://www.kaggle.com/c/child-mind-institute-problematic-internet-use/discussion/552677) | `🟢 可直接迁移`（B 路专借其 QWK 防洗牌阈值策略） |
| **AES 2.0 赛后归档对照**（2024，复盘验证用） | 1st–5th | 完全重合 12/12 | 按数据源（Kaggle-only vs Persuade）分层验证，重点盯 Kaggle-only OOF | `DeBERTa-v3-large`（多上下文窗口）+ 少量 `Qwen2/Mistral-7B LoRA` + `LightGBM/CatBoost` 二阶段 | **识别隐含数据源差异**：把“是否属于新采集样本”作为特征或两阶段精调（先全量预训，再 Kaggle-only 域精调） | GBDT 二阶段吃 DeBERTa 概率/回归值 + 词法特征，最后按目标分布做 QWK 阈值切分 | [1st](https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2/discussion/516791) · [3rd](https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2/discussion/517014) · [4th](https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2/discussion/516639) · [5th](https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2/discussion/516922) | `🟢 黄金标杆` |

---

### 2. 共识底座（前排方案高度一致的做法）

- **把离散 1–6 分当连续回归（或有序回归 + 期望值）训练，绝不直接拿 Argmax 分类交结果**（几乎 `100%` QWK 前排采用）：MSE / SmoothL1 / BCE-Ordinal 都能让模型学到“错 1 分比错 3 分惩罚小得多”的序数关系。
- **架构不是“纯大模型单打独斗”，而是 `DeBERTa OOF 预测特征 + 细粒度文本统计特征 → 二阶段 GBDT (LightGBM/CatBoost)`**（`5/6` 前排方案采用）：DeBERTa 擅长抓语义连贯度，但由于分词器归一化，往往对**段落换行符 `\n\n`、首尾句标点缺失、拼写错误数量、精确词数阶梯**不如手工特征 + GBDT 敏感；两者融合不仅稳涨 `CV +0.004~0.008`，而且 GBDT 推理耗时几乎为零。
- **长文本不能默认 `max_length=512` 一刀切**：议论文的总结段在文末，512 截断会丢掉核心论点收束，至少扩到 `1024`–`1536`，配合按测试文本长度排序组 Batch（Length-sorted Dynamic Padding）把 9 小时双卡推理提速 `2.5x+`。

---

### 3. 值得一试的差异化 Trick（按投入产出比 ROI 排序）

1. **[⚡ 极高 ROI · 30 行代码] 数据源域识别与分域验证（Source-aware Validation & Two-Stage Finetuning）**
   - **做法**：先通过开源 Persuade 2.0 语料比对切出训练集中哪些是旧语料、哪些是本赛独有新语料；CV 拆成全局 OOF 与 **本赛独有子集 OOF** 双指标监控，并尝试“全量训 → 新语料子集微调”或在模型输入前拼上数据源提示词。
   - **预期增益与开销**：决定公私榜对齐生死线（往届前 5 名胜负手），几乎零额外推理耗时（来源：[AES2 3rd](https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2/discussion/517014) / [4th](https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2/discussion/516639)）。
2. **[⚡ 高 ROI · 20 行后处理] 嵌套验证版 `OptimizedRounder` 阈值搜索**
   - **做法**：用 `scipy.optimize.minimize(..., method='Nelder-Mead')` 在 OOF 上搜索 5 个切分点把连续预测映射回 `1..6`，但**必须在每一折内部搜阈值测折外分数**验证是否真涨分，避免直接在单次 OOF 上过拟合极端分档。
   - **预期增益与开销**：相比四舍五入默认 `1.5, 2.5...` 通常稳定带来 `+0.005~0.012 QWK`，推理耗时 `< 1 秒`（来源：[CMI 1st](https://www.kaggle.com/c/child-mind-institute-problematic-internet-use/discussion/552638)）。
3. **[🔨 中高收益 · 需显存规划] 双 T4 双进程切卡并行 + 4-bit 量化 Decoder LLM 补充多样性**
   - **做法**：编码器家族（DeBERTa-v3）同构融合很快触顶，加入 1 个 QLoRA 微调的 7B/8B 模型（如 Qwen2.5-7B / Mistral-7B 4-bit 量化，双进程分别绑 `cuda:0` 和 `cuda:1` 各跑一半测试集）提供异构预测。
   - **迁移前提**：必须先实测单折在预估全量测试集上的耗时，严控在总预算 9 小时的 75% 以内（来源：[AES2 5th](https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2/discussion/516922)）。

---

### 4. 已知无效或高危的做法（避坑黑名单）

- ❌ **直接拿公榜反馈反复微调 5 个切分阈值**：QWK 对边界样本极敏感，公榜仅占测试集一小部分，对着公榜调阈值是历届 QWK 比赛私榜暴跌几百名的头号死因。
- ❌ **盲目清洗所有拼写错误和换行符**：在作文评分任务里，拼写错误率、标点规范度和自然段切分本身就是评分员打分的核心依据，“帮学生把错别字改对”反而抹掉了强判别信号！
- ❌ **只堆 5 个不同随机种子的同一款 `DeBERTa-v3-large`**：边际收益极低（常 `< +0.001`），却白白吃掉宝贵的 9h 代码赛推理配额。

---

### 5. 开局前 48 小时验证单（不拍脑袋定方案，先做这三步）

1. **跑通离线推理与双卡管线**：拉取一份干净的 `DeBERTa-v3-large` 离线推理 Baseline，确认按文本长度排序推理并还原原始 `essay_id` 顺序无误。
2. **EDA 必查的 3 个数据假设**：
   - [ ] **假设 1（域偏移）**：与公开 Persuade 2.0 语料做精确/近似文本匹配后，重叠样本与非重叠样本的分数分布（1–6 分占比）和篇幅分布差多少？
   - [ ] **假设 2（题目分组）**：能否通过文本聚类恢复隐含的写作题目（`prompt_id`）？测试集更像“已知题目的新作文”还是“全新未见题目”（决定用 `StratifiedKFold` 还是 `GroupKFold`）？
   - [ ] **假设 3（截断损耗）**：统计全量训练作文在 DeBERTa tokenizer 下的 token 长度分位数（P90 / P99），超过 `1024` tokens 的样本占多少？
3. **首个试金石实验**：搭好第一版可信 CV 后，先用最轻量的 `DeBERTa-v3-small + 基础词法段落统计特征 LightGBM` 验证二阶段架构是否稳定优于单模型。

---

### 6. 合规红线提醒
- **禁网代码赛**：提交 Notebook 禁用互联网访问，所有 HuggingFace 模型权重与第三方包（`.whl`）必须提前通过 Kaggle Datasets / Models 挂载；注意算足全量隐藏测试集重跑内存与 9 小时上限。
- **外部数据与模型许可证**：若引入 Persuade 2.0 等外部语料或开源大模型权重，须确认其开源协议符合本赛 Rules 要求并在官方 External Data 讨论帖确认合规性。

---

等你跑完上面 3 项 EDA 检查并搭好本地第一版 CV 后，把统计结果发我，要不要接着起草第一轮实验迭代方案？
