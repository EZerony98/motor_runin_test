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
        self.worker.release_button_pressed.connect(lambda: presses.append(True))

        self.worker.poll()
        self.worker.driver.set_simulated_release_button(True)
        self.worker.poll()
        self.worker.poll()
        self.worker.driver.set_simulated_release_button(False)
        self.worker.poll()
        self.worker.driver.set_simulated_release_button(True)
        self.worker.poll()

        self.assertEqual(presses, [True, True])


if __name__ == "__main__":
    unittest.main()
