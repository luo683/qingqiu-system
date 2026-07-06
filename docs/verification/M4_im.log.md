# M4 验证日志 · 飞书 IM 全链路

> **切片**：M4 · S4.1 + S4.2 + S4.3（飞书 WebSocket 客户端 / 消息→Router / 响应回发）
> **状态**：✅ PASS
> **分支**：`slice/M4`
> **日期**：2026-07-06 13:42
> **验证脚本**：`scripts/verify_m4.py`

## 1. 单元 / 集成测试（67/67 PASS）

```
tests/im/test_client.py      · 19 tests · FeishuConfig + FeishuClient + IncomingMessage + MockTransport + 文本提取
tests/im/test_handler.py     · 19 tests · MessageHandler + Sender + 端到端 memory/task/status/UNKNOWN
tests/im/test_reply.py       · 19 tests · reply() + chat_id 提取 + 长文本分 chunk + 默认 client
tests/im/test_e2e.py         ·  5 tests · 端到端 WS→Handler→Reply（含中文 / UNKNOWN / 多消息串行）
tests/im/test_integration.py ·  5 tests · 集成：mock memory set/get/list + multi-user 隔离

============================= 67 passed in 0.38s ==============================
```

### 覆盖矩阵

| 类别 | 测试 | 说明 |
|------|------|------|
| Config | `test_config_from_env_no_creds_is_mock` | 无 creds → mock |
| Config | `test_config_from_env_with_creds_is_real` | 有 creds → real |
| Config | `test_config_force_mock_overrides_creds` | FEISHU_USE_MOCK=1 强制 mock |
| 生命周期 | `test_client_mock_start_stop` / `_double_start_raises` / `_double_stop_is_idempotent` | start/stop 幂等性 |
| API | `test_client_on_message_decorator` / `_register_message_callback` | 装饰器风格 + 函数式 |
| API | `test_client_inject_message_dispatches` | 注入触发回调 |
| API | `test_client_send_message_text` / `_with_open_id_type` | 发送文本（含 open_id 模式） |
| 数据 | `test_incoming_message_defaults` / `_all_fields` | dataclass 默认值与全字段构造 |
| 数据 | `test_extract_text_from_message` / `_post_type` / `_invalid_json` | text / post / JSON 容错提取 |
| Transport | `test_mock_transport_basic` / `_reset` | MockTransport 隔离与重置 |
| Routing | `test_handler_routes_memory_get` / `_set` / `_task_add` / `_status` | Executor 复用 |
| Routing | `test_handler_unknown_returns_friendly` / `_english` | UNKNOWN 友好回退 |
| Routing | `test_handler_empty_text` / `_whitespace_text` | 空 / 空白消息 |
| Routing | `test_handler_extra_contains_chat_id` / `_extract_intent_for_known` / `_unknown` | HandlerResult 元数据 |
| Routing | `test_handler_does_not_propagate_executor_exception` | 异常隔离 |
| Routing | `test_handler_captures_multi_line_output` / `_stream_is_isolated` | stream 输出捕获与隔离 |
| Routing | `test_aon_message_sync_result` | async wrapper |
| Routing | `test_get_default_handler_creates_executor` / `_with_executor` | 工厂 |
| Routing | `test_sender_defaults` | Sender dataclass |
| Reply | `test_reply_with_incoming_message` / `_dict_target` / `_str_target` | 多形态 target |
| Reply | `test_reply_falls_back_to_sender_id_when_no_chat` | 缺 chat_id 回退 |
| Reply | `test_reply_uses_default_client` / `_no_client_returns_error` | 默认 client + 缺 client 错误 |
| Reply | `test_reply_empty_text_returns_ok_no_chunks` | 空文本不发送 |
| Reply | `test_reply_client_not_started_returns_error` | 未启动 client 错误 |
| Reply | `test_reply_no_chat_id_returns_error` | 无 chat_id 错误 |
| Reply | `test_reply_long_text_chunks` / `_short_text_no_chunk` | 长文本切分 |
| Reply | `test_reply_open_id_type` | receive_id_type 透传 |
| Reply | `test_chunk_text_short_no_chunk` / `_long_splits` / `_handles_no_break` | chunk 切分算法 |
| Reply | `test_extract_chat_id_from_incoming` / `_dict` / `_str` / `_invalid_type` | chat_id 提取 |
| E2E | `test_e2e_memory_get_via_client_callback` | WS → Handler → Reply |
| E2E | `test_e2e_unknown_message_friendly` | UNKNOWN 友好回发 |
| E2E | `test_e2e_multiple_messages_serial` | 多条消息串行（含中文） |
| E2E | `test_e2e_message_with_chinese_text` | 中文 task_add 链路 |
| E2E | `test_e2e_handler_callback_runs_after_inject` | 回调真触发 |
| Integration | `test_e2e_memory_set_then_get` / `_memory_list` | IM 全链路 memory |
| Integration | `test_e2e_unknown_returns_friendly` | IM 全链路 UNKNOWN |
| Integration | `test_e2e_multi_user_separate_chats` | 多 chat 隔离（共享 L3） |
| Integration | `test_e2e_inbox_outbox_grows_symmetrically` | 收发对称 |

