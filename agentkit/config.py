"""Configuration loading utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


@dataclass
class ModelSettings:
    provider: str
    name: str
    temperature: float = 0.0


@dataclass
class ToolSettings:
    wikipedia: bool = True
    requests: bool = True
    python_repl: bool = False


@dataclass
class AgentConfig:
    model: ModelSettings
    tools: ToolSettings
    raw: Dict[str, Any]


def load_config(config_path: str | Path = "agent.yaml") -> AgentConfig:
    load_dotenv(override=False)
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Agent config not found at {path}")
    data: Dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    model_cfg = data.get("model", {})
    tool_cfg = data.get("tools", {})
    model = ModelSettings(
        provider=model_cfg.get("provider", "openai"),
        name=model_cfg.get("name", "gpt-3.5-turbo"),
        temperature=float(model_cfg.get("temperature", 0.0)),
    )
    tools = ToolSettings(
        wikipedia=bool(tool_cfg.get("wikipedia", True)),
        requests=bool(tool_cfg.get("requests", True)),
        python_repl=bool(tool_cfg.get("python_repl", False)),
    )
    return AgentConfig(model=model, tools=tools, raw=data)


def data_dir() -> Path:
    path = Path(os.getenv("AGENTKIT_DATA", "./data"))
    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = ["AgentConfig", "ModelSettings", "ToolSettings", "load_config", "data_dir"]
