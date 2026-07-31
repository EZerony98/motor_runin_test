"""产品信息模型。"""

from dataclasses import dataclass


@dataclass
class Product:
    model: str
    serial_number: str
    operator: str = ""
