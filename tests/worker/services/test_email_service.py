import email as stdlib_email
from email.header import decode_header as _decode_header
from unittest.mock import MagicMock, patch

import pytest

from core.config import Settings
from worker.services.email import EmailService


@pytest.fixture
def email_service(settings):
    return EmailService(settings)


@pytest.fixture
def tls_settings(settings):
    return Settings(
        _env_file=None,
        mongo_uri=settings.mongo_uri,
        smtp_host=settings.smtp_host,
        smtp_port=465,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        email_from=settings.email_from,
        email_to=settings.email_to,
        smtp_use_tls=True,
        smtp_start_tls=False,
    )


@pytest.fixture
def plain_settings(settings):
    return Settings(
        _env_file=None,
        mongo_uri=settings.mongo_uri,
        smtp_host=settings.smtp_host,
        smtp_port=25,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        email_from=settings.email_from,
        email_to=settings.email_to,
        smtp_use_tls=False,
        smtp_start_tls=False,
    )


def _smtp_mock():
    """Return a (context_manager, server_mock) pair for smtplib.SMTP / SMTP_SSL."""
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


class TestStartTls:
    """Default mode: smtp_use_tls=False, smtp_start_tls=True (SMTP + STARTTLS)."""

    def test_uses_smtp_class(self, email_service, settings, usd_rate_data):
        ctx, _ = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx) as mock_smtp:
            email_service.send_alert(usd_rate_data, "above threshold")
        mock_smtp.assert_called_once_with(settings.smtp_host, settings.smtp_port)

    def test_calls_starttls(self, email_service, settings, usd_rate_data):
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            email_service.send_alert(usd_rate_data, "above threshold")
        server.starttls.assert_called_once()
        server.login.assert_called_once_with(settings.smtp_user, settings.smtp_password)

    def test_does_not_use_smtp_ssl(self, email_service, usd_rate_data):
        ctx, _ = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            with patch("worker.services.email.smtplib.SMTP_SSL") as mock_ssl:
                email_service.send_alert(usd_rate_data, "above threshold")
        mock_ssl.assert_not_called()


class TestSslTls:
    """SMTP_USE_TLS=true mode: smtp_use_tls=True (SMTP_SSL, no STARTTLS)."""

    def test_uses_smtp_ssl_class(self, tls_settings, usd_rate_data):
        service = EmailService(tls_settings)
        ctx, _ = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP_SSL", return_value=ctx) as mock_ssl:
            service.send_alert(usd_rate_data, "above threshold")
        mock_ssl.assert_called_once_with(tls_settings.smtp_host, tls_settings.smtp_port)

    def test_does_not_call_starttls(self, tls_settings, usd_rate_data):
        service = EmailService(tls_settings)
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP_SSL", return_value=ctx):
            service.send_alert(usd_rate_data, "above threshold")
        server.starttls.assert_not_called()

    def test_does_not_use_plain_smtp(self, tls_settings, usd_rate_data):
        service = EmailService(tls_settings)
        ctx, _ = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP_SSL", return_value=ctx):
            with patch("worker.services.email.smtplib.SMTP") as mock_smtp:
                service.send_alert(usd_rate_data, "above threshold")
        mock_smtp.assert_not_called()


class TestPlainSmtp:
    """No TLS mode: smtp_use_tls=False, smtp_start_tls=False."""

    def test_uses_smtp_without_starttls(self, plain_settings, usd_rate_data):
        service = EmailService(plain_settings)
        ctx, server = _smtp_mock()
        with patch("worker.services.email.smtplib.SMTP", return_value=ctx):
            service.send_alert(usd_rate_data, "above threshold")
        server.starttls.assert_not_called()


class TestSendAlert:
    """Content and addressing tests — independent of TLS mode."""

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
        assert "5.5000" in html
        assert "5.5500" in html
        assert "5.6000" in html
        assert "5.4500" in html

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
