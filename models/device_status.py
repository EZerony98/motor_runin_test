"""设备状态模型。"""

from dataclasses import dataclass
from enum import Enum


class DeviceState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class DeviceStatus:
    name: str
    state: DeviceState = DeviceState.DISCONNECTED
    message: str = ""
