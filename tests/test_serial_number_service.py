import unittest

from services.serial_number_service import SerialNumberError, SerialNumberService


class SerialNumberServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SerialNumberService()

    def test_build_sequence_preserves_numeric_width(self) -> None:
        serial_numbers = self.service.build_sequence("MOTOR000123")
        self.assertEqual(serial_numbers[0], "MOTOR000123")
        self.assertEqual(serial_numbers[-1], "MOTOR000132")
        self.assertEqual(len(serial_numbers), 10)

    def test_build_sequence_requires_trailing_number(self) -> None:
        with self.assertRaisesRegex(SerialNumberError, "数字结尾"):
            self.service.build_sequence("MOTOR-ABC")

    def test_validate_batch_rejects_missing_positions(self) -> None:
        with self.assertRaisesRegex(SerialNumberError, "2"):
            self.service.validate_batch(["SN001", ""] + [f"SN{i:03d}" for i in range(3, 11)])

    def test_validate_batch_rejects_duplicates(self) -> None:
        serial_numbers = [f"SN{i:03d}" for i in range(1, 10)] + ["SN001"]
        with self.assertRaisesRegex(SerialNumberError, "重复"):
            self.service.validate_batch(serial_numbers)

    def test_plc_batch_requires_uint32_serial_numbers(self) -> None:
        with self.assertRaisesRegex(SerialNumberError, "纯数字"):
            self.service.validate_plc_uint32_batch(
                [f"MOTOR{i:04d}" for i in range(1, 11)]
            )

    def test_plc_batch_accepts_numeric_serial_numbers(self) -> None:
        serial_numbers = [f"{i:08d}" for i in range(1, 11)]
        self.assertEqual(
            self.service.validate_plc_uint32_batch(serial_numbers),
            serial_numbers,
        )
