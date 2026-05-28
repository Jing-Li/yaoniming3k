"""ProjectConfig — 项目级全局配置加载模块

从 configs/project.yaml 读取项目全局配置。
优先级：内嵌默认值 < project.yaml
project.yaml 不存在时静默降级到默认值，不报错。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


_DEFAULTS: dict[str, Any] = {
    "data_dir": "/home/user/data",
    "output_dir": "./runs",
    "api_port": 8001,
}


@dataclass
class ProjectConfig:
    data_dir: str = field(default_factory=lambda: _DEFAULTS["data_dir"])
    output_dir: str = field(default_factory=lambda: _DEFAULTS["output_dir"])
    api_port: int = field(default_factory=lambda: _DEFAULTS["api_port"])

    @classmethod
    def load(cls, project_root: Path | None = None) -> "ProjectConfig":
        """从 project_root/configs/project.yaml 加载配置。

        project_root 为 None 时自动推断为 caisen 包的上级目录（即项目根）。
        文件不存在时返回默认值。
        """
        if project_root is None:
            # __file__ = src/caisen/config/project_config.py
            # 向上三级到达 src/，再上一级到项目根
            project_root = Path(__file__).parent.parent.parent.parent

        config_path = project_root / "configs" / "project.yaml"

        data: dict[str, Any] = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    data = loaded

        return cls(
            data_dir=str(data.get("data_dir", _DEFAULTS["data_dir"])),
            output_dir=str(data.get("output_dir", _DEFAULTS["output_dir"])),
            api_port=int(data.get("api_port", _DEFAULTS["api_port"])),
        )