## 2. 全量回归（543/543 PASS · M4 worktree）

```
============================= 543 passed in 9.33s =============================
```

M4 新增 67 测试（476 → 543 = 476 + 67）。零回归。

## 3. 真跑验证（4/4 场景全 PASS · `scripts/verify_m4.py`）

```
============================================================
[verify] M4-1 · 飞书 SDK 初始化（mock credentials）
============================================================
  · no creds                 → mock=True, started=False
  · creds + mock=True        → mock=True, started=False
  · mock=False + empty creds → mock=True（自动降级）
  · creds + mock=False       → is_real=True（MVP 不连真飞书）
  [OK] M4-1 · 4 个 config 模式全部初始化成功
```

```
============================================================
[verify] M4-2 · WebSocket 连接（mock 事件循环）
============================================================
  · 启动前: started=False
  · 启动后: started=True, mode=mock
  · 收到: sender=ou_user_alpha, text='ping'
  · 收到: sender=ou_user_beta,  text='pong'
  · 收到: sender=ou_user_alpha, text='中文也试试'
  · 收到 3 条消息（mock WS 事件循环 ✓）
  · 停止后: started=False
  [OK] M4-2 · WS 连接 + 事件分发正常
```

```
============================================================
[verify] M4-3 · memory set/get 端到端（IM 全链路）
============================================================
  · 用户: memory set user_name ROG
  · 飞书收到回发: set 'user_name' in L3 (length=3)
                    [router] intent=memory_set source=rule
  · 用户: memory get user_name
  · 飞书收到回发: ▶ memory get
                    {
                      "key": "user_name",
                      "value": "ROG",
                      "layer": "L3"
                    }
                    [router] intent=memory_get source=rule
  [OK] M4-3 · memory set/get 全链路：set 已发 → get 响应含 ROG/L3 ✓
```

```
============================================================
[verify] M4-4 · 未知意图 → 飞书友好提示
============================================================
  · 用户: 随便说点乱码 123
  · 飞书收到回发: 未识别意图（source=fallback, reason=no rule matched + no LLM）。
                    试试：'memory get user_name' / 'task add 写文档' / '看任务' / 'status'
  [OK] M4-4 · UNKNOWN 给出友好提示 + 示例指令 ✓
```

```
============================================================
[verify] M4 PASS · 4/4 场景全过
============================================================
```

## 4. 验收结论

| 验收项 | 结果 |
|--------|------|
| S4.1 飞书 WebSocket 客户端（lark-oapi SDK + mock fallback） | ✅ FeishuClient + FeishuConfig + MockTransport |
| S4.2 消息 → Router 接入（IM 文本走 Executor） | ✅ MessageHandler.on_message → Executor.execute（复用零业务） |
| S4.3 IM 响应回发（Executor 输出 → 飞书 send_message） | ✅ reply() + chunk（>4000 字符切分） |
| MVP 不依赖真实飞书账号 | ✅ MockTransport + FEISHU_USE_MOCK=1 强制 mock |
| mock credentials 可测连接 | ✅ M4-1 |
| mock WebSocket 事件可接收 | ✅ M4-2 + inject_message |
| `memory get user_name` 端到端可见 | ✅ M4-3 + response 含 "ROG" / "L3" |
| UNKNOWN 指令友好提示 | ✅ M4-4 + 含示例指令 |
| 全量测试 ≥ 476 不回归 | ✅ 543/543 PASS |
| 单元测试 ≥ 12 | ✅ 67 个 im 测试（远超 20 目标） |
| 验收 4 场景全 PASS | ✅ |

