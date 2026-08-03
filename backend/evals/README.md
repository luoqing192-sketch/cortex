# Cortex 自动评测（Phase 1：确定性）

把系统从「能跑」推进到「可信、可回归」。核心洞察：Cortex 的事件流
（`intent / tool_progress / sources / preview / content`）天生是评测信号源，跑器只是它的又一个消费者。

## 架构

```
datasets/*.yaml ──load──▶ runner(复用 LocalEngine 事件流) ──▶ Trajectory
                                                                  │
                                            graders(确定性注册表) ─┤─▶ Score
                                                                  ▼
                                    eval.db(eval_runs/eval_results) ──▶ report(聚合+baseline diff)
```

- **用例**：`datasets/*.yaml`（进 Git、可 review/diff）
- **跑器** `runner.py`：用 CLI 的 `LocalEngine` 进程内直跑，每用例独立会话 + 独立 `demo_code/{id}`
- **评分器** `graders/`：可插拔注册表（同构 skill）；Phase 1 全部确定性、零成本零抖动
- **结果**：写独立库 `eval.db`
- **报告** `report.py`：通过率/延迟聚合 + 与 baseline run 对比出**新失败/新通过**

## 用法（CLI）

```bash
cortex eval suites                       # 列可用套件
cortex eval run intent                   # 跑单个套件
cortex eval run                          # 跑全部
cortex eval run --json                   # JSON 输出（供 CI）
cortex eval run --fail-under 0.8         # 通过率门禁：低于则退出码=1
cortex eval run generate_page --baseline 12   # 与 run 12 对比出回归
cortex eval list                         # 历史 run
cortex eval report 12                    # 某次 run 详情
```

> `eval` 命令需 backend 可导入（`pip install -e backend/`，或从仓库根运行）。

## 用例格式

```yaml
suite: intent            # 套件名（= 文件名）
route: intent            # 被测路由：intent|knowledge_qa|generate_page|web_research|casual_chat
cases:
  - id: intent-web-001   # 唯一
    tags: [web, zh]
    input:
      message: "联网查一下 X 并总结"
      seed_history:            # 可选：预置多轮上下文
        - {role: user, content: "..."}
        - {role: assistant, content: "..."}
      attachments: []          # 可选：图片附件
    expected:
      graders:                 # 该用例要跑的评分器（全 passed 才算通过）
        - {name: intent_match, args: {expected: web_research}}
```

## 内置确定性评分器

| 名称 | 判定 |
|------|------|
| `intent_match` | `args.expected` == 实际 intent 事件 |
| `must_contain` / `must_not_contain` | 答案（子串或 `regex: true`）包含/不含 `value` 或 `values[]` |
| `tool_called` | `args.tool` 在 tool_progress 轨迹中出现 |
| `preview_emitted` | 发出了 preview 事件 |
| `sources_nonempty` | 来源数 ≥ `args.min`（默认 1） |
| `file_exists` | `artifacts_dir/args.path` 存在 |
| `html_parses` | 该文件 BeautifulSoup 可解析且非空 |
| `no_error` | 轨迹无 error 事件 |

## 加用例

编辑对应 `datasets/*.yaml` 追加一条 `case`；loader 会校验 id 唯一、message 非空、grader 名合法。

## 注意（无 LLM key 时）

`intent` / `generate_page` 套件的真实分类是一次 LLM 调用——未配 LLM 时会 401/超时，相关断言失败属**预期**。
Phase 3 引入**录制回放**后，CI 回归套件将不依赖真实 LLM（快、稳、离线）。

## 后续阶段（已留接口）

- **P2**：LLM 裁判 / groundedness / 参考对比（在 `graders/` 注册表追加，无需改跑器）
- **P3**：录制回放 + CI 门禁（GitHub Actions）
- **P4**：LangGraph 扇出并发（`run_case` 只依赖 Engine，无需重构）+ 合成数据
- **P5**：在线采样飞轮 + 裁判校准

## 测试

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_evals.py -q
```
