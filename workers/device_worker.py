"""设备轮询后台任务。"""

from PySide6.QtCore import QObject, Signal, Slot

from drivers.base_device import BaseDevice


class DeviceWorker(QObject):
    data_ready = Signal(dict)
    error = Signal(str)
    finished = Signal()

    def __init__(self, device: BaseDevice) -> None:
        super().__init__()
        self.device = device

    @Slot()
    def read_once(self) -> None:
        try:
            self.data_ready.emit(self.device.read())
        except Exception as error:
            self.error.emit(str(error))
        finally:
            self.finished.emit()
