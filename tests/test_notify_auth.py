"""Fail-fast when Gmail rejects the app password (SMTP 535)."""

from unittest.mock import MagicMock, patch

import smtplib

import notify


def test_is_smtp_auth_error_detects_gmail_535():
    exc = smtplib.SMTPAuthenticationError(
        535,
        b"5.7.8 Username and Password not accepted. BadCredentials",
    )
    assert notify._is_smtp_auth_error(exc) is True
    assert notify._is_smtp_auth_error(RuntimeError("temporary timeout")) is False


def test_send_email_aborts_remaining_batches_on_auth_error():
    recipients = [f"user{i}@example.com" for i in range(60)]  # 2 batches of 30
    auth_error = smtplib.SMTPAuthenticationError(
        535, b"5.7.8 Username and Password not accepted"
    )
    with (
        patch.object(notify, "SENDER_EMAIL", "bot@gmail.com"),
        patch.object(notify, "GMAIL_APP_PASSWORD", "bad-pass"),
        patch("notify.smtplib.SMTP_SSL") as smtp_cls,
        patch("notify.time.sleep") as sleep,
    ):
        server = MagicMock()
        smtp_cls.return_value.__enter__.return_value = server
        server.login.side_effect = auth_error

        ok = notify.send_email([], [], recipients)

        assert ok is False
        assert server.login.call_count == 1
        sleep.assert_not_called()
