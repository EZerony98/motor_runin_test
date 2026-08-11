"""电机跑合测试上位机入口。"""

import sys
from datetime import datetime
from functools import partial
from pathlib import Path
from threading import Thread
from typing import Any, Dict, List, Optional, Sequence

from PySide6.QtCore import QEvent, QMetaObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QPixmap, QRegion
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services.config_service import ConfigService
from services.serial_number_service import SerialNumberError, SerialNumberService
from services.traceability_service import TraceabilityService
from services.tray_mapping_sync_service import TrayMappingSyncService
from ui.runin_result_widget import RuninResultWidget
from ui.ui_main import Ui_MainWindow
from workers.plc_worker import PlcWorker
from workers.runin_plc_worker import RuninPlcWorker


PROJECT_DIR = Path(__file__).resolve().parent
CONFIG = ConfigService(PROJECT_DIR / "config")


class MainWindow(QMainWindow):
    """跑合测试主窗口。"""

    plc_control_requested = Signal(str, bool)
    mapping_sync_succeeded = Signal(str, str)
    mapping_sync_failed = Signal(str, str, str)
    mapping_sync_finished = Signal()
    runin_result_processed = Signal(str, bool)

    def __init__(
        self,
        start_plc: bool = True,
        database_path: Optional[Path] = None,
    ) -> None:
        super().__init__()
        self.config = CONFIG.load_all()
        self.serial_number_service = SerialNumberService()
        traceability_config = self.config["server"].get("traceability", {})
        configured_database_path = Path(
            str(traceability_config.get("database_path", "data/traceability.db"))
        )
        if not configured_database_path.is_absolute():
            configured_database_path = PROJECT_DIR / configured_database_path
        self.traceability_service = TraceabilityService(
            database_path or configured_database_path
        )
        self.mapping_sync_service = TrayMappingSyncService(
            traceability_config.get("spectrum_peer", {})
        )
        self.mapping_sync_running = False
        self.plc_thread: Optional[QThread] = None
        self.plc_worker: Optional[PlcWorker] = None
        self.runin_plc_configs = list(
            self.config["devices"].get("runin_plcs", [])
        )
        self.runin_threads: Dict[str, QThread] = {}
        self.runin_workers: Dict[str, RuninPlcWorker] = {}
        self.runin_snapshots: Dict[str, Dict[str, Any]] = {}
        self.runin_records: Dict[str, List[Dict[str, Any]]] = {}
        self.plc_control_states = {
            "mode_auto": False,
            "reset": False,
            "start": False,
            "emergency_stop_ok": False,
        }
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._configure_runin_workspace()
        self.ui.submitButton.setText("保存上料信息")
        self.serial_inputs: List[QLineEdit] = list(
            self.ui.trayEntryWidget.serial_inputs
        )
        for serial_input in self.serial_inputs:
            serial_input.installEventFilter(self)
        self.setWindowTitle(
            self.config["app"]["application"].get("window_title", "电机跑合测试系统")
        )
        self._connect_signals()
        self.mapping_sync_timer = QTimer(self)
        self.mapping_sync_timer.setInterval(
            max(
                5,
                int(
                    traceability_config.get("spectrum_peer", {}).get(
                        "retry_interval_seconds", 15
                    )
                ),
            )
            * 1000
        )
        self.mapping_sync_timer.timeout.connect(
            self._sync_pending_tray_mappings
        )
        if self.mapping_sync_service.enabled:
            self.mapping_sync_timer.start()
            QTimer.singleShot(0, self._sync_pending_tray_mappings)
        self._configure_branding()
        self._configure_plc_status()
        if start_plc:
            self._start_plc_worker()
            self._start_runin_plc_workers()
        else:
            self._set_plc_connection(False, "总控 PLC 未启动")
            for config in self.runin_plc_configs:
                self._set_runin_connection(
                    str(config.get("id")),
                    False,
                    f"{config.get('name', config.get('id'))} "
                    + ("未启动" if config.get("enabled") else "未启用"),
                )
        self._update_sn_progress()
        self.serial_inputs[0].setFocus()
        self.append_log(
            "应用启动完成，等待 PLC 读取托盘编号并录入 10 个电机 SN；"
            "SN 仅保存到上位机，不再写入 PLC。"
        )

    def _connect_signals(self) -> None:
        self.ui.fillButton.clicked.connect(self._fill_serial_numbers)
        self.ui.clearButton.clicked.connect(self._clear_serial_numbers)
        self.ui.submitButton.clicked.connect(self._submit_serial_numbers)
        self.ui.modeButton.clicked.connect(self._request_mode_change)
        self.ui.resetButton.pressed.connect(
            partial(self._request_momentary_control, "reset", True)
        )
        self.ui.resetButton.released.connect(
            partial(self._request_momentary_control, "reset", False)
        )
        self.ui.startButton.pressed.connect(
            partial(self._request_momentary_control, "start", True)
        )
        self.ui.startButton.released.connect(
            partial(self._request_momentary_control, "start", False)
        )
        self.ui.emergencyButton.clicked.connect(
            self._request_emergency_change
        )
        self.mapping_sync_succeeded.connect(self._on_mapping_sync_succeeded)
        self.mapping_sync_failed.connect(self._on_mapping_sync_failed)
        self.mapping_sync_finished.connect(self._on_mapping_sync_finished)

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
        """兼容作为文本输入的 CR/LF，不进行延时自动确认。"""
        if "\r" in text or "\n" in text:
            sanitized = text.replace("\r", "").replace("\n", "").strip()
            self.serial_inputs[index].setText(sanitized)
            self._accept_scan(index)

    def _configure_plc_status(self) -> None:
        plc_config = self.config["devices"]["plc"]
        self.ui.plcConnectionLabel.setText("● 总控 PLC 未连接")
        self.ui.plcAddressLabel.setText(
            f"{plc_config.get('host', '')}:{plc_config.get('port', 9600)}"
        )

    def _configure_runin_workspace(self) -> None:
        self.setStyleSheet(
            self.styleSheet()
            + """
QFrame#runinStatusPanel {
    background: #ffffff;
    border: 1px solid #d8dee5;
    border-radius: 9px;
}
QLabel[runinDeviceStatus="true"] {
    min-height: 28px;
    padding: 0 12px;
    border: 1px solid #d6dce2;
    border-radius: 14px;
    background: #eef1f4;
    color: #7b8794;
    font-weight: 600;
}
QLabel[runinSn="true"] {
    border: 1px solid #c7d1db;
    border-radius: 4px;
    background: #ffffff;
    color: #334e68;
    font-family: Menlo, Consolas, monospace;
    font-size: 11px;
    font-weight: 600;
}
QLabel[runinValue="true"] {
    border-radius: 4px;
    background: #f7f9fb;
    color: #607286;
    font-family: Menlo, Consolas, monospace;
    font-size: 10px;
}
QLabel[runinValue="true"][passed="ok"] {
    background: #e9f7ef;
    color: #137333;
}
QLabel[runinValue="true"][passed="ng"] {
    background: #fff0f2;
    color: #b42334;
}
QTabWidget::pane {
    border: none;
}
QTabBar::tab {
    min-width: 110px;
    min-height: 30px;
    padding: 0 12px;
}
QTabBar::tab:selected {
    color: #d41432;
    font-weight: 700;
}
"""
        )

        self.runinStatusPanel = QFrame(self.ui.centralwidget)
        self.runinStatusPanel.setObjectName("runinStatusPanel")
        status_layout = QHBoxLayout(self.runinStatusPanel)
        status_layout.setContentsMargins(12, 6, 12, 6)
        status_layout.setSpacing(10)
        title = QLabel("跑合设备连接", self.runinStatusPanel)
        title.setStyleSheet("font-weight: 700; color: #33404d;")
        status_layout.addWidget(title)
        self.runinStatusLabels: Dict[str, QLabel] = {}
        for config in self.runin_plc_configs:
            device_id = str(config.get("id"))
            label = QLabel(self.runinStatusPanel)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setProperty("runinDeviceStatus", True)
            self.runinStatusLabels[device_id] = label
            status_layout.addWidget(label, 1)
        self.ui.rootLayout.insertWidget(1, self.runinStatusPanel)

        existing_items = []
        while self.ui.testPanelLayout.count():
            existing_items.append(self.ui.testPanelLayout.takeAt(0))
        self.workspaceTabs = QTabWidget(self.ui.testPanel)
        self.workspaceTabs.setObjectName("workspaceTabs")

        input_tab = QWidget(self.workspaceTabs)
        input_layout = QVBoxLayout(input_tab)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)
        for item in existing_items:
            if item.widget() is not None:
                input_layout.addWidget(item.widget())
            elif item.layout() is not None:
                input_layout.addLayout(item.layout())
        self.workspaceTabs.addTab(input_tab, "上料扫码")

        result_tab = QWidget(self.workspaceTabs)
        result_layout = QVBoxLayout(result_tab)
        result_layout.setContentsMargins(0, 4, 0, 0)
        result_layout.setSpacing(8)
        result_header = QHBoxLayout()
        result_header.addWidget(QLabel("显示设备", result_tab))
        self.resultDeviceCombo = QComboBox(result_tab)
        for config in self.runin_plc_configs:
            self.resultDeviceCombo.addItem(
                f"{config.get('name')}  {config.get('host')}",
                str(config.get("id")),
            )
        result_header.addWidget(self.resultDeviceCombo)
        result_header.addSpacing(18)
        self.runinTrayLabel = QLabel("当前卸载托盘：--", result_tab)
        self.runinTrayLabel.setStyleSheet("font-weight: 700;")
        result_header.addWidget(self.runinTrayLabel)
        result_header.addStretch(1)
        self.runinResultStateLabel = QLabel("等待跑合设备数据", result_tab)
        self.runinResultStateLabel.setStyleSheet("color: #627d98;")
        result_header.addWidget(self.runinResultStateLabel)
        result_layout.addLayout(result_header)
        self.runinResultWidget = RuninResultWidget(result_tab)
        result_layout.addWidget(self.runinResultWidget, 1)
        self.workspaceTabs.addTab(result_tab, "跑合数据")
        self.resultDeviceCombo.currentIndexChanged.connect(
            self._display_selected_runin_result
        )
        self.ui.testPanelLayout.addWidget(self.workspaceTabs)

    def _configure_branding(self) -> None:
        logo = QPixmap(str(PROJECT_DIR / "assets" / "logo.png"))
        if logo.isNull():
            self.ui.logoLabel.setText("LOGO")
            return
        visible_bounds = QRegion(logo.mask()).boundingRect()
        if not visible_bounds.isEmpty():
            logo = logo.copy(visible_bounds)
        self.ui.logoLabel.setPixmap(
            logo.scaled(
                self.ui.logoLabel.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
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
        self.plc_worker.release_button_pressed.connect(
            self._on_release_button_pressed
        )
        self.plc_worker.control_states_changed.connect(
            self._update_plc_control_states
        )
        self.plc_worker.control_write_succeeded.connect(
            self._on_control_write_succeeded
        )
        self.plc_worker.control_write_failed.connect(
            self._on_control_write_failed
        )
        self.plc_worker.finished.connect(self.plc_thread.quit)
        self.plc_control_requested.connect(self.plc_worker.write_control)
        self.plc_thread.start()

    def _start_runin_plc_workers(self) -> None:
        for config in self.runin_plc_configs:
            device_id = str(config.get("id"))
            if not bool(config.get("enabled", False)):
                self._set_runin_connection(
                    device_id,
                    False,
                    f"{config.get('name', device_id)} 未启用",
                )
                continue
            thread = QThread(self)
            worker = RuninPlcWorker(config)
            worker.moveToThread(thread)
            thread.started.connect(worker.start)
            worker.connection_changed.connect(self._set_runin_connection)
            worker.result_ready.connect(self._on_runin_result_ready)
            worker.log.connect(self.append_log)
            worker.finished.connect(thread.quit)
            self.runin_result_processed.connect(
                worker.handle_result_processed
            )
            self.runin_threads[device_id] = thread
            self.runin_workers[device_id] = worker
            self._set_runin_connection(
                device_id,
                False,
                f"{config.get('name', device_id)} 连接中",
            )
            thread.start()

    def _set_runin_connection(
        self, device_id: str, connected: bool, message: str
    ) -> None:
        label = self.runinStatusLabels.get(str(device_id))
        if label is None:
            return
        config = next(
            (
                item
                for item in self.runin_plc_configs
                if str(item.get("id")) == str(device_id)
            ),
            {},
        )
        name = str(config.get("name", device_id))
        enabled = bool(config.get("enabled", False))
        if connected:
            state = "已连接"
            style = (
                "background: #e9f7ef; color: #137333; "
                "border: 1px solid #a7d7b5; border-radius: 14px;"
            )
        elif not enabled:
            state = "未启用"
            style = (
                "background: #eef1f4; color: #7b8794; "
                "border: 1px solid #d6dce2; border-radius: 14px;"
            )
        else:
            state = "未连接"
            style = (
                "background: #fff4e5; color: #a15c00; "
                "border: 1px solid #efc98f; border-radius: 14px;"
            )
        label.setText(f"● {name} {state}")
        label.setStyleSheet(style)
        label.setToolTip(
            f"{config.get('host', '')}:{config.get('port', 9600)}\n{message}"
        )

    def _set_plc_connection(self, connected: bool, message: str) -> None:
        if connected:
            self.ui.plcConnectionLabel.setText("● 总控 PLC 已连接")
            self.ui.plcConnectionLabel.setStyleSheet(
                "background: #e9f7ef; color: #137333; "
                "border: 1px solid #a7d7b5; border-radius: 15px; "
                "padding: 0 14px; font-weight: 600;"
            )
        else:
            self.ui.plcConnectionLabel.setText("● 总控 PLC 未连接")
            self.ui.plcConnectionLabel.setStyleSheet(
                "background: #fff4e5; color: #a15c00; "
                "border: 1px solid #efc98f; border-radius: 15px; "
                "padding: 0 14px; font-weight: 600;"
            )
        self.ui.plcConnectionLabel.setToolTip(message)
        for button in (
            self.ui.modeButton,
            self.ui.resetButton,
            self.ui.startButton,
            self.ui.emergencyButton,
        ):
            button.setEnabled(connected)
        self.statusBar().showMessage(message)
        self.append_log(message)

    def _request_mode_change(self, automatic: bool) -> None:
        self._set_mode_button(automatic)
        self.plc_control_requested.emit("mode_auto", automatic)
        self.append_log(
            f"请求切换为{'自动' if automatic else '手动'}模式。"
        )

    def _request_momentary_control(self, name: str, pressed: bool) -> None:
        self.plc_control_requested.emit(name, pressed)
        label = "复位" if name == "reset" else "启动"
        self.append_log(f"{label}按钮{'按下' if pressed else '松开'}。")

    def _request_emergency_change(self, emergency_active: bool) -> None:
        emergency_stop_ok = not emergency_active
        self._set_emergency_button(emergency_stop_ok)
        self.plc_control_requested.emit(
            "emergency_stop_ok", emergency_stop_ok
        )
        self.append_log(
            "请求进入急停状态。"
            if emergency_active
            else "请求解除急停状态。"
        )

    def _update_plc_control_states(self, states: dict) -> None:
        self.plc_control_states.update(states)
        self._set_mode_button(self.plc_control_states["mode_auto"])
        self.ui.resetButton.setDown(self.plc_control_states["reset"])
        self.ui.startButton.setDown(self.plc_control_states["start"])
        self._set_emergency_button(
            self.plc_control_states["emergency_stop_ok"]
        )

    def _set_mode_button(self, automatic: bool) -> None:
        self.ui.modeButton.setChecked(automatic)
        self.ui.modeButton.setText("自动模式" if automatic else "手动模式")

    def _set_emergency_button(self, emergency_stop_ok: bool) -> None:
        emergency_active = not emergency_stop_ok
        self.ui.emergencyButton.setChecked(emergency_active)
        self.ui.emergencyButton.setText(
            "急停中" if emergency_active else "急停正常"
        )

    def _on_control_write_succeeded(self, name: str, value: bool) -> None:
        self.plc_control_states[name] = value
        self._update_plc_control_states(self.plc_control_states)

    def _on_control_write_failed(self, name: str, message: str) -> None:
        labels = {
            "mode_auto": "模式切换",
            "reset": "复位",
            "start": "启动",
            "emergency_stop_ok": "急停",
        }
        label = labels.get(name, name)
        self.append_log(f"PLC {label}命令写入失败：{message}")
        QMessageBox.warning(self, "PLC 控制失败", f"{label}命令失败：{message}")

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
        for serial_input in self.serial_inputs:
            serial_input.clear()
        self.serial_inputs[0].setFocus()
        self.append_log("已清空当前托盘的 10 个 SN。")

    def _on_release_button_pressed(self) -> None:
        """PLC 实体放行按钮上升沿到达后清空本次上料信息。"""
        released_tray_id = self.ui.trayIdEdit.text().strip()
        self.ui.trayIdEdit.clear()
        for serial_input in self.serial_inputs:
            serial_input.clear()
        self.serial_inputs[0].setFocus()
        self._update_sn_progress()
        if released_tray_id:
            self.append_log(
                f"检测到 PLC 实体放行按钮，托盘 {released_tray_id} 已放行，"
                "录入信息已清空。"
            )
        else:
            self.append_log("检测到 PLC 实体放行按钮，录入信息已清空。")

    def _submit_serial_numbers(self) -> None:
        tray_id = self.ui.trayIdEdit.text().strip()
        if not tray_id:
            self._warn("请输入托盘编号，或等待 PLC 读取 RFID 后再保存上料信息。")
            return

        try:
            serial_numbers = self.serial_number_service.validate_batch(
                self.serial_numbers()
            )
            too_long_positions = [
                str(index)
                for index, serial_number in enumerate(serial_numbers, start=1)
                if len(serial_number) > 50
            ]
            if too_long_positions:
                raise SerialNumberError(
                    "以下位置的 SN 超过 PostgreSQL VARCHAR(50)："
                    + "、".join(too_long_positions)
                )
        except SerialNumberError as error:
            self._warn(str(error))
            return

        try:
            batch = self.traceability_service.save_tray_batch(
                tray_id, serial_numbers
            )
        except Exception as error:
            self._warn(f"上料信息本地保存失败：{error}")
            return

        self.ui.testStateLabel.setText("当前状态：上料信息已保存")
        self.append_log(
            f"托盘 {tray_id} 的 10 个坑位与 SN 已保存到本地数据库，"
            f"批次 {batch['tray_cycle_id']}。"
        )
        self._sync_pending_tray_mappings()

    def _sync_pending_tray_mappings(self) -> None:
        if not self.mapping_sync_service.enabled:
            self.append_log("频谱电脑映射同步未启用，数据保留在本机等待配置。")
            return
        if self.mapping_sync_running:
            return
        self.mapping_sync_running = True
        Thread(target=self._run_mapping_sync, daemon=True).start()

    def _run_mapping_sync(self) -> None:
        try:
            for batch in self.traceability_service.pending_peer_batches():
                tray_cycle_id = batch["tray_cycle_id"]
                try:
                    self.mapping_sync_service.send(batch)
                except Exception as error:
                    self.traceability_service.mark_peer_sync_failed(
                        tray_cycle_id, str(error)
                    )
                    self.mapping_sync_failed.emit(
                        tray_cycle_id, batch["tray_id"], str(error)
                    )
                    continue
                self.traceability_service.mark_peer_synced(tray_cycle_id)
                self.mapping_sync_succeeded.emit(
                    tray_cycle_id, batch["tray_id"]
                )
        finally:
            self.mapping_sync_finished.emit()

    def _on_mapping_sync_succeeded(
        self, tray_cycle_id: str, tray_id: str
    ) -> None:
        self.append_log(
            f"托盘 {tray_id} 的坑位与 SN 映射已同步到频谱电脑。"
        )

    def _on_mapping_sync_failed(
        self, tray_cycle_id: str, tray_id: str, message: str
    ) -> None:
        self.append_log(
            f"托盘 {tray_id} 映射同步失败，已保留待重试：{message}"
        )

    def _on_mapping_sync_finished(self) -> None:
        self.mapping_sync_running = False

    def _on_runin_result_ready(
        self, device_id: str, snapshot: Dict[str, Any]
    ) -> None:
        """显示、关联并保存一盘10个产品结果，成功后通知PLC放行。"""
        device_id = str(device_id)
        self.runin_snapshots[device_id] = dict(snapshot)
        selected_index = self.resultDeviceCombo.findData(device_id)
        if selected_index >= 0:
            self.resultDeviceCombo.setCurrentIndex(selected_index)
        tray_id = str(snapshot.get("tray_id", "")).strip()
        raw_items = [dict(item) for item in snapshot.get("items", [])]
        self.runinResultWidget.set_results(raw_items)
        self.runinTrayLabel.setText(f"当前卸载托盘：{tray_id or '--'}")
        self.runinResultStateLabel.setText("正在匹配 SN 并保存本地数据…")
        self.runinResultStateLabel.setStyleSheet("color: #627d98;")

        try:
            records = self.traceability_service.save_runin_tray_results(
                tray_id,
                device_id,
                raw_items,
            )
        except Exception as error:
            self.runinResultStateLabel.setText(f"保存失败：{error}")
            self.runinResultStateLabel.setStyleSheet(
                "color: #b42334; font-weight: 700;"
            )
            self.append_log(
                f"{snapshot.get('device_name', device_id)} 托盘 {tray_id} "
                f"跑合数据未确认：{error}"
            )
            self.runin_result_processed.emit(device_id, False)
            return

        self.runin_records[device_id] = records
        self.runinResultWidget.set_results(records)
        passed_count = sum(bool(item["runin_passed"]) for item in records)
        self.runinResultStateLabel.setText(
            f"已保存 10/10，合格 {passed_count}，不合格 {10 - passed_count}"
        )
        self.runinResultStateLabel.setStyleSheet(
            "color: #137333; font-weight: 700;"
        )
        self.workspaceTabs.setTabText(1, f"跑合数据 · {tray_id}")
        self.append_log(
            f"{snapshot.get('device_name', device_id)} 托盘 {tray_id} 的 "
            "10 个产品跑合数据已保存，向 PLC 写入读取完成确认。"
        )
        self.runin_result_processed.emit(device_id, True)

    def _display_selected_runin_result(self) -> None:
        device_id = str(self.resultDeviceCombo.currentData() or "")
        records = self.runin_records.get(device_id)
        snapshot = self.runin_snapshots.get(device_id)
        if records:
            self.runinResultWidget.set_results(records)
            tray_id = str(records[0].get("tray_id", ""))
            passed_count = sum(bool(item["runin_passed"]) for item in records)
            self.runinTrayLabel.setText(f"当前卸载托盘：{tray_id or '--'}")
            self.runinResultStateLabel.setText(
                f"已保存 10/10，合格 {passed_count}，不合格 {10 - passed_count}"
            )
            self.runinResultStateLabel.setStyleSheet(
                "color: #137333; font-weight: 700;"
            )
            return
        if snapshot:
            self.runinResultWidget.set_results(snapshot.get("items", []))
            self.runinTrayLabel.setText(
                f"当前卸载托盘：{snapshot.get('tray_id') or '--'}"
            )
            self.runinResultStateLabel.setText("数据等待保存确认")
            self.runinResultStateLabel.setStyleSheet("color: #a15c00;")
            return
        self.runinResultWidget.clear_results()
        self.runinTrayLabel.setText("当前卸载托盘：--")
        self.runinResultStateLabel.setText("等待跑合设备数据")
        self.runinResultStateLabel.setStyleSheet("color: #627d98;")

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
        for device_id, worker in list(self.runin_workers.items()):
            thread = self.runin_threads.get(device_id)
            if thread is None or not thread.isRunning():
                continue
            QMetaObject.invokeMethod(
                worker,
                "stop",
                Qt.ConnectionType.QueuedConnection,
            )
        for thread in self.runin_threads.values():
            if thread.isRunning() and not thread.wait(1500):
                thread.quit()
                thread.wait(1000)
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
