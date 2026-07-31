"""电机跑合测试上位机入口。"""

import sys
from datetime import datetime
from functools import partial
from pathlib import Path
from time import monotonic
from typing import List, Optional, Sequence

from PySide6.QtCore import QEvent, QMetaObject, QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow, QMessageBox

from models.tray_batch import TrayBatch
from services.config_service import ConfigService
from services.serial_number_service import SerialNumberError, SerialNumberService
from ui.ui_main import Ui_MainWindow
from workers.plc_worker import PlcWorker


PROJECT_DIR = Path(__file__).resolve().parent
CONFIG = ConfigService(PROJECT_DIR / "config")


class MainWindow(QMainWindow):
    """跑合测试主窗口。"""

    serial_numbers_ready = Signal(str, list)

    def __init__(self, start_plc: bool = True) -> None:
        super().__init__()
        self.config = CONFIG.load_all()
        self.serial_number_service = SerialNumberService()
        self.plc_thread: Optional[QThread] = None
        self.plc_worker: Optional[PlcWorker] = None
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.serial_inputs: List[QLineEdit] = [
            getattr(self.ui, f"snInput{position}")
            for position in range(1, SerialNumberService.MOTOR_COUNT + 1)
        ]
        scanner_config = self.config["app"].get("scanner", {})
        self.scanner_auto_finish_delay_ms = max(
            50, int(scanner_config.get("auto_finish_delay_ms", 180))
        )
        self.scanner_max_input_duration_ms = max(
            500, int(scanner_config.get("max_input_duration_ms", 2000))
        )
        self.scanner_min_length = max(
            1, int(scanner_config.get("min_serial_length", 3))
        )
        self.scan_started_at: List[Optional[float]] = [
            None for _ in self.serial_inputs
        ]
        self.scan_timers: List[QTimer] = []
        for index, serial_input in enumerate(self.serial_inputs):
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(partial(self._finish_timed_scan, index))
            self.scan_timers.append(timer)
            serial_input.installEventFilter(self)
        self.setWindowTitle(
            self.config["app"]["application"].get("window_title", "电机跑合测试系统")
        )
        self._connect_signals()
        self._configure_plc_status()
        if start_plc:
            self._start_plc_worker()
        else:
            self._set_plc_connection(False, "PLC 未启动")
        self._update_sn_progress()
        self.serial_inputs[0].setFocus()
        self.append_log("应用启动完成，等待 PLC 读取托盘编号并录入 10 个电机 SN。")

    def _connect_signals(self) -> None:
        self.ui.fillButton.clicked.connect(self._fill_serial_numbers)
        self.ui.clearButton.clicked.connect(self._clear_serial_numbers)
        self.ui.submitButton.clicked.connect(self._submit_serial_numbers)

        for index, serial_input in enumerate(self.serial_inputs):
            serial_input.returnPressed.connect(partial(self._accept_scan, index))
            serial_input.textChanged.connect(self._update_sn_progress)
            serial_input.textEdited.connect(
                partial(self._on_sn_text_edited, index)
            )

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        """兼容扫码枪发送的 Return、Enter、CR、LF 和未知控制键。"""
        if watched in self.serial_inputs and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            text = event.text() or ""
            if (
                key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                or "\r" in text
                or "\n" in text
            ):
                self._accept_scan(self.serial_inputs.index(watched))
                return True
        return super().eventFilter(watched, event)

    def _on_sn_text_edited(self, index: int, text: str) -> None:
        """扫码无有效结束符时，通过快速输入后的短暂停顿自动确认。"""
        if "\r" in text or "\n" in text:
            sanitized = text.replace("\r", "").replace("\n", "").strip()
            self.serial_inputs[index].setText(sanitized)
            self._accept_scan(index)
            return

        if not text:
            self.scan_started_at[index] = None
            self.scan_timers[index].stop()
            return

        if self.scan_started_at[index] is None:
            self.scan_started_at[index] = monotonic()
        self.scan_timers[index].start(self.scanner_auto_finish_delay_ms)

    def _finish_timed_scan(self, index: int) -> None:
        serial_number = self.serial_inputs[index].text().strip()
        started_at = self.scan_started_at[index]
        if not serial_number or started_at is None:
            return

        duration_ms = (monotonic() - started_at) * 1000
        if (
            len(serial_number) >= self.scanner_min_length
            and duration_ms <= self.scanner_max_input_duration_ms
        ):
            self._accept_scan(index)

    def _configure_plc_status(self) -> None:
        plc_config = self.config["devices"]["plc"]
        self.ui.plcAddressLabel.setText(
            f"{plc_config.get('host', '')}:{plc_config.get('port', 9600)}"
        )

    def _start_plc_worker(self) -> None:
        plc_config = self.config["devices"]["plc"]
        self._set_plc_connection(False, "PLC 连接中")
        self.plc_thread = QThread(self)
        self.plc_worker = PlcWorker(plc_config)
        self.plc_worker.moveToThread(self.plc_thread)

        self.plc_thread.started.connect(self.plc_worker.start)
        self.plc_worker.connection_changed.connect(self._set_plc_connection)
        self.plc_worker.tray_id_changed.connect(self.set_tray_id)
        self.plc_worker.write_succeeded.connect(self._on_plc_write_succeeded)
        self.plc_worker.write_failed.connect(self._on_plc_write_failed)
        self.plc_worker.finished.connect(self.plc_thread.quit)
        self.serial_numbers_ready.connect(self.plc_worker.write_serial_numbers)
        self.plc_thread.start()

    def _set_plc_connection(self, connected: bool, message: str) -> None:
        if connected:
            self.ui.plcConnectionLabel.setText("● PLC 已连接")
            self.ui.plcConnectionLabel.setStyleSheet(
                "background: #e9f7ef; color: #137333; "
                "border: 1px solid #a7d7b5; border-radius: 15px; "
                "padding: 0 14px; font-weight: 600;"
            )
        else:
            self.ui.plcConnectionLabel.setText("● PLC 未连接")
            self.ui.plcConnectionLabel.setStyleSheet(
                "background: #fff4e5; color: #a15c00; "
                "border: 1px solid #efc98f; border-radius: 15px; "
                "padding: 0 14px; font-weight: 600;"
            )
        self.ui.plcConnectionLabel.setToolTip(message)
        self.statusBar().showMessage(message)
        self.append_log(message)

    def set_tray_id(self, tray_id: str) -> None:
        """由 PLC 通信层在读取到 RFID 托盘编号后调用。"""
        tray_id = str(tray_id or "").strip()
        self.ui.trayIdEdit.setText(tray_id)
        if tray_id:
            self.append_log(f"PLC 已读取托盘编号：{tray_id}")
            self.serial_inputs[0].setFocus()
        else:
            self.append_log("PLC 托盘编号已清除。")
        self._update_sn_progress()

    def serial_numbers(self) -> List[str]:
        return [serial_input.text().strip() for serial_input in self.serial_inputs]

    def _accept_scan(self, index: int) -> None:
        self.scan_timers[index].stop()
        self.scan_started_at[index] = None
        serial_input = self.serial_inputs[index]
        serial_number = self.serial_number_service.normalize(serial_input.text())
        serial_input.setText(serial_number)
        if not serial_number:
            return

        duplicate_position = next(
            (
                other_index
                for other_index, other_input in enumerate(self.serial_inputs)
                if other_index != index
                and other_input.text().strip() == serial_number
            ),
            None,
        )
        if duplicate_position is not None:
            serial_input.clear()
            serial_input.setFocus()
            self._warn(
                f"SN {serial_number} 已在位置 {duplicate_position + 1} 录入，不能重复。"
            )
            return

        self.append_log(f"位置 {index + 1} 扫码完成：{serial_number}")
        if index + 1 < len(self.serial_inputs):
            self.serial_inputs[index + 1].setFocus()
            self.serial_inputs[index + 1].selectAll()
        else:
            self.ui.submitButton.setFocus()

    def _fill_serial_numbers(self) -> None:
        try:
            serial_numbers = self.serial_number_service.build_sequence(
                self.serial_inputs[0].text()
            )
        except SerialNumberError as error:
            self._warn(str(error))
            self.serial_inputs[0].setFocus()
            return

        for serial_input, serial_number in zip(self.serial_inputs, serial_numbers):
            serial_input.setText(serial_number)
        self.ui.submitButton.setFocus()
        self.append_log(
            f"已从 {serial_numbers[0]} 顺序补齐至 {serial_numbers[-1]}。"
        )

    def _clear_serial_numbers(self) -> None:
        for index, serial_input in enumerate(self.serial_inputs):
            self.scan_timers[index].stop()
            self.scan_started_at[index] = None
            serial_input.clear()
        self.serial_inputs[0].setFocus()
        self.append_log("已清空当前托盘的 10 个 SN。")

    def _submit_serial_numbers(self) -> None:
        tray_id = self.ui.trayIdEdit.text().strip()
        if not tray_id:
            self._warn("尚未收到 PLC 读取的托盘编号，不能写入 SN。")
            return

        try:
            serial_numbers = self.serial_number_service.validate_plc_uint32_batch(
                self.serial_numbers()
            )
        except SerialNumberError as error:
            self._warn(str(error))
            return

        batch = TrayBatch(tray_id=tray_id, serial_numbers=serial_numbers)
        self.serial_numbers_ready.emit(batch.tray_id, batch.serial_numbers)
        self.ui.testStateLabel.setText("当前状态：等待 PLC 写入确认")
        self.append_log(
            f"托盘 {batch.tray_id} 的 10 个 SN 已生成 PLC 写入请求。"
        )

    def _on_plc_write_succeeded(self, tray_id: str) -> None:
        mapping = self.config["devices"]["plc"]["mapping"]
        start_address = int(mapping["serial_start_address"])
        end_address = start_address + int(mapping["serial_count"]) * 2 - 1
        self.ui.testStateLabel.setText("当前状态：PLC 写入完成")
        self.append_log(
            f"托盘 {tray_id} 的 10 个 SN 已写入 "
            f"D{start_address}-D{end_address} 并通过回读校验。"
        )

    def _on_plc_write_failed(self, message: str) -> None:
        self.ui.testStateLabel.setText("当前状态：PLC 写入失败")
        self.append_log(f"PLC 写入失败：{message}")
        QMessageBox.warning(self, "PLC 写入失败", message)

    def _update_sn_progress(self) -> None:
        completed = sum(bool(item.text().strip()) for item in self.serial_inputs)
        tray_id = self.ui.trayIdEdit.text().strip()
        if completed == SerialNumberService.MOTOR_COUNT:
            state = "SN 已就绪"
        elif tray_id:
            state = f"已录入 {completed}/{SerialNumberService.MOTOR_COUNT}"
        else:
            state = f"等待托盘，已录入 {completed}/{SerialNumberService.MOTOR_COUNT}"
        self.ui.testStateLabel.setText(f"当前状态：{state}")

    def _warn(self, message: str) -> None:
        self.append_log(f"录入提示：{message}")
        QMessageBox.warning(self, "SN 录入", message)

    def append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ui.logOutput.appendPlainText(f"[{timestamp}] {message}")

    def closeEvent(self, event: object) -> None:
        if (
            self.plc_worker is not None
            and self.plc_thread is not None
            and self.plc_thread.isRunning()
        ):
            QMetaObject.invokeMethod(
                self.plc_worker,
                "stop",
                Qt.ConnectionType.QueuedConnection,
            )
            if not self.plc_thread.wait(1500):
                self.plc_thread.quit()
                self.plc_thread.wait(1000)
        event.accept()


def create_application(argv: Optional[Sequence[str]] = None) -> QApplication:
    app = QApplication(list(argv) if argv is not None else sys.argv)
    application_config = CONFIG.load("app").get("application", {})
    app.setApplicationName(application_config.get("name", "Motor Run-in Test"))
    app.setOrganizationName("Motor Test")
    return app


def main(argv: Optional[Sequence[str]] = None) -> int:
    app = create_application(argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
