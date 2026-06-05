import sys
import types
import unittest


sys.modules.setdefault(
    "dotenv",
    types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None),
)

import notify


class NotifyMobileTemplateTests(unittest.TestCase):
    def test_digest_template_has_mobile_readability_contracts(self):
        html = notify.build_html(
            [
                {
                    "Title": "Frontend Internship",
                    "Application Link": "https://example.com/apply",
                    "Category": "Internship",
                    "Industry": "Software",
                    "Deadline": "Jun 30",
                }
            ],
            [],
        )

        self.assertIn("@media only screen and (max-width: 480px)", html)
        self.assertIn('class="email-shell"', html)
        self.assertIn('class="opportunity-title"', html)
        self.assertIn('class="apply-link"', html)
        self.assertIn("font-size:15px", html)
        self.assertIn("min-height: 44px", html)
        self.assertIn("line-height:44px", html)


if __name__ == "__main__":
    unittest.main()
