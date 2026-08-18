"""跑合设备 PLC 单托盘结果交换驱动。"""

from typing import Any, Dict, Iterable, List, Optional

from .plc_fins import FinsPlcDriver, FinsProtocolError


class RuninPlcDriver(FinsPlcDriver):
    # 界面、数据库及上传记录统一使用的标准字段顺序。
    PRODUCT_FIELDS = (
        "runin_speed_rpm",
        "runin_voltage_v",
        "runin_temperature_c",
        "runin_current_a",
        "runin_error_code",
        "runin_passed",
    )
    # 从数组1号元素开始后，每组6个DM的实际排列。
    DEFAULT_PLC_FIELD_ORDER = (
        "runin_speed_rpm",
        "runin_voltage_v",
        "runin_temperature_c",
        "runin_current_a",
        "runin_error_code",
        "runin_passed",
    )

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.device_id = str(config.get("id", "RUNIN_01"))
        self.device_name = str(config.get("name", self.device_id))
        mapping = config.get("mapping", {})
        self.result_array_base_address = int(
            mapping.get("result_base_address", 1000)
        )
        self.result_start_offset = int(mapping.get("result_start_offset", 1))
        self.result_base_address = (
            self.result_array_base_address + self.result_start_offset
        )
        self.products_per_tray = int(mapping.get("products_per_tray", 10))
        self.words_per_product = int(mapping.get("words_per_product", 6))
        self.handshake_address = int(mapping.get("handshake_address", 3502))
        self.data_ready_bit = int(mapping.get("data_ready_bit", 0))
        self.read_complete_bit = int(mapping.get("read_complete_bit", 1))
        self.plc_field_order = tuple(
            mapping.get("result_field_order", self.DEFAULT_PLC_FIELD_ORDER)
        )
        if self.products_per_tray != 10 or self.words_per_product != 6:
            raise ValueError("跑合结果当前必须按 10 个产品、每产品 6 个 INT 配置")
        if self.result_start_offset < 0:
            raise ValueError("跑合结果起始偏移不能为负数")
        if (
            len(self.plc_field_order) != self.words_per_product
            or set(self.plc_field_order) != set(self.PRODUCT_FIELDS)
        ):
            raise ValueError("跑合结果字段顺序必须完整包含6个标准字段且不能重复")
        if self.data_ready_bit == self.read_complete_bit:
            raise ValueError("数据就绪位和读取完成位不能相同")

    @property
    def result_word_count(self) -> int:
        return self.products_per_tray * self.words_per_product

    def _probe_connection(self) -> None:
        self.read_words(self.tray_id_address, 1)
        self.read_words(self.handshake_address, 1)

    def read_data_ready(self) -> bool:
        self._require_connection()
        word = self.read_words(self.handshake_address, 1)[0]
        return bool(word & (1 << self.data_ready_bit))

    def read_live_snapshot(self) -> Dict[str, Any]:
        """不依赖握手位，读取当前托盘号及实际产品区用于界面预览。"""
        self._require_connection()
        handshake_word = self.read_words(self.handshake_address, 1)[0]
        tray_id = self.read_tray_id()
        words = self.read_words(self.result_base_address, self.result_word_count)
        return self._parse_snapshot(
            tray_id,
            words,
            strict_passed=False,
            data_ready=bool(handshake_word & (1 << self.data_ready_bit)),
            handshake_word=handshake_word,
        )

    def read_result_snapshot(self) -> Optional[Dict[str, Any]]:
        """读取稳定的一盘10产品结果；PLC在就绪期间必须保持数据不变。"""
        self._require_connection()
        if not self.read_data_ready():
            return None
        tray_id = self.read_tray_id()
        if not tray_id:
            raise FinsProtocolError("跑合 PLC 数据已就绪，但 DM3008 托盘号为空")
        words = self.read_words(self.result_base_address, self.result_word_count)
        if not self.read_data_ready():
            raise FinsProtocolError("读取跑合结果期间数据就绪位被清除")

        return self._parse_snapshot(
            tray_id,
            words,
            strict_passed=True,
            data_ready=True,
            handshake_word=1 << self.data_ready_bit,
        )

    def _parse_snapshot(
        self,
        tray_id: str,
        words: List[int],
        *,
        strict_passed: bool,
        data_ready: bool,
        handshake_word: int,
    ) -> Dict[str, Any]:
        """将60个连续INT字解析为10个产品；预览允许合格位尚未生成。"""

        items: List[Dict[str, Any]] = []
        for slot in range(1, self.products_per_tray + 1):
            start = (slot - 1) * self.words_per_product
            values = [
                self.word_to_int16(value)
                for value in words[start : start + self.words_per_product]
            ]
            raw_values = dict(zip(self.plc_field_order, values))
            passed = raw_values["runin_passed"]
            if strict_passed and passed not in (0, 1):
                raise FinsProtocolError(
                    f"托盘 {tray_id} 坑位 {slot} 合格值必须为 0 或 1，实际 {passed}"
                )
            # 合格标志也需要像其他测量值一样实时预览；握手位只控制
            # 是否允许正式保存，不应控制界面是否显示 PLC 当前值。
            passed_value = bool(passed) if passed in (0, 1) else None
            items.append(
                {
                    "tray_slot": slot,
                    "runin_speed_rpm": raw_values["runin_speed_rpm"],
                    "runin_voltage_v": raw_values["runin_voltage_v"],
                    "runin_temperature_c": raw_values[
                        "runin_temperature_c"
                    ],
                    "runin_current_a": raw_values["runin_current_a"],
                    "runin_error_code": raw_values["runin_error_code"],
                    "runin_passed_raw": passed,
                    "runin_passed": passed_value,
                    "runin_result_code": (
                        0 if passed_value else 1
                    ) if passed_value is not None else None,
                }
            )
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "tray_id": tray_id,
            "tray_id_address": self.tray_id_address,
            "result_base_address": self.result_base_address,
            "result_end_address": (
                self.result_base_address + self.result_word_count - 1
            ),
            "handshake_address": self.handshake_address,
            "data_ready_bit": self.data_ready_bit,
            "read_complete_bit": self.read_complete_bit,
            "data_ready": bool(data_ready),
            "handshake_word": int(handshake_word) & 0xFFFF,
            "items": items,
        }

    def write_read_complete(self, completed: bool) -> None:
        self._require_connection()
        self.write_bit(
            self.handshake_address,
            self.read_complete_bit,
            bool(completed),
        )

    def set_simulated_result(
        self,
        tray_id: str,
        rows: Iterable[Iterable[int]],
        ready: bool = True,
    ) -> None:
        if not self.simulation:
            raise RuntimeError("仅仿真模式支持设置跑合结果")
        normalized = [list(row) for row in rows]
        if len(normalized) != self.products_per_tray:
            raise ValueError("仿真结果必须包含 10 个产品")
        words: List[int] = []
        for row in normalized:
            if len(row) != self.words_per_product:
                raise ValueError("每个仿真产品必须包含 6 个 INT")
            words.extend(int(value) for value in row)
        self.set_simulated_tray_id(tray_id)
        self.write_words(self.result_base_address, words)
        self.write_bit(self.handshake_address, self.data_ready_bit, ready)
