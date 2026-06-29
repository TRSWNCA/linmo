from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from linmo.runtime import (
    add_runtime_log,
    clear_runtime_logs,
    configure_runtime_logging,
    get_runtime_diagnostics,
    set_runtime_status,
)


class RuntimeDiagnosticsTests(unittest.TestCase):
    def test_runtime_entries_status_and_file_are_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "logs" / "linmo.log"
            configure_runtime_logging(log_path)
            clear_runtime_logs()

            entry = add_runtime_log(
                "warning",
                "backend.test",
                "PaddleOCR unavailable",
                "missing DLL",
                echo=False,
            )
            set_runtime_status(
                "ocr",
                "initializing_model",
                "正在初始化模型",
                page_id=7,
            )
            diagnostics = get_runtime_diagnostics()

            self.assertEqual(diagnostics["entries"][0]["id"], entry["id"])
            self.assertEqual(diagnostics["entries"][0]["level"], "warning")
            self.assertEqual(diagnostics["status"]["stage"], "initializing_model")
            self.assertEqual(diagnostics["status"]["page_id"], 7)
            self.assertEqual(diagnostics["log_path"], str(log_path))
            self.assertIn("missing DLL", log_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