## 5. 设计要点

### 复用 Executor 优先
- **零新业务**：MessageHandler 只做 `Executor.execute(text, out)` 包装
- **零新路由**：分类 + 实体提取 + 路由全部走 `qingqiu.router.executor.Executor`
- **零新存储**：L3 / TaskStore / Memory facade 完全不动
- **零新 CLI**：消息 → Executor 链路全复用

### 双模设计（real / mock）
- **mock 模式**：无 `FEISHU_APP_ID`/`FEISHU_APP_SECRET` 或 `FEISHU_USE_MOCK=1` → MockTransport
  - `MockTransport.inject_message(msg)` 模拟飞书推送
  - `MockTransport.send_message(...)` 记录到 `.sent` 列表
  - 不联网 / 不需要 lark-oapi 后端
- **real 模式**：lark_oapi.ws.Client + EventDispatcherHandler 真实连飞书 OpenAPI
  - `_on_lark_message` 把 lark P2ImMessageReceiveV1 事件归一化为 IncomingMessage
  - `send_message` 走 lark CreateMessageRequest API

### 统一内部表示
- `IncomingMessage` 不依赖 lark SDK（dataclass 字段：`text` / `sender_id` / `chat_id` / `message_id` 等）
- `HandlerResult` 携带 `intent` / `exit_code` / `text` / `extra` 便于回执 + 日志
- 飞书 `receive_id_type` 支持 `chat_id`（群）和 `open_id`（私聊）

### 长文本切分
- 飞书单条消息限制 ~4000 字符（保守值 `MAX_MESSAGE_CHARS = 4000`）
- `_chunk_text` 优先按 `\n\n` 切，fallback 到 `\n`，再 fallback 到空格，最后硬切
- 测试覆盖：短文本不切、长文本切多段、无换行长文本硬切

### 异常隔离
- Executor 异常在 MessageHandler 内部捕获 → 返回 "内部错误：..."，不传播
- callback 异常在 `_dispatch` 捕获 → log 后继续（不影响后续消息）
- mock 模式 `inject_message` 中 callback 异常也被 `_dispatch_sync` 捕获

### inbox / outbox 兼容层
- `FeishuClient.inbox` / `outbox` 暴露在 client 上（测试断言用）
- real 模式 `_on_lark_message` 注入到 inbox
- mock 模式 transport.sent 持久所有 send

### Chat 多形态 target
- `reply(target, ...)` 支持：
  - `IncomingMessage` → 提取 `chat_id`
  - `dict` → 取 `chat_id`/`sender_id` 字段
  - `str` → 直接当 chat_id
  - 其他 → 返回 error

## 6. 文件清单

```
pyproject.toml
├── dependencies += lark-oapi>=1.7.0
├── dependencies += websockets>=15.0.1

src/qingqiu/im/
├── __init__.py                              (导出 feishu.*)
└── feishu/
    ├── __init__.py                          (~30 lines · 公开 API)
    ├── client.py                            (~411 lines · FeishuConfig + FeishuClient + 消息类型)
    ├── mock.py                              (~152 lines · MockTransport + sent/received)
    ├── handler.py                           (~180 lines · MessageHandler + Sender + HandlerResult)
    └── reply.py                             (~143 lines · reply() + chunk)

tests/im/
├── __init__.py
├── test_client.py                           (19 tests · config / client / transport)
├── test_handler.py                          (19 tests · handler 端到端)
├── test_reply.py                            (19 tests · reply 模块)
├── test_e2e.py                              ( 5 tests · WS→Handler→Reply)
└── test_integration.py                      ( 5 tests · 集成场景)

scripts/
└── verify_m4.py                             (4 场景真跑验证)
```

## 7. 集成点

### 已被 M4 启用
- 飞书 IM 端到端：`@client.on_message` → `handler.on_message(msg)` → `reply(msg, result.text, client=client)`
- mock-first：单测 + 集成测试 + CI 全可跑（无需飞书账号）
- `set_default_client(client)` + `get_default_client()` 支持单实例场景

