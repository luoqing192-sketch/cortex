# Cortex

> 基于 LangGraph 的多能力智能对话系统 —— 意图分类四路路由（知识问答 / 代码生成 / **网络研究** / 闲聊），后端 Python，前端复用 React。

Cortex 是 `llm_test` 的 Python/LangGraph 重构版：完整保留原有能力，并新增**网络查询、读网页文档、总结分析**。

## ✨ 特性

- 🧭 **意图分类路由（LangGraph）** — LLM 对消息分类（含上下文）→ 四路分发
- 📚 **知识问答** — Wiki 知识库，LLM tool-call agent 自动检索 markdown 文档并带引用
- 🛠️ **代码生成与预览** — 6 个工具的 tool-call 循环，隔离目录 `demo_code/{convId}` + 动态预览 URL + iframe
- 🌐 **网络研究（新增）** — DuckDuckGo 联网搜索 + 网页正文抽取（trafilatura）+ 结构化总结分析 + 来源引用
- 💬 **多对话并行流式** — SSE，按 `conversationId` 隔离，切换对话不中断后台流
- 🧠 **上下文记忆** — Token-aware 截断 + 最多 20 条历史
- 🔐 **用户隔离** — JWT 认证，conversation/message 按 user_id 隔离
- ⚙️ **动态配置** — 管理后台实时切换 LLM 模型、Prompt 模板
- 🚦 **LLM 请求队列** — asyncio 并发控制 + 入队超时
- 📝 **文件日志** — 终端 + `app.log`，10MB 自动轮转

## 🧱 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | Python 3.10+ · FastAPI · uvicorn |
| 工作流 | **LangGraph** (StateGraph) · langchain-openai |
| 数据库 | SQLite (aiosqlite) |
| 认证 | PyJWT · bcrypt |
| 网络研究 | ddgs (DuckDuckGo) · trafilatura · httpx · BeautifulSoup |
| Wiki agent | 复用 Python DeepSeek tool-call 脚本 |
| 前端 | React 18 · TypeScript · Vite · Ant Design 5 · Zustand · TanStack Query |

## 🚀 快速开始

### 前置要求
- **Python 3.10+**（3.12 已验证）
- Node.js 18+
- 推荐使用 [uv](https://github.com/astral-sh/uv) 管理 Python 环境（也可用标准 venv）

### 1. 后端

```bash
cd cortex/backend

# 方式 A：uv（推荐）
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt

# 方式 B：标准 venv
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env    # 按需修改 JWT_SECRET 等

# 启动（默认端口 8000，首次启动自动建库 + 默认 admin）
.venv/Scripts/python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. 前端

```bash
cd cortex/frontend
npm install
npm run dev        # 开发（proxy → 8000），或
npm run build      # 构建，产物 dist/ 由后端直接托管
```

访问：
- 开发：http://localhost:5173
- 生产（后端托管 dist）：http://localhost:8000

### 3. 默认账户 & 配置 LLM

```
用户名：admin   密码：123456
```
登录后进入 **管理后台 → 系统设置**，填写 LLM 的 `base_url` / `api_key` / `model`（OpenAI 兼容端点，如 DeepSeek、通义千问、OpenAI 等）。这些配置存于数据库，无需改代码。

## 🧭 LLM Workflow（LangGraph 四路路由）

```
POST /api/chat { conversationId, message }
      │
   classify（LLM 意图分类，含最近 6 条上下文，temperature=0.1）
      │
      ├─ knowledge_qa  → wiki_query.py 检索 + 流式回答
      ├─ generate_page → 代码生成 tool-call 循环（6 工具）+ preview 链接
      ├─ web_research  → web_search + fetch_webpage 循环 → sources 来源 → 流式总结分析
      └─ casual_chat   → 拒绝消息 + 功能引导
```

SSE 事件类型：`queue` / `intent` / `notice` / `tool_progress` / `preview` / **`sources`** / `content` / `error` / `[DONE]`。

## 🌐 网络研究能力（新增）

`graph/nodes/web_research.py` + `tools/web_tools.py`：

- `web_search(query, max_results)` — DuckDuckGo（免费、无需 Key），返回 `[{title, url, snippet}]`
- `fetch_webpage(url)` — httpx 抓取 + trafilatura 抽正文（回退 BeautifulSoup），截断到 8000 字符

模型在一个 ≤6 轮的 tool-call 循环里自主：搜索 → 挑结果读取正文 → 基于真实内容做结构化「总结 + 要点分析」，并附带来源链接（前端「参考来源」卡片展示）。

触发示例：
- “联网查一下 LangGraph 的最新特性并总结”
- “帮我读这个链接 https://example.com/doc 并分析要点”

## 🗂️ 目录结构

```
cortex/
├── backend/
│   ├── main.py              # FastAPI 入口（路由 + /preview 静态 + 前端 dist + SPA fallback）
│   ├── config.py logger.py db.py auth.py init_admin.py llm_queue.py llm.py schemas.py wiki_service.py
│   ├── routers/             # auth / admin_* / conversations / chat(SSE) / queue / health
│   ├── graph/               # LangGraph：state / prompts / workflow / agent_loop
│   │   └── nodes/           # classify / knowledge_qa / generate_page / web_research / casual_chat
│   ├── tools/               # code_generator（6 工具）+ web_tools（搜索/抓取）
│   ├── wiki/                # Wiki 知识库 + Python agent（复用）
│   └── requirements.txt .env.example
└── frontend/                # React（复用 llm_test，新增「来源」UI）
```

## 🔧 环境变量（backend/.env）

| 变量 | 说明 |
|------|------|
| `PORT` | HTTP 端口（默认 8000） |
| `JWT_SECRET` / `JWT_EXPIRES_IN` | JWT 密钥 / 有效期（默认 30d） |
| `DB_PATH` | SQLite 文件（默认 cortex.db） |
| `LLM_MAX_CONCURRENT` / `LLM_REQUEST_TIMEOUT` | 队列并发 / 入队超时(s) |
| `DEEPSEEK_API_KEY` | Wiki agent 用；留空则回退到管理后台配置的主 LLM |

> 主 LLM 的 base_url / api_key / model 在管理后台配置，存数据库，不写在 .env。

## ✅ 已验证

- 后端全模块导入、DB 初始化、全部 REST 端点（登录/用户/设置/Prompt/会话/Wiki/队列/健康）
- Chat SSE 事件流（intent → notice → content/error → DONE）
- DuckDuckGo 搜索 + 网页正文抽取（真实网络）
- 前端 `tsc` + `vite build` 通过

## 📄 License

MIT
