"""JSON 配置读取与保存。"""

import json
from pathlib import Path
from typing import Any, Dict


class ConfigService:
    CONFIG_NAMES = ("app", "devices", "process", "server")

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = Path(config_dir)

    def load(self, name: str) -> Dict[str, Any]:
        path = self._path(name)
        with path.open("r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        if not isinstance(data, dict):
            raise ValueError(f"配置文件必须是 JSON 对象: {path}")
        return data

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        return {name: self.load(name) for name in self.CONFIG_NAMES}

    def save(self, name: str, data: Dict[str, Any]) -> None:
        path = self._path(name)
        temporary_path = path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)

    def _path(self, name: str) -> Path:
        if name not in self.CONFIG_NAMES:
            raise KeyError(f"未知配置名称: {name}")
        path = self.config_dir / f"{name}.json"
        if not path.is_file():
            raise FileNotFoundError(f"找不到配置文件: {path}")
        return path
