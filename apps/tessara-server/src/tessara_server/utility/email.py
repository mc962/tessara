"""Email sending — verification and password-reset links.

Degrades gracefully when SMTP isn't configured (homelab/dev use without a
mail server): the message is logged instead of sent, so signup/reset flows
still work end-to-end, just with the link surfaced in the server log rather
than an inbox.
"""

import logging
from email.message import EmailMessage

import aiosmtplib

from tessara_server.configuration.settings import application_settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str) -> None:
    if not application_settings.smtp_host:
        logger.warning(
            "SMTP not configured — logging email instead of sending.\nTo: %s\nSubject: %s\n%s",
            to,
            subject,
            body,
        )
        return

    message = EmailMessage()
    message["From"] = application_settings.smtp_from_address
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=application_settings.smtp_host,
            port=application_settings.smtp_port,
            username=application_settings.smtp_user or None,
            password=application_settings.smtp_password.get_secret_value() or None,
            start_tls=application_settings.smtp_use_tls,
        )
    except Exception:
        logger.exception("Failed to send email to %s", to)
