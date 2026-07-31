import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from main import MainWindow


class MainWindowSerialEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(["main-window-test"])

    def setUp(self) -> None:
        self.window = MainWindow(start_plc=False)

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


if __name__ == "__main__":
    unittest.main()
