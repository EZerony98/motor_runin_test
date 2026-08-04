import os
import unittest

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
        self.window = MainWindow(start_plc=False)
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()

    def test_fill_button_generates_ten_serial_numbers(self) -> None:
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()
        self.assertEqual(self.window.serial_numbers()[0], "C66HNI042665")
        self.assertEqual(self.window.serial_numbers()[-1], "C66HNI042674")

    def test_submit_emits_tray_and_serial_numbers(self) -> None:
        submissions = []
        self.window.serial_numbers_ready.connect(
            lambda tray_id, serial_numbers: submissions.append(
                (tray_id, serial_numbers)
            )
        )
        self.window.set_tray_id("TRAY-001")
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()
        self.window.ui.submitButton.click()

        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0][0], "TRAY-001")
        self.assertEqual(submissions[0][1][-1], "C66HNI042674")

    def test_release_button_clears_tray_and_all_serial_numbers(self) -> None:
        self.window.set_tray_id("7001")
        self.window.serial_inputs[0].setText("C66HNI042665")
        self.window.ui.fillButton.click()

        self.window._on_release_button_pressed()

        self.assertEqual(self.window.ui.trayIdEdit.text(), "")
        self.assertEqual(self.window.serial_numbers(), [""] * 10)
        self.assertIn("已放行", self.window.ui.logOutput.toPlainText())

    def test_tray_layout_uses_two_rows_of_five_inputs(self) -> None:
        self.window.resize(1180, 720)
        self.app.processEvents()

        top_row_y = {item.geometry().y() for item in self.window.serial_inputs[:5]}
        bottom_row_y = {item.geometry().y() for item in self.window.serial_inputs[5:]}
        self.assertEqual(len(top_row_y), 1)
        self.assertEqual(len(bottom_row_y), 1)
        self.assertGreater(next(iter(bottom_row_y)), next(iter(top_row_y)))
        self.assertIsNotNone(self.window.ui.logoLabel.pixmap())

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
