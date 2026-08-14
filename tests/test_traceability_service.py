import sqlite3
import tempfile
import unittest
from pathlib import Path

from services.traceability_service import TraceabilityService


class TraceabilityServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.service = TraceabilityService(
            Path(self.temporary_directory.name) / "traceability.db"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_save_and_resolve_ten_tray_products(self) -> None:
        serial_numbers = [f"C66HNI042{index:03d}" for index in range(665, 675)]
        batch = self.service.save_tray_batch("7001", serial_numbers)

        self.assertEqual(len(batch["items"]), 10)
        self.assertEqual(
            self.service.resolve_product("7001", 6)["product_sn"],
            "C66HNI042670",
        )
        self.assertEqual(len(self.service.pending_peer_batches()), 1)
        self.assertEqual(
            self.service.pending_uploads()[0]["entity_type"], "tray_mapping"
        )

    def test_same_mapping_is_idempotent(self) -> None:
        serial_numbers = [f"SN{index:02d}" for index in range(1, 11)]
        first = self.service.save_tray_batch("7001", serial_numbers)
        second = self.service.save_tray_batch("7001", serial_numbers)

        self.assertEqual(first["tray_cycle_id"], second["tray_cycle_id"])

    def test_existing_database_is_upgraded_with_error_code_column(self) -> None:
        legacy_path = Path(self.temporary_directory.name) / "legacy.db"
        with sqlite3.connect(str(legacy_path)) as connection:
            connection.execute(
                """
                CREATE TABLE runin_results (
                    record_id TEXT PRIMARY KEY,
                    runin_result_code TEXT
                )
                """
            )

        TraceabilityService(legacy_path)

        with sqlite3.connect(str(legacy_path)) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(runin_results)"
                )
            }
        self.assertIn("runin_error_code", columns)

    def test_runin_result_uses_product_sn_from_mapping(self) -> None:
        serial_numbers = [f"SN{index:02d}" for index in range(1, 11)]
        self.service.save_tray_batch("7001", serial_numbers)

        record = self.service.save_runin_result(
            "7001",
            3,
            "RUNIN_01",
            {
                "runin_voltage_v": 24.1,
                "runin_current_a": 0.11,
                "runin_speed_rpm": 17888,
                "runin_temperature_c": 43.9,
                "runin_passed": True,
                "runin_result_code": "OK",
                "runin_error_code": 0,
            },
        )

        self.assertEqual(record["product_sn"], "SN03")
        self.assertEqual(record["tray_slot"], 3)
        self.assertTrue(record["runin_passed"])
        entity_types = {
            item["entity_type"] for item in self.service.pending_uploads()
        }
        self.assertEqual(entity_types, {"tray_mapping", "runin_result"})

    def test_save_runin_tray_results_saves_ten_products_atomically(self) -> None:
        serial_numbers = [f"SN{index:02d}" for index in range(1, 11)]
        self.service.save_tray_batch("7001", serial_numbers)
        results = [
            {
                "tray_slot": slot,
                "runin_current_a": 10 + slot,
                "runin_voltage_v": 20 + slot,
                "runin_speed_rpm": 17000 + slot,
                "runin_temperature_c": 40 + slot,
                "runin_passed": slot != 5,
                "runin_result_code": 0 if slot != 5 else 1,
                "runin_error_code": 0 if slot != 5 else 105,
            }
            for slot in range(1, 11)
        ]

        records = self.service.save_runin_tray_results(
            "7001", "RUNIN_01", results
        )

        self.assertEqual(len(records), 10)
        self.assertEqual(records[0]["product_sn"], "SN01")
        self.assertEqual(records[-1]["product_sn"], "SN10")
        self.assertFalse(records[4]["runin_passed"])
        self.assertEqual(records[4]["runin_error_code"], 105)
        runin_uploads = [
            item
            for item in self.service.pending_uploads(limit=20)
            if item["entity_type"] == "runin_result"
        ]
        self.assertEqual(len(runin_uploads), 10)


if __name__ == "__main__":
    unittest.main()
