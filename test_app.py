import json
import unittest
from unittest.mock import patch, MagicMock
import app


class TestSREAssistant(unittest.TestCase):

    def test_log_truncation(self):
        """Tests that raw log payloads over 4000 characters are safely truncated."""
        large_log = "ERROR line\n" * 500  # > 5000 characters
        self.assertGreater(len(large_log), 4000)

        sample_event = {"raw_log": large_log}

        with patch("app.diagnose_log", return_value="Mock Diagnosis") as mock_diag:
            with patch("app.send_slack_alert", return_value=True):
                response = app.lambda_handler(sample_event, None)
                self.assertEqual(response["statusCode"], 200)

                # Verify diagnose_log received a truncated log payload
                passed_log = mock_diag.call_args[0][0]
                self.assertLessEqual(len(passed_log), 4100)
                self.assertIn("[Truncated remaining log payload for analysis]", passed_log)

    @patch("app.send_slack_alert")
    @patch("app.diagnose_log")
    def test_lambda_handler_custom_event(self, mock_diagnose, mock_slack):
        """Tests standard custom event handling."""
        mock_diagnose.return_value = "### SRE Report\n* Root Cause: Test error"
        mock_slack.return_value = True

        event = {"raw_log": "2026-07-23 [ERROR] Database connection failed"}
        result = app.lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertTrue(body["slack_sent"])
        self.assertIn("Root Cause", body["diagnosis"])

    @patch("app.send_slack_alert")
    @patch("app.diagnose_log")
    def test_lambda_handler_none_event(self, mock_diagnose, mock_slack):
        """Tests that None or non-dict events are handled safely without crashing."""
        mock_diagnose.return_value = "Mock Diagnosis"
        mock_slack.return_value = True

        result = app.lambda_handler(None, None)
        self.assertEqual(result["statusCode"], 200)


if __name__ == "__main__":
    unittest.main()
