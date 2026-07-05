"""schema.py 测试 · Pydantic 配置模型"""

from pydantic import ValidationError
import pytest

from qingqiu.config.schema import (
    Config,
    LLMConfig,
    LoggingConfig,
    ObsidianConfig,
    PersonalityConfig,
    SecurityConfig,
    VoiceConfig,
)


def test_llm_config_defaults():
    cfg = LLMConfig()
    assert cfg.default == "anthropic"
    assert cfg.routing == {}
    assert cfg.providers == {}


def test_voice_config_defaults():
    cfg = VoiceConfig()
    assert cfg.hotkey == "ctrl+shift+q"
    assert cfg.stt_model == "small"
    assert cfg.tts_voice == "zh_CN-huayan-medium"


def test_security_config_defaults():
    cfg = SecurityConfig()
    assert cfg.confirm_writes is True
    assert cfg.auto_upload is False
    assert cfg.whitelist_dirs == []


def test_obsidian_config_defaults():
    cfg = ObsidianConfig()
    assert cfg.vault_path is None
    assert cfg.auto_discover is True
    assert ".trash/" in cfg.ignore_patterns


def test_personality_config_defaults():
    cfg = PersonalityConfig()
    assert cfg.name == "清秋"
    assert "ROG" in cfg.system_prompt


def test_config_default_complete():
    cfg = Config()
    assert cfg.version == "0.3.0"
    assert isinstance(cfg.llm, LLMConfig)
    assert isinstance(cfg.voice, VoiceConfig)
    assert isinstance(cfg.security, SecurityConfig)
    assert isinstance(cfg.logging, LoggingConfig)
    assert isinstance(cfg.obsidian, ObsidianConfig)
    assert isinstance(cfg.personality, PersonalityConfig)


def test_config_rejects_unknown_field():
    """Pydantic strict mode：禁止未定义字段（防止 typo 静默失败）"""
    with pytest.raises(ValidationError):
        Config(unknown_field="oops")


def test_config_nested_construction():
    cfg = Config(
        llm=LLMConfig(default="openai", routing={"planner": "anthropic"}),
        personality=PersonalityConfig(name="小秋"),
    )
    assert cfg.llm.default == "openai"
    assert cfg.llm.routing["planner"] == "anthropic"
    assert cfg.personality.name == "小秋"


def test_config_model_dump_json_safe():
    """model_dump 能正确输出 JSON-friendly 数据"""
    cfg = Config(personality=PersonalityConfig(name="清秋"))
    data = cfg.model_dump(mode="json", exclude_none=True)
    assert data["personality"]["name"] == "清秋"
    assert data["version"] == "0.3.0"


def test_config_model_dump_round_trip():
    """dump → load 应该不丢失信息"""
    original = Config(
        llm=LLMConfig(routing={"planner": "anthropic", "router": "openai"}),
        obsidian=ObsidianConfig(vault_path="C:\\Users\\ROG\\Documents\\Vault"),
    )
    data = original.model_dump(mode="json")
    reloaded = Config(**data)
    assert reloaded.llm.routing == original.llm.routing
    assert reloaded.obsidian.vault_path == original.obsidian.vault_path