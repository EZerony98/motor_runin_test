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
        self.window.serial_inputs[0].setText("00000001")
        self.window.ui.fillButton.click()
        self.assertEqual(self.window.serial_numbers()[0], "00000001")
        self.assertEqual(self.window.serial_numbers()[-1], "00000010")

    def test_submit_emits_tray_and_serial_numbers(self) -> None:
        submissions = []
        self.window.serial_numbers_ready.connect(
            lambda tray_id, serial_numbers: submissions.append(
                (tray_id, serial_numbers)
            )
        )
        self.window.set_tray_id("TRAY-001")
        self.window.serial_inputs[0].setText("00000101")
        self.window.ui.fillButton.click()
        self.window.ui.submitButton.click()

        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0][0], "TRAY-001")
        self.assertEqual(submissions[0][1][-1], "00000110")

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

    def test_fast_scanner_input_auto_advances_without_enter(self) -> None:
        first_input = self.window.serial_inputs[0]
        second_input = self.window.serial_inputs[1]
        first_input.setFocus()

        QTest.keyClicks(first_input, "00020001", delay=5)
        QTest.qWait(self.window.scanner_auto_finish_delay_ms + 80)

        self.assertTrue(second_input.hasFocus())
        self.assertEqual(first_input.text(), "00020001")


if __name__ == "__main__":
    unittest.main()
