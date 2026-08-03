"""托盘电机序列号的生成与校验。"""

import re
from typing import Iterable, List


class SerialNumberError(ValueError):
    """序列号为空、重复或无法顺序生成。"""


class SerialNumberService:
    MOTOR_COUNT = 10
    _TRAILING_NUMBER = re.compile(r"^(.*?)(\d+)$")

    @staticmethod
    def normalize(serial_number: str) -> str:
        return str(serial_number or "").strip()

    def build_sequence(self, first_serial_number: str) -> List[str]:
        """从首个 SN 的末尾数字生成连续的 10 个 SN，并保持数字位数。"""
        first_serial_number = self.normalize(first_serial_number)
        match = self._TRAILING_NUMBER.fullmatch(first_serial_number)
        if not match:
            raise SerialNumberError("第 1 个 SN 必须以数字结尾，才能顺序补齐")

        prefix, number_text = match.groups()
        first_number = int(number_text)
        width = len(number_text)
        return [
            f"{prefix}{first_number + offset:0{width}d}"
            for offset in range(self.MOTOR_COUNT)
        ]

    def validate_batch(self, serial_numbers: Iterable[str]) -> List[str]:
        normalized = [self.normalize(item) for item in serial_numbers]
        if len(normalized) != self.MOTOR_COUNT:
            raise SerialNumberError(f"每个托盘必须包含 {self.MOTOR_COUNT} 个 SN")

        empty_positions = [
            str(index + 1) for index, serial_number in enumerate(normalized)
            if not serial_number
        ]
        if empty_positions:
            raise SerialNumberError(
                "以下位置尚未录入 SN：" + "、".join(empty_positions)
            )

        duplicates = sorted(
            {
                serial_number
                for serial_number in normalized
                if normalized.count(serial_number) > 1
            }
        )
        if duplicates:
            raise SerialNumberError("存在重复 SN：" + "、".join(duplicates))
        return normalized

    def validate_plc_ascii_batch(
        self, serial_numbers: Iterable[str], max_bytes: int
    ) -> List[str]:
        """校验每个 SN 都能写入 PLC 的定长 ASCII STRING。"""
        normalized = self.validate_batch(serial_numbers)
        for position, serial_number in enumerate(normalized, start=1):
            try:
                encoded = serial_number.encode("ascii")
            except UnicodeEncodeError as error:
                raise SerialNumberError(
                    f"位置 {position} 的 SN 含有非 ASCII 字符"
                ) from error
            if any(byte < 0x20 or byte > 0x7E for byte in encoded):
                raise SerialNumberError(
                    f"位置 {position} 的 SN 含有不可显示的控制字符"
                )
            if len(encoded) > max_bytes:
                raise SerialNumberError(
                    f"位置 {position} 的 SN 最多允许 {max_bytes} 个 ASCII 字符"
                )
        return normalized
