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
import config  # noqa: E402
import data_manager as dm  # noqa: E402


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(dm, "ADMINS_FILE", tmp_path / "admins.json")
    monkeypatch.setattr(dm, "LOGS_FILE", tmp_path / "logs.json")
    monkeypatch.setattr(dm, "CALENDAR_FILE", tmp_path / "calendar.json")
    monkeypatch.setattr(dm, "CALENDAR_CONFIG_FILE", tmp_path / "calendar_config.json")
    # Outros módulos de teste definem MANAGER_IDS antes deste; fixar aqui.
    monkeypatch.setattr(config, "get_manager_ids", lambda: ["1"])
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


def run(uid, tipo, o_que, disc, data, turno=None, obs=None):
    i = make_interaction(uid)
    asyncio.run(bot.calendario.callback(i, tipo, o_que, disc, data, turno, obs))
    return i


def test_add_and_remove():
    i = run("2", "add", "teste", "1103", "25/01/2027")
    assert "Feito" in text(i)
    assert dm.get_calendar() == [
        {"kind": "teste", "subject": "1103", "date": "2027-01-25", "turno": "", "notes": ""}
    ]
    i = run("2", "remove", "teste", "1103", "25/01/2027")
    assert "Feito" in text(i)
    assert dm.get_calendar() == []


def test_duplicate_and_missing():
    run("1", "add", "exame final", "2101", "01/02/2027")
    i = run("1", "add", "exame final", "2101", "01/02/2027")
    assert "já existe" in text(i)
    i = run("1", "remove", "exame recurso", "2101", "01/02/2027")
    assert "Não encontrei" in text(i)


def test_invalid_date():
    i = run("2", "add", "teste", "2101", "2027-01-25")
    assert "Data inválida" in text(i)
    assert dm.get_calendar() == []


def test_anyone_can_add_but_only_neei_plus_can_remove():
    i = run("4", "add", "teste", "2101", "25/01/2027")
    assert "Feito" in text(i)
    i = run("4", "remove", "teste", "2101", "25/01/2027")
    assert "NEEI" in text(i)
    assert len(dm.get_calendar()) == 1
    i = make_interaction("3")
    role = MagicMock()
    role.name = "NEEI"
    i.user.roles = [role]
    asyncio.run(bot.calendario.callback(i, "remove", "teste", "2101", "25/01/2027"))
    assert "Feito" in text(i)
    assert dm.get_calendar() == []


def test_embed_sent_to_channel():
    i = run("2", "add", "exame final", "2101", "01/02/2027")
    embed = i.guild.get_channel.return_value.send.call_args.kwargs["embed"]
    assert [f.value for f in embed.fields] == ["Exame final", "Bases de Dados", "01/02/2027"]


def test_requires_configured_channel():
    dm.set_calendar_channel_id(None)
    i = run("2", "add", "teste", "2101", "25/01/2027")
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


def test_only_active_semester_subjects():
    i = run("2", "add", "teste", "1201", "25/01/2027")  # 2º semestre, ativo é o 1º
    assert "inválida" in text(i)
    dm.set_semester(2)
    i = run("2", "add", "teste", "1201", "25/01/2027")
    assert "Feito" in text(i)
    dm.set_semester(1)
    i = run("2", "remove", "teste", "1201", "25/01/2027")  # remover continua possível
    assert "Feito" in text(i)


def test_autocomplete_follows_semester():
    def values(cur):
        i = make_interaction("4")
        return [c.value for c in asyncio.run(bot.calendario_disciplina_autocomplete(i, cur))]
    assert "1103" in values("") and "1201" not in values("")
    assert values("cálc") == ["ano:1", "1102"]
    dm.set_semester(2)
    assert "1201" in values("") and "1103" not in values("")


def test_configsemestre_managers_only_and_keeps_channel():
    i = make_interaction("2")
    asyncio.run(bot.configsemestre.callback(i, 2))
    assert dm.get_semester() == 1
    i = make_interaction("1")
    asyncio.run(bot.configsemestre.callback(i, 2))
    assert dm.get_semester() == 2
    assert dm.get_calendar_channel_id() == 555


def test_autocomplete_year_separators():
    i = make_interaction("4")
    names = [c.name for c in asyncio.run(bot.calendario_disciplina_autocomplete(i, ""))]
    assert names[0] == "──── 1º ano ────"
    assert names.index("──── 2º ano ────") == 6
    assert names.index("──── 3º ano ────") == 12
    names = [c.name for c in asyncio.run(bot.calendario_disciplina_autocomplete(i, "cálc"))]
    assert names == ["──── 1º ano ────", "Cálculo"]
    i = run("2", "add", "teste", "ano:1", "25/01/2027")
    assert "separador" in text(i)


def test_turno_and_observacoes():
    i = run("2", "add", "teste", "1103", "25/01/2027", "B", "Levar calculadora")
    embed = i.guild.get_channel.return_value.send.call_args.kwargs["embed"]
    assert [(f.name, f.value) for f in embed.fields][-2:] == [
        ("Turno", "B"), ("Observações", "Levar calculadora")
    ]
    # outro turno no mesmo dia é um evento diferente
    assert "Feito" in text(run("2", "add", "teste", "1103", "25/01/2027", "C"))
    assert "já existe" in text(run("2", "add", "teste", "1103", "25/01/2027", "B"))
    assert "Não encontrei" in text(run("2", "remove", "teste", "1103", "25/01/2027"))
    assert "Feito" in text(run("2", "remove", "teste", "1103", "25/01/2027", "B"))
    assert [e["turno"] for e in dm.get_calendar()] == ["C"]
