"""按产品型号配置判定跑合结果。"""

from numbers import Real
from typing import Any, Dict, Iterable, List, Tuple


class QualityRuleError(ValueError):
    """判定规则缺失、未启用或格式无效。"""


class QualityRuleService:
    """使用JSON配置的闭区间规则计算产品跑合是否合格。"""

    RANGE_FIELDS: Tuple[str, ...] = (
        "runin_speed_rpm",
        "runin_voltage_v",
        "runin_temperature_c",
        "runin_current_a",
    )

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = dict(config or {})

    def evaluate_items(
        self, items: Iterable[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return [self.evaluate_item(item) for item in items]

    def evaluate_item(self, source: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(source)
        product_sn = str(item.get("product_sn", "")).strip()
        model_code, model = self._rule_for_sn(product_sn)
        version = str(model.get("rule_version", "")).strip()
        ranges = self._validated_ranges(model_code, model)
        allowed_error_codes = self._allowed_error_codes(model_code, model)

        failures: List[str] = []
        for field, minimum, maximum, label in ranges:
            value = item.get(field)
            if not isinstance(value, Real) or isinstance(value, bool):
                failures.append(f"{label}无有效数值")
                continue
            if value < minimum or value > maximum:
                failures.append(
                    f"{label}{value}超出[{minimum}, {maximum}]"
                )

        error_code = item.get("runin_error_code")
        if error_code not in allowed_error_codes:
            failures.append(
                f"报警码{error_code}不在允许值{sorted(allowed_error_codes)}内"
            )

        passed = not failures
        item.update(
            {
                "product_model": model_code,
                "quality_rule_version": version,
                "quality_failures": failures,
                "runin_passed": passed,
                "runin_result_code": 0 if passed else 1,
                "judgement_source": "upper_computer",
            }
        )
        return item

    def _rule_for_sn(self, product_sn: str) -> Tuple[str, Dict[str, Any]]:
        if not product_sn:
            raise QualityRuleError("产品SN为空，无法判断产品型号")
        models = self.config.get("models")
        if not isinstance(models, dict):
            raise QualityRuleError("quality_rules.json 缺少 models")
        matches = []
        for model_code, candidate in models.items():
            if not isinstance(candidate, dict):
                continue
            prefixes = candidate.get("sn_prefixes", [])
            if not isinstance(prefixes, list):
                raise QualityRuleError(
                    f"产品型号 {model_code} 的 sn_prefixes 必须是数组"
                )
            if any(
                str(prefix) and product_sn.startswith(str(prefix))
                for prefix in prefixes
            ):
                matches.append((str(model_code), candidate))
        if not matches:
            raise QualityRuleError(f"SN {product_sn} 未匹配到产品型号判定规则")
        if len(matches) > 1:
            names = "、".join(model_code for model_code, _ in matches)
            raise QualityRuleError(f"SN {product_sn} 同时匹配多个型号：{names}")
        model_code, model = matches[0]
        if not isinstance(model, dict):
            raise QualityRuleError(f"产品型号 {model_code} 的判定规则必须是对象")
        if not bool(model.get("configured", False)):
            raise QualityRuleError(
                f"产品型号 {model_code} 的判定条件尚未确认，请先配置上下限"
            )
        return model_code, model

    def _validated_ranges(
        self, model_code: str, model: Dict[str, Any]
    ) -> List[Tuple[str, Real, Real, str]]:
        source = model.get("ranges")
        if not isinstance(source, dict):
            raise QualityRuleError(f"产品型号 {model_code} 缺少 ranges")
        result: List[Tuple[str, Real, Real, str]] = []
        for field in self.RANGE_FIELDS:
            rule = source.get(field)
            if not isinstance(rule, dict):
                raise QualityRuleError(
                    f"产品型号 {model_code} 缺少字段 {field} 的上下限"
                )
            minimum = rule.get("min")
            maximum = rule.get("max")
            if (
                not isinstance(minimum, Real)
                or isinstance(minimum, bool)
                or not isinstance(maximum, Real)
                or isinstance(maximum, bool)
            ):
                raise QualityRuleError(
                    f"产品型号 {model_code} 的 {field} 必须填写数字 min/max"
                )
            if minimum > maximum:
                raise QualityRuleError(
                    f"产品型号 {model_code} 的 {field} 最小值不能大于最大值"
                )
            label = str(rule.get("label", field))
            result.append((field, minimum, maximum, label))
        return result

    @staticmethod
    def _allowed_error_codes(
        model_code: str, model: Dict[str, Any]
    ) -> set:
        values = model.get("allowed_error_codes")
        if not isinstance(values, list) or not values:
            raise QualityRuleError(
                f"产品型号 {model_code} 必须设置 allowed_error_codes"
            )
        if any(
            not isinstance(value, int) or isinstance(value, bool)
            for value in values
        ):
            raise QualityRuleError(
                f"产品型号 {model_code} 的 allowed_error_codes 必须是整数数组"
            )
        return set(values)
