"""托盘、产品及测试结果的本地追溯存储。"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


class ProductMappingNotFoundError(LookupError):
    """PLC 托盘号和坑位号无法解析到产品 SN。"""


def local_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class TraceabilityService:
    """使用 SQLite 保存产线本地数据，网络中断时仍可继续生产。"""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path), timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tray_cycles (
                    tray_cycle_id TEXT PRIMARY KEY,
                    tray_id TEXT NOT NULL,
                    loaded_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    peer_sync_status TEXT NOT NULL DEFAULT 'pending',
                    peer_synced_at TEXT,
                    last_sync_error TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_tray_cycles_active
                ON tray_cycles(tray_id, status, loaded_at);

                CREATE TABLE IF NOT EXISTS tray_products (
                    tray_cycle_id TEXT NOT NULL,
                    tray_id TEXT NOT NULL,
                    tray_slot INTEGER NOT NULL CHECK(tray_slot BETWEEN 1 AND 10),
                    product_sn TEXT NOT NULL,
                    scanned_at TEXT NOT NULL,
                    PRIMARY KEY (tray_cycle_id, tray_slot),
                    UNIQUE (tray_cycle_id, product_sn),
                    FOREIGN KEY (tray_cycle_id)
                        REFERENCES tray_cycles(tray_cycle_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tray_products_lookup
                ON tray_products(tray_id, tray_slot, scanned_at);

                CREATE TABLE IF NOT EXISTS runin_results (
                    record_id TEXT PRIMARY KEY,
                    tray_cycle_id TEXT NOT NULL,
                    tray_id TEXT NOT NULL,
                    tray_slot INTEGER NOT NULL CHECK(tray_slot BETWEEN 1 AND 10),
                    product_sn TEXT NOT NULL,
                    station_code TEXT NOT NULL,
                    product_model TEXT,
                    quality_rule_version TEXT,
                    judgement_source TEXT,
                    runin_speed_rpm INTEGER,
                    runin_voltage_v REAL,
                    runin_temperature_c REAL,
                    runin_current_a REAL,
                    runin_error_code INTEGER,
                    runin_passed INTEGER,
                    runin_result_code TEXT,
                    quality_failures_json TEXT,
                    runin_tested_at TEXT NOT NULL,
                    upload_status TEXT NOT NULL DEFAULT 'pending',
                    server_received_at TEXT,
                    UNIQUE (tray_cycle_id, tray_slot),
                    FOREIGN KEY (tray_cycle_id)
                        REFERENCES tray_cycles(tray_cycle_id)
                );

                CREATE TABLE IF NOT EXISTS upload_outbox (
                    outbox_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    next_retry_at TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    uploaded_at TEXT,
                    UNIQUE (entity_type, entity_id)
                );
                """
            )
            self._ensure_column(
                connection,
                "runin_results",
                "runin_error_code",
                "INTEGER",
            )
            for column_name in (
                "product_model",
                "quality_rule_version",
                "judgement_source",
                "quality_failures_json",
            ):
                self._ensure_column(
                    connection, "runin_results", column_name, "TEXT"
                )
            self._ensure_runin_results_column_order(connection)

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> None:
        """为已有生产数据库补充新列，不要求删除或重建数据库。"""
        columns = {
            str(row["name"])
            for row in connection.execute(
                f"PRAGMA table_info({table_name})"
            ).fetchall()
        }
        if column_name not in columns:
            connection.execute(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} {column_type}"
            )

    @staticmethod
    def _ensure_runin_results_column_order(
        connection: sqlite3.Connection,
    ) -> None:
        """将已有数据库的跑合字段迁移为PLC数据顺序，按列名保留数据。"""
        desired_columns = [
            "record_id",
            "tray_cycle_id",
            "tray_id",
            "tray_slot",
            "product_sn",
            "station_code",
            "product_model",
            "quality_rule_version",
            "judgement_source",
            "runin_speed_rpm",
            "runin_voltage_v",
            "runin_temperature_c",
            "runin_current_a",
            "runin_error_code",
            "runin_passed",
            "runin_result_code",
            "quality_failures_json",
            "runin_tested_at",
            "upload_status",
            "server_received_at",
        ]
        existing_columns = [
            str(row["name"])
            for row in connection.execute(
                "PRAGMA table_info(runin_results)"
            ).fetchall()
        ]
        if existing_columns == desired_columns:
            return
        if not set(desired_columns).issubset(existing_columns):
            return

        column_list = ", ".join(desired_columns)
        connection.executescript(
            f"""
            CREATE TABLE runin_results_reordered (
                record_id TEXT PRIMARY KEY,
                tray_cycle_id TEXT NOT NULL,
                tray_id TEXT NOT NULL,
                tray_slot INTEGER NOT NULL CHECK(tray_slot BETWEEN 1 AND 10),
                product_sn TEXT NOT NULL,
                station_code TEXT NOT NULL,
                product_model TEXT,
                quality_rule_version TEXT,
                judgement_source TEXT,
                runin_speed_rpm INTEGER,
                runin_voltage_v REAL,
                runin_temperature_c REAL,
                runin_current_a REAL,
                runin_error_code INTEGER,
                runin_passed INTEGER,
                runin_result_code TEXT,
                quality_failures_json TEXT,
                runin_tested_at TEXT NOT NULL,
                upload_status TEXT NOT NULL DEFAULT 'pending',
                server_received_at TEXT,
                UNIQUE (tray_cycle_id, tray_slot),
                FOREIGN KEY (tray_cycle_id)
                    REFERENCES tray_cycles(tray_cycle_id)
                    ON DELETE CASCADE
            );
            INSERT INTO runin_results_reordered ({column_list})
            SELECT {column_list} FROM runin_results;
            DROP TABLE runin_results;
            ALTER TABLE runin_results_reordered RENAME TO runin_results;
            """
        )

    def save_tray_batch(
        self,
        tray_id: str,
        serial_numbers: Sequence[str],
    ) -> Dict[str, Any]:
        tray_id = str(tray_id or "").strip()
        serial_numbers = [str(item or "").strip() for item in serial_numbers]
        if not tray_id:
            raise ValueError("托盘编号不能为空")
        if len(serial_numbers) != 10 or any(not item for item in serial_numbers):
            raise ValueError("每个托盘必须保存 10 个有效产品 SN")
        if len(set(serial_numbers)) != len(serial_numbers):
            raise ValueError("同一托盘内不能存在重复产品 SN")

        loaded_at = local_timestamp()
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT tray_cycle_id
                FROM tray_cycles
                WHERE tray_id = ? AND status = 'active'
                ORDER BY loaded_at DESC
                LIMIT 1
                """,
                (tray_id,),
            ).fetchone()
            if existing is not None:
                existing_items = connection.execute(
                    """
                    SELECT product_sn
                    FROM tray_products
                    WHERE tray_cycle_id = ?
                    ORDER BY tray_slot
                    """,
                    (existing["tray_cycle_id"],),
                ).fetchall()
                if [row["product_sn"] for row in existing_items] == serial_numbers:
                    return self.get_tray_batch(existing["tray_cycle_id"])
                connection.execute(
                    "UPDATE tray_cycles SET status = 'superseded' WHERE tray_cycle_id = ?",
                    (existing["tray_cycle_id"],),
                )

            tray_cycle_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO tray_cycles(
                    tray_cycle_id, tray_id, loaded_at, status, peer_sync_status
                ) VALUES (?, ?, ?, 'active', 'pending')
                """,
                (tray_cycle_id, tray_id, loaded_at),
            )
            connection.executemany(
                """
                INSERT INTO tray_products(
                    tray_cycle_id, tray_id, tray_slot, product_sn, scanned_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (tray_cycle_id, tray_id, slot, product_sn, loaded_at)
                    for slot, product_sn in enumerate(serial_numbers, start=1)
                ],
            )
            mapping_payload = {
                "schema_version": "1.0",
                "tray_cycle_id": tray_cycle_id,
                "tray_id": tray_id,
                "loaded_at": loaded_at,
                "status": "active",
                "items": [
                    {
                        "tray_slot": slot,
                        "product_sn": product_sn,
                        "scanned_at": loaded_at,
                    }
                    for slot, product_sn in enumerate(serial_numbers, start=1)
                ],
            }
            connection.execute(
                """
                INSERT INTO upload_outbox(
                    outbox_id, entity_type, entity_id, payload_json, created_at
                ) VALUES (?, 'tray_mapping', ?, ?, ?)
                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    status = 'pending',
                    last_error = NULL
                """,
                (
                    str(uuid.uuid4()), tray_cycle_id,
                    json.dumps(mapping_payload, ensure_ascii=False), loaded_at,
                ),
            )
        return self.get_tray_batch(tray_cycle_id)

    def get_tray_batch(self, tray_cycle_id: str) -> Dict[str, Any]:
        with self._connect() as connection:
            cycle = connection.execute(
                "SELECT * FROM tray_cycles WHERE tray_cycle_id = ?",
                (tray_cycle_id,),
            ).fetchone()
            if cycle is None:
                raise LookupError(f"找不到托盘批次：{tray_cycle_id}")
            items = connection.execute(
                """
                SELECT tray_slot, product_sn, scanned_at
                FROM tray_products
                WHERE tray_cycle_id = ?
                ORDER BY tray_slot
                """,
                (tray_cycle_id,),
            ).fetchall()
        return {
            "schema_version": "1.0",
            "tray_cycle_id": cycle["tray_cycle_id"],
            "tray_id": cycle["tray_id"],
            "loaded_at": cycle["loaded_at"],
            "status": cycle["status"],
            "items": [dict(row) for row in items],
        }

    def pending_peer_batches(self) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT tray_cycle_id
                FROM tray_cycles
                WHERE peer_sync_status != 'synced' AND status = 'active'
                ORDER BY loaded_at
                """
            ).fetchall()
        return [self.get_tray_batch(row["tray_cycle_id"]) for row in rows]

    def mark_peer_synced(self, tray_cycle_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE tray_cycles
                SET peer_sync_status = 'synced',
                    peer_synced_at = ?,
                    last_sync_error = NULL
                WHERE tray_cycle_id = ?
                """,
                (local_timestamp(), tray_cycle_id),
            )

    def mark_peer_sync_failed(self, tray_cycle_id: str, message: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE tray_cycles
                SET peer_sync_status = 'pending', last_sync_error = ?
                WHERE tray_cycle_id = ?
                """,
                (str(message), tray_cycle_id),
            )

    def pending_uploads(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM upload_outbox
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["payload"] = json.loads(record.pop("payload_json"))
            records.append(record)
        return records

    def mark_upload_succeeded(
        self,
        outbox_id: str,
        server_received_at: Optional[str] = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE upload_outbox
                SET status = 'uploaded', uploaded_at = ?, last_error = NULL
                WHERE outbox_id = ?
                """,
                (server_received_at or local_timestamp(), str(outbox_id)),
            )

    def mark_upload_failed(self, outbox_id: str, message: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE upload_outbox
                SET status = 'pending', retry_count = retry_count + 1,
                    last_error = ?
                WHERE outbox_id = ?
                """,
                (str(message), str(outbox_id)),
            )

    def resolve_product(self, tray_id: str, tray_slot: int) -> Dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT p.tray_cycle_id, p.tray_id, p.tray_slot, p.product_sn,
                       p.scanned_at
                FROM tray_products AS p
                JOIN tray_cycles AS c ON c.tray_cycle_id = p.tray_cycle_id
                WHERE p.tray_id = ? AND p.tray_slot = ? AND c.status = 'active'
                ORDER BY c.loaded_at DESC
                LIMIT 1
                """,
                (str(tray_id).strip(), int(tray_slot)),
            ).fetchone()
        if row is None:
            raise ProductMappingNotFoundError(
                f"找不到托盘 {tray_id} 坑位 {tray_slot} 对应的产品 SN"
            )
        return dict(row)

    def save_runin_result(
        self,
        tray_id: str,
        tray_slot: int,
        station_code: str,
        measurements: Dict[str, Any],
        tested_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        product = self.resolve_product(tray_id, tray_slot)
        record = self._build_runin_record(
            product,
            station_code,
            measurements,
            tested_at or local_timestamp(),
        )
        with self._connect() as connection:
            self._upsert_runin_record(connection, record)
        return record

    def save_runin_tray_results(
        self,
        tray_id: str,
        station_code: str,
        measurements: Sequence[Dict[str, Any]],
        tested_at: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """在一个事务内保存当前卸载托盘的10条跑合结果。"""
        tray_id = str(tray_id or "").strip()
        items = [dict(item) for item in measurements]
        slots = sorted(int(item.get("tray_slot", 0)) for item in items)
        if not tray_id:
            raise ValueError("跑合结果托盘号不能为空")
        if slots != list(range(1, 11)):
            raise ValueError("跑合结果必须完整包含坑位 1～10")
        unjudged_slots = [
            str(item.get("tray_slot"))
            for item in items
            if not isinstance(item.get("runin_passed"), bool)
            or item.get("judgement_source") != "upper_computer"
        ]
        if unjudged_slots:
            raise ValueError(
                "以下坑位缺少上位机合格判定：" + "、".join(unjudged_slots)
            )
        tested_at = tested_at or local_timestamp()

        with self._connect() as connection:
            products = connection.execute(
                """
                SELECT p.tray_cycle_id, p.tray_id, p.tray_slot, p.product_sn,
                       p.scanned_at
                FROM tray_products AS p
                JOIN tray_cycles AS c ON c.tray_cycle_id = p.tray_cycle_id
                WHERE p.tray_id = ? AND c.status = 'active'
                ORDER BY p.tray_slot
                """,
                (tray_id,),
            ).fetchall()
            if len(products) != 10:
                raise ProductMappingNotFoundError(
                    f"找不到托盘 {tray_id} 完整的 10 个坑位与产品 SN 映射"
                )
            measurements_by_slot = {
                int(item["tray_slot"]): item for item in items
            }
            records = [
                self._build_runin_record(
                    dict(product),
                    station_code,
                    measurements_by_slot[int(product["tray_slot"])],
                    tested_at,
                )
                for product in products
            ]
            for record in records:
                self._upsert_runin_record(connection, record)
        return records

    @staticmethod
    def _build_runin_record(
        product: Dict[str, Any],
        station_code: str,
        measurements: Dict[str, Any],
        tested_at: str,
    ) -> Dict[str, Any]:
        record_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"runin:{product['tray_cycle_id']}:{product['tray_slot']}",
            )
        )
        return {
            "record_id": record_id,
            "tray_cycle_id": product["tray_cycle_id"],
            "tray_id": product["tray_id"],
            "tray_slot": product["tray_slot"],
            "product_sn": product["product_sn"],
            "station_code": str(station_code),
            "product_model": measurements.get("product_model"),
            "quality_rule_version": measurements.get("quality_rule_version"),
            "judgement_source": measurements.get("judgement_source"),
            "runin_speed_rpm": measurements.get("runin_speed_rpm"),
            "runin_voltage_v": measurements.get("runin_voltage_v"),
            "runin_temperature_c": measurements.get("runin_temperature_c"),
            "runin_current_a": measurements.get("runin_current_a"),
            "runin_error_code": measurements.get("runin_error_code"),
            "runin_passed": measurements.get("runin_passed"),
            "runin_result_code": measurements.get("runin_result_code"),
            "quality_failures": list(
                measurements.get("quality_failures") or []
            ),
            "runin_tested_at": tested_at,
        }

    @staticmethod
    def _upsert_runin_record(
        connection: sqlite3.Connection, record: Dict[str, Any]
    ) -> None:
        connection.execute(
            """
            INSERT INTO runin_results(
                record_id, tray_cycle_id, tray_id, tray_slot, product_sn,
                station_code, product_model, quality_rule_version,
                judgement_source, runin_speed_rpm, runin_voltage_v,
                runin_temperature_c, runin_current_a, runin_error_code,
                runin_passed, runin_result_code, quality_failures_json,
                runin_tested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tray_cycle_id, tray_slot) DO UPDATE SET
                record_id = excluded.record_id,
                station_code = excluded.station_code,
                product_model = excluded.product_model,
                quality_rule_version = excluded.quality_rule_version,
                judgement_source = excluded.judgement_source,
                runin_speed_rpm = excluded.runin_speed_rpm,
                runin_voltage_v = excluded.runin_voltage_v,
                runin_temperature_c = excluded.runin_temperature_c,
                runin_current_a = excluded.runin_current_a,
                runin_error_code = excluded.runin_error_code,
                runin_passed = excluded.runin_passed,
                runin_result_code = excluded.runin_result_code,
                quality_failures_json = excluded.quality_failures_json,
                runin_tested_at = excluded.runin_tested_at,
                upload_status = 'pending',
                server_received_at = NULL
            """,
            (
                record["record_id"], record["tray_cycle_id"],
                record["tray_id"], record["tray_slot"],
                record["product_sn"], record["station_code"],
                record["product_model"], record["quality_rule_version"],
                record["judgement_source"],
                record["runin_speed_rpm"], record["runin_voltage_v"],
                record["runin_temperature_c"], record["runin_current_a"],
                record["runin_error_code"],
                None
                if record["runin_passed"] is None
                else int(bool(record["runin_passed"])),
                record["runin_result_code"],
                json.dumps(record["quality_failures"], ensure_ascii=False),
                record["runin_tested_at"],
            ),
        )
        connection.execute(
            """
            INSERT INTO upload_outbox(
                outbox_id, entity_type, entity_id, payload_json, created_at
            ) VALUES (?, 'runin_result', ?, ?, ?)
            ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                payload_json = excluded.payload_json,
                status = 'pending',
                last_error = NULL
            """,
            (
                str(uuid.uuid4()), record["record_id"],
                json.dumps(record, ensure_ascii=False), local_timestamp(),
            ),
        )