### 接 M4-S4.4
- S4.4 · Confirm 飞书卡片按钮：`P2CardActionTrigger` 事件接入类似 `P2ImMessageReceiveV1` 模式
- `_on_card_action(data)` 把卡片回调归一化为 IncomingMessage → handler 处理 → reply

### 接未来切片
- 多 IM 渠道：`im/telegram/` `im/slack/` 等可复用 `MessageHandler` 接口
- chat 子命令复用：`qingqiu chat "<text>"` → Executor 同链路

## 8. 已知限制 / 待办

### MVP 局限
- IM 回复文本直接是 OutputFormatter 输出（含 `\u25b6 memory get`、JSON 结构、emoji 前缀）；飞书端可能渲染稍粗
  - **后续**：S4+ 切片可加 `IMOutputFormatter` 简化输出（IM 友好单行）
- 真实模式需要真实飞书 app credentials + 外网；MVP 未在真飞书联调
- `_on_lark_message` 中 `sender_name` 暂用 `union_id` 占位（生产环境应取 `name` 字段）

### 与 S4.1 验收清单差异
- 任务 prompt 要求 `init(app_id, app_secret)` / `start()` / `stop()` 三入口
  - 当前实现：`FeishuConfig(app_id, app_secret, mock)` + `FeishuClient(config)` + `start()` / `stop()`
  - 等价（caller 把 app_id/secret 放进 config 而非直接传给 client）

### 测试中发现并修复的问题
- **L3 / TaskStore 全局状态污染**：`test_e2e_multiple_messages_serial` 单跑因共享 HOME 触发意外 chunk
  - **修复**：加 `isolated_home` fixture，monkeypatch HOME/USERPROFILE 到 `tmp_path`
  - **教训**：所有用 Executor 的测试都应隔离 HOME（已修复 test_e2e.py，test_handler.py / test_integration.py 已有等价 fixture）

### 与现有切片的依赖
- **`observability/logger.py`**：handler 复用 `get_logger(name)`
- **`cli/output.py`**：handler 内部构造 OutputFormatter 捕获 stream
- **`router/executor.py`**：handler 完全复用 `Executor.execute(text, out)`
- **`router/intent.py`**：`HandlerResult.intent` 从 Intent enum 派生

## 9. M4 链路完整图

```
用户手机飞书发 "memory get user_name"
    ↓
[飞书 OpenAPI 服务器]
    ↓ (WebSocket 推送 p2_im_message_receive_v1)
[lark-oapi ws.Client (real 模式)]                    [MockTransport.inject_message (mock 模式)]
    ↓                                                          ↓
[qingqiu/im/feishu/client.py::_on_lark_message]    [_dispatch]
    ↓                                                          ↓
    └──────────────→ IncomingMessage (dataclass) ←──────────────┘
                              ↓
              [qingqiu/im/feishu/handler.py::MessageHandler.on_message]
                              ↓
              [qingqiu/router/executor.py::Executor.execute]
                              ↓
              [qingqiu/router/classifier.py::IntentClassifier] → MEMORY_GET
                              ↓
              [qingqiu/router/executor.py::_extract_entities] → {"key": "user_name"}
                              ↓
              [qingqiu/cli/memory.py::run_memory_get]
                              ↓
              [qingqiu/memory/manager.py::Memory.get] → L3 SQLite lookup
                              ↓
              HandlerResult(text="▶ memory get\n{...}\n[router] intent=memory_get source=rule",
                            intent="memory_get",
                            exit_code=0,
                            extra={"chat_id": "oc_xxx", "sender_id": "ou_xxx"})
                              ↓
              [qingqiu/im/feishu/reply.py::reply(msg, result.text, client=client)]
                              ↓
                              ↓ (long text >4000 chars → chunk)
              [qingqiu/im/feishu/client.py::send_message]
                              ↓
                              ↓ (lark CreateMessageRequest - real) || (MockTransport.send_message - mock)
                              ↓
[飞书 OpenAPI 服务器] → 用户手机收到 bot 回发 ✓
```

**链路完整：手机 → 飞书 → daemon → Executor → Memory → 回发 → 手机** ✅

## 10. 状态

- **M4 进度**：0 → **3/4**（S4.1/S4.2/S4.3 done；S4.4 Confirm 卡片按钮留待）
- **总进度**：14 → 15 切片
- **测试**：476 → 543（+67）
- **下一步**：S4.4 Confirm 卡片按钮 / commit + merge
