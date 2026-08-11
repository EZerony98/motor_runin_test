"""向频谱电脑同步托盘坑位与产品 SN 映射。"""

from typing import Any, Dict

import requests


class TrayMappingSyncService:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = dict(config or {})

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", False))

    def send(self, batch: Dict[str, Any]) -> None:
        if not self.enabled:
            raise RuntimeError("频谱电脑映射同步未启用")
        base_url = str(self.config.get("base_url", "")).rstrip("/")
        if not base_url:
            raise RuntimeError("未配置频谱电脑映射服务地址")
        token = str(self.config.get("token", ""))
        headers = {"X-Line-Token": token} if token else {}
        response = requests.post(
            base_url + "/api/v1/tray-mappings",
            json=batch,
            headers=headers,
            timeout=float(self.config.get("timeout_seconds", 2)),
        )
        response.raise_for_status()
