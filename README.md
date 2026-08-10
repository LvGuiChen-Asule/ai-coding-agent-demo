# AI Coding Agent Workflow Demo

基于 **Agent Workflow** 的智能代码开发助手 Demo —— 模拟真实 AI 软件工程师的完整工作流：

```
需求理解 → 任务规划 → 文件分析 → 代码生成 → 自动修改 → 测试验证 → 结果优化
```

本项目研究 Claude Code / OpenAI Codex 等 AI Coding Agent 的工作模式，用 **Python + FastAPI**
实现了一个轻量级、可运行、可扩展的 Agent 系统，让 AI 从「代码补全工具」向「自主开发 Agent」演进。

> 无需任何 API Key 即可运行：内置 **Mock Provider**（离线模式），可以完整演示
> 任务规划、代码生成、文件操作、自动测试、自我审查等全部环节。

---

## ✨ 核心能力

| 模块 | 作用 | 技术实现 |
| --- | --- | --- |
| Planner Agent | 自然语言需求 → 结构化任务规划 | Prompt Engineering + Chain of Thought + JSON 输出 |
| Code Generation Agent | 按规划生成 Java / Python / JavaScript 代码 | LLM API / 离线模板，按分层结构生成 |
| File Operation Agent | 读文件、建目录、改代码、记录 diff | FileReader / FileWriter 工具 + 备份机制 |
| Tool Calling 系统 | Agent 自主选择工具完成任务 | 工具注册表，类似 Function Calling / MCP |
| Test Agent | 自动运行测试、分析异常 | mvn test / npm test / python unittest / 静态校验 |
| Fixer（自动修复） | 测试失败 → 定位错误 → 修改 → 重测 | 循环修复，最多 N 轮 |
| Reflection Agent | 代码质量 / 安全 / 架构审查 | 规则启发式 + LLM，输出 Code Review 报告 |

支持的代码生成目标：

- ☕ **SpringBoot**（MyBatis + MySQL + REST API + MockMvc 测试）
- 🐍 **Python FastAPI**（分层结构 + unittest 测试，离线可运行）
- 🟩 **Node.js Express**（REST API + node:test 测试）

---

## 🏗️ 架构

```text
                 用户需求
                    |
                    v
           Natural Language Input
                    |
                    v
         ┌──────────────────────┐
         │   Planner Agent      │  需求拆解 / CoT / JSON 结构化任务
         └──────────────────────┘
                    |
        ┌───────────┼───────────┐
        v           v           v
   Code Agent   File Agent   Test Agent
   代码生成     文件读写/修改  自动测试 + 失败分析
        |           |           |
        └───────────┼───────────┘
                    v
        ┌──────────────────────┐
        │  Fixer（自动修复循环） │  失败 → 定位 → 修改 → 重测
        └──────────────────────┘
                    |
                    v
        ┌──────────────────────┐
        │  Reflection Agent    │  质量 / 安全 / 架构审查
        └──────────────────────┘
                    |
                    v
               输出结果 + Code Review 报告
```

## 🧩 核心机制

### 1. 任务规划（Planner）

用户输入自然语言需求（如「帮我创建一个 SpringBoot 用户登录模块」），Planner 通过
Chain of Thought 拆解为带依赖顺序的结构化步骤：

```json
{
  "task": "创建 SpringBoot 用户登录模块",
  "stack": "springboot",
  "steps": [
    { "id": 1, "title": "创建 Maven 工程骨架", "type": "codegen", "detail": { "files": ["pom.xml", "..."] } },
    { "id": 2, "title": "创建 User 实体类", "type": "codegen", "detail": { "files": [".../User.java"] } },
    { "id": 3, "title": "创建 Mapper 数据访问层", "type": "codegen", "detail": { "files": ["..."] } },
    { "id": 9, "title": "运行测试并静态验证", "type": "test", "detail": {} }
  ]
}
```

### 2. 工具调用系统（Tool Calling）

Agent 根据任务自主选择工具，工具统一注册、调用并记录日志：

| 工具 | 功能 |
| --- | --- |
| `FileReader` | 读取代码文件（支持行号） |
| `FileWriter` | 创建 / 修改文件，自动备份 + 生成 diff |
| `Terminal` | 执行命令（限制在工作区内） |
| `Git` | 版本管理 |
| `TestRunner` | 自动检测并运行测试 |

### 3. 自动测试与修复闭环

```text
生成代码 → 运行测试 → 发现 Error → 分析异常堆栈
    → 定位代码位置 → 修改代码 → 重新测试（最多 N 轮）
```

运行 `python run_demo.py --demo-bug ...` 可以看到完整的「测试失败 → 自动修复 → 重测通过」演示。

### 4. Reflection 自我优化

代码生成完成后自动执行代码审查，检查：代码质量、重复代码、安全隐患（SQL 注入、
硬编码口令、弱密码哈希、越权）、架构合理性，最终生成 `CODE_REVIEW_REPORT.md`。

> 示例生成的代码**刻意包含**几个典型问题（如 Mapper XML 中 `${}` 拼接导致的 SQL 注入风险、
> 无盐 SHA-256 密码哈希、`getById` 查询逻辑错误等），供 Reflection Agent 审查发现。

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- （可选）Java 17+ / Maven —— SpringBoot 真实测试
- （可选）Node.js 18+ —— Node 栈测试

