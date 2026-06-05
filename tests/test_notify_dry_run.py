import contextlib
import io
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


sys.modules.setdefault(
    "dotenv",
    types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None),
)

import notify


class NotifyDryRunTests(unittest.TestCase):
    def test_write_email_preview_writes_file_and_metadata(self):
        with TemporaryDirectory() as tmpdir:
            preview_path = Path(tmpdir) / "email_preview.html"
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                notify.write_email_preview(
                    "<html><body>Preview</body></html>",
                    "ScoutBot Weekly — 2 Fresh Opportunities (Jun 08)",
                    ["one@example.com", "two@example.com"],
                    preview_path=preview_path,
                )

            self.assertEqual(
                preview_path.read_text(encoding="utf-8"),
                "<html><body>Preview</body></html>",
            )
            stdout = output.getvalue()
            self.assertIn("Subject: ScoutBot Weekly", stdout)
            self.assertIn("Recipients: 2", stdout)
            self.assertIn("HTML preview written to: email_preview.html", stdout)


if __name__ == "__main__":
    unittest.main()
