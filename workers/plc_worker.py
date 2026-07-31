"""PLC 轮询与写入后台工作对象。"""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from drivers.plc_fins import FinsPlcDriver


class PlcWorker(QObject):
    connection_changed = Signal(bool, str)
    tray_id_changed = Signal(str)
    write_succeeded = Signal(str)
    write_failed = Signal(str)
    log = Signal(str)
    finished = Signal()

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__()
        self.config = config
        self.driver = FinsPlcDriver(config)
        self.poll_interval_ms = max(100, int(config.get("poll_interval_ms", 500)))
        self.timer: Optional[QTimer] = None
        self.last_tray_id: Optional[str] = None
        self.last_connection_state: Optional[bool] = None

    @Slot()
    def start(self) -> None:
        if not bool(self.config.get("enabled", False)):
            self._emit_connection(False, "PLC 未启用")
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
            tray_id = self.driver.read_tray_id()
            self._emit_connection(True, "PLC 已连接")
            if tray_id != self.last_tray_id:
                self.last_tray_id = tray_id
                self.tray_id_changed.emit(tray_id)
        except Exception as error:
            self.driver.disconnect()
            self._emit_connection(False, f"PLC 未连接：{error}")

    @Slot(str, list)
    def write_serial_numbers(self, tray_id: str, serial_numbers: List[str]) -> None:
        try:
            if not self.driver.is_connected:
                self.driver.connect()
            self.driver.write_tray_serial_numbers(tray_id, serial_numbers)
            self._emit_connection(True, "PLC 已连接")
            self.write_succeeded.emit(tray_id)
        except Exception as error:
            self.driver.disconnect()
            self._emit_connection(False, f"PLC 未连接：{error}")
            self.write_failed.emit(str(error))

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
            self.connection_changed.emit(connected, message)
        elif not connected:
            self.log.emit(message)
