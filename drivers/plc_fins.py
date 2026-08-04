"""欧姆龙 PLC FINS/UDP 驱动及托盘数据映射。"""

import socket
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .base_device import BaseDevice, DeviceConnectionError


class FinsProtocolError(DeviceConnectionError):
    """PLC 返回了无效响应或非零 End Code。"""


class FinsPlcDriver(BaseDevice):
    DM_BIT_AREA = 0x02
    DM_WORD_AREA = 0x82
    MOTOR_COUNT = 10
    INT16_MIN = -0x8000
    INT16_MAX = 0x7FFF

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
        self.control_word_address = int(mapping.get("control_word_address", 3000))
        self.release_button_bit = int(mapping.get("release_button_bit", 0))
        self.control_bits = {
            "mode_auto": int(mapping.get("mode_button_bit", 1)),
            "reset": int(mapping.get("reset_button_bit", 2)),
            "start": int(mapping.get("start_button_bit", 3)),
            "emergency_stop_ok": int(mapping.get("emergency_stop_bit", 4)),
        }
        self.tray_id_address = int(mapping.get("tray_id_address", 3008))
        self.tray_id_words = int(mapping.get("tray_id_words", 1))
        self.tray_id_type = str(mapping.get("tray_id_type", "int16")).lower()
        self.serial_start_address = int(mapping.get("serial_start_address", 3456))
        self.serial_slot_words = int(mapping.get("serial_slot_words", 50))
        self.serial_count = int(mapping.get("serial_count", self.MOTOR_COUNT))
        self.serial_encoding = str(mapping.get("serial_encoding", "ascii")).lower()
        self.serial_byte_order = str(
            mapping.get("serial_byte_order", "low_high")
        ).lower()

        configured_bits = [self.release_button_bit, *self.control_bits.values()]
        if any(not 0 <= bit <= 15 for bit in configured_bits):
            raise ValueError("PLC 控制位必须在 0-15 之间")
        if len(set(configured_bits)) != len(configured_bits):
            raise ValueError("PLC 控制位配置不能重复")
        if self.tray_id_words != 1 or self.tray_id_type != "int16":
            raise ValueError("托盘号当前必须按 INT16 占用 1 个 D 寄存器")
        if self.serial_count != self.MOTOR_COUNT:
            raise ValueError("当前托盘配置必须包含 10 个电机")
        if self.serial_slot_words < 1:
            raise ValueError("每个 PLC STRING 至少需要占用 1 个 D 寄存器")
        if self.serial_encoding != "ascii":
            raise ValueError("产品 SN 当前仅支持 ASCII 编码")
        if self.serial_byte_order not in {"low_high", "high_low"}:
            raise ValueError("产品 SN 字节序必须是 low_high 或 high_low")

        self._socket: Optional[socket.socket] = None
        self._sim_words: Dict[int, int] = {}

    @property
    def last_serial_address(self) -> int:
        return self.serial_start_address + self.serial_count * self.serial_slot_words - 1

    @property
    def serial_max_bytes(self) -> int:
        """Sysmac STRING 的最后一个字节预留给 NULL 结束符。"""
        return self.serial_slot_words * 2 - 1

    @property
    def serial_addresses(self) -> List[int]:
        return [
            self.serial_start_address + index * self.serial_slot_words
            for index in range(self.serial_count)
        ]

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
            self.read_words(self.tray_id_address, self.tray_id_words)
            self.read_words(self.control_word_address, 1)
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
        control_states = self.read_control_states()
        return {
            "tray_id": self.read_tray_id(),
            "release_button": control_states["release_button"],
            "controls": {
                name: control_states[name] for name in self.control_bits
            },
        }

    def read_release_button(self) -> bool:
        return self.read_control_states()["release_button"]

    def read_control_states(self) -> Dict[str, bool]:
        """一次读取 D3000，返回放行按钮和上位机控制位状态。"""
        self._require_connection()
        value = self.read_words(self.control_word_address, 1)[0]
        states = {
            name: bool(value & (1 << bit))
            for name, bit in self.control_bits.items()
        }
        states["release_button"] = bool(
            value & (1 << self.release_button_bit)
        )
        return states

    def write_control(self, name: str, value: bool) -> None:
        """按位写入一个上位机控制命令，不影响 D3000 的其他位。"""
        self._require_connection()
        if name not in self.control_bits:
            raise ValueError(f"未知 PLC 控制项：{name}")
        self.write_bit(
            self.control_word_address,
            self.control_bits[name],
            bool(value),
        )

    def read_tray_id(self) -> str:
        self._require_connection()
        value = self.read_words(self.tray_id_address, self.tray_id_words)[0]
        if value & 0x8000:
            value -= 0x10000
        return "" if value == 0 else str(value)

    def write_tray_serial_numbers(
        self, tray_id: str, serial_numbers: Sequence[str]
    ) -> None:
        """将 10 个 ASCII SN 写入 D3456 起、每项间隔 50 字的 STRING 区。"""
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

        for position, (address, serial_number) in enumerate(
            zip(self.serial_addresses, serial_numbers), start=1
        ):
            words = self.ascii_to_words(
                serial_number,
                self.serial_slot_words,
                self.serial_byte_order,
            )
            self.write_words(address, words)
            readback = self.read_words(address, self.serial_slot_words)
            if readback != words:
                raise FinsProtocolError(
                    f"PLC 第 {position} 个 SN 回读校验失败："
                    f"D{address}-D{address + self.serial_slot_words - 1}"
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

    def write_bit(self, address: int, bit: int, value: bool) -> None:
        if not 0 <= int(bit) <= 15:
            raise ValueError(f"无效的 DM 位：{address}.{bit:02d}")
        if self.simulation:
            current = self._sim_words.get(int(address), 0)
            mask = 1 << int(bit)
            self._sim_words[int(address)] = (
                current | mask if value else current & ~mask
            )
            return

        command = (
            bytes([0x01, 0x02, self.DM_BIT_AREA])
            + self._encode_address(address, bit)
            + (1).to_bytes(2, "big")
            + bytes([1 if value else 0])
        )
        self._request(command)

    def set_simulated_tray_id(self, tray_id: str) -> None:
        if not self.simulation:
            raise RuntimeError("仅仿真模式支持直接设置托盘号")
        self.write_words(self.tray_id_address, [self.parse_int16(tray_id, "托盘号")])

    def set_simulated_release_button(self, pressed: bool) -> None:
        if not self.simulation:
            raise RuntimeError("仅仿真模式支持直接设置放行按钮")
        self.write_bit(
            self.control_word_address,
            self.release_button_bit,
            pressed,
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
    def _encode_address(address: int, bit: int = 0) -> bytes:
        if not 0 <= int(address) <= 0xFFFF:
            raise ValueError(f"无效的 DM 地址：{address}")
        if not 0 <= int(bit) <= 15:
            raise ValueError(f"无效的 DM 位：{address}.{bit:02d}")
        return int(address).to_bytes(2, "big") + bytes([int(bit)])

    @classmethod
    def parse_int16(cls, value: str, field_name: str) -> int:
        text = str(value or "").strip()
        try:
            number = int(text)
        except ValueError as error:
            raise ValueError(f"{field_name} 必须是整数") from error
        if not cls.INT16_MIN <= number <= cls.INT16_MAX:
            raise ValueError(
                f"{field_name} 超出 INT16 范围 {cls.INT16_MIN}-{cls.INT16_MAX}"
            )
        return number

    @staticmethod
    def ascii_to_words(
        value: str, slot_words: int, byte_order: str = "low_high"
    ) -> List[int]:
        """将 ASCII 文本编码为带 NULL 结束符的 Sysmac 定长 STRING 字区。"""
        try:
            encoded = str(value or "").encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError("SN 含有非 ASCII 字符") from error

        slot_bytes = int(slot_words) * 2
        if len(encoded) >= slot_bytes:
            raise ValueError(f"SN 最多允许 {slot_bytes - 1} 个 ASCII 字符")
        data = encoded + bytes(slot_bytes - len(encoded))
        words: List[int] = []
        for index in range(0, len(data), 2):
            first, second = data[index], data[index + 1]
            if byte_order == "low_high":
                words.append(first | (second << 8))
            elif byte_order == "high_low":
                words.append((first << 8) | second)
            else:
                raise ValueError(f"不支持的字符串字节序：{byte_order}")
        return words

    @staticmethod
    def words_to_ascii(
        words: Sequence[int], byte_order: str = "low_high"
    ) -> str:
        data = bytearray()
        for word in words:
            value = int(word) & 0xFFFF
            low_byte = value & 0xFF
            high_byte = (value >> 8) & 0xFF
            if byte_order == "low_high":
                data.extend((low_byte, high_byte))
            elif byte_order == "high_low":
                data.extend((high_byte, low_byte))
            else:
                raise ValueError(f"不支持的字符串字节序：{byte_order}")
        return bytes(data).split(b"\x00", 1)[0].decode("ascii")
