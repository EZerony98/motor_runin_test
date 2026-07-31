"""托盘及其 10 个电机的上料数据。"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class TrayBatch:
    tray_id: str
    serial_numbers: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
