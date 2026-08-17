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

    def test_runin_result_columns_follow_plc_field_order(self) -> None:
        with self.service._connect() as connection:
            columns = [
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(runin_results)"
                )
            ]

        first_measurement = columns.index("runin_speed_rpm")
        self.assertEqual(
            columns[first_measurement : first_measurement + 6],
            [
                "runin_speed_rpm",
                "runin_voltage_v",
                "runin_temperature_c",
                "runin_current_a",
                "runin_error_code",
                "runin_passed",
            ],
        )

    def test_existing_runin_rows_survive_column_order_migration(self) -> None:
        legacy_path = Path(self.temporary_directory.name) / "old-order.db"
        with sqlite3.connect(str(legacy_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE tray_cycles (
                    tray_cycle_id TEXT PRIMARY KEY,
                    tray_id TEXT NOT NULL,
                    loaded_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    peer_sync_status TEXT NOT NULL DEFAULT 'pending',
                    peer_synced_at TEXT,
                    last_sync_error TEXT
                );
                INSERT INTO tray_cycles(
                    tray_cycle_id, tray_id, loaded_at
                ) VALUES ('cycle-1', '7001', '2026-08-17T10:00:00+08:00');
                CREATE TABLE runin_results (
                    record_id TEXT PRIMARY KEY,
                    tray_cycle_id TEXT NOT NULL,
                    tray_id TEXT NOT NULL,
                    tray_slot INTEGER NOT NULL,
                    product_sn TEXT NOT NULL,
                    station_code TEXT NOT NULL,
                    runin_voltage_v REAL,
                    runin_current_a REAL,
                    runin_speed_rpm INTEGER,
                    runin_temperature_c REAL,
                    runin_passed INTEGER,
                    runin_result_code TEXT,
                    runin_error_code INTEGER,
                    runin_tested_at TEXT NOT NULL,
                    upload_status TEXT NOT NULL DEFAULT 'pending',
                    server_received_at TEXT
                );
                INSERT INTO runin_results VALUES (
                    'record-1', 'cycle-1', '7001', 1, 'SN01', 'RUNIN_01',
                    20, 234, 21384, -41, 1, '0', 7,
                    '2026-08-17T10:30:00+08:00', 'pending', NULL
                );
                """
            )

        migrated = TraceabilityService(legacy_path)
        with migrated._connect() as connection:
            row = connection.execute(
                "SELECT * FROM runin_results WHERE record_id = 'record-1'"
            ).fetchone()
            columns = [
                item["name"]
                for item in connection.execute(
                    "PRAGMA table_info(runin_results)"
                )
            ]

        self.assertEqual(row["runin_speed_rpm"], 21384)
        self.assertEqual(row["runin_voltage_v"], 20)
        self.assertEqual(row["runin_temperature_c"], -41)
        self.assertEqual(row["runin_current_a"], 234)
        self.assertEqual(row["runin_error_code"], 7)
        self.assertEqual(row["runin_passed"], 1)
        self.assertLess(
            columns.index("runin_speed_rpm"),
            columns.index("runin_voltage_v"),
        )

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
