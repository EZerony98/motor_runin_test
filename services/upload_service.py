"""测试结果服务器上传服务。"""

import json
import time
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class UploadService:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", False))

    def upload(self, record: Dict[str, Any]) -> int:
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
                request = Request(
                    url,
                    data=json.dumps(record, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    method="POST",
                )
                with urlopen(request, timeout=timeout) as response:
                    response.read()
                    return int(response.status)
            except (HTTPError, URLError, TimeoutError, OSError) as error:
                last_error = error
                if attempt + 1 < retry_count:
                    time.sleep(retry_interval)

        raise RuntimeError(f"上传失败，已重试 {retry_count} 次") from last_error
