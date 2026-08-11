"""跑合设备 PLC 单托盘结果交换驱动。"""

from typing import Any, Dict, Iterable, List, Optional

from .plc_fins import FinsPlcDriver, FinsProtocolError


class RuninPlcDriver(FinsPlcDriver):
    PRODUCT_FIELDS = (
        "runin_current_a",
        "runin_voltage_v",
        "runin_speed_rpm",
        "runin_temperature_c",
        "runin_passed",
    )

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.device_id = str(config.get("id", "RUNIN_01"))
        self.device_name = str(config.get("name", self.device_id))
        mapping = config.get("mapping", {})
        self.result_base_address = int(mapping.get("result_base_address", 1000))
        self.products_per_tray = int(mapping.get("products_per_tray", 10))
        self.words_per_product = int(mapping.get("words_per_product", 5))
        self.handshake_address = int(mapping.get("handshake_address", 3502))
        self.data_ready_bit = int(mapping.get("data_ready_bit", 0))
        self.read_complete_bit = int(mapping.get("read_complete_bit", 1))
        if self.products_per_tray != 10 or self.words_per_product != 5:
            raise ValueError("跑合结果当前必须按 10 个产品、每产品 5 个 INT 配置")
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

        items: List[Dict[str, Any]] = []
        for slot in range(1, self.products_per_tray + 1):
            start = (slot - 1) * self.words_per_product
            values = [
                self.word_to_int16(value)
                for value in words[start : start + self.words_per_product]
            ]
            passed = values[4]
            if passed not in (0, 1):
                raise FinsProtocolError(
                    f"托盘 {tray_id} 坑位 {slot} 合格值必须为 0 或 1，实际 {passed}"
                )
            items.append(
                {
                    "tray_slot": slot,
                    "runin_current_a": values[0],
                    "runin_voltage_v": values[1],
                    "runin_speed_rpm": values[2],
                    "runin_temperature_c": values[3],
                    "runin_passed": bool(passed),
                    "runin_result_code": 0 if passed else 1,
                }
            )
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "tray_id": tray_id,
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
                raise ValueError("每个仿真产品必须包含 5 个 INT")
            words.extend(int(value) for value in row)
        self.set_simulated_tray_id(tray_id)
        self.write_words(self.result_base_address, words)
        self.write_bit(self.handshake_address, self.data_ready_bit, ready)
