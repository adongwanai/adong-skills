# 竞赛评估指标、防泄漏 CV 与代码赛实战速查手册

> 本文件浓缩往届 Kaggle 金牌方案中最常跨赛复用的数学与工程规律，供 Step 1（指纹提取）、Step 2（正交检索 B 路）和 Step 4（综合提炼）参考。引用具体结论时仍须结合检索到的真实往届方案帖印证。

---

## 一、常见评估指标 → 训练 Loss 与专属后处理映射表

许多比赛的胜负手不在换更大的模型，而在于**训练目标与评估指标对齐**以及**零训练成本的 OOF 后处理**：

| 评估指标 | 训练阶段常见黄金搭配 | OOF / 推理阶段经典后处理（高 ROI 优先验证项） | 常见翻车坑 |
|---|---|---|---|
| **QWK (Quadratic Weighted Kappa)**（如作文评分、糖网分级） | 将离散等级当连续值做 **MSE / Smooth L1 回归**，或 Ordinal Regression（有序分类） | **Nelder-Mead / Powell 阈值搜索 (`OptimizedRounder`)**：在 OOF 连续预测值上拟合最优切分阈值替代固定 `0.5, 1.5, ...`；集成时先融连续值再卡阈值 | 小样本下直接在全量 OOF 上搜阈值极易过拟合公榜，必须用 **Nested CV（嵌套交叉验证）** 或固定先验分布比例搜阈值 |
| **F1 / Macro-F1 / MCC / Jaccard** | BCE / Focal Loss / Asymmetric Loss（极度不平衡或多标签场景） | **OOF 阈值寻优**：按类别或全局网格搜索最优分类概率阈值（远优于默认 `0.5`）；若正例率已知可按分位数（Percentile）卡截断 | 公私榜正负样本比例漂移时，固定概率阈值可能失效，需对比概率阈值 vs 预测正例比例约束 |
| **LogLoss / Balanced LogLoss / Brier Score** | 带 Label Smoothing 的 Cross-Entropy；类别极不平衡时对样本加权后必须做概率重校准 | **概率校准与极值裁剪（Clipping）**：Temperature Scaling（温度缩放）、Platt Scaling / Isotonic Regression；对极端预测做 `[eps, 1-eps]` 截断防单样本错判爆罚分 | GBDT 多折或异构模型直接算术平均概率会欠自信，常试 **Log-odds（logit 空间）加权融合** 或几何平均 |
| **ROC-AUC / pAUC（局部高 TPR 区 AUC）** | BCE、Pairwise Ranking Loss（针对 AUC/pAUC 直接优化排序对） | **融合前先做 Rank Averaging（秩平均）或按折 Z-score 标准化**！因为不同模型（如 GBDT 与 NN）输出的概率尺度不一致，直接概率相加会毁掉弱校准模型的排序贡献 | 对单模型做任何严格单调变换**不会**改变其 AUC，但会剧烈影响多模型加权融合后的 AUC |
| **MAP@K / NDCG@K / Recall@K**（推荐与检索） | 双塔/召回（Covisitation 共现矩阵 + 向量检索 + 热门规则）→ **二阶段 GBDT (LightGBM/CatBoost `lambdarank` / ` YetiRank`) 精排** | 候选池扩充（每路召回造 50–200 个候选并提取交叉共现特征、会话时间差特征、用户-物品交互频次比）；多排模型对打分按会话内归一化后再融合 | 只优化精排模型而忽略**召回率天花板（Recall@100）**——不在候选池里的正确样本精排永远救不回来；验证集必须按时间窗口切分模拟真实冷启动 |
| **KL Divergence（分布预测）**（如脑电 HMS、软标签赛题） | 直接用 **KLDivLoss** 拟合标注者投票概率分布（Soft Labels），而非转成硬标签做 Cross-Entropy；两阶段训练（先全量低票数样本预训练，再高票数高质量子集精调） | 温度系数微调平滑分布峰值，多模型在概率或 log-prob 空间凸组合并重归一化 | 忽略样本间总投票数（置信度）差异——低票数噪声样本与高一致样本等权训练会拖垮收敛 |
| **Pearson / Spearman 相关系数**（如专利语义匹配、金融因子） | **Cosine Similarity Loss / Pearson Correlation Loss** 或 MSE（对目标标准化后） | 按分组（如按 anchor / 按交易日截面）做均值归零与方差归一化；集成前统一各单模预测的均值与标准差 | 直接用逐样本 MSE 训练忽略了批次/分组内的相对均值偏移 |
| **Dice / Surface Dice / IoU（2D/3D 分割）** | **BCE + Dice Loss（或 Lovász-Softmax / Tversky Loss）组合** | 双阈值法（高阈值判是否存在前景 `p_exist`，低阈值切像素掩码）+ 连通域过滤剔除极小噪点 + 多尺度/翻转 **TTA (Test-Time Augmentation)** | 3D 医学体积直接按 2D 切片随机划分 train/val 会造成相邻切片严重跨折泄漏，必须按 `patient_id / case_id` 分组 |

