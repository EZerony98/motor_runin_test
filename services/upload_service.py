"""测试结果服务器上传服务。"""

import time
from typing import Any, Dict

import requests


class UploadService:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", False))

    def upload(self, record: Dict[str, Any]) -> requests.Response:
        if not self.enabled:
            raise RuntimeError("服务器上传功能未启用")

        url = (
            str(self.config.get("base_url", "")).rstrip("/")
            + "/"
            + str(self.config.get("upload_path", "")).lstrip("/")
        )
        timeout = float(self.config.get("timeout_seconds", 10))
        retry_count = max(1, int(self.config.get("retry_count", 3)))
        retry_interval = max(0.0, float(self.config.get("retry_interval_seconds", 5)))

        last_error = None
        for attempt in range(retry_count):
            try:
                response = requests.post(url, json=record, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as error:
                last_error = error
                if attempt + 1 < retry_count:
                    time.sleep(retry_interval)

        raise RuntimeError(f"上传失败，已重试 {retry_count} 次") from last_error
