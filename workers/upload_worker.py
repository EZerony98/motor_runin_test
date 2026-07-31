"""服务器上传后台任务。"""

from typing import Any, Dict

from PySide6.QtCore import QObject, Signal, Slot

from services.upload_service import UploadService


class UploadWorker(QObject):
    succeeded = Signal()
    error = Signal(str)
    finished = Signal()

    def __init__(self, service: UploadService, record: Dict[str, Any]) -> None:
        super().__init__()
        self.service = service
        self.record = record

    @Slot()
    def run(self) -> None:
        try:
            self.service.upload(self.record)
            self.succeeded.emit()
        except Exception as error:
            self.error.emit(str(error))
        finally:
            self.finished.emit()