---

## 二、CV 切分与防泄漏核查四问（EDA 必查清单模板）

90% 的“CV 虚高、上榜暴跌”都源于验证集切分没有对齐测试集的真实生成过程。输出报告第 5 节《EDA 必查假设》时，围绕以下四问结合赛题具体字段定制：

1. **实体重叠（Group Overlap）**：`train` 和 `test` 里的核心实体（`patient_id`、`user_id`、`site_id`、`prompt_id`、`molecule_scaffold`、`video_id`）是**完全互斥**还是**部分重叠**？
   - 若测试集全是未见新实体 → 必须用 `GroupKFold` / `StratifiedGroupKFold`；误用普通 `KFold` 会让本地 CV 高出 0.05+ 全是假象。
2. **时间箭头（Temporal Split）**：数据是否带时间戳或隐含顺序 ID？测试集是否严格位于训练集未来时间段？
   - 若是未来预测 → 必须用滚动时间窗或 `PurgedGroupTimeSeriesSplit`（留出 embargo 隔离期防止滞后特征穿越）。
3. **标签分布与标注噪声**：多标签/不平衡分类是否需要 `MultilabelStratifiedKFold`？是否存在不同标注批次尺度不一（需分层或两阶段精调）？
4. **公私榜切分规则**：Evaluation / Overview 页是否透露了公私榜怎么切（例如公榜是前 3 个月、私榜是后 6 个月；或公榜只含已知 prompt、私榜全是新 prompt）？

---

## 三、禁网代码赛（Code Competition）常见工程与加速共识

当本赛为 **禁网 + 固定时长（如 9h / 12h CPU 或双 T4 / L4）** 代码赛时，往届前排方案的高频工程底座：

1. **训练与推理解耦**：训练 100% 在线下或独立训练环境完成，将训练好的多折权重与第三方依赖 `.whl` 打包上传为私有 Kaggle Dataset，提交 Notebook **只做纯推理与融合**。
2. **NLP / LLM 推理压榨**：
   - **按 token 长度排序组 Batch（Length-sorted Dynamic Padding）**：把长短相近的测试文本排在一起推理，消除无效 pad 计算，通常直接提速 **2x–3.5x**（完成后严格按原 `id` 还原顺序！）；
   - 双卡并行（`DataParallel` 或双进程各绑一张 `cuda:0` / `cuda:1` 切分测试集并行跑，规避 GIL 与单卡空转）；
   - 大模型用 `vLLM` / `AWQ 4-bit` / `FP16` / `ONNX Runtime` / `TensorRT`。
3. **防提交崩溃（Submission Scoring Error 铁律）**：
   - 公开测试集往往只有几行假数据（Dummy test），正式重跑时才注入上万行真实测试集——**严禁硬编码测试集行数、严禁一次性把全量图像/长序列读入内存**；
   - 算好单样本耗时 × 预估真实测试集规模，留足至少 **15%–20% 时间余量**，并处理测试集可能出现的 `NaN`、超长文本、损坏图像或未见新类别。
