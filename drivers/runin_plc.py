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
    # PLC 以整数传输；进入上位机后统一换算为实际工程量。界面、判定、
    # SQLite 和后续上传全部使用这里换算后的值。
    MEASUREMENT_SCALES = {
        "runin_speed_rpm": 2,
        "runin_voltage_v": 0.1,
        "runin_temperature_c": 1,
        "runin_current_a": 1,
    }

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
        self.result_sequence_address = int(
            mapping.get("result_sequence_address", 3072)
        )
        self.result_sequence_words = int(
            mapping.get("result_sequence_words", 2)
        )
        self.result_sequence_word_order = str(
            mapping.get("result_sequence_word_order", "low_high")
        ).lower()
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
        if self.result_sequence_words != 2:
            raise ValueError("跑合结果流水号当前必须配置为2个DM字")
        if self.result_sequence_word_order not in {"low_high", "high_low"}:
            raise ValueError(
                "流水号字序必须是 low_high 或 high_low"
            )

    @property
    def result_word_count(self) -> int:
        return self.products_per_tray * self.words_per_product

    def _probe_connection(self) -> None:
        self.read_words(self.tray_id_address, 1)
        self.read_words(self.handshake_address, 1)
        self.read_words(
            self.result_sequence_address, self.result_sequence_words
        )

    def read_result_sequence(self) -> Dict[str, Any]:
        """读取PLC双字结果流水号，并同时返回原始两个DM字便于诊断。"""
        self._require_connection()
        words = self.read_words(
            self.result_sequence_address, self.result_sequence_words
        )
        first, second = (int(value) & 0xFFFF for value in words)
        if self.result_sequence_word_order == "low_high":
            value = first | (second << 16)
        else:
            value = (first << 16) | second
        return {
            "value": value,
            "words": [first, second],
            "address": self.result_sequence_address,
            "word_order": self.result_sequence_word_order,
        }

    def read_data_ready(self) -> bool:
        self._require_connection()
        word = self.read_words(self.handshake_address, 1)[0]
        return bool(word & (1 << self.data_ready_bit))

    def read_live_snapshot(self) -> Dict[str, Any]:
        """不依赖握手位，读取当前托盘号及实际产品区用于界面预览。"""
        self._require_connection()
        handshake_word = self.read_words(self.handshake_address, 1)[0]
        sequence = self.read_result_sequence()
        tray_id = self.read_tray_id()
        words = self.read_words(self.result_base_address, self.result_word_count)
        return self._parse_snapshot(
            tray_id,
            words,
            data_ready=bool(handshake_word & (1 << self.data_ready_bit)),
            handshake_word=handshake_word,
            sequence=sequence,
        )

    def read_result_snapshot(self) -> Optional[Dict[str, Any]]:
        """读取稳定的一盘10产品结果；PLC在就绪期间必须保持数据不变。"""
        self._require_connection()
        if not self.read_data_ready():
            return None
        sequence_before = self.read_result_sequence()
        if int(sequence_before["value"]) <= 0:
            raise FinsProtocolError(
                "跑合PLC数据已就绪，但D"
                f"{self.result_sequence_address}～D"
                f"{self.result_sequence_address + 1}流水号无效："
                f"{sequence_before['value']}"
            )
        tray_id = self.read_tray_id()
        if not tray_id:
            raise FinsProtocolError("跑合 PLC 数据已就绪，但 DM3008 托盘号为空")
        words = self.read_words(self.result_base_address, self.result_word_count)
        sequence_after = self.read_result_sequence()
        if sequence_after["value"] != sequence_before["value"]:
            raise FinsProtocolError(
                "读取跑合结果期间PLC流水号发生变化："
                f"{sequence_before['value']} -> {sequence_after['value']}"
            )
        if not self.read_data_ready():
            raise FinsProtocolError("读取跑合结果期间数据就绪位被清除")

        return self._parse_snapshot(
            tray_id,
            words,
            data_ready=True,
            handshake_word=1 << self.data_ready_bit,
            sequence=sequence_before,
        )

    def _parse_snapshot(
        self,
        tray_id: str,
        words: List[int],
        *,
        data_ready: bool,
        handshake_word: int,
        sequence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """解析10个产品原始值；原PLC合格位仅保留作诊断。"""

        items: List[Dict[str, Any]] = []
        for slot in range(1, self.products_per_tray + 1):
            start = (slot - 1) * self.words_per_product
            values = [
                self.word_to_int16(value)
                for value in words[start : start + self.words_per_product]
            ]
            raw_values = dict(zip(self.plc_field_order, values))
            items.append(
                {
                    "tray_slot": slot,
                    "runin_speed_rpm": self._engineering_value(
                        "runin_speed_rpm", raw_values["runin_speed_rpm"]
                    ),
                    "runin_voltage_v": self._engineering_value(
                        "runin_voltage_v", raw_values["runin_voltage_v"]
                    ),
                    "runin_temperature_c": self._engineering_value(
                        "runin_temperature_c",
                        raw_values["runin_temperature_c"],
                    ),
                    "runin_current_a": self._engineering_value(
                        "runin_current_a", raw_values["runin_current_a"]
                    ),
                    "runin_error_code": raw_values["runin_error_code"],
                    "plc_passed_raw": raw_values["runin_passed"],
                    "runin_passed": None,
                    "runin_result_code": None,
                    "judgement_source": None,
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
            "result_sequence": int(sequence["value"]),
            "result_sequence_words": list(sequence["words"]),
            "result_sequence_address": int(sequence["address"]),
            "result_sequence_word_order": str(sequence["word_order"]),
            "items": items,
        }

    @classmethod
    def _engineering_value(cls, field: str, raw_value: int) -> Any:
        scale = cls.MEASUREMENT_SCALES[field]
        if scale == 1:
            return raw_value
        if isinstance(scale, int):
            return raw_value * scale
        return round(raw_value * scale, 6)

    def write_pass_results(self, items: Iterable[Dict[str, Any]]) -> None:
        """将上位机判定的10个0/1写入原PLC合格标志位置并回读校验。"""
        normalized = [dict(item) for item in items]
        slots = sorted(int(item.get("tray_slot", 0)) for item in normalized)
        if slots != list(range(1, self.products_per_tray + 1)):
            raise ValueError("写入合格标志必须完整包含坑位 1～10")

        passed_offset = self.plc_field_order.index("runin_passed")
        for item in normalized:
            slot = int(item["tray_slot"])
            passed = item.get("runin_passed")
            if not isinstance(passed, bool):
                raise ValueError(f"坑位 {slot} 上位机合格结果必须是 bool")
            address = (
                self.result_base_address
                + (slot - 1) * self.words_per_product
                + passed_offset
            )
            expected = 1 if passed else 0
            self.write_words(address, [expected])
            actual = self.read_words(address, 1)[0]
            if actual != expected:
                raise FinsProtocolError(
                    f"坑位 {slot} 合格结果写入校验失败："
                    f"D{address} 期望 {expected}，实际 {actual}"
                )

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
        sequence: int = 1,
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
        sequence = int(sequence) & 0xFFFFFFFF
        low_word = sequence & 0xFFFF
        high_word = (sequence >> 16) & 0xFFFF
        sequence_words = (
            [low_word, high_word]
            if self.result_sequence_word_order == "low_high"
            else [high_word, low_word]
        )
        self.write_words(self.result_sequence_address, sequence_words)
        self.write_bit(self.handshake_address, self.data_ready_bit, ready)
