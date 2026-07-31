"""温度采集设备驱动占位。"""

from typing import Any, Dict

from .base_device import BaseDevice, DeviceConnectionError


class TemperatureSensorDriver(BaseDevice):
    def connect(self) -> None:
        raise DeviceConnectionError("温度采集设备尚未配置")

    def disconnect(self) -> None:
        self._connected = False

    def read(self) -> Dict[str, Any]:
        if not self.is_connected:
            raise DeviceConnectionError("温度采集设备未连接")
        return {}
