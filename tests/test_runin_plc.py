import tempfile
import unittest
from pathlib import Path

from drivers.runin_plc import RuninPlcDriver
from services.quality_rule_service import QualityRuleService
from services.traceability_service import TraceabilityService
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
            "result_start_offset": 1,
            "products_per_tray": 10,
            "words_per_product": 6,
            "handshake_address": 3502,
            "data_ready_bit": 0,
            "read_complete_bit": 1,
        },
    }


def sample_rows():
    return [
        [
            17000 + slot,
            200 + slot,
            40 + slot,
            100 + slot,
            0 if slot != 10 else 105,
            slot != 10,
        ]
        for slot in range(1, 11)
    ]


def configured_rules():
    return {
        "models": {
            "C68": {
                "sn_prefixes": ["C68"],
                "configured": True,
                "rule_version": "test-1",
                "ranges": {
                    "runin_speed_rpm": {"min": 32000, "max": 44000},
                    "runin_voltage_v": {"min": 19, "max": 22},
                    "runin_temperature_c": {"min": 30, "max": 60},
                    "runin_current_a": {"min": 90, "max": 120},
                },
                "allowed_error_codes": [0],
            }
        }
    }


class RuninPlcDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = RuninPlcDriver(runin_simulation_config())
        self.driver.connect()

    def tearDown(self) -> None:
        self.driver.disconnect()

    def test_reads_dm1001_to_1060_as_ten_interleaved_results(self) -> None:
        self.driver.set_simulated_result("7001", sample_rows())

        snapshot = self.driver.read_result_snapshot()

        self.assertEqual(snapshot["tray_id"], "7001")
        self.assertEqual(len(snapshot["items"]), 10)
        self.assertEqual(snapshot["items"][0]["runin_current_a"], 101)
        self.assertEqual(snapshot["items"][0]["runin_speed_rpm"], 34002)
        self.assertEqual(snapshot["items"][0]["runin_voltage_v"], 20.1)
        self.assertEqual(snapshot["items"][0]["runin_temperature_c"], 41)
        self.assertEqual(snapshot["items"][9]["runin_voltage_v"], 21.0)
        self.assertIsNone(snapshot["items"][9]["runin_passed"])
        self.assertEqual(snapshot["items"][9]["plc_passed_raw"], 0)
        self.assertEqual(snapshot["items"][9]["runin_error_code"], 105)
        self.assertEqual(snapshot["result_base_address"], 1001)
        self.assertEqual(snapshot["result_end_address"], 1060)
        self.assertEqual(snapshot["handshake_address"], 3502)

    def test_live_snapshot_reads_values_without_data_ready_handshake(self) -> None:
        self.driver.set_simulated_result("7001", sample_rows(), ready=False)

        snapshot = self.driver.read_live_snapshot()

        self.assertEqual(snapshot["tray_id"], "7001")
        self.assertFalse(snapshot["data_ready"])
        self.assertEqual(snapshot["items"][0]["runin_current_a"], 101)
        self.assertEqual(snapshot["items"][9]["runin_speed_rpm"], 34020)
        self.assertIsNone(snapshot["items"][0]["runin_passed"])
        self.assertEqual(snapshot["items"][0]["plc_passed_raw"], 1)

    def test_plc_passed_value_is_only_preserved_for_diagnostics(self) -> None:
        rows = sample_rows()
        rows[0][-1] = 20
        self.driver.set_simulated_result("7001", rows, ready=False)

        snapshot = self.driver.read_live_snapshot()

        self.assertIsNone(snapshot["items"][0]["runin_passed"])
        self.assertEqual(snapshot["items"][0]["plc_passed_raw"], 20)

    def test_writes_upper_computer_results_to_original_pass_addresses(self) -> None:
        self.driver.set_simulated_result("7001", sample_rows(), ready=True)
        items = self.driver.read_result_snapshot()["items"]
        for item in items:
            item["runin_passed"] = item["tray_slot"] != 10

        self.driver.write_pass_results(items)

        self.assertEqual(self.driver.read_words(1006, 1)[0], 1)
        self.assertEqual(self.driver.read_words(1012, 1)[0], 1)
        self.assertEqual(self.driver.read_words(1060, 1)[0], 0)

    def test_writes_read_complete_to_dm3502_bit_one(self) -> None:
        self.driver.write_read_complete(True)
        self.assertEqual(self.driver.read_words(3502, 1)[0], 0b10)
        self.driver.write_read_complete(False)
        self.assertEqual(self.driver.read_words(3502, 1)[0], 0)

    def test_raw_plc_order_is_saved_to_matching_database_fields(self) -> None:
        # 使用现场触摸屏同量级数据，确认 D1000 占位不会进入任何字段。
        rows = [[21696, 210, 34, 108, 0, 20] for _ in range(10)]
        self.driver.write_words(1000, [1])
        self.driver.set_simulated_result("7001", rows)
        snapshot = self.driver.read_result_snapshot()
        for slot, item in enumerate(snapshot["items"], start=1):
            item["product_sn"] = f"C68SN{slot:02d}"
        judged_items = QualityRuleService(configured_rules()).evaluate_items(
            snapshot["items"]
        )

        with tempfile.TemporaryDirectory() as directory:
            service = TraceabilityService(Path(directory) / "traceability.db")
            service.save_tray_batch(
                "7001", [f"C68SN{slot:02d}" for slot in range(1, 11)]
            )
            records = service.save_runin_tray_results(
                "7001", "RUNIN_01", judged_items
            )

        first = records[0]
        self.assertEqual(first["runin_speed_rpm"], 43392)
        self.assertEqual(first["runin_voltage_v"], 21.0)
        self.assertEqual(first["runin_temperature_c"], 34)
        self.assertEqual(first["runin_current_a"], 108)
        self.assertEqual(first["runin_error_code"], 0)
        self.assertTrue(first["runin_passed"])
        self.assertEqual(first["product_model"], "C68")

    def test_plc_field_order_can_be_overridden_by_mapping(self) -> None:
        config = runin_simulation_config()
        config["mapping"]["result_field_order"] = [
            "runin_voltage_v",
            "runin_speed_rpm",
            "runin_current_a",
            "runin_temperature_c",
            "runin_error_code",
            "runin_passed",
        ]
        driver = RuninPlcDriver(config)
        driver.connect()
        try:
            driver.set_simulated_result(
                "7001", [[20, 21384, 234, -41, 7, 1] for _ in range(10)]
            )
            item = driver.read_result_snapshot()["items"][0]
        finally:
            driver.disconnect()

        self.assertEqual(item["runin_speed_rpm"], 42768)
        self.assertEqual(item["runin_voltage_v"], 2.0)
        self.assertEqual(item["runin_temperature_c"], -41)
        self.assertEqual(item["runin_current_a"], 234)


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

    def test_worker_writes_judgement_before_database_acknowledgement(self) -> None:
        received = []
        written = []
        self.worker.result_ready.connect(
            lambda device_id, data: received.append((device_id, data))
        )
        self.worker.judgement_written.connect(
            lambda device_id, data: written.append((device_id, data))
        )
        self.worker.driver.connect()
        self.worker.driver.set_simulated_result("7001", sample_rows())
        self.worker.poll()
        judged_snapshot = received[0][1]
        for item in judged_snapshot["items"]:
            item["runin_passed"] = item["tray_slot"] != 10

        self.worker.write_judgement("RUNIN_01", judged_snapshot)

        self.assertEqual(len(written), 1)
        self.assertEqual(self.worker.driver.read_words(1006, 1)[0], 1)
        self.assertEqual(self.worker.driver.read_words(1060, 1)[0], 0)
        self.assertEqual(self.worker.driver.read_words(1005, 1)[0], 0)
        self.assertEqual(self.worker.driver.read_words(1007, 1)[0], 17002)

    def test_clears_stale_read_complete_bit_while_idle(self) -> None:
        self.worker.driver.connect()
        self.worker.driver.write_read_complete(True)

        self.worker.poll()

        self.assertEqual(self.worker.driver.read_words(3502, 1)[0], 0)

    def test_emits_live_snapshot_before_handshake_is_ready(self) -> None:
        received = []
        logs = []
        self.worker.live_snapshot.connect(
            lambda device_id, data: received.append((device_id, data))
        )
        self.worker.log.connect(logs.append)
        self.worker.driver.connect()
        self.worker.driver.set_simulated_result("7001", sample_rows(), ready=False)

        self.worker.poll()

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0], "RUNIN_01")
        self.assertFalse(received[0][1]["data_ready"])
        self.assertEqual(
            received[0][1]["items"][0]["runin_voltage_v"], 20.1
        )
        self.assertTrue(any("D3502.00=0" in message for message in logs))

    def test_poll_failure_is_written_to_runtime_log(self) -> None:
        logs = []
        self.worker.log.connect(logs.append)
        self.worker.driver.connect()

        def fail_read():
            raise TimeoutError("timed out")

        self.worker.driver.read_live_snapshot = fail_read
        self.worker.poll()

        self.assertTrue(
            any(
                "跑合设备 1 读取失败：timed out" in message
                for message in logs
            )
        )


if __name__ == "__main__":
    unittest.main()
