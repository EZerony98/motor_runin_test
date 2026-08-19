"""按托盘实际逆时针坑位显示一盘跑合临时结果。"""

from typing import Any, Dict, Iterable, List

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from .tray_entry_widget import TrayEntryWidget


class RuninResultWidget(QWidget):
    """两排五工位结果视图，按PLC顺序显示每个坑位的跑合数据。"""

    MOTOR_COUNT = 10
    OUTER_MARGIN = 24
    COLUMN_GAP = 12

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setObjectName("runinResultWidget")
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.sn_labels: List[QLabel] = []
        self.value_labels: List[QLabel] = []
        for slot in range(1, self.MOTOR_COUNT + 1):
            sn_label = QLabel(f"SN {slot}: --", self)
            sn_label.setObjectName(f"runinSnLabel{slot}")
            sn_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sn_label.setProperty("runinSn", True)
            self.sn_labels.append(sn_label)

            value_label = QLabel("n --  U --\nT --  I --  E --  --", self)
            value_label.setObjectName(f"runinValueLabel{slot}")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setProperty("runinValue", True)
            self.value_labels.append(value_label)

        self.clear_results()

    def sizeHint(self) -> QSize:
        return QSize(1100, 360)

    def resizeEvent(self, event: object) -> None:
        self._layout_labels()
        super().resizeEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tray_rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        painter.setPen(QPen(QColor("#b8c3cf"), 2))
        painter.setBrush(QColor("#eef1f4"))
        painter.drawRoundedRect(tray_rect, 14, 14)
        self._draw_mounting_holes(painter, tray_rect)
        for slot in range(1, self.MOTOR_COUNT + 1):
            row, column = TrayEntryWidget.slot_position(slot)
            self._draw_motor(painter, slot, row, column)

    def clear_results(self) -> None:
        for slot, (sn_label, value_label) in enumerate(
            zip(self.sn_labels, self.value_labels), start=1
        ):
            sn_label.setText(f"SN {slot}: --")
            value_label.setText("n --  U --\nT --  I --  E --  --")
            value_label.setToolTip("")
            value_label.setProperty("passed", "unknown")
            value_label.style().unpolish(value_label)
            value_label.style().polish(value_label)

    def set_results(self, items: Iterable[Dict[str, Any]]) -> None:
        self.clear_results()
        for item in items:
            slot = int(item.get("tray_slot", 0))
            if not 1 <= slot <= self.MOTOR_COUNT:
                continue
            index = slot - 1
            product_sn = str(item.get("product_sn") or "未匹配")
            current = self._display(item.get("runin_current_a"))
            voltage = self._display(item.get("runin_voltage_v"))
            speed = self._display(item.get("runin_speed_rpm"))
            temperature = self._display(item.get("runin_temperature_c"))
            error_code = self._display(item.get("runin_error_code"))
            passed_value = item.get("runin_passed")
            passed_raw = item.get("runin_passed_raw")
            quality_error = str(item.get("quality_error") or "").strip()
            quality_failures = [
                str(value) for value in item.get("quality_failures", [])
            ]
            if passed_value is None:
                if quality_error:
                    result_text = "未判定"
                    passed_property = "ng"
                elif passed_raw is None:
                    result_text = "--"
                    passed_property = "unknown"
                else:
                    result_text = f"异常({self._display(passed_raw)})"
                    passed_property = "ng"
            else:
                result_text = "OK" if bool(passed_value) else "NG"
                passed_property = "ok" if bool(passed_value) else "ng"
            self.sn_labels[index].setText(f"SN {slot}: {product_sn}")
            self.value_labels[index].setText(
                f"n {speed}  U {voltage}\n"
                f"T {temperature}  I {current}  E {error_code}  {result_text}"
            )
            self.value_labels[index].setProperty("passed", passed_property)
            tooltip_lines = []
            if item.get("product_model"):
                tooltip_lines.append(
                    f"型号：{item.get('product_model')}，规则："
                    f"{item.get('quality_rule_version') or '--'}"
                )
            if quality_error:
                tooltip_lines.append(quality_error)
            tooltip_lines.extend(quality_failures)
            self.value_labels[index].setToolTip("\n".join(tooltip_lines))
            self.value_labels[index].style().unpolish(self.value_labels[index])
            self.value_labels[index].style().polish(self.value_labels[index])

    def _layout_labels(self) -> None:
        column_width = self._column_width()
        row_band = (self.height() - 24) / 2
        label_width = max(150, min(215, int(column_width - 8)))
        for slot in range(1, self.MOTOR_COUNT + 1):
            row, column = TrayEntryWidget.slot_position(slot)
            center_x = self._column_center(column)
            band_top = 12 + row * row_band
            self.sn_labels[slot - 1].setGeometry(
                int(center_x - label_width / 2),
                int(band_top + row_band - 67),
                label_width,
                25,
            )
            self.value_labels[slot - 1].setGeometry(
                int(center_x - label_width / 2),
                int(band_top + row_band - 40),
                label_width,
                36,
            )

    def _draw_motor(
        self, painter: QPainter, slot: int, row: int, column: int
    ) -> None:
        row_band = (self.height() - 24) / 2
        band_top = 12 + row * row_band
        label_top = band_top + row_band - 67
        center_x = self._column_center(column)
        center_y = band_top + (label_top - band_top) * 0.48
        housing_width = min(96.0, self._column_width() * 0.54)
        housing_height = min(68.0, max(54.0, row_band - 86))
        housing = QRectF(
            center_x - housing_width / 2,
            center_y - housing_height / 2,
            housing_width,
            housing_height,
        )
        painter.setPen(QPen(QColor("#4b5563"), 2))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(housing, 7, 7)
        motor_radius = min(housing_height * 0.34, housing_width * 0.27)
        painter.setBrush(QColor("#e8edf2"))
        painter.drawEllipse(
            QRectF(
                center_x - motor_radius,
                center_y - motor_radius,
                motor_radius * 2,
                motor_radius * 2,
            )
        )
        painter.setPen(QPen(QColor("#657384"), 1.3))
        painter.setBrush(QColor("#cbd3dc"))
        for x in (housing.left() + 8, housing.right() - 8):
            for y in (housing.top() + 8, housing.bottom() - 8):
                painter.drawEllipse(QRectF(x - 3, y - 3, 6, 6))
        badge = QRectF(housing.left() + 6, housing.top() + 5, 27, 19)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d41432"))
        painter.drawRoundedRect(badge, 9.5, 9.5)
        painter.setPen(QColor("#ffffff"))
        badge_font = painter.font()
        badge_font.setBold(True)
        badge_font.setPointSize(8)
        painter.setFont(badge_font)
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, f"{slot:02d}")

    def _draw_mounting_holes(self, painter: QPainter, tray_rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#8795a5"), 1.5))
        painter.setBrush(QColor("#f8fafc"))
        radius = 5.5
        for x, y in (
            (tray_rect.left() + 14, tray_rect.top() + 14),
            (tray_rect.right() - 14, tray_rect.top() + 14),
            (tray_rect.left() + 14, tray_rect.bottom() - 14),
            (tray_rect.right() - 14, tray_rect.bottom() - 14),
        ):
            painter.drawEllipse(QRectF(x - radius, y - radius, radius * 2, radius * 2))

    def _column_width(self) -> float:
        available = self.width() - self.OUTER_MARGIN * 2 - self.COLUMN_GAP * 4
        return max(130.0, available / 5)

    def _column_center(self, column: int) -> float:
        width = self._column_width()
        return self.OUTER_MARGIN + width / 2 + column * (width + self.COLUMN_GAP)

    @staticmethod
    def _display(value: Any) -> str:
        return "--" if value is None else str(value)
