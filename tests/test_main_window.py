import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from main import MainWindow


class MainWindowSerialEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(["main-window-test"])

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "traceability.db"
        self.window = MainWindow(start_plc=False, database_path=database_path)
        self.window.mapping_sync_timer.stop()
        self.window.mapping_sync_service.config["enabled"] = False
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.temporary_directory.cleanup()

    def test_fill_button_generates_ten_serial_numbers(self) -> None:
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()
        self.assertEqual(self.window.serial_numbers()[0], "C66HNI042665")
        self.assertEqual(self.window.serial_numbers()[-1], "C66HNI042674")

    def test_submit_saves_tray_mapping_locally(self) -> None:
        requests = []
        self.window.plc_control_requested.connect(
            lambda name, value: requests.append((name, value))
        )
        self.window.set_tray_id("TRAY-001")
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()
        self.window.ui.submitButton.click()

        first_product = self.window.traceability_service.resolve_product(
            "TRAY-001", 1
        )
        last_product = self.window.traceability_service.resolve_product(
            "TRAY-001", 10
        )
        self.assertEqual(first_product["product_sn"], "C66HNI042665")
        self.assertEqual(last_product["product_sn"], "C66HNI042674")
        self.assertEqual(self.window.ui.submitButton.text(), "保存上料信息")
        self.assertIn("已保存到本地数据库", self.window.ui.logOutput.toPlainText())
        self.assertEqual(requests[-1], ("loading_saved", True))

    def test_debug_tray_id_can_be_entered_manually_and_saved(self) -> None:
        self.assertFalse(self.window.ui.trayIdEdit.isReadOnly())
        self.window.ui.trayIdEdit.setText("DEBUG-TRAY-001")
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()
        self.window.ui.submitButton.click()

        product = self.window.traceability_service.resolve_product(
            "DEBUG-TRAY-001", 1
        )
        self.assertEqual(product["product_sn"], "C66HNI042665")

    def test_release_button_clears_tray_and_all_serial_numbers(self) -> None:
        self.window.set_tray_id("7001")
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()

        self.window._on_release_button_pressed()

        self.assertEqual(self.window.ui.trayIdEdit.text(), "7001")
        self.assertTrue(self.window.release_clear_pending)
        self.window._on_control_write_succeeded("loading_saved", True)

        self.assertEqual(self.window.ui.trayIdEdit.text(), "")
        self.assertEqual(self.window.serial_numbers(), [""] * 10)
        self.assertIn("已放行", self.window.ui.logOutput.toPlainText())
        product = self.window.traceability_service.resolve_product("7001", 1)
        self.assertEqual(product["product_sn"], "C66HNI042665")
        self.assertIn(
            "放行前自动保存", self.window.ui.logOutput.toPlainText()
        )

    def test_release_button_keeps_incomplete_unsaved_information(self) -> None:
        warnings = []
        self.window._warn = warnings.append
        self.window.set_tray_id("7002")
        self.window.serial_inputs[0].setText("C66HNI042665")

        self.window._on_release_button_pressed()

        self.assertEqual(self.window.ui.trayIdEdit.text(), "7002")
        self.assertEqual(
            self.window.serial_inputs[0].text(), "C66HNI042665"
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("信息已保留", self.window.ui.testStateLabel.text())

    def test_release_write_failure_keeps_information_and_cancels_clear(self) -> None:
        self.window._warn = lambda _message: None
        self.window.set_tray_id("7003")
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()
        self.window._on_release_button_pressed()

        self.window._on_control_write_failed("loading_saved", "timeout")

        self.assertEqual(self.window.ui.trayIdEdit.text(), "7003")
        self.assertFalse(self.window.release_clear_pending)
        self.assertIn("信息已保留", self.window.ui.testStateLabel.text())

    def test_release_button_up_cancels_pending_clear_and_permission(self) -> None:
        requests = []
        self.window.plc_control_requested.connect(
            lambda name, value: requests.append((name, value))
        )
        self.window.set_tray_id("7004")
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()
        self.window._on_release_button_pressed()

        self.window._on_release_button_released()

        self.assertEqual(self.window.ui.trayIdEdit.text(), "7004")
        self.assertFalse(self.window.release_clear_pending)
        self.assertEqual(requests[-1], ("loading_saved", False))

    def test_edit_after_save_revokes_loading_saved_permission(self) -> None:
        requests = []
        self.window.plc_control_requested.connect(
            lambda name, value: requests.append((name, value))
        )
        self.window.set_tray_id("7005")
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()
        self.window.ui.submitButton.click()
        self.window._on_control_write_succeeded("loading_saved", True)

        self.window.serial_inputs[0].setFocus()
        QTest.keyClick(self.window.serial_inputs[0], Qt.Key.Key_Backspace)

        self.assertEqual(requests[-1], ("loading_saved", False))

    def test_tray_layout_uses_two_rows_of_five_inputs(self) -> None:
        self.window.resize(1180, 720)
        self.app.processEvents()

        bottom_row_y = {
            item.geometry().y() for item in self.window.serial_inputs[:5]
        }
        top_row_y = {
            item.geometry().y() for item in self.window.serial_inputs[5:]
        }
        self.assertEqual(len(top_row_y), 1)
        self.assertEqual(len(bottom_row_y), 1)
        self.assertGreater(next(iter(bottom_row_y)), next(iter(top_row_y)))
        self.assertLess(
            self.window.serial_inputs[0].geometry().x(),
            self.window.serial_inputs[4].geometry().x(),
        )
        self.assertGreater(
            self.window.serial_inputs[5].geometry().x(),
            self.window.serial_inputs[9].geometry().x(),
        )
        self.assertIsNotNone(self.window.ui.logoLabel.pixmap())

    def test_four_runin_device_statuses_and_result_view_are_created(self) -> None:
        self.assertEqual(len(self.window.runinStatusLabels), 4)
        self.assertEqual(self.window.resultDeviceCombo.count(), 4)
        self.assertEqual(len(self.window.runinResultWidget.sn_labels), 10)

    def test_runin_tray_result_is_saved_and_displayed_by_slot(self) -> None:
        self.window.set_tray_id("7001")
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()
        self.window.ui.submitButton.click()
        snapshot = {
            "device_id": "RUNIN_01",
            "device_name": "跑合设备 1",
            "tray_id": "7001",
            "items": [
                {
                    "tray_slot": slot,
                    "runin_current_a": 100 + slot,
                    "runin_voltage_v": 200 + slot,
                    "runin_speed_rpm": 17000 + slot,
                    "runin_temperature_c": 40 + slot,
                    "runin_passed": slot != 10,
                    "runin_result_code": 0 if slot != 10 else 1,
                    "runin_error_code": 0 if slot != 10 else 105,
                }
                for slot in range(1, 11)
            ],
        }

        self.window._on_runin_result_ready("RUNIN_01", snapshot)

        self.assertIn(
            "C66HNI042665", self.window.runinResultWidget.sn_labels[0].text()
        )
        self.assertIn(
            "C66HNI042674", self.window.runinResultWidget.sn_labels[9].text()
        )
        self.assertIn("NG", self.window.runinResultWidget.value_labels[9].text())
        self.assertIn("已保存 10/10", self.window.runinResultStateLabel.text())

    def test_runin_live_snapshot_displays_without_saving(self) -> None:
        snapshot = {
            "device_id": "RUNIN_01",
            "device_name": "跑合设备 1",
            "tray_id": "7001",
            "data_ready": False,
            "handshake_word": 0,
            "items": [
                {
                    "tray_slot": slot,
                    "runin_current_a": 100 + slot,
                    "runin_voltage_v": 200 + slot,
                    "runin_speed_rpm": 17000 + slot,
                    "runin_temperature_c": 40 + slot,
                    "runin_passed": None,
                    "runin_result_code": None,
                    "runin_error_code": 0,
                }
                for slot in range(1, 11)
            ],
        }

        self.window._on_runin_live_snapshot("RUNIN_01", snapshot)

        value_text = self.window.runinResultWidget.value_labels[0].text()
        self.assertIn("n 17001  U 201", value_text)
        self.assertIn("T 41  I 101  E 0", value_text)
        self.assertIn("--", self.window.runinResultWidget.value_labels[0].text())
        self.assertIn("D3502.00/.01：0/0", self.window.runinHandshakeLabel.text())

    def test_runin_live_snapshot_displays_invalid_passed_raw_value(self) -> None:
        snapshot = {
            "device_id": "RUNIN_01",
            "device_name": "跑合设备 1",
            "tray_id": "7001",
            "data_ready": False,
            "handshake_word": 0,
            "items": [
                {
                    "tray_slot": 1,
                    "runin_speed_rpm": 21696,
                    "runin_voltage_v": 234,
                    "runin_temperature_c": 57,
                    "runin_current_a": 185,
                    "runin_error_code": 1,
                    "runin_passed_raw": 20,
                    "runin_passed": None,
                }
            ],
        }

        self.window._on_runin_live_snapshot("RUNIN_01", snapshot)

        self.assertIn(
            "异常(20)", self.window.runinResultWidget.value_labels[0].text()
        )
        self.assertIn("实时预览中", self.window.runinResultStateLabel.text())

    def test_runin_address_label_follows_device_configuration(self) -> None:
        self.window.runin_plc_configs[0]["mapping"].update(
            {
                "result_base_address": 2000,
                "result_start_offset": 0,
                "words_per_product": 6,
                "handshake_address": 3002,
                "data_ready_bit": 3,
                "read_complete_bit": 4,
            }
        )

        self.window._update_runin_address_label()

        self.assertIn(
            "D3002.03/.04", self.window.runinHandshakeLabel.text()
        )
        self.assertIn(
            "D2000–D2059", self.window.runinHandshakeLabel.toolTip()
        )

    def test_plc_control_buttons_follow_required_bit_behaviour(self) -> None:
        requests = []
        self.window.plc_control_requested.connect(
            lambda name, value: requests.append((name, value))
        )
        self.window._set_plc_connection(True, "测试连接")
        self.window._update_plc_control_states(
            {
                "mode_auto": False,
                "reset": False,
                "start": False,
                "emergency_stop_ok": True,
            }
        )

        self.window.ui.modeButton.click()
        QTest.mousePress(self.window.ui.resetButton, Qt.MouseButton.LeftButton)
        QTest.mouseRelease(self.window.ui.resetButton, Qt.MouseButton.LeftButton)
        QTest.mousePress(self.window.ui.startButton, Qt.MouseButton.LeftButton)
        QTest.mouseRelease(self.window.ui.startButton, Qt.MouseButton.LeftButton)
        self.window.ui.emergencyButton.click()

        self.assertEqual(
            requests,
            [
                ("mode_auto", True),
                ("reset", True),
                ("reset", False),
                ("start", True),
                ("start", False),
                ("emergency_stop_ok", False),
            ],
        )

    def test_scanner_cr_control_character_advances_focus(self) -> None:
        first_input = self.window.serial_inputs[0]
        second_input = self.window.serial_inputs[1]
        first_input.setFocus()
        first_input.setText("00010001")

        cr_event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_unknown,
            Qt.KeyboardModifier.NoModifier,
            "\r",
        )
        QApplication.sendEvent(first_input, cr_event)
        self.app.processEvents()

        self.assertTrue(second_input.hasFocus())
        self.assertIn("位置 1 扫码完成", self.window.ui.logOutput.toPlainText())

    def test_input_without_terminator_does_not_auto_advance(self) -> None:
        first_input = self.window.serial_inputs[0]
        first_input.setFocus()

        QTest.keyClicks(first_input, "00020001", delay=5)
        QTest.qWait(300)

        self.assertTrue(first_input.hasFocus())
        self.assertEqual(first_input.text(), "00020001")

if __name__ == "__main__":
    unittest.main()
