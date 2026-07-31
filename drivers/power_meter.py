"""电参数仪驱动占位。"""

from typing import Any, Dict

from .base_device import BaseDevice, DeviceConnectionError


class PowerMeterDriver(BaseDevice):
    def connect(self) -> None:
        raise DeviceConnectionError("电参数仪尚未配置")

    def disconnect(self) -> None:
        self._connected = False

    def read(self) -> Dict[str, Any]:
        if not self.is_connected:
            raise DeviceConnectionError("电参数仪未连接")
        return {}
