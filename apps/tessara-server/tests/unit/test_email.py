"""Tests for tessara_server.utility.email — graceful degradation without SMTP."""

from unittest.mock import AsyncMock

import pytest

from tessara_server.configuration.settings import application_settings
from tessara_server.utility import email


class TestSendEmail:
    @pytest.mark.asyncio
    async def test_logs_instead_of_sending_when_smtp_unset(self, monkeypatch, caplog):
        monkeypatch.setattr(application_settings, "smtp_host", "")
        send = AsyncMock()
        monkeypatch.setattr(email.aiosmtplib, "send", send)

        with caplog.at_level("WARNING"):
            await email.send_email("to@x.com", "Subject", "Body with a link")

        send.assert_not_called()
        assert "to@x.com" in caplog.text
        assert "Body with a link" in caplog.text

    @pytest.mark.asyncio
    async def test_sends_when_smtp_configured(self, monkeypatch):
        monkeypatch.setattr(application_settings, "smtp_host", "smtp.example.com")
        send = AsyncMock()
        monkeypatch.setattr(email.aiosmtplib, "send", send)

        await email.send_email("to@x.com", "Subject", "Body")

        send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_failure_is_swallowed(self, monkeypatch, caplog):
        monkeypatch.setattr(application_settings, "smtp_host", "smtp.example.com")
        send = AsyncMock(side_effect=RuntimeError("boom"))
        monkeypatch.setattr(email.aiosmtplib, "send", send)

        with caplog.at_level("ERROR"):
            await email.send_email("to@x.com", "Subject", "Body")

        send.assert_awaited_once()
