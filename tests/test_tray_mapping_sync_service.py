import json
import unittest
from unittest.mock import patch

from services.tray_mapping_sync_service import TrayMappingSyncService


class ResponseStub:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return b'{"status":"saved"}'


class TrayMappingSyncServiceTests(unittest.TestCase):
    def test_send_uses_standard_library_json_post(self) -> None:
        service = TrayMappingSyncService(
            {
                "enabled": True,
                "base_url": "http://192.168.250.100:8765",
                "token": "test-token",
                "timeout_seconds": 2,
            }
        )
        batch = {"tray_id": "7001", "items": [{"tray_slot": 1}]}

        with patch(
            "services.tray_mapping_sync_service.urlopen",
            return_value=ResponseStub(),
        ) as mocked_urlopen:
            service.send(batch)

        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "http://192.168.250.100:8765/api/v1/tray-mappings",
        )
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("X-line-token"), "test-token")
        self.assertEqual(json.loads(request.data.decode("utf-8")), batch)
        self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], 2.0)


if __name__ == "__main__":
    unittest.main()
