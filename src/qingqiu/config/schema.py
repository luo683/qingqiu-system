"""清秋配置 schema · 用 Pydantic 定义所有可配置项"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM provider 配置"""

    default: str = "anthropic"  # 默认 provider 名
    routing: dict[str, str] = Field(
        default_factory=dict,
        description="按角色分派 provider · 例: {planner: anthropic, router: openai}",
    )
    providers: dict[str, dict] = Field(
        default_factory=dict,
        description="provider 特定参数 · 例: {anthropic: {default_model: claude-sonnet-4-5}}",
    )


class VoiceConfig(BaseModel):
    """语音入口配置"""

    hotkey: str = "ctrl+shift+q"
    stt_model: str = "small"  # whisper model: tiny/base/small/medium/large-v3
    tts_voice: str = "zh_CN-huayan-medium"  # piper voice


class SecurityConfig(BaseModel):
    """安全与权限配置"""

    confirm_writes: bool = True  # 每次写入前询问
    whitelist_dirs: list[str] = Field(
        default_factory=list,
        description="可读目录白名单",
    )
    auto_upload: bool = False  # 是否允许自动上传到云端（默认关）


class LoggingConfig(BaseModel):
    """日志配置"""

    level: str = "INFO"  # DEBUG/INFO/WARNING/ERROR
    max_bytes: int = 100 * 1024 * 1024  # 100MB
    backup_count: int = 7  # 保留 7 天


class ObsidianConfig(BaseModel):
    """Obsidian 知识库配置"""

    vault_path: str | None = None  # vault 根目录路径
    auto_discover: bool = True
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [".trash/", ".obsidian/cache/", "*.tmp"],
    )


class PersonalityConfig(BaseModel):
    """人格 / prompt 配置"""

    name: str = "清秋"
    system_prompt: str = "你是清秋，给 ROG 个人使用。\n风格：简洁、直接、技术男、偶尔幽默。\n不说废话、不用 emoji。\n用中文回复，技术名词保留英文。"
    voice_style: dict[str, str] = Field(
        default_factory=lambda: {"tts_voice": "zh_CN-huayan-medium", "pace": "1.0"},
    )


class Config(BaseModel):
    """清秋总配置"""

    version: str = "0.3.0"

    llm: LLMConfig = Field(default_factory=LLMConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    obsidian: ObsidianConfig = Field(default_factory=ObsidianConfig)
    personality: PersonalityConfig = Field(default_factory=PersonalityConfig)

    model_config = {"extra": "forbid"}  # 禁止未定义字段，避免 typo 静默失败