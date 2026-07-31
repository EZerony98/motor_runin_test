"""跑合测试后台任务。"""

from PySide6.QtCore import QObject, Signal, Slot

from services.runin_test_service import RunInTestService


class TestWorker(QObject):
    stage_started = Signal(dict)
    log = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(self, service: RunInTestService) -> None:
        super().__init__()
        self.service = service
        self._stop_requested = False

    @Slot()
    def run(self) -> None:
        try:
            for stage in self.service.iter_stages():
                if self._stop_requested:
                    self.log.emit("收到停止请求，跑合任务结束。")
                    break
                self.stage_started.emit(stage)
                self.log.emit(f"进入工艺阶段：{stage.get('name', '未命名')}")
                # 后续在这里调用设备驱动并执行定时采集。
        except Exception as error:
            self.error.emit(str(error))
        finally:
            self.finished.emit()

    @Slot()
    def stop(self) -> None:
        self._stop_requested = True
