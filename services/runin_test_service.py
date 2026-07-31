"""电机跑合流程编排。"""

from typing import Any, Dict, Iterable, List


class RunInTestService:
    """保存工艺阶段并向后台测试线程提供执行顺序。"""

    def __init__(self, process_config: Dict[str, Any]) -> None:
        self.process_config = process_config

    def stages(self) -> List[Dict[str, Any]]:
        stages = self.process_config.get("stages", [])
        if not isinstance(stages, list):
            raise ValueError("process.json 中的 stages 必须是数组")
        return [dict(stage) for stage in stages]

    def iter_stages(self) -> Iterable[Dict[str, Any]]:
        yield from self.stages()
