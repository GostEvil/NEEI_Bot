"""tests/test_calendario.py — Testes (com mocks) do comando /calendario."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ["GUILD_ID"] = "999"
os.environ["MANAGER_IDS"] = "1,10"
os.environ["NEEI_ROLE_NAME"] = "NEEI"
os.environ["DISCORD_TOKEN"] = "x"

import bot  # noqa: E402
import data_manager as dm  # noqa: E402


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(dm, "ADMINS_FILE", tmp_path / "admins.json")
    monkeypatch.setattr(dm, "LOGS_FILE", tmp_path / "logs.json")
    monkeypatch.setattr(dm, "CALENDAR_FILE", tmp_path / "calendar.json")
    monkeypatch.setattr(dm, "CALENDAR_CONFIG_FILE", tmp_path / "calendar_config.json")
    dm.add_admin("2")
    dm.set_calendar_channel_id(555)


def make_interaction(uid: str):
    i = MagicMock()
    i.user.id = int(uid)
    i.user.roles = []
    i.response.send_message = AsyncMock()
    i.guild.get_channel.return_value.send = AsyncMock()
    return i


def text(i):
    args, kwargs = i.response.send_message.call_args
    return args[0] if args else kwargs.get("content", "")


def run(uid, tipo, o_que, disc, data):
    i = make_interaction(uid)
    asyncio.run(bot.calendario.callback(i, tipo, o_que, disc, data))
    return i


def test_add_and_remove():
    i = run("2", "add", "teste", "Programação", "25/01/2027")
    assert "Feito" in text(i)
    assert dm.get_calendar() == [
        {"kind": "teste", "subject": "Programação", "date": "2027-01-25"}
    ]
    i = run("2", "remove", "teste", "programação", "25/01/2027")
    assert "Feito" in text(i)
    assert dm.get_calendar() == []


def test_duplicate_and_missing():
    run("1", "add", "exame final", "BD", "01/02/2027")
    i = run("1", "add", "exame final", "BD", "01/02/2027")
    assert "já existe" in text(i)
    i = run("1", "remove", "exame recurso", "BD", "01/02/2027")
    assert "Não encontrei" in text(i)


def test_invalid_date_and_permission():
    i = run("2", "add", "teste", "BD", "2027-01-25")
    assert "Data inválida" in text(i)
    i = run("4", "add", "teste", "BD", "25/01/2027")
    assert "permissão" in text(i)
    assert dm.get_calendar() == []


def test_embed_sent_to_channel():
    i = run("2", "add", "exame final", "BD", "01/02/2027")
    embed = i.guild.get_channel.return_value.send.call_args.kwargs["embed"]
    assert [f.value for f in embed.fields] == ["Exame final", "BD", "01/02/2027"]


def test_requires_configured_channel():
    dm.set_calendar_channel_id(None)
    i = run("2", "add", "teste", "BD", "25/01/2027")
    assert "configcalendario" in text(i)
    assert dm.get_calendar() == []


def test_configcalendario_managers_only():
    ch = MagicMock(id=777)
    i = make_interaction("2")
    asyncio.run(bot.configcalendario.callback(i, ch))
    assert dm.get_calendar_channel_id() == 555
    i = make_interaction("1")
    asyncio.run(bot.configcalendario.callback(i, ch))
    assert dm.get_calendar_channel_id() == 777
