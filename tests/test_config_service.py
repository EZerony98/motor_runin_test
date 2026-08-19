import tempfile
import unittest
from pathlib import Path

from services.config_service import ConfigService


class ConfigServiceTests(unittest.TestCase):
    def test_load_all_project_config(self) -> None:
        config_dir = Path(__file__).resolve().parent.parent / "config"
        config = ConfigService(config_dir).load_all()
        self.assertEqual(set(config), set(ConfigService.CONFIG_NAMES))
        self.assertIn("application", config["app"])
        self.assertIn("C68", config["quality_rules"]["models"])
        self.assertEqual(
            set(config["quality_rules"]["models"]),
            {
                "C68",
                "46520-24-43000",
                "38230-24-60000",
                "52232-24-430",
                "40S18-24-500-C080",
                "52237-24-500",
                "52237-24-540",
            },
        )

    def test_unknown_config_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            service = ConfigService(Path(temporary_dir))
            with self.assertRaises(KeyError):
                service.load("unknown")


if __name__ == "__main__":
    unittest.main()
