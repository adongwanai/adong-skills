# agent-resource-scout

**帮 Agent 小白和做技术选型的人少走弯路**：把一句模糊需求（如“我想学 MCP”、“怎么准备 Agent 实习项目”、“生产环境选 LangGraph 还是 Pydantic AI”），变成**排好先后顺序、逐个链接实时核验过**的行动方案。

零 API Key 硬性依赖，纯 Python 标准库双核验引擎，可在 **Claude Code、OpenAI Codex、Antigravity、Cursor** 中即插即用。

---

## 为什么要做这个 Skill？

初学者想入门 Agent 或工程师想找现成开源轮子时，缺的从来不是链接，而是**“先看哪 3 个、今晚先跑哪一步、为什么”**。直接搜全网或裸问大模型，十有八九踩这四个坑：

1. **好坏混杂**：2023 年过时的链式拼接教程、老式 AutoGPT 死循环，和靠刷星包装出来的空壳项目混在一起；
2. **引流带偏**：搜出来满屏 CSDN 搬运帖、Gitee/GitCode 野生镜像仓，点进去全是“关注公众号回复 666 领源码 / 扫码进群领资料”；
3. **过载劝退**：一次甩给你 30 个 `awesome-*` 链接，或者第一步就让你啃重型编排框架，环境还没配通就放弃了；
4. **幻觉造假**：直接让大模型推荐，它会凭旧记忆编出根本不存在的 GitHub 仓库、已归档停更的项目，或把非商用协议说成可商用。

---

## 核心功能与用户体验设计

围绕“不让用户在配置、盘问和阅读上受罪”，做了五层体验设计：

### 1. 首轮直给结果，拒绝“盘问式冷启动”
只要你说出了具体主题（如“我想学 MCP”），**第一轮直接给核验完毕的完整路线或对比结论**，绝不先甩 3 个问题让你填空干等；只在末尾留一句轻量微调入口（如切换 TypeScript 栈或算法训练方向）。

### 2. A 学习模式：3 步阶梯 + 前 30 分钟开跑指引（防“收藏吃灰”）
严格按 **「原生 API 手写最小闭环 → 官方系统课 → 主流框架实战」** 排好 3 步（外加最多 2 个备选）：
- 每一步不仅给链接和避坑提示，还直接写明**前 30 分钟先打开哪个文件怎么跑起来**，以及**做到什么算真正过关**（不以“看完视频”当标准）。

### 3. 从 Demo 到简历与面试的“最后一公里”防坑（按人群分层，不硬广）
- 针对小白最容易踩的“把玩具教程原封不动抄上简历被秒挂”，在学习路线末尾按 **Agent 开发岗**（重工具边界、超时幂等、固定 Bad-case 评测集、成本延迟账）或 **Agent 算法岗**（重数据防泄漏、轨迹构建、Verifier 与同预算消融）给出 **2 个最小工程化改造动作** + **面试官真正会追问的 3 个硬问题**。
- 按需指路同样经过实时核验的开源题库 [AgentGuide](https://github.com/adongwanai/AgentGuide)、干净排版底板 [LLM-Resume-Template](https://github.com/adongwanai/LLM-Resume-Template)，以及审简历/跑模拟面试的 `agent-career-kit`。
- **克制边界**：纯个人兴趣折腾不贩卖求职焦虑；**B 选型模式（纯工程技术对比）0 句简历/面试内容**。

### 4. B 选型模式：结论置顶 + 6 列窄屏友好对比表 + 排雷卡
- **3 秒看懂**：顶部先给直球结论（首选谁、什么条件下换备选、为什么排除某热门项）；
- **拒绝宽表乱码**：主表严格压在 **6 列以内**（在 IDE 侧边栏和终端里一屏扫完），把部署门槛、适用边界和**带原帖链接与日期的真实踩坑记录**放进表下排雷卡。

### 5. 双脚本并发实时核验（把筛选铁律写成代码，而非只靠 Prompt 祈祷）
- **`scripts/github_check.py`**：自动复用本地 `GITHUB_TOKEN` / `GH_TOKEN` / `gh auth token` 多线程核验仓库存活、改名跳转、归档/Fork 状态、商用危险协议（`AGPL`、`BSL`、`CC-BY-NC` 等）、热门库纯 Issue 维护者响应率与中位耗时、异常刷星比（`SUSPICIOUS_STAR_RATIO`），并支持 `--pypi` / `--npm` 直拉近 30 天真实下载量拆穿“高星没人用”的空壳。
- **`scripts/url_check.py`**：并发核验课程、文档、博客等非 GitHub 链接的存活状态、跨站重定向（如已关闭的 Papers with Code 跳转）、自动标记 CSDN / Gitee / GitCode 搬运镜像与“扫码加群/公众号回复引流”页面。

---

## 怎么安装与使用

### 方式一：用 `skills` CLI 一键安装（推荐）

```bash
npx skills add adongwanai/adong-skills --skill agent-resource-scout -g
```

### 方式二：Clone 仓库手动建软链

```bash
git clone https://github.com/adongwanai/adong-skills.git
cd adong-skills

# Claude Code
ln -sfn "$(pwd)/agent-resource-scout" ~/.claude/skills/agent-resource-scout

# OpenAI Codex
ln -sfn "$(pwd)/agent-resource-scout" ~/.codex/skills/agent-resource-scout

# Antigravity / Gemini CLI
ln -sfn "$(pwd)/agent-resource-scout" ~/.gemini/config/skills/agent-resource-scout
```

### 直接用自然语言提问即可

- **入门学习**：“我想学 MCP，平时写 Python，怎么从零跑通？”
- **求职攒项目**：“研一找 Agent 开发实习，想学 RAG 和工具调用，怎么学、做什么才好写进简历？”
- **工程选型**：“Python 生产环境做可观测可控的 Agent，LangGraph、Pydantic AI 和 OpenAI Agents SDK 怎么选？需要可商用。”

---

## 本地测试与脚本验证

```bash
# 1. 运行全量离线单元测试（纯 Python 标准库，兼容 unittest 与 pytest）
python3 -m unittest discover -s tests -v

# 2. 实测 GitHub 仓库核验 + PyPI 真实月下载量
python3 scripts/github_check.py langchain-ai/langgraph pydantic/pydantic-ai \
  --track selection --pypi langgraph pydantic-ai

# 3. 实测非 GitHub 课程/文档链接与引流检测
python3 scripts/url_check.py \
  https://huggingface.co/learn/agents-course \
  https://modelcontextprotocol.io/introduction
```

## License

[MIT License](./LICENSE)
