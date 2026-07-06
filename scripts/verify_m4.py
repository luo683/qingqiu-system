"""M4 飞书 IM 真跑验证脚本（端到端 mock 链路）

Run: uv run python scripts/verify_m4.py

4 个验收场景（来自 task_prompt_M4.json）：
- M4-1: 飞书 SDK 初始化（mock credentials）
- M4-2: WebSocket 连接（mock WebSocket 事件）
- M4-3: 收到 'memory get user_name' → Executor → 回发响应
- M4-4: 收到 UNKNOWN → 回发友好提示
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 让 src/ 可 import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> int:
    # 强制 mock（无 creds 也无影响）
    os.environ["FEISHU_USE_MOCK"] = "1"

    from qingqiu.im.feishu import (
        FeishuClient,
        FeishuConfig,
        MessageHandler,
        reply,
    )
    from qingqiu.im.feishu.client import IncomingMessage

    failures: list[str] = []
    passed = 0

    def expect(label: str, ok: bool, detail: str = "") -> None:
        nonlocal passed
        if ok:
            print(f"  [PASS] {label}")
            passed += 1
        else:
            print(f"  [FAIL] {label} {detail}")
            failures.append(label)

    print("[verify] M4 飞书 IM · 4 个验收场景")
    print()

    # === 场景 1: 飞书 SDK 初始化（mock credentials） ===
    print("[scenario 1] Feishu SDK 初始化（mock）")
    cfg = FeishuConfig.from_env()
    expect("FEISHU_USE_MOCK=1 → mock=True", cfg.mock is True)
    expect("is_real=False", cfg.is_real is False)

    client = FeishuClient(cfg)
    expect("client 构造成功", client is not None)
    expect("is_started=False（未 start）", client.is_started is False)
    expect("is_mock=True", client.is_mock is True)
    expect("transport 已注入", client.transport is not None)
    expect("inbox/outbox 初始化为空",
           len(client.inbox) == 0 and len(client.outbox) == 0)

    client.start()
    expect("client.start() 后 is_started=True", client.is_started is True)
    print()

    # === 场景 2: WebSocket 连接（mock WebSocket 事件） ===
    print("[scenario 2] WebSocket 连接 + 事件注入")

    received = []

    @client.on_message
    def cb(msg: IncomingMessage):
        received.append(msg)

    # 注入多条 mock 消息
    for i in range(3):
        client.inject_mock_event(
            text=f"test msg {i}",
            sender_id=f"ou_user_{i}",
            chat_id=f"oc_chat_{i}",
        )

    expect("inbox 收到 3 条", len(client.inbox) == 3, f"got {len(client.inbox)}")
    expect("callback 触发 3 次", len(received) == 3, f"got {len(received)}")
    expect("第 1 条文本 = 'test msg 0'", received[0].text == "test msg 0")
    expect("第 3 条 chat_id = 'oc_chat_2'", received[2].chat_id == "oc_chat_2")
    print()

    # === 场景 3: 收到 'memory get user_name' → Executor → 回发响应 ===
    print("[scenario 3] memory get → Executor → 回发")

    handler = MessageHandler()
    msg = IncomingMessage(
        sender_id="ou_user_x",
        chat_id="oc_chat_e2e",
        text="memory set user_name ROG",  # 先 set
    )
    client.inject_mock_event(msg.text, sender_id=msg.sender_id, chat_id=msg.chat_id)
    set_result = handler.on_message(
        client.inbox[-1]  # 最后一条
    )
    expect("memory set intent", set_result.intent == "memory_set")
    expect("memory set exit_code=0", set_result.exit_code == 0)

    # 回发 set 响应
    rr_set = reply(msg, set_result.text, client=client)
    expect("reply(set) ok=True", rr_set.ok)
    expect("outbox 追加 1 条", len(client.outbox) == 1)
    expect("outbox[0].chat_id=oc_chat_e2e", client.outbox[0].chat_id == "oc_chat_e2e")

    # 然后 get
    msg2 = IncomingMessage(
        sender_id="ou_user_x",
        chat_id="oc_chat_e2e",
        text="memory get user_name",
    )
    client.inject_mock_event(msg2.text, sender_id=msg2.sender_id, chat_id=msg2.chat_id)
    get_result = handler.on_message(client.inbox[-1])
    expect("memory get intent", get_result.intent == "memory_get")
    expect("memory get exit_code=0", get_result.exit_code == 0)
    expect("memory get text 非空", bool(get_result.text), f"got {get_result.text!r}")

    # 回发 get 响应
    rr_get = reply(msg2, get_result.text, client=client)
    expect("reply(get) ok=True", rr_get.ok)
    expect("outbox 追加 2 条", len(client.outbox) == 2)

    # 验证回发的内容
    out_text = client.outbox[-1].text
    print(f"    (reply text preview: {out_text[:80]!r})")
    print()

    # === 场景 4: 收到 UNKNOWN → 回发友好提示 ===
    print("[scenario 4] UNKNOWN → 友好提示")

    unknown_text = "xyzabc random gibberish 9999"
    msg3 = IncomingMessage(
        sender_id="ou_user_y",
        chat_id="oc_chat_unknown",
        text=unknown_text,
    )
    client.inject_mock_event(msg3.text, sender_id=msg3.sender_id, chat_id=msg3.chat_id)
    unk_result = handler.on_message(client.inbox[-1])

    expect("unknown intent", unk_result.intent == "unknown")
    expect("unknown exit_code != 0", unk_result.exit_code != 0)
    expect("unknown text 含 '试试' 或 '未识别'",
           "试试" in unk_result.text or "未识别" in unk_result.text)
    expect("unknown text 含示例指令", "memory" in unk_result.text)

    # 回发
    rr_unk = reply(msg3, unk_result.text, client=client)
    expect("reply(unknown) ok=True", rr_unk.ok)
    expect("outbox 追加 3 条", len(client.outbox) == 3)
    expect("回发的 text 含 '试试' 或 '未识别'",
           "试试" in client.outbox[-1].text or "未识别" in client.outbox[-1].text)

    client.stop()
    print()

    # === 总结 ===
    print("=" * 60)
    if failures:
        print(f"[verify] M4 FAIL · {len(failures)} failures:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"[verify] M4 PASS · {passed}/{passed} scenarios passed")
    print()
    print("Summary:")
    print(f"  · inbox (received): {len(client.inbox)}")
    print(f"  · outbox (sent): {len(client.outbox)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())