import unittest

from drivers.runin_plc import RuninPlcDriver
from workers.runin_plc_worker import RuninPlcWorker


def runin_simulation_config():
    return {
        "id": "RUNIN_01",
        "name": "跑合设备 1",
        "enabled": True,
        "host": "127.0.0.1",
        "port": 9600,
        "simulation": True,
        "mapping": {
            "tray_id_address": 3008,
            "tray_id_words": 1,
            "tray_id_type": "int16",
            "result_base_address": 1000,
            "products_per_tray": 10,
            "words_per_product": 5,
            "handshake_address": 3502,
            "data_ready_bit": 0,
            "read_complete_bit": 1,
        },
    }


def sample_rows():
    return [
        [100 + slot, 200 + slot, 17000 + slot, 40 + slot, slot != 10]
        for slot in range(1, 11)
    ]


class RuninPlcDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = RuninPlcDriver(runin_simulation_config())
        self.driver.connect()

    def tearDown(self) -> None:
        self.driver.disconnect()

    def test_reads_dm1000_to_1049_as_ten_interleaved_results(self) -> None:
        self.driver.set_simulated_result("7001", sample_rows())

        snapshot = self.driver.read_result_snapshot()

        self.assertEqual(snapshot["tray_id"], "7001")
        self.assertEqual(len(snapshot["items"]), 10)
        self.assertEqual(snapshot["items"][0]["runin_current_a"], 101)
        self.assertEqual(snapshot["items"][9]["runin_voltage_v"], 210)
        self.assertFalse(snapshot["items"][9]["runin_passed"])

    def test_writes_read_complete_to_dm3502_bit_one(self) -> None:
        self.driver.write_read_complete(True)
        self.assertEqual(self.driver.read_words(3502, 1)[0], 0b10)
        self.driver.write_read_complete(False)
        self.assertEqual(self.driver.read_words(3502, 1)[0], 0)


class RuninPlcWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.worker = RuninPlcWorker(runin_simulation_config())

    def tearDown(self) -> None:
        self.worker.driver.disconnect()

    def test_emits_once_then_completes_four_phase_handshake(self) -> None:
        received = []
        self.worker.result_ready.connect(lambda device_id, data: received.append(data))
        self.worker.driver.connect()
        self.worker.driver.set_simulated_result("7001", sample_rows())

        self.worker.poll()
        self.worker.poll()
        self.assertEqual(len(received), 1)

        self.worker.handle_result_processed("RUNIN_01", True)
        self.assertEqual(self.worker.driver.read_words(3502, 1)[0], 0b11)

        self.worker.driver.write_bit(3502, 0, False)
        self.worker.poll()
        self.assertEqual(self.worker.driver.read_words(3502, 1)[0], 0)

    def test_clears_stale_read_complete_bit_while_idle(self) -> None:
        self.worker.driver.connect()
        self.worker.driver.write_read_complete(True)

        self.worker.poll()

        self.assertEqual(self.worker.driver.read_words(3502, 1)[0], 0)


if __name__ == "__main__":
    unittest.main()
