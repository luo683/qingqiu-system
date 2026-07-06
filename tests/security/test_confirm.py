"""S5.1 测试 · Confirm 通用框架"""

import time

import pytest

from qingqiu.security.confirm import (
    CLIPrompter,
    Confirm,
    ConfirmRejected,
    ConfirmTimeout,
    Prompter,
    ask,
    get_default_confirm,
)


# === CLIPrompter · 注入式 input 测试 ===

def test_cli_prompter_user_says_yes():
    """用户输入 'y' 返回 True"""
    p = CLIPrompter(input_func=lambda _: "y")
    assert p.ask("Apply changes?", timeout_sec=1) is True


def test_cli_prompter_user_says_yes_full():
    p = CLIPrompter(input_func=lambda _: "yes")
    assert p.ask("Apply changes?", timeout_sec=1) is True


def test_cli_prompter_user_says_no():
    """用户输入 'n' 返回 False"""
    p = CLIPrompter(input_func=lambda _: "n")
    assert p.ask("Apply changes?", timeout_sec=1) is False


def test_cli_prompter_user_says_empty():
    """空输入（默认 N）返回 False"""
    p = CLIPrompter(input_func=lambda _: "")
    assert p.ask("Apply changes?", timeout_sec=1) is False


def test_cli_prompter_user_says_diff_then_yes():
    """输入 diff 后再 yes"""
    responses = iter(["diff", "y"])
    p = CLIPrompter(input_func=lambda _: next(responses))
    assert p.ask("Apply changes?", timeout_sec=1) is True


def test_cli_prompter_user_says_diff_then_no():
    responses = iter(["diff", "n"])
    p = CLIPrompter(input_func=lambda _: next(responses))
    assert p.ask("Apply changes?", timeout_sec=1) is False


def test_cli_prompter_timeout_returns_false():
    """超时返回 False"""
    def slow_input(_):
        time.sleep(5)
        return "y"
    p = CLIPrompter(input_func=slow_input)
    assert p.ask("Apply?", timeout_sec=1) is False


def test_cli_prompter_invalid_input_then_yes():
    """无效输入后再 y"""
    responses = iter(["xyz", "y"])
    p = CLIPrompter(input_func=lambda _: next(responses))
    assert p.ask("Apply?", timeout_sec=1) is True


# === Confirm · 包装层 ===

def test_confirm_agree_returns_true():
    p = CLIPrompter(input_func=lambda _: "y")
    c = Confirm(prompter=p, default_timeout=1)
    assert c.ask("Apply 3 changes?") is True


def test_confirm_reject_raises():
    p = CLIPrompter(input_func=lambda _: "n")
    c = Confirm(prompter=p, default_timeout=1)
    with pytest.raises(ConfirmRejected):
        c.ask("Apply 3 changes?")


def test_confirm_timeout_raises():
    def slow_input(_):
        time.sleep(5)
        return "y"
    p = CLIPrompter(input_func=slow_input)
    c = Confirm(prompter=p, default_timeout=1)
    with pytest.raises(ConfirmRejected):
        c.ask("Apply?")


def test_confirm_custom_timeout():
    """自定义 timeout 参数覆盖 default"""
    def slow_input(_):
        time.sleep(2)
        return "y"
    p = CLIPrompter(input_func=slow_input)
    c = Confirm(prompter=p, default_timeout=10)  # 默认 10s
    # 但传 1s → 1s 后超时
    with pytest.raises(ConfirmRejected):
        c.ask("Apply?", timeout_sec=1)


def test_confirm_default_prompter_is_cli():
    """无 prompter 参数时默认 CLIPrompter"""
    c = Confirm()
    assert isinstance(c.prompter, CLIPrompter)


# === 异常体系 ===

def test_confirm_rejected_is_cli_error():
    """ConfirmRejected 继承 CLIError code=1"""
    from qingqiu.cli.errors import CLIError
    assert issubclass(ConfirmRejected, CLIError)
    assert ConfirmRejected.code == 1


def test_confirm_timeout_is_rejected():
    """ConfirmTimeout 继承 ConfirmRejected"""
    assert issubclass(ConfirmTimeout, ConfirmRejected)


def test_confirm_timeout_specific_message():
    """ConfirmTimeout 消息含秒数"""
    e = ConfirmTimeout(timeout_sec=30)
    assert "30" in str(e)
    assert "timeout" in str(e).lower()


# === Prompter 抽象 ===

def test_prompter_is_abstract():
    """Prompter 不能直接实例化"""
    with pytest.raises(TypeError):
        Prompter()


def test_custom_prompter_works():
    """用户可实现自定义 Prompter"""

    class AlwaysYesPrompter(Prompter):
        def ask(self, summary: str, timeout_sec: int = 60) -> bool:
            return True

    c = Confirm(prompter=AlwaysYesPrompter())
    assert c.ask("anything?") is True


class AlwaysNoPrompter(Prompter):
    def ask(self, summary: str, timeout_sec: int = 60) -> bool:
        return False


def test_custom_always_no_prompter():
    c = Confirm(prompter=AlwaysNoPrompter())
    with pytest.raises(ConfirmRejected):
        c.ask("anything?")


# === 便捷函数 ===

def test_default_confirm_singleton():
    """get_default_confirm 返回单例"""
    a = get_default_confirm()
    b = get_default_confirm()
    assert a is b


def test_ask_function_works():
    """便捷函数 ask() 用默认 singleton"""
    import io
    import sys

    # patch input
    import qingqiu.security.confirm as confirm_mod
    old_input = confirm_mod.CLIBrompter.__init__ if False else None
    confirm_mod._default_confirm = Confirm(
        prompter=CLIPrompter(input_func=lambda _: "y")
    )
    assert ask("test?", timeout_sec=1) is True
    # 重置 singleton
    confirm_mod._default_confirm = None


# === 集成测试 · Confirm + Whitelist + Blacklist ===

def test_full_security_check_path(tmp_path):
    """写文件前完整流程：whitelist + Confirm"""
    from qingqiu.security.whitelist import check_path
    target = tmp_path / "test.txt"
    # 在白名单外的路径应被拒
    with pytest.raises(Exception):  # WhitelistError
        check_path(__import__("pathlib").Path("C:/Windows/test.txt"))