### 1. 安装依赖

```bash
git clone https://github.com/LvGuiChen-Asule/ai-coding-agent-demo.git
cd ai-coding-agent-demo

python -m pip install -r requirements.txt
```

> 核心 Agent 引擎仅依赖 Python 标准库；`requirements.txt` 中的 FastAPI / uvicorn
> 只用于 Web UI 与 REST API。

### 2. 离线 Demo（无需 API Key）

生成 SpringBoot 用户登录模块：

```bash
python run_demo.py "帮我创建一个SpringBoot用户登录模块"
```

生成 Python FastAPI 用户接口（真实运行 unittest）：

```bash
python run_demo.py "创建一个Python FastAPI用户接口" --stack python
```

演示「测试失败 → 自动修复」闭环：

```bash
python run_demo.py "创建一个Python FastAPI用户接口" --stack python --demo-bug
```

对已生成项目执行修改（增加验证码校验）：

```bash
python run_demo.py "修改登录逻辑，增加验证码校验" --modify
```

所有产物输出到 `demo_output/`：

```text
demo_output/
├── src/main/java/com/example/userlogin/...   # 生成的 Java 代码
├── src/main/resources/                      # 配置、SQL、Mapper XML
├── src/test/java/.../UserControllerTest.java
├── CODE_REVIEW_REPORT.md                    # Reflection 审查报告
└── workflow_result.json                     # 完整执行记录
```

### 3. Web UI

```bash
uvicorn app.main:app --reload
```

浏览器打开 <http://127.0.0.1:8000>，输入自然语言需求即可可视化运行整个 Agent 工作流：

- 实时事件时间线（规划 / 生成 / 测试 / 修复 / 审查）
- 测试报告（逐项检查）
- Code Review 报告（评分 + 问题清单）
- 生成文件列表

### 4. REST API

| 接口 | 说明 |
| --- | --- |
| `GET /healthz` | 健康检查 |
| `GET /api/tools` | 列出已注册工具 |
| `POST /api/workflow/run` | 执行一次完整工作流 |

```bash
curl -X POST http://127.0.0.1:8000/api/workflow/run \
  -H "Content-Type: application/json" \
  -d '{"requirement": "帮我创建一个SpringBoot用户登录模块", "provider": "mock"}'
```

---

## 🔑 接入真实 LLM

复制 `.env.example` 为 `.env`，配置 Provider：

### OpenAI

```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxx
OPENAI_MODEL=gpt-4o-mini
```

### 通义千问（DashScope 兼容模式）

```ini
LLM_PROVIDER=qwen
QWEN_API_KEY=sk-xxxx
QWEN_MODEL=qwen-plus
```

`LLM_PROVIDER` 可选值：`mock`（默认，离线）/ `openai` / `qwen`。
LLM 请求使用 Python 标准库实现，无需安装额外 SDK。

---

## 📁 项目结构

```text
ai-coding-agent-workflow-demo/
├── agent_core/                  # Agent 工作流核心引擎（纯标准库）
│   ├── llm.py                   #   LLM Provider（OpenAI / Qwen / Mock）
│   ├── planner.py               #   任务规划 Agent
│   ├── coder.py                 #   代码生成 Agent
│   ├── fileops.py               #   文件操作 Agent
│   ├── tester.py                #   自动测试 Agent
│   ├── reflector.py             #   Reflection 审查 Agent
│   ├── orchestrator.py          #   工作流编排器（含自动修复循环）
│   ├── tools.py                 #   Tool Calling 工具注册系统
│   ├── context.py               #   项目上下文 / 文件分析
│   ├── prompts.py               #   Prompt Engineering 模板
│   ├── config.py                #   配置（.env）
│   └── types.py                 #   数据模型
├── templates/                   # Mock Provider 代码模板
│   ├── springboot.py            #   SpringBoot 登录模块模板
│   ├── python_fastapi.py        #   Python FastAPI 模板
│   └── nodejs.py                #   Node.js Express 模板
├── app/                         # FastAPI Web 服务
├── webui/index.html             # Web UI（原生 HTML/JS）
├── examples/                    # 生成的示例项目（提交入库）
│   ├── springboot-login/
│   └── python-fastapi/
├── tests/                       # 自动化测试（unittest）
├── run_demo.py                  # 命令行 Demo 入口
├── requirements.txt
└── .env.example
```

## ✅ 运行测试

```bash
python -m unittest discover -s tests
```

覆盖：JSON 解析、Mock Provider 路由、工具注册与 diff 备份、路径穿越防护、
SpringBoot / Python 全流程生成、验证码修改、修复闭环。

## 📌 可扩展方向

- 接入真实 MCP / Function Calling 生态，注册更多工具（数据库、浏览器、CI）
- 支持更多技术栈（Go / Rust / Vue / React）
- 引入向量检索，实现基于仓库历史代码的上下文增强
- 将 Reflection 发现的问题自动转成新一轮修改需求（自我进化循环）
- 多 Agent 并行协作（如同 Claude Code 的 subagent）

## 📄 License

MIT License. 本项目为个人探索 / 学习用途。
