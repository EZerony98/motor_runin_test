import unittest

from drivers.plc_fins import FinsPlcDriver


def simulation_config():
    return {
        "host": "127.0.0.1",
        "port": 9600,
        "simulation": True,
        "mapping": {
            "control_word_address": 3000,
            "release_button_bit": 0,
            "mode_button_bit": 1,
            "reset_button_bit": 2,
            "start_button_bit": 3,
            "emergency_stop_bit": 4,
            "loading_saved_bit": 5,
            "tray_id_address": 3008,
            "tray_id_words": 1,
            "tray_id_type": "int16",
        },
    }


class FinsPlcDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = FinsPlcDriver(simulation_config())
        self.driver.connect()

    def tearDown(self) -> None:
        self.driver.disconnect()

    def test_register_mapping_matches_sysmac_variables(self) -> None:
        self.assertEqual(self.driver.control_word_address, 3000)
        self.assertEqual(self.driver.release_button_bit, 0)
        self.assertEqual(
            self.driver.control_bits,
            {
                "mode_auto": 1,
                "reset": 2,
                "start": 3,
                "emergency_stop_ok": 4,
                "loading_saved": 5,
            },
        )
        self.assertEqual(self.driver.tray_id_address, 3008)

    def test_release_button_reads_d3000_bit_zero(self) -> None:
        self.assertFalse(self.driver.read_release_button())

    def test_simulation_tray_id_is_seeded_on_connect(self) -> None:
        config = simulation_config()
        config["simulation_tray_id"] = "7001"
        driver = FinsPlcDriver(config)

        driver.connect()

        self.assertEqual(driver.read_tray_id(), "7001")
        driver.disconnect()
        self.driver.set_simulated_release_button(True)
        self.assertTrue(self.driver.read_release_button())
        self.driver.set_simulated_release_button(False)
        self.assertFalse(self.driver.read_release_button())

    def test_control_bits_write_independently(self) -> None:
        self.driver.set_simulated_release_button(True)
        self.driver.write_control("mode_auto", True)
        self.driver.write_control("reset", True)
        self.driver.write_control("start", False)
        self.driver.write_control("emergency_stop_ok", True)
        self.driver.write_control("loading_saved", True)

        states = self.driver.read_control_states()
        self.assertEqual(
            states,
            {
                "mode_auto": True,
                "reset": True,
                "start": False,
                "emergency_stop_ok": True,
                "loading_saved": True,
                "release_button": True,
            },
        )
        self.assertEqual(self.driver.read_words(3000, 1), [0b110111])

    def test_loading_saved_permission_uses_d3000_bit_five(self) -> None:
        self.driver.write_control("loading_saved", True)
        self.assertEqual(self.driver.read_words(3000, 1), [1 << 5])

        self.driver.write_control("loading_saved", False)
        self.assertEqual(self.driver.read_words(3000, 1), [0])

    def test_real_control_write_uses_fins_dm_bit_command(self) -> None:
        config = simulation_config()
        config["simulation"] = False
        driver = FinsPlcDriver(config)
        commands = []
        driver._connected = True
        driver._request = lambda command: commands.append(command) or bytes(14)

        driver.write_control("mode_auto", True)

        self.assertEqual(
            commands,
            [b"\x01\x02\x02\x0b\xb8\x01\x00\x01\x01"],
        )


if __name__ == "__main__":
    unittest.main()
