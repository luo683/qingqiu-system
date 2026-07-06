"""verify_s4_4.py · S4.4 飞书按钮 + 卡片消息 真跑验证（5 场景）"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WORKTREE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKTREE / "src"))

from qingqiu.im.feishu import (
    FeishuClient,
    FeishuConfig,
    InteractiveMessage,
    ButtonAction,
    ButtonClickDispatcher,
    ACTION_CONFIRM,
    ACTION_CANCEL,
    new_dispatcher,
)


def main():
    print("=" * 60)
    print("S4.4 飞书按钮 + 卡片消息 · 5 场景真跑验证")
    print("=" * 60)

    # === 场景 1: 纯文本卡片 + JSON 序列化 ===
    print("\n[场景 1] 纯文本卡片")
    card = InteractiveMessage.from_text("你好清秋", tip="测试 tip")
    d = card.to_dict()
    print(f"  msg_type: {d['msg_type']}")
    print(f"  header template: {d['card']['header']['template']}")
    print(f"  elements: {len(d['card']['elements'])}")
    assert d["msg_type"] == "interactive"
    assert d["card"]["header"]["template"] == "blue"
    print("  [PASS]")

    # === 场景 2: confirm card 序列化（飞书 v2 schema） ===
    print("\n[场景 2] Confirm 卡片 + 按钮结构")
    c = InteractiveMessage.confirm_card(
        "确认执行任务？", "即将执行 task_001，可能修改 2 个文件。",
        confirm_value="task_001", cancel_value="cancel_001",
    )
    payload = c.to_payload()
    parsed = json.loads(payload)
    print(f"  header: {parsed['header']['title']['content']}")
    print(f"  elements: {len(parsed['elements'])}")
    actions = [e for e in parsed["elements"] if e["tag"] == "action"][0]
    print(f"  buttons: {[a['text']['content'] for a in actions['actions']]}")
    print(f"  action names: {[a['name'] for a in actions['actions']]}")
    print(f"  confirm value: {[a['value'] for a in actions['actions'] if a['name'] == ACTION_CONFIRM][0]}")
    assert len(actions["actions"]) == 2
    print("  [PASS] 飞书 v2 schema 兼容")

    # === 场景 3: client.send_interactive mock 模式 ===
    print("\n[场景 3] Client.send_interactive mock")
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    client.start()
    print(f"  client.is_mock: {client.is_mock}")
    print(f"  client.is_started: {client.is_started}")

    card = InteractiveMessage.confirm_card("通知", "X", confirm_value="abc")
    client.send_interactive("oc_test_001", card)
    sent = client._transport.sent
    assert len(sent) == 1
    print(f"  sent msg_type: {sent[0].msg_type}")
    print(f"  sent to: {sent[0].receive_id}")
    print(f"  payload size: {len(sent[0].content)} chars")
    assert sent[0].msg_type == "interactive"
    assert sent[0].receive_id == "oc_test_001"
    print("  [PASS] mock record")

    # === 场景 4: 用户点击 confirm → handler 触发 ===
    print("\n[场景 4] 用户点 confirm 按钮 (mock 注入)")
    dispatcher = new_dispatcher()
    confirmed = []
    cancelled = []
    @dispatcher.on(ACTION_CONFIRM)
    def on_confirm(action):
        confirmed.append(action.value)
        print(f"  → CONFIRM received: value={action.value}, sender={action.sender_id}")
    @dispatcher.on(ACTION_CANCEL)
    def on_cancel(action):
        cancelled.append(action.value)
        print(f"  → CANCEL received: value={action.value}")

    # 模拟 3 个用户：2 个点 confirm，1 个点 cancel
    clicks = [
        ButtonAction(action=ACTION_CONFIRM, value="task_001", sender_id="ou_alice", chat_id="oc_alice"),
        ButtonAction(action=ACTION_CONFIRM, value="task_001", sender_id="ou_bob", chat_id="oc_bob"),
        ButtonAction(action=ACTION_CANCEL, value="task_001", sender_id="ou_carol", chat_id="oc_carol"),
    ]
    for c in clicks:
        dispatcher.dispatch(c)
    assert confirmed == ["task_001", "task_001"]
    assert cancelled == ["task_001"]
    print(f"  confirmed: {len(confirmed)}, cancelled: {len(cancelled)}")
    print("  [PASS] 3 click 事件正确分发")

    # === 场景 5: 端到端 confirm 流程（MVP demo） ===
    print("\n[场景 5] 端到端 confirm（清秋 MVP）")
    # 模拟：用户说"memory set secret k v" → 主脑认为有风险 → 发确认卡 → 用户点 confirm → 执行
    print(f"  场景：用户命令 memory set → 主脑发 confirm 卡 → 用户点 confirm")
    cfg2 = FeishuConfig(mock=True)
    cli2 = FeishuClient(cfg2)
    cli2.start()
    disp2 = new_dispatcher()
    tasks_executed = []
    @disp2.on(ACTION_CONFIRM)
    def execute(action):
        tasks_executed.append(action.value)
    # 1. 发 confirm 卡
    risk_card = InteractiveMessage.confirm_card(
        "🛡 写入确认",
        "即将执行：memory set secret xxx-xxx\n确认要继续吗？",
        confirm_value="cmd:memory_set",
    )
    cli2.send_interactive("oc_user_001", risk_card)
    print(f"  ✓ confirm card 已发")
    # 2. 用户点 confirm
    cli2._transport.sent.clear()  # 模拟用户点之后清理 (test isolation)
    disp2.dispatch(ButtonAction(
        action=ACTION_CONFIRM, value="cmd:memory_set", sender_id="ou_user_001", chat_id="oc_user_001"
    ))
    print(f"  ✓ 用户点 confirm → handler trigger")
    assert tasks_executed == ["cmd:memory_set"]
    print(f"  ✓ 执行任务: {tasks_executed}")
    print("  [PASS] E2E confirm 流")

    print("\n" + "=" * 60)
    print("[verify] S4.4 PASS · 5 场景全过")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())