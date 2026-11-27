# 主题分类规则

共 8 个互斥主类。跨类论文按核心技术贡献归类，不要按应用场景泛化。

## LLM
语言模型本体（预训练架构、长上下文、推理链、代码与数学能力）、纯文本 Agent 与工具调用、文本对齐。
不含：图像/视频/音频输入输出（归 Multimodal 或 VisionGen）。

## Multimodal
视觉-语言模型（VLM）、音频/视频-语言理解、跨模态对齐、文档与图表理解、含视觉输入的 GUI/Web Agent。

## VisionGen
图像/视频/3D/4D 生成与编辑、扩散与流匹配生成模型、可控生成、神经渲染与超分。

## RLPostTraining
强化学习算法、偏好优化（RLHF / DPO / GRPO）、过程奖励模型（PRM）、测试时强化搜索、自我博弈与递归自改进算法本体。
判据：后训练或自进化机制本身是主要贡献时归入此类；仅将常规 DPO 作为训练步骤的模型工作归入对应模态类。

## EfficiencySystems
推理与训练系统、量化、剪枝、蒸馏、投机解码（Speculative Decoding）、KV Cache 压缩、算子优化、MoE 路由与通信优化。

## EmbodiedRobotics
机器人操作与移动控制、VLA（Vision-Language-Action）、具身导航、用于物理控制的世界模型、Sim2Real、触觉与灵巧手。凡涉及真实或仿真机器人控制优先归入此类。

## DataEvalSurvey
基准测试（Benchmark）、数据集构建、评测方法学、综述（Survey）与系统性实证审计。
判据：核心产出是评测基准、数据集或综述分析本身，而非新模型。

## ScienceOther
AI4Science（生物、蛋白质、化学、材料、气象、医疗影像与生理信号）、纯语音合成识别、传统图网络及不属于以上 7 类的其他方向。

## 兜底判据
- 核心贡献是 Benchmark / Dataset / Survey，归 `DataEvalSurvey`。
- 涉及机器人、具身控制、VLA，归 `EmbodiedRobotics`。
- 生物医药、物理化学、脑电生理信号等科学计算论文归 `ScienceOther`，不要塞入 `LLM`。
