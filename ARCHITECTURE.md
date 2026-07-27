# Cortex - 技术架构文档

> 版本：1.0
> 后端：Python 3.10+ · FastAPI · LangGraph
> 作者：qing + AI Assistant

Cortex 是 `llm_test`（Node/Express）的 Python/LangGraph 重构版，完整复制原有能力，并新增网络研究能力。

## 目录
1. [系统概览](#系统概览)
2. [技术栈](#技术栈)
3. [整体架构](#整体架构)
4. [LangGraph Workflow](#langgraph-workflow)
5. [网络研究能力](#网络研究能力)
6. [SSE 事件桥接](#sse-事件桥接)
7. [核心模块](#核心模块)
8. [数据模型](#数据模型)
9. [与 llm_test 的差异](#与-llm_test-的差异)
10. [安全性](#安全性)

---

## 系统概览

多用户、多会话的智能对话系统，核心是一个 **LangGraph 状态机**：对用户消息做意图分类，再路由到四类处理节点之一。

| 能力 | 说明 |
|------|------|
| 意图分类路由 | LLM 分类（含上下文）→ knowledge_qa / generate_page / web_research / casual_chat |
| 知识问答 | Wiki 知识库，Python DeepSeek tool-call agent 检索并带引用 |
| 代码生成 | 6 工具 tool-call 循环，隔离目录 + 动态预览 |
| **网络研究** | DuckDuckGo 搜索 + 网页正文抽取 + 结构化总结分析 + 来源 |
| 多对话并行流式 | SSE，按 conversationId 隔离 |
| 上下文记忆 | Token-aware 截断 + 最多 20 条历史 |
| LLM 队列 | asyncio 并发控制 + 入队超时 |
| 文件日志 | 终端 + app.log，10MB 轮转 |

---

## 技术栈

**后端**：Python 3.10+ · FastAPI · uvicorn · LangGraph (StateGraph) · langchain-openai · aiosqlite · PyJWT · bcrypt
**网络研究**：ddgs (DuckDuckGo) · trafilatura · httpx · BeautifulSoup
**前端**（复用 llm_test）：React 18 · TypeScript · Vite · Ant Design 5 · Zustand · TanStack Query · 原生 fetch + SSE

---

## 整体架构

```
┌───────────────────────────────────────────────────────────────┐
│                        Browser (React SPA)                     │
│  Chat UI（SSE 多对话并行） · Admin（用户/设置/Prompt/Wiki）      │
│  streamStates: Record<convId, {content, tool, preview, sources}>│
└─────────────────────────────┬─────────────────────────────────┘
                              │ HTTP + SSE (fetch)
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                     FastAPI (main.py)                          │
│  routers/  auth · admin_* · conversations · chat(SSE) · queue  │
│  /preview 静态（CSP 同源） · 前端 dist 托管 · SPA fallback       │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ POST /api/chat → LLM Queue → LangGraph workflow          │  │
│  │   classify → {knowledge_qa|generate_page|web_research|    │  │
│  │               casual_chat}                                │  │
│  │   节点通过 asyncio.Queue emitter 推送 SSE 事件            │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────┬───────────────────┬───────────────────┬────────────────┘
       │                   │                   │
   ┌───▼────┐      ┌───────▼────────┐   ┌──────▼─────────────┐
   │ SQLite │      │ Wiki agent      │   │ Web tools           │
   │(aiosql)│      │ (subprocess)    │   │ DDG + trafilatura   │
   └────────┘      └───────┬─────────┘   └─────────────────────┘
                           ▼
                   OpenAI 兼容 LLM 端点（DeepSeek/通义/OpenAI…）
```

---

## LangGraph Workflow

`graph/workflow.py` 用 `StateGraph(GraphState)` 构建：

```
set_entry_point("classify")
add_conditional_edges("classify", route_by_intent, {
    knowledge_qa, generate_page, web_research, casual_chat
})
每个节点 → END
```

- **状态** `graph/state.py`：`GraphState(TypedDict)` 携带 user_message、history（已截断）、settings、active_prompt、conversation_id、intent、full_response，以及 SSE `emit` 回调。不使用 checkpointer，故可在状态里放运行期对象。
- **LLM** `llm.py`：`build_chat()` 从 DB settings 动态构造 `ChatOpenAI`（base_url 归一化去掉 `/chat/completions` 后缀；`.bind_tools()` 做工具调用，`.astream()` 做流式）。
- **classify** `graph/nodes/classify.py`：非流式、temperature=0.1、max_tokens=50，取最近 6 条上下文；解析 `{"intent": ...}`，失败 fallback=knowledge_qa。
- **共享骨架** `graph/agent_loop.py`：`run_tool_loop()`（反复调用工具直到无 tool_calls 或到达上限）+ `stream_final()`（无工具流式回答，逐块 emit `content`）。generate_page / web_research 复用。

### 各节点
| 节点 | 逻辑 |
|------|------|
| knowledge_qa | `wiki_service.search_knowledge()` → 注入 system → 流式回答；失败发 notice |
| generate_page | system += 代码生成 prompt → tool-call 循环（≤10，6 工具）→ 流式收尾 → 发 preview |
| web_research | system += 研究 prompt → tool-call 循环（≤6，2 工具）→ 发 sources → 流式总结分析 |
| casual_chat | 直接返回拒绝文本 |

---

## 网络研究能力

`tools/web_tools.py`：
- `web_search(query, max_results)` → DuckDuckGo（`ddgs`，兼容旧 `duckduckgo_search`），返回 `[{title, url, snippet}]`，无需 API Key。
- `fetch_webpage(url)` → httpx 抓取 → **trafilatura** 抽正文（回退 BeautifulSoup 去脚本/样式后取文本），截断到 8000 字符。

`web_research` 节点在 ≤6 轮 tool-call 循环中：模型自主搜索/读页 → 收集访问过的 URL（去重）→ emit `sources` → 基于真实抓取内容做结构化「## 总结 / ## 要点分析」并标注 `[来源N]`。前端 `Sources.tsx` 渲染来源卡片。

---

## SSE 事件桥接

不与 LangGraph 内部流式抽象耦合，而是显式控制事件形状：

```
chat 路由创建 asyncio.Queue → emit(event) = queue.put(event)
run() 中：llm_queue.enqueue(workload) → workflow.ainvoke(state, emit)
节点内 await emit({...})
StreamingResponse 消费 queue：yield f"data: {json}\n\n"，结束 yield "data: [DONE]\n\n"
```

事件类型（与前端 `services/sse.ts` 逐一对齐）：
`queue` · `intent` · `notice` · `tool_progress`(running/completed/error) · `preview` · **`sources`**（新增）· `content` · `error` · `[DONE]`

---

## 核心模块

| 模块 | 职责 |
|------|------|
| `config.py` | 按 backend/ 加载 .env，路径/常量 |
| `logger.py` | 终端 + RotatingFileHandler(10MB)，强制 UTF-8 |
| `db.py` | aiosqlite 连接、建表、默认 settings/prompt/admin、fetch/execute 辅助 |
| `auth.py` | PyJWT 签发/校验；`get_current_user` / `require_admin` 依赖 |
| `llm_queue.py` | asyncio 信号量队列；超时只作用于入队等待阶段 |
| `llm.py` | 从 settings 构建 ChatOpenAI；读取 active prompt |
| `wiki_service.py` | 子进程调用 wiki_query.py / wiki_agent.py，解析 `═` 分隔答案 |
| `tools/code_generator.py` | 6 工具（safe_path 防越界、命令白名单、30s 超时） |
| `tools/web_tools.py` | web_search / fetch_webpage |

---

## 数据模型（SQLite）

`users` · `conversations` · `messages` · `settings` · `prompts`，结构对齐原 MySQL schema（外键级联、user_id 隔离、prompts 单一激活）。首次启动自动建表 + 默认 6 项 settings + 「默认助手」prompt + admin/123456。

---

## 与 llm_test 的差异

| 方面 | llm_test | Cortex |
|------|----------|--------|
| 后端语言/框架 | Node.js / Express | Python / FastAPI |
| 工作流 | 手写 switch 路由 | **LangGraph StateGraph** |
| 意图路由 | 3 路 | **4 路（+ web_research）** |
| LLM 调用 | 原生 fetch | langchain-openai ChatOpenAI |
| 数据库 | MySQL（+mock 模式） | SQLite（零配置，去 mock） |
| 新能力 | — | **网络搜索 + 读网页 + 总结分析** |
| 前端 | React | 复用 + 「来源」UI |

---

## 安全性

- JWT（HS256，默认 30d）；bcrypt(10) 密码哈希
- 所有 admin API 经 `require_admin`；conversation/message 按 user_id 隔离
- 代码生成：`safe_path` 防路径遍历 + `run_command` 白名单（ls/cat/find/node/npm/npx/echo/mkdir）+ 30s 超时；每会话隔离目录 `demo_code/{convId}`
- 预览：`X-Frame-Options: SAMEORIGIN` + CSP `frame-ancestors 'self'`
- 网络研究：仅 http/https，抓取 20s 超时、正文截断
- SQL 全部参数化

---

**文档维护**：每次重大架构变更后更新此文档。
