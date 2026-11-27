# 完整信源清单与 Kaggle 工具生态对照

> 本文件供 `kaggle-prior-art` 在需要扩展检索面或协同外部工具时按需查阅。

## 一、六类先例信源全景（A–F）

### A. Kaggle 站内一手区
- **比赛核心页**：`Overview`、`Evaluation`（重点看公式边界条件与自定义 Python Metric Notebook）、`Data`、`Rules`（外部数据报备帖、开源许可证要求）、`Timeline`
- **Leaderboard**：对比 Public LB 与 Private LB 排名差，判断该赛题类型的固有 Shake-up 烈度
- **Writeups 专区**：`https://www.kaggle.com/competitions/<slug>/writeups`（新版 Kaggle 集中归档获奖方案的入口）
- **Discussion 高价值帖**：
  - 赛后：`"1st place solution"`、`"gold medal approach"`、`"what didn't work"`
  - 赛中：主办方置顶勘误、`"CV vs LB"` 相关性讨论、数据坏点/异常样本排查帖、外部数据集集中报备帖（Official External Data Thread）
- **Code 区**：按 `voteCount`（看清爽 EDA 与可靠 baseline）和按 `scoreAscending/scoreDescending`（看当前公榜公开天花板与潜在过拟合 blending notebook）分别查看
- **Models & Datasets 区**：往届或本赛选手上传的预训练骨干权重、离线 wheel 安装包（代码赛禁网必备）
- **Meta Kaggle & Meta Kaggle Code**：Kaggle 官方维护的全量历史比赛、论坛主题、队伍公私榜名次表

### B. 跨赛方案聚合索引（均作为候选池，必须回原帖/原仓库核验）
- **`faridrashidi/kaggle-solutions`**（站点 `kaggle.farid.one`，本 skill 脚本默认免配置拉取其 `data/competitions.yml`）：更新及时，区分 `description`（方案帖）、`code`（GitHub 仓库）与 `kernel`（Notebook）
- **`EliotAndres/kaggle-past-solutions`**（及社区 fork）：覆盖早年经典比赛
- **`the-black-knight-01/Data-Science-Competitions`**：覆盖 Kaggle 之外的多平台竞赛方案
- **`anuj0456/kaggle_competition_solutions`**：按年份与领域归档
- **Hugging Face 数据集 `Abirate/all_write_ups`、`Abirate/min_write_ups`**：历史方案全文静态快照（适合关键词全文搜早年 trick，但不含近年新赛）

### C. 其他高含金量数据科学竞赛平台
- **国际平台**：
  - **DrivenData (`drivendataorg/competition-winners`)**：极具参考价值，获奖方案代码几乎 100% 强制完整开源（MIT/Apache 等），遥感、医疗、公益、多模态赛题尤多
  - **AIcrowd / Codabench (原 CodaLab) / EvalAI / Zindi / Signate（日本，表格与工业视觉强）**
- **顶会竞赛赛道（Workshop Challenges）**：
  - **NeurIPS Competition Track**、**KDD Cup**（推荐、图计算、风控、大模型评测）、**CVPR / ICCV / ECCV Workshops**（分割、检测、底层视觉、自动驾驶）、**MICCAI Grand Challenge**（医学影像 3D 分割/分类圣地）
- **中文竞赛社区**：
  - **天池（Tianchi）**、**DataFountain**、**和鲸（Heywhale）**、**科大讯飞 AI 开发者大赛**（时序预测、工业质检、结构化风控与中文 NLP 赛后答辩 PPT/代码丰富）

### D. 年度趋势与 Grandmaster 深度复盘
- **ML Contests (`mlcontests.com`)**：每年发布的 *State of Competitive Machine Learning* 报告，统计当年所有获奖方案使用的主流架构、硬件、框架变迁
- **NVIDIA Technical Blog (`Kaggle Grandmasters Playbook` 系列)**：NVIDIA Kaggle Grandmaster 团队（Chris Deotte, Christof Henkel, Jean-Francois Puget, Kazuki Onodera 等）撰写的赛后硬核复盘，包含大量 CV 设计与代码赛加速实战细节
- **arXiv 赛后技术报告**：搜索 `"<Competition Name>" solution` 或 `"1st place" NeurIPS KDD challenge`

### E. 技术落地与核验文档
- **主流竞赛库官方文档**（可通过 Context7 或官方站核对 API）：`LightGBM`、`XGBoost`、`CatBoost`、`scikit-learn`、`PyTorch`、`timm`、`HuggingFace Transformers / PEFT`、`albumentations`、`MONAI`、`vLLM`、`ONNX Runtime`、`Optuna`、`RAPIDS cuDF/cuML`
- *(注：Papers with Code 现已停止动态更新，查新方法请直接走 arXiv / HuggingFace Papers / GitHub)*

### F. 中文二手线索（仅作导航索引，严禁直接采信二手转述数字）
- 知乎「Kaggle / 数据竞赛」高赞赛后亲历复盘（优先看参赛者本人写的 `知乎专栏` 原帖）
- Datawhale 开源竞赛基线与赛题解析

---

## 二、Kaggle 相关 Skill 与 MCP 协同分工表

本 skill 专注**跨赛先例检索、可复现性排雷与实验起点规划**，与以下单赛执行类工具天然互补：

| 工具名称 | 类型 | 核心能力 | 与 `kaggle-prior-art` 怎么配合 |
|---|---|---|---|
| **`NVIDIA/nvidia-kaggle` (`nvidia-kaggle-skill`)** | 官方开源 Skill (MIT) | 获取单赛规则/数据描述、拉取并本地复现公开 Kernel、执行代码、提交预测结果 | 装有它时：用它读本赛概况；本 skill 完成跨赛先例对比并选定推荐 Baseline 后，交由它拉取数据与复现提交 |
| **Kaggle 官方 MCP (`kaggle.com/mcp`)** | 官方远程 MCP | 查询比赛元数据、排行榜、数据集、Notebook 与 Models（不含完整论坛搜索） | 在支持 MCP 的客户端里直接读取实时榜单和比赛元数据，免写 CLI 命令 |
| **`Galaxy-Dawn/kaggle-mcp`** | 社区 MCP | 补齐 Discussion 讨论区与方案帖读取 | 在无浏览器环境下辅助拉取单篇方案帖正文 |
| **`shepsci/kaggle-skill`** | 社区 Skill | 封装常用 Kaggle CLI 操作 | 可作为 `nvidia-kaggle-skill` 未安装时的轻量单赛操作替代 |
| **`FrankS-IntelLab/agentic-kaggle-skill`** | 社区 Skill | 端到端实验迭代与提交排障流程 | 当用户完成 EDA 并基于本 skill 的验证单进入正式建模阶段后，可参考其验证驱动建模循环 |
