import unittest

from services.quality_rule_service import QualityRuleError, QualityRuleService


def configured_rules():
    return {
        "models": {
            "C68": {
                "sn_prefixes": ["C68"],
                "configured": True,
                "rule_version": "2026-08-19-01",
                "ranges": {
                    "runin_speed_rpm": {
                        "label": "转速", "min": 21000, "max": 22000
                    },
                    "runin_voltage_v": {
                        "label": "电压", "min": 220, "max": 240
                    },
                    "runin_temperature_c": {
                        "label": "温度", "min": 20, "max": 70
                    },
                    "runin_current_a": {
                        "label": "电流", "min": 170, "max": 220
                    },
                },
                "allowed_error_codes": [0],
            }
        }
    }


def measurement(**overrides):
    result = {
        "tray_slot": 1,
        "product_sn": "C68HNI042665",
        "runin_speed_rpm": 21696,
        "runin_voltage_v": 234,
        "runin_temperature_c": 57,
        "runin_current_a": 185,
        "runin_error_code": 0,
    }
    result.update(overrides)
    return result


class QualityRuleServiceTests(unittest.TestCase):
    def test_sn_prefix_selects_c68_and_passes_inclusive_ranges(self) -> None:
        service = QualityRuleService(configured_rules())

        result = service.evaluate_item(measurement(runin_speed_rpm=21000))

        self.assertTrue(result["runin_passed"])
        self.assertEqual(result["product_model"], "C68")
        self.assertEqual(result["quality_rule_version"], "2026-08-19-01")
        self.assertEqual(result["judgement_source"], "upper_computer")

    def test_out_of_range_or_alarm_is_ng_with_reasons(self) -> None:
        service = QualityRuleService(configured_rules())

        result = service.evaluate_item(
            measurement(runin_voltage_v=250, runin_error_code=7)
        )

        self.assertFalse(result["runin_passed"])
        self.assertEqual(result["runin_result_code"], 1)
        self.assertEqual(len(result["quality_failures"]), 2)

    def test_unknown_sn_prefix_is_rejected(self) -> None:
        service = QualityRuleService(configured_rules())

        with self.assertRaisesRegex(QualityRuleError, "未匹配"):
            service.evaluate_item(measurement(product_sn="C66HNI042665"))

    def test_unconfigured_model_is_rejected(self) -> None:
        rules = configured_rules()
        rules["models"]["C68"]["configured"] = False
        service = QualityRuleService(rules)

        with self.assertRaisesRegex(QualityRuleError, "尚未确认"):
            service.evaluate_item(measurement())


if __name__ == "__main__":
    unittest.main()
