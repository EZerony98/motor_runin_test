import unittest

from drivers.plc_fins import FinsPlcDriver


def simulation_config():
    return {
        "host": "127.0.0.1",
        "port": 9600,
        "simulation": True,
        "mapping": {
            "tray_id_address": 3580,
            "serial_start_address": 3582,
            "words_per_value": 2,
            "serial_count": 10,
            "value_type": "uint32",
            "word_order": "low_high",
        },
    }


class FinsPlcDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = FinsPlcDriver(simulation_config())
        self.driver.connect()

    def tearDown(self) -> None:
        self.driver.disconnect()

    def test_register_mapping_ends_at_d3601(self) -> None:
        self.assertEqual(self.driver.tray_id_address, 3580)
        self.assertEqual(self.driver.serial_start_address, 3582)
        self.assertEqual(self.driver.last_serial_address, 3601)

    def test_uint32_low_word_is_stored_first(self) -> None:
        words = self.driver.uint32_to_words(0x12345678, "low_high")
        self.assertEqual(words, [0x5678, 0x1234])
        self.assertEqual(
            self.driver.words_to_uint32(words, "low_high"),
            0x12345678,
        )

    def test_read_tray_and_write_ten_serial_numbers(self) -> None:
        self.driver.set_simulated_tray_id("70001")
        serial_numbers = [str(100001 + offset) for offset in range(10)]
        self.driver.write_tray_serial_numbers("70001", serial_numbers)

        self.assertEqual(self.driver.read_tray_id(), "70001")
        first_words = self.driver.read_words(3582, 2)
        last_words = self.driver.read_words(3600, 2)
        self.assertEqual(
            self.driver.words_to_uint32(first_words, "low_high"),
            100001,
        )
        self.assertEqual(
            self.driver.words_to_uint32(last_words, "low_high"),
            100010,
        )

    def test_non_numeric_serial_number_is_rejected(self) -> None:
        self.driver.set_simulated_tray_id("70001")
        serial_numbers = [str(100001 + offset) for offset in range(9)] + ["SN10"]
        with self.assertRaisesRegex(ValueError, "纯数字"):
            self.driver.write_tray_serial_numbers("70001", serial_numbers)


if __name__ == "__main__":
    unittest.main()
