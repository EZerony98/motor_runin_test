"""设备驱动统一接口。"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class DeviceConnectionError(RuntimeError):
    """设备连接或通信失败。"""


class BaseDevice(ABC):
    """所有设备驱动应实现的最小接口。"""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    def connect(self) -> None:
        """连接设备，失败时抛出 DeviceConnectionError。"""

    @abstractmethod
    def disconnect(self) -> None:
        """断开设备并释放资源。"""

    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """读取一次设备数据。"""

    def __enter__(self) -> "BaseDevice":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()
