"""跑合设备 PLC 独立轮询、结果读取及握手确认。"""

import time
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from drivers.runin_plc import RuninPlcDriver


class RuninPlcWorker(QObject):
    connection_changed = Signal(str, bool, str)
    live_snapshot = Signal(str, dict)
    result_ready = Signal(str, dict)
    log = Signal(str)
    finished = Signal()

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__()
        self.config = dict(config)
        self.device_id = str(config.get("id", "RUNIN_01"))
        self.device_name = str(config.get("name", self.device_id))
        self.enabled = bool(config.get("enabled", False))
        self.poll_interval_ms = max(100, int(config.get("poll_interval_ms", 200)))
        self.retry_interval_seconds = max(
            1.0, float(config.get("result_retry_seconds", 5))
        )
        self.driver = RuninPlcDriver(config)
        self.timer: Optional[QTimer] = None
        self.last_connection_state: Optional[bool] = None
        self.processing_pending = False
        self.ack_sent = False
        self.idle_ack_cleared = False
        self.retry_not_before = 0.0
        self.last_live_signature = None
        self.last_live_emit_at = 0.0
        self.last_ready_state: Optional[bool] = None
        self.last_error_message = ""
        self.last_error_log_at = 0.0

    @Slot()
    def start(self) -> None:
        if not self.enabled:
            self._emit_connection(False, f"{self.device_name} 未启用")
            self.finished.emit()
            return
        self.timer = QTimer(self)
        self.timer.setInterval(self.poll_interval_ms)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        self.poll()

    @Slot()
    def poll(self) -> None:
        try:
            if not self.driver.is_connected:
                self.driver.connect()
            self._emit_connection(True, f"{self.device_name} 已连接")
            live_snapshot = self.driver.read_live_snapshot()
            signature = (
                live_snapshot.get("tray_id"),
                live_snapshot.get("data_ready"),
                tuple(
                    tuple(
                        item.get(field)
                        for field in self.driver.PRODUCT_FIELDS
                    )
                    for item in live_snapshot.get("items", [])
                ),
            )
            now = time.monotonic()
            if (
                signature != self.last_live_signature
                or now - self.last_live_emit_at >= 1.0
            ):
                self.last_live_signature = signature
                self.last_live_emit_at = now
                self.live_snapshot.emit(self.device_id, live_snapshot)
            ready = bool(live_snapshot.get("data_ready"))
            if ready != self.last_ready_state:
                self.last_ready_state = ready
                self.log.emit(
                    f"{self.device_name} 数据可读 "
                    f"D{self.driver.handshake_address}."
                    f"{self.driver.data_ready_bit:02d}="
                    f"{1 if ready else 0}，托盘 "
                    f"{live_snapshot.get('tray_id') or '--'}"
                )
            if not ready:
                if self.ack_sent or not self.idle_ack_cleared:
                    self.driver.write_read_complete(False)
                    self.idle_ack_cleared = True
                self.processing_pending = False
                self.ack_sent = False
                self.retry_not_before = 0.0
                return
            self.idle_ack_cleared = False
            if (
                self.processing_pending
                or self.ack_sent
                or time.monotonic() < self.retry_not_before
            ):
                return
            snapshot = self.driver.read_result_snapshot()
            if snapshot is not None:
                self.processing_pending = True
                self.result_ready.emit(self.device_id, snapshot)
        except Exception as error:
            self.driver.disconnect()
            self.last_live_signature = None
            self.last_live_emit_at = 0.0
            self.last_ready_state = None
            self.idle_ack_cleared = False
            self._report_failure(
                f"{self.device_name} 读取失败：{error}"
            )

    @Slot(str, bool)
    def handle_result_processed(self, device_id: str, succeeded: bool) -> None:
        if str(device_id) != self.device_id:
            return
        if not self.processing_pending:
            return
        if not succeeded:
            self.processing_pending = False
            self.retry_not_before = time.monotonic() + self.retry_interval_seconds
            return
        try:
            if not self.driver.is_connected:
                self.driver.connect()
            self.driver.write_read_complete(True)
            self.processing_pending = False
            self.ack_sent = True
            self.log.emit(f"{self.device_name} 已写入数据读取完成确认")
        except Exception as error:
            self.driver.disconnect()
            self.processing_pending = False
            self.retry_not_before = time.monotonic() + self.retry_interval_seconds
            self._report_failure(
                f"{self.device_name} 确认写入失败：{error}"
            )

    @Slot()
    def stop(self) -> None:
        if self.timer is not None:
            self.timer.stop()
            self.timer.deleteLater()
            self.timer = None
        self.driver.disconnect()
        self.finished.emit()

    def _emit_connection(self, connected: bool, message: str) -> None:
        if connected != self.last_connection_state:
            self.last_connection_state = connected
            self.connection_changed.emit(self.device_id, connected, message)

    def _report_failure(self, message: str) -> None:
        """连接状态和运行日志同时报告错误，并限制重复日志频率。"""
        self._emit_connection(False, message)
        now = time.monotonic()
        if (
            message != self.last_error_message
            or now - self.last_error_log_at >= 2.0
        ):
            self.last_error_message = message
            self.last_error_log_at = now
            self.log.emit(message)
