"""欧姆龙 PLC FINS/UDP 驱动及托盘数据映射。"""

import socket
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .base_device import BaseDevice, DeviceConnectionError


class FinsProtocolError(DeviceConnectionError):
    """PLC 返回了无效响应或非零 End Code。"""


class FinsPlcDriver(BaseDevice):
    DM_WORD_AREA = 0x82
    MOTOR_COUNT = 10
    UINT32_MAX = 0xFFFFFFFF

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.host = str(config.get("host", "192.168.250.1"))
        self.port = int(config.get("port", 9600))
        self.timeout = float(config.get("timeout_seconds", 1.0))
        self.source_node = int(config.get("source_node", 2))
        self.destination_node = int(config.get("destination_node", 1))
        self.service_id = int(config.get("service_id", 1)) & 0xFF or 1
        self.simulation = bool(config.get("simulation", False))

        mapping = config.get("mapping", {})
        self.tray_id_address = int(mapping.get("tray_id_address", 3580))
        self.serial_start_address = int(mapping.get("serial_start_address", 3582))
        self.words_per_value = int(mapping.get("words_per_value", 2))
        self.serial_count = int(mapping.get("serial_count", self.MOTOR_COUNT))
        self.word_order = str(mapping.get("word_order", "low_high")).lower()
        self.value_type = str(mapping.get("value_type", "uint32")).lower()

        if self.words_per_value != 2:
            raise ValueError("托盘号和 SN 当前必须各占 2 个 D 寄存器")
        if self.serial_count != self.MOTOR_COUNT:
            raise ValueError("当前托盘配置必须包含 10 个电机")
        if self.value_type != "uint32":
            raise ValueError("两个 D 寄存器当前仅支持 uint32 编码")

        self._socket: Optional[socket.socket] = None
        self._sim_words: Dict[int, int] = {}

    @property
    def last_serial_address(self) -> int:
        return (
            self.serial_start_address
            + (self.serial_count - 1) * self.words_per_value
            + self.words_per_value
            - 1
        )

    def connect(self) -> None:
        if self.is_connected:
            return
        if self.simulation:
            self._connected = True
            return

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(self.timeout)
        self._socket.connect((self.host, self.port))
        try:
            self.read_words(self.tray_id_address, self.words_per_value)
        except Exception:
            self.disconnect()
            raise
        self._connected = True

    def disconnect(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._connected = False

    def read(self) -> Dict[str, Any]:
        return {"tray_id": self.read_tray_id()}

    def read_tray_id(self) -> str:
        self._require_connection()
        words = self.read_words(self.tray_id_address, self.words_per_value)
        value = self.words_to_uint32(words, self.word_order)
        return "" if value == 0 else str(value)

    def write_tray_serial_numbers(
        self, tray_id: str, serial_numbers: Sequence[str]
    ) -> None:
        """将 10 个 UINT32 SN 连续写入 D3582-D3601 并进行回读校验。"""
        self._require_connection()
        if len(serial_numbers) != self.serial_count:
            raise ValueError(f"PLC 写入要求正好 {self.serial_count} 个 SN")

        current_tray_id = self.read_tray_id()
        expected_tray_id = str(tray_id or "").strip()
        if current_tray_id != expected_tray_id:
            raise DeviceConnectionError(
                f"托盘编号已变化：界面为 {expected_tray_id or '空'}，"
                f"PLC D{self.tray_id_address} 为 {current_tray_id or '空'}"
            )

        values = [self.parse_uint32(serial_number, "SN") for serial_number in serial_numbers]
        words = [
            word
            for value in values
            for word in self.uint32_to_words(value, self.word_order)
        ]
        self.write_words(self.serial_start_address, words)

        readback = self.read_words(self.serial_start_address, len(words))
        if readback != words:
            raise FinsProtocolError(
                f"PLC SN 回读校验失败：D{self.serial_start_address}-D{self.last_serial_address}"
            )

    def read_words(self, address: int, count: int) -> List[int]:
        if self.simulation:
            return [self._sim_words.get(address + offset, 0) for offset in range(count)]

        command = (
            bytes([0x01, 0x01, self.DM_WORD_AREA])
            + self._encode_address(address)
            + int(count).to_bytes(2, "big")
        )
        response = self._request(command)
        data = response[14:]
        expected_length = count * 2
        if len(data) < expected_length:
            raise FinsProtocolError(
                f"PLC 读取长度不足：期望 {expected_length} 字节，实际 {len(data)} 字节"
            )
        return [
            int.from_bytes(data[index : index + 2], "big")
            for index in range(0, expected_length, 2)
        ]

    def write_words(self, address: int, values: Iterable[int]) -> None:
        words = [int(value) & 0xFFFF for value in values]
        if self.simulation:
            for offset, word in enumerate(words):
                self._sim_words[address + offset] = word
            return

        payload = b"".join(word.to_bytes(2, "big") for word in words)
        command = (
            bytes([0x01, 0x02, self.DM_WORD_AREA])
            + self._encode_address(address)
            + len(words).to_bytes(2, "big")
            + payload
        )
        self._request(command)

    def set_simulated_tray_id(self, tray_id: str) -> None:
        if not self.simulation:
            raise RuntimeError("仅仿真模式支持直接设置托盘号")
        value = self.parse_uint32(tray_id, "托盘号")
        self.write_words(
            self.tray_id_address,
            self.uint32_to_words(value, self.word_order),
        )

    def _request(self, command: bytes) -> bytes:
        if self._socket is None:
            raise DeviceConnectionError("PLC UDP Socket 未连接")
        service_id = self._next_service_id()
        frame = self._header(service_id) + command
        try:
            self._socket.send(frame)
            response = self._socket.recv(4096)
        except (OSError, socket.timeout) as error:
            raise DeviceConnectionError(f"PLC 通信失败：{error}") from error

        if len(response) < 14:
            raise FinsProtocolError(f"PLC 响应过短：{len(response)} 字节")
        if response[9] != service_id:
            raise FinsProtocolError(
                f"FINS SID 不一致：发送 {service_id}，收到 {response[9]}"
            )
        end_code = int.from_bytes(response[12:14], "big")
        if end_code:
            raise FinsProtocolError(f"FINS End Code：0x{end_code:04X}")
        return response

    def _header(self, service_id: int) -> bytes:
        return bytes(
            [
                0x80,
                0x00,
                0x02,
                0x00,
                self.destination_node & 0xFF,
                0x00,
                0x00,
                self.source_node & 0xFF,
                0x00,
                service_id & 0xFF,
            ]
        )

    def _next_service_id(self) -> int:
        service_id = self.service_id
        self.service_id = (self.service_id + 1) & 0xFF or 1
        return service_id

    def _require_connection(self) -> None:
        if not self.is_connected:
            raise DeviceConnectionError("PLC 未连接")

    @staticmethod
    def _encode_address(address: int) -> bytes:
        if not 0 <= int(address) <= 0xFFFF:
            raise ValueError(f"无效的 DM 地址：{address}")
        return int(address).to_bytes(2, "big") + b"\x00"

    @classmethod
    def parse_uint32(cls, value: str, field_name: str) -> int:
        text = str(value or "").strip()
        if not text.isdigit():
            raise ValueError(f"{field_name} 必须是纯数字")
        number = int(text)
        if not 0 <= number <= cls.UINT32_MAX:
            raise ValueError(f"{field_name} 超出 UINT32 范围 0-{cls.UINT32_MAX}")
        return number

    @staticmethod
    def uint32_to_words(value: int, word_order: str = "low_high") -> List[int]:
        value = int(value)
        if not 0 <= value <= 0xFFFFFFFF:
            raise ValueError("数值超出 UINT32 范围")
        high_word = (value >> 16) & 0xFFFF
        low_word = value & 0xFFFF
        if word_order in {"low_high", "little", "swap"}:
            return [low_word, high_word]
        if word_order in {"high_low", "big"}:
            return [high_word, low_word]
        raise ValueError(f"不支持的字序：{word_order}")

    @staticmethod
    def words_to_uint32(words: Sequence[int], word_order: str = "low_high") -> int:
        if len(words) != 2:
            raise ValueError("UINT32 必须由 2 个字组成")
        first, second = (int(word) & 0xFFFF for word in words)
        if word_order in {"low_high", "little", "swap"}:
            low_word, high_word = first, second
        elif word_order in {"high_low", "big"}:
            high_word, low_word = first, second
        else:
            raise ValueError(f"不支持的字序：{word_order}")
        return (high_word << 16) | low_word
