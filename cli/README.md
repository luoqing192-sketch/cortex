# Cortex CLI

Cortex 的终端客户端 —— 像 Claude Code 一样在命令行里对话、生成代码、联网研究，支持**图片输入**。

双模架构：
- **remote（默认）**：连后端 `/api` + SSE，复用认证/队列/持久化/四路路由/网络研究。
- **local（`--local`）**：进程内直接跑 LangGraph workflow，离线、无需启动后端（需装 backend）。

## 安装

```bash
# 远程模式（仅需连后端）
pip install -e cli/

# 若要 local 离线模式，额外装 backend
pip install -e backend/

# 交互式增强（历史/多行）
pip install -e "cli/[repl]"
```

安装后得到全局命令 `cortex`。

## 快速开始

```bash
cortex config set api_url http://localhost:8000
cortex login                       # admin / 123456
cortex whoami
cortex chat "帮我做一个 TodoList 页面"   # 一次性，流式输出
cortex chat                        # 无参 → 进入交互式 REPL
```

## 命令

| 命令 | 说明 |
|------|------|
| `cortex chat [消息]` | 一次性对话；省略消息进 REPL；`-` 从 stdin 读 |
| `cortex login / logout / whoami` | 认证（token 存 keyring，回退 `~/.cortex/credentials`） |
| `cortex conv list / new / rm / switch` | 会话管理 |
| `cortex config get / set / list` | 本地配置 `~/.cortex/config.toml` |
| `cortex skill / mcp / schedule` | 平台化能力（预留，未实现） |

### chat 选项

```
-c, --conversation <id>   指定会话（默认用 last 或自动新建）
    --image <path>        携带图片（可多次，多模态）
    --local / --remote    覆盖默认模式
-q, --quiet               只输出最终回答（纯文本，可管道）
    --json                每事件一行 NDJSON（供脚本消费）
```

### 脚本化示例

```bash
echo "总结这段文字：..." | cortex chat -              # 管道
cortex chat -q "一句话解释 LangGraph" | tee out.txt    # 纯文本
cortex chat --json "联网查 X" | jq 'select(.type=="sources")'  # 结构化
```

### 图片输入

```bash
# 一次性
cortex chat --image screenshot.png "这张图里有什么？"
cortex chat --image a.png --image b.jpg "对比这两张图"

# REPL 内
› /image ./chart.png     # 附加到下一条消息
› 帮我分析这张图表
```

> 需要在管理后台把 LLM 配成 **vision 模型**，否则模型端会返回错误（经 error 事件反馈）。

## REPL 斜杠命令

```
/new [标题]     新建会话并切换
/list           列出会话
/switch <id>    切换会话
/rm <id>        删除会话
/image <path>   为下一条消息附加图片
/images         查看待发图片
/clear          清空待发图片
/help /exit
```

## 环境变量

`CORTEX_API_URL` · `CORTEX_TOKEN` · `CORTEX_MODE` · `CORTEX_HOME`（配置目录，默认 `~/.cortex`）。
优先级：环境变量 > 配置文件 > 默认值。

## 测试

```bash
cd cli && python -m pytest tests -q
```
