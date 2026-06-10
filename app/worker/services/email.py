import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.config import Settings

logger = logging.getLogger(__name__)

CURRENCY_LABELS: dict[str, tuple[str, str]] = {
    "USD-BRL": ("Dollar", "🇺🇸"),
    "EUR-BRL": ("Euro", "🇪🇺"),
}


class EmailService:
    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password
        self._from = settings.email_from
        self._to = settings.email_to

    def send_alert(self, rate_data: dict, reason: str) -> None:
        pair = rate_data["pair"]
        label, flag = CURRENCY_LABELS.get(pair, (pair, "💱"))
        bid = rate_data["bid"]
        ask = rate_data["ask"]
        high = rate_data["high"]
        low = rate_data["low"]
        change = rate_data["change_pct"]
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        change_color = "green" if change >= 0 else "red"
        subject = f"{flag} {label} alert — R$ {bid:.4f} ({reason})"
        html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #333;">
          <h2>{flag} Exchange Rate Alert — {label}</h2>
          <table style="border-collapse:collapse; width:320px;">
            <tr><td style="padding:6px 12px; background:#f5f5f5;"><b>Bid</b></td>
                <td style="padding:6px 12px;"><b>R$ {bid:.4f}</b></td></tr>
            <tr><td style="padding:6px 12px; background:#f5f5f5;"><b>Ask</b></td>
                <td style="padding:6px 12px;">R$ {ask:.4f}</td></tr>
            <tr><td style="padding:6px 12px; background:#f5f5f5;"><b>Day high</b></td>
                <td style="padding:6px 12px;">R$ {high:.4f}</td></tr>
            <tr><td style="padding:6px 12px; background:#f5f5f5;"><b>Day low</b></td>
                <td style="padding:6px 12px;">R$ {low:.4f}</td></tr>
            <tr><td style="padding:6px 12px; background:#f5f5f5;"><b>Change</b></td>
                <td style="padding:6px 12px; color:{change_color};">{change:+.2f}%</td></tr>
          </table>
          <p style="margin-top:16px; color:#666; font-size:13px;">
            Alert reason: <i>{reason}</i><br>Checked at {ts}
          </p>
          <p style="color:#aaa; font-size:11px;">Exchange Bot 🤖</p>
        </body></html>
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = self._to
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(self._host, self._port) as server:
            server.ehlo()
            server.starttls()
            server.login(self._user, self._password)
            server.sendmail(self._from, self._to, msg.as_string())
        logger.info("Alert email sent to %s: %s", self._to, subject)
