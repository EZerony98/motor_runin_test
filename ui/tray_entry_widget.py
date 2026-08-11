"""与实物托盘位置一致的十工位 SN 录入组件。"""

from typing import List

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QLineEdit, QSizePolicy, QWidget


class TrayEntryWidget(QWidget):
    """绘制两排五工位托盘，并将 SN 输入框放在对应电机下方。"""

    MOTOR_COUNT = 10
    OUTER_MARGIN = 24
    COLUMN_GAP = 12
    INPUT_HEIGHT = 38

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setObjectName("trayEntryWidget")
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.serial_inputs: List[QLineEdit] = []
        for position in range(1, self.MOTOR_COUNT + 1):
            serial_input = QLineEdit(self)
            serial_input.setObjectName(f"snInput{position}")
            serial_input.setMaxLength(99)
            serial_input.setPlaceholderText(f"扫描 SN {position}")
            serial_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            serial_input.setProperty("traySnInput", True)
            self.serial_inputs.append(serial_input)

        for current, following in zip(
            self.serial_inputs, self.serial_inputs[1:]
        ):
            QWidget.setTabOrder(current, following)

    def sizeHint(self) -> QSize:
        return QSize(1100, 350)

    def resizeEvent(self, event: object) -> None:
        self._layout_inputs()
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
            row, column = self.slot_position(slot)
            self._draw_motor(painter, slot, row, column)

    def _layout_inputs(self) -> None:
        column_width = self._column_width()
        row_band = (self.height() - 24) / 2
        input_width = max(120, min(190, int(column_width - 10)))

        for slot, serial_input in enumerate(self.serial_inputs, start=1):
            row, column = self.slot_position(slot)
            center_x = self._column_center(column)
            band_top = 12 + row * row_band
            input_y = int(band_top + row_band - self.INPUT_HEIGHT - 8)
            serial_input.setGeometry(
                int(center_x - input_width / 2),
                input_y,
                input_width,
                self.INPUT_HEIGHT,
            )

    def _draw_motor(
        self, painter: QPainter, slot: int, row: int, column: int
    ) -> None:
        row_band = (self.height() - 24) / 2
        band_top = 12 + row * row_band
        input_top = band_top + row_band - self.INPUT_HEIGHT - 8
        center_x = self._column_center(column)
        center_y = band_top + (input_top - band_top) * 0.48

        housing_width = min(108.0, self._column_width() * 0.60)
        housing_height = min(78.0, max(60.0, row_band - 70))
        housing = QRectF(
            center_x - housing_width / 2,
            center_y - housing_height / 2,
            housing_width,
            housing_height,
        )

        painter.setPen(QPen(QColor("#4b5563"), 2))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(housing, 7, 7)

        motor_radius = min(housing_height * 0.34, housing_width * 0.28)
        painter.setBrush(QColor("#e8edf2"))
        painter.drawEllipse(
            QRectF(
                center_x - motor_radius,
                center_y - motor_radius,
                motor_radius * 2,
                motor_radius * 2,
            )
        )

        painter.setPen(QPen(QColor("#657384"), 1.4))
        painter.setBrush(QColor("#cbd3dc"))
        bolt_radius = 3.4
        for x in (housing.left() + 9, housing.right() - 9):
            for y in (housing.top() + 9, housing.bottom() - 9):
                painter.drawEllipse(
                    QRectF(
                        x - bolt_radius,
                        y - bolt_radius,
                        bolt_radius * 2,
                        bolt_radius * 2,
                    )
                )

        connector_width = 10
        connector_x = (
            housing.left() - connector_width
            if row == 0
            else housing.right()
        )
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(
            QRectF(connector_x, center_y - 10, connector_width, 20), 4, 4
        )

        badge = QRectF(housing.left() + 7, housing.top() + 6, 27, 19)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d41432"))
        painter.drawRoundedRect(badge, 9.5, 9.5)
        painter.setPen(QColor("#ffffff"))
        badge_font = painter.font()
        badge_font.setBold(True)
        badge_font.setPointSize(8)
        painter.setFont(badge_font)
        painter.drawText(
            badge,
            Qt.AlignmentFlag.AlignCenter,
            f"{slot:02d}",
        )

    @classmethod
    def slot_position(cls, slot: int) -> tuple[int, int]:
        """返回逆时针坑位在两排五列托盘中的视觉位置。"""
        if not 1 <= int(slot) <= cls.MOTOR_COUNT:
            raise ValueError(f"无效托盘坑位：{slot}")
        if slot <= 5:
            return 1, slot - 1
        return 0, 10 - slot

    def _draw_mounting_holes(self, painter: QPainter, tray_rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#8795a5"), 1.5))
        painter.setBrush(QColor("#f8fafc"))
        radius = 5.5
        points = (
            (tray_rect.left() + 14, tray_rect.top() + 14),
            (tray_rect.right() - 14, tray_rect.top() + 14),
            (tray_rect.left() + 14, tray_rect.bottom() - 14),
            (tray_rect.right() - 14, tray_rect.bottom() - 14),
        )
        for x, y in points:
            painter.drawEllipse(
                QRectF(x - radius, y - radius, radius * 2, radius * 2)
            )

    def _column_width(self) -> float:
        available = (
            self.width()
            - self.OUTER_MARGIN * 2
            - self.COLUMN_GAP * 4
        )
        return max(130.0, available / 5)

    def _column_center(self, column: int) -> float:
        width = self._column_width()
        return (
            self.OUTER_MARGIN
            + width / 2
            + column * (width + self.COLUMN_GAP)
        )
