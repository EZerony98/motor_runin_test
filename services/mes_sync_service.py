"""MES heartbeat and reliable local-outbox synchronization."""

import json
import os
import socket
from typing import Any, Dict, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class MesSyncService:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = dict(config or {})

    @property
    def enabled(self) -> bool:
        return bool(
            self.config.get("enabled", False)
            and str(self.config.get("base_url", "")).strip()
        )

    def _post(self, path_key: str, default_path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        base_url = str(self.config.get("base_url", "")).rstrip("/")
        path = str(self.config.get(path_key, default_path)).lstrip("/")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        api_token = os.getenv(
            "MES_API_TOKEN", str(self.config.get("api_token", ""))
        ).strip()
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        request = Request(
            f"{base_url}/{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=float(self.config.get("timeout_seconds", 3))) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"MES HTTP {error.code}: {detail}") from error
        except (URLError, TimeoutError, OSError) as error:
            raise RuntimeError(f"MES 无法连接: {error}") from error

    def heartbeat(self, device: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(
            "heartbeat_path",
            "/api/stations/heartbeat",
            {
                "station_code": device["station_code"],
                "connected": bool(device.get("connected", False)),
                "status": "idle" if device.get("connected") else "stopped",
                "source_app": "电机跑合测试上位机",
                "host_name": socket.gethostname(),
                "metadata": device.get("metadata") or {},
            },
        )

    def upload_outbox_item(self, item: Dict[str, Any], default_station_code: str) -> Dict[str, Any]:
        payload = item.get("payload") or {}
        return self._post(
            "upload_path",
            "/api/test-records",
            {
                "outbox_id": item.get("outbox_id"),
                "entity_type": item.get("entity_type"),
                "entity_id": item.get("entity_id"),
                "station_code": payload.get("station_code") or default_station_code,
                "source_app": "电机跑合测试上位机",
                "actor": "runin-upper-computer",
                "payload": payload,
            },
        )

    def sync_once(
        self,
        store: Any,
        devices: Iterable[Dict[str, Any]],
        default_station_code: str,
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "uploaded": 0, "failed": 0}

        failed = 0
        last_error = ""
        for device in devices:
            try:
                self.heartbeat(device)
            except Exception as error:
                failed += 1
                last_error = str(error)

        uploaded = 0
        for item in store.pending_uploads(limit=int(self.config.get("batch_size", 100))):
            try:
                response = self.upload_outbox_item(item, default_station_code)
                store.mark_upload_succeeded(
                    item["outbox_id"],
                    response.get("server_received_at"),
                )
                uploaded += 1
            except Exception as error:
                failed += 1
                last_error = str(error)
                store.mark_upload_failed(item["outbox_id"], last_error)
        return {"enabled": True, "uploaded": uploaded, "failed": failed, "last_error": last_error}
