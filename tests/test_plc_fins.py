import unittest

from drivers.plc_fins import FinsPlcDriver


def simulation_config():
    return {
        "host": "127.0.0.1",
        "port": 9600,
        "simulation": True,
        "mapping": {
            "release_button_address": 3000,
            "release_button_bit": 0,
            "tray_id_address": 3008,
            "tray_id_words": 1,
            "tray_id_type": "int16",
            "serial_start_address": 3456,
            "serial_slot_words": 50,
            "serial_count": 10,
            "serial_encoding": "ascii",
            "serial_byte_order": "low_high",
        },
    }


class FinsPlcDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = FinsPlcDriver(simulation_config())
        self.driver.connect()

    def tearDown(self) -> None:
        self.driver.disconnect()

    def test_register_mapping_matches_sysmac_variables(self) -> None:
        self.assertEqual(self.driver.release_button_address, 3000)
        self.assertEqual(self.driver.release_button_bit, 0)
        self.assertEqual(self.driver.tray_id_address, 3008)
        self.assertEqual(self.driver.serial_addresses[0], 3456)
        self.assertEqual(self.driver.serial_addresses[-1], 3906)
        self.assertEqual(self.driver.last_serial_address, 3955)
        self.assertEqual(self.driver.serial_max_bytes, 99)

    def test_ascii_string_uses_sysmac_low_byte_first_layout(self) -> None:
        words = self.driver.ascii_to_words("C66HNI042665", 50, "low_high")
        self.assertEqual(
            words[:7],
            [0x3643, 0x4836, 0x494E, 0x3430, 0x3632, 0x3536, 0x0000],
        )
        self.assertEqual(
            self.driver.words_to_ascii(words, "low_high"),
            "C66HNI042665",
        )

    def test_read_tray_and_write_ten_ascii_serial_numbers(self) -> None:
        self.driver.set_simulated_tray_id("7001")
        serial_numbers = [f"C66HNI{42665 + offset:06d}" for offset in range(10)]
        self.driver.write_tray_serial_numbers("7001", serial_numbers)

        self.assertEqual(self.driver.read_tray_id(), "7001")
        first_words = self.driver.read_words(3456, 50)
        last_words = self.driver.read_words(3906, 50)
        self.assertEqual(
            self.driver.words_to_ascii(first_words, "low_high"),
            serial_numbers[0],
        )
        self.assertEqual(
            self.driver.words_to_ascii(last_words, "low_high"),
            serial_numbers[-1],
        )

    def test_release_button_reads_d3000_bit_zero(self) -> None:
        self.assertFalse(self.driver.read_release_button())
        self.driver.set_simulated_release_button(True)
        self.assertTrue(self.driver.read_release_button())
        self.driver.set_simulated_release_button(False)
        self.assertFalse(self.driver.read_release_button())

    def test_non_ascii_serial_number_is_rejected(self) -> None:
        self.driver.set_simulated_tray_id("7001")
        serial_numbers = [f"SN{offset:02d}" for offset in range(9)] + ["电机10"]
        with self.assertRaisesRegex(ValueError, "非 ASCII"):
            self.driver.write_tray_serial_numbers("7001", serial_numbers)


if __name__ == "__main__":
    unittest.main()
