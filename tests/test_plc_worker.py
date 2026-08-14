import unittest

from tests.test_plc_fins import simulation_config
from workers.plc_worker import PlcWorker


class PlcWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.worker = PlcWorker(simulation_config())

    def tearDown(self) -> None:
        self.worker.driver.disconnect()

    def test_release_button_emits_only_on_rising_edge(self) -> None:
        presses = []
        releases = []
        self.worker.release_button_pressed.connect(lambda: presses.append(True))
        self.worker.release_button_released.connect(
            lambda: releases.append(True)
        )

        self.worker.poll()
        self.worker.driver.set_simulated_release_button(True)
        self.worker.poll()
        self.worker.poll()
        self.worker.driver.set_simulated_release_button(False)
        self.worker.poll()
        self.worker.driver.set_simulated_release_button(True)
        self.worker.poll()

        self.assertEqual(presses, [True, True])
        self.assertEqual(releases, [True])

    def test_connect_resets_stale_loading_saved_permission(self) -> None:
        self.worker.driver.connect()
        self.worker.driver.write_control("loading_saved", True)
        self.worker.driver.disconnect()

        self.worker.poll()

        self.assertFalse(
            self.worker.driver.read_control_states()["loading_saved"]
        )

    def test_control_write_and_poll_emit_current_states(self) -> None:
        writes = []
        states = []
        self.worker.control_write_succeeded.connect(
            lambda name, value: writes.append((name, value))
        )
        self.worker.control_states_changed.connect(states.append)

        self.worker.write_control("mode_auto", True)
        self.worker.write_control("emergency_stop_ok", True)
        self.worker.poll()

        self.assertEqual(
            writes,
            [("mode_auto", True), ("emergency_stop_ok", True)],
        )
        self.assertEqual(states[-1]["mode_auto"], True)
        self.assertEqual(states[-1]["emergency_stop_ok"], True)


if __name__ == "__main__":
    unittest.main()
