import email as stdlib_email
from email.header import decode_header as _decode_header
from unittest.mock import MagicMock, patch

import pytest

from worker.services.email import EmailService


@pytest.fixture
def email_service(settings):
    return EmailService(settings)


def _smtp_mock():
    """Return a (context_manager, server_mock) pair for smtplib.SMTP."""
    server = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=server)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, server


def _parse_sent_email(server):
    """Decode the MIME message captured by the mock SMTP server."""
    raw = server.sendmail.call_args[0][2]
    msg = stdlib_email.message_from_string(raw)

    parts = _decode_header(msg["Subject"])
    subject = "".join(
        chunk.decode(enc or "utf-8") if isinstance(chunk, bytes) else chunk
        for chunk, enc in parts
    )

    html = ""
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            html = part.get_payload(decode=True).decode("utf-8")
            break

    return subject, html


class TestSendAlert:
    def test_connects_to_configured_host_and_port(self, email_service, settings, usd_rate_data):
        ctx, _ = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx) as mock_smtp:
            email_service.send_alert(usd_rate_data, "above threshold")
        mock_smtp.assert_called_once_with(settings.smtp_host, settings.smtp_port)

    def test_performs_tls_handshake_and_login(self, email_service, settings, usd_rate_data):
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            email_service.send_alert(usd_rate_data, "above threshold")
        server.ehlo.assert_called_once()
        server.starttls.assert_called_once()
        server.login.assert_called_once_with(settings.smtp_user, settings.smtp_password)

    def test_sends_from_and_to_correct_addresses(self, email_service, settings, usd_rate_data):
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            email_service.send_alert(usd_rate_data, "above threshold")
        from_addr, to_addr, _ = server.sendmail.call_args[0]
        assert from_addr == settings.email_from
        assert to_addr == settings.email_to

    def test_subject_contains_bid_and_reason(self, email_service, usd_rate_data):
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            email_service.send_alert(usd_rate_data, "above threshold")
        subject, _ = _parse_sent_email(server)
        assert "5.5000" in subject
        assert "above threshold" in subject

    def test_html_body_contains_all_rate_fields(self, email_service, usd_rate_data):
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            email_service.send_alert(usd_rate_data, "above threshold")
        _, html = _parse_sent_email(server)
        assert "5.5000" in html   # bid
        assert "5.5500" in html   # ask
        assert "5.6000" in html   # high
        assert "5.4500" in html   # low

    def test_positive_change_renders_green(self, email_service, usd_rate_data):
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            email_service.send_alert(usd_rate_data, "above threshold")
        _, html = _parse_sent_email(server)
        assert "green" in html

    def test_negative_change_renders_red(self, email_service, usd_rate_data):
        usd_rate_data["change_pct"] = -1.0
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            email_service.send_alert(usd_rate_data, "above threshold")
        _, html = _parse_sent_email(server)
        assert "red" in html

    def test_unknown_pair_falls_back_to_pair_name(self, email_service):
        rate_data = {
            "pair": "GBP-BRL",
            "bid": 7.00,
            "ask": 7.05,
            "high": 7.10,
            "low": 6.95,
            "change_pct": 0.1,
        }
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            email_service.send_alert(rate_data, "above threshold")
        subject, html = _parse_sent_email(server)
        assert "GBP-BRL" in subject or "GBP-BRL" in html

    def test_eur_pair_uses_euro_label(self, email_service):
        rate_data = {
            "pair": "EUR-BRL",
            "bid": 6.00,
            "ask": 6.05,
            "high": 6.10,
            "low": 5.95,
            "change_pct": 0.3,
        }
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            email_service.send_alert(rate_data, "above threshold")
        _, html = _parse_sent_email(server)
        assert "Euro" in html
