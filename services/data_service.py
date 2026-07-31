"""测试数据本地保存服务。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class DataService:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_record(self, record: Dict[str, Any]) -> Path:
        record_id = str(record.get("record_id") or datetime.now().strftime("%Y%m%d_%H%M%S"))
        path = self.data_dir / f"{record_id}.json"
        path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path
