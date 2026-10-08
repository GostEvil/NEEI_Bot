"""
tests/test_cmds_misc.py — Testes (com mocks) de /sayimage, /delete, /logs,
/certconfig (addyear, removeyear, listyears, alertchannel) e data_manager.

Nada toca em dados reais: data_manager é redirecionado para tmp_path e as
variáveis de ambiente são definidas antes de importar bot (load_dotenv não
sobrepõe variáveis já definidas; o .env real nunca é escrito).
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ["GUILD_ID"] = "999"
os.environ["MANAGER_IDS"] = "1,10"
os.environ["NEEI_ROLE_NAME"] = "NEEI"
os.environ["DISCORD_TOKEN"] = "x"
os.environ.pop("TARGET_CHANNEL_ID", None)

import discord  # noqa: E402

import bot  # noqa: E402
import data_manager as dm  # noqa: E402

MANAGER, ADMIN, NEEI, USER = "1", "2", "3", "4"


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(dm, "ADMINS_FILE", tmp_path / "admins.json")
    monkeypatch.setattr(dm, "LOGS_FILE", tmp_path / "logs.json")
    monkeypatch.setattr(dm, "CERT_CONFIG_FILE", tmp_path / "cert_config.json")
    monkeypatch.delenv("TARGET_CHANNEL_ID", raising=False)
    dm.add_admin(ADMIN)
    return tmp_path


def make_interaction(uid: str, neei: bool = False):
    i = MagicMock()
    i.user.id = int(uid)
    i.user.roles = [MagicMock(**{"name": "NEEI"})] if neei else []
    i.response.send_message = AsyncMock()
    i.response.defer = AsyncMock()
    i.followup.send = AsyncMock()
    i.guild = MagicMock()
    i.channel = MagicMock()
    i.channel.send = AsyncMock()
    i.channel.purge = AsyncMock(return_value=[1, 2, 3])
    return i


def forbidden():
    return discord.Forbidden(MagicMock(status=403, reason="Forbidden"), "no perms")


def msg(i):
    """Texto da primeira resposta."""
    args, kwargs = i.response.send_message.call_args
    return args[0] if args else kwargs.get("content", "")


def ephemeral(i):
    return i.response.send_message.call_args.kwargs.get("ephemeral", False)


def attachment(ctype="image/png"):
    a = MagicMock()
    a.content_type = ctype
    a.to_file = AsyncMock(return_value="FILE")
    return a


def last_log():
    return dm.get_logs()[-1]


# ═════════════════════════════════════════════════════════════════════════════
# /sayimage  (nota: não existe /say em bot.py, apenas /sayimage)
# ═════════════════════════════════════════════════════════════════════════════

class TestSayImage:
    cb = staticmethod(lambda *a, **k: bot.sayimage.callback(*a, **k))

    @pytest.mark.parametrize("uid", [USER, NEEI])
    async def test_no_permission(self, uid):
        i = make_interaction(uid, neei=(uid == NEEI))
        await self.cb(i, attachment())
        assert "permissão" in msg(i) and ephemeral(i)
        i.channel.send.assert_not_called()
        assert dm.get_logs() == []

    @pytest.mark.parametrize("ctype", [None, "", "application/pdf", "text/plain"])
    async def test_not_image(self, ctype):
        i = make_interaction(ADMIN)
        await self.cb(i, attachment(ctype))
        assert "imagem válida" in msg(i)
        i.channel.send.assert_not_called()

    @pytest.mark.parametrize("uid,role", [(ADMIN, "admin"), (MANAGER, "manager")])
    async def test_success_current_channel(self, uid, role):
        i = make_interaction(uid)
        i.channel.mention = "#geral"
        await self.cb(i, attachment())
        i.channel.send.assert_awaited_once_with(file="FILE")
        assert "#geral" in msg(i) and ephemeral(i)
        assert last_log()["action"] == "sayimage" and last_log()["actor_role"] == role

    async def test_target_channel_from_env_cached(self, monkeypatch):
        monkeypatch.setenv("TARGET_CHANNEL_ID", "555")
        i = make_interaction(ADMIN)
        target = MagicMock(mention="#alvo")
        target.send = AsyncMock()
        i.guild.get_channel.return_value = target
        await self.cb(i, attachment())
        target.send.assert_awaited_once()
        i.channel.send.assert_not_called()

    async def test_target_channel_fetch_fallback(self, monkeypatch):
        monkeypatch.setenv("TARGET_CHANNEL_ID", "555")
        i = make_interaction(ADMIN)
        target = MagicMock(mention="#alvo")
        target.send = AsyncMock()
        i.guild.get_channel.return_value = None
        i.guild.fetch_channel = AsyncMock(return_value=target)
        await self.cb(i, attachment())
        target.send.assert_awaited_once()

    async def test_target_channel_not_found(self, monkeypatch):
        monkeypatch.setenv("TARGET_CHANNEL_ID", "555")
        i = make_interaction(ADMIN)
        i.guild.get_channel.return_value = None
        i.guild.fetch_channel = AsyncMock(side_effect=discord.NotFound(MagicMock(status=404, reason="x"), "nf"))
        await self.cb(i, attachment())
        assert "555" in msg(i)
        i.channel.send.assert_not_called()

    async def test_send_forbidden_is_handled(self):
        """BUG: Forbidden no channel.send não é tratado -> exceção, sem resposta ao utilizador."""
        i = make_interaction(ADMIN)
        i.channel.send = AsyncMock(side_effect=forbidden())
        await self.cb(i, attachment())
        i.response.send_message.assert_awaited_once()
        assert "❌" in msg(i)

    async def test_to_file_failure_is_handled(self):
        """BUG: falha em download do anexo (HTTPException) não é tratada."""
        i = make_interaction(ADMIN)
        a = attachment()
        a.to_file = AsyncMock(side_effect=discord.HTTPException(MagicMock(status=500, reason="x"), "boom"))
        await self.cb(i, a)
        i.response.send_message.assert_awaited_once()


# ═════════════════════════════════════════════════════════════════════════════
# /delete
# ═════════════════════════════════════════════════════════════════════════════

class TestDelete:
    cb = staticmethod(lambda *a, **k: bot.delete_messages.callback(*a, **k))

    @pytest.mark.parametrize("uid", [ADMIN, NEEI, USER])
    async def test_only_managers(self, uid):
        i = make_interaction(uid)
        await self.cb(i, 5)
        assert "Managers" in msg(i) and ephemeral(i)
        i.channel.purge.assert_not_called()

    @pytest.mark.parametrize("n", [0, -1, 101, 10_000])
    async def test_invalid_quantity(self, n):
        i = make_interaction(MANAGER)
        await self.cb(i, n)
        assert "entre 1 e 100" in msg(i)
        i.channel.purge.assert_not_called()

    @pytest.mark.parametrize("n", [1, 100])
    async def test_boundaries_ok(self, n):
        i = make_interaction(MANAGER)
        await self.cb(i, n)
        i.channel.purge.assert_awaited_once_with(limit=n)
        i.response.defer.assert_awaited_once_with(ephemeral=True)
        assert "**3**" in i.followup.send.call_args.args[0]
        assert last_log()["action"] == "delete" and "3" in last_log()["details"]

    async def test_forbidden(self):
        i = make_interaction(MANAGER)
        i.channel.purge = AsyncMock(side_effect=forbidden())
        await self.cb(i, 5)
        assert "Manage Messages" in i.followup.send.call_args.args[0]
        assert dm.get_logs() == []

    async def test_generic_error(self):
        i = make_interaction(MANAGER)
        i.channel.purge = AsyncMock(side_effect=RuntimeError("boom"))
        await self.cb(i, 5)
        assert "boom" in i.followup.send.call_args.args[0]


# ═════════════════════════════════════════════════════════════════════════════
# /logs
# ═════════════════════════════════════════════════════════════════════════════

class TestLogs:
    cb = staticmethod(lambda *a, **k: bot.logs_command.callback(*a, **k))

    def seed(self):
        dm.add_log(MANAGER, "manager", "admingive", ADMIN, "d1")
        dm.add_log(ADMIN, "admin", "neeigive", NEEI, "d2")
        dm.add_log(NEEI, "neei", "something", None, "")

    @pytest.mark.parametrize("uid", [NEEI, USER])
    async def test_permission(self, uid):
        i = make_interaction(uid, neei=(uid == NEEI))
        await self.cb(i, "all")
        assert "permissão" in msg(i) and ephemeral(i)

    async def test_empty(self):
        i = make_interaction(MANAGER)
        await self.cb(i, "all")
        assert "Não existem logs" in msg(i)

    @pytest.mark.parametrize("grp,expected", [
        ("manager", 1),
        ("admin", 2),   # actor admin + action admingive
        ("neei", 2),    # actor neei + action neeigive
        ("all", 3),
    ])
    async def test_filters(self, grp, expected):
        self.seed()
        i = make_interaction(ADMIN)
        await self.cb(i, grp)
        desc = i.response.send_message.call_args.kwargs["embed"].description
        assert len(desc.splitlines()) == expected

    async def test_choice_object_accepted(self):
        self.seed()
        i = make_interaction(MANAGER)
        await self.cb(i, discord.app_commands.Choice(name="All", value="all"))
        assert len(i.response.send_message.call_args.kwargs["embed"].description.splitlines()) == 3

    async def test_unknown_group_reports_no_logs(self):
        self.seed()
        i = make_interaction(MANAGER)
        await self.cb(i, "bogus")
        assert "Desconhecido" in msg(i)

    async def test_most_recent_first(self):
        self.seed()
        i = make_interaction(MANAGER)
        await self.cb(i, "all")
        first = i.response.send_message.call_args.kwargs["embed"].description.splitlines()[0]
        assert "something" in first

    @pytest.mark.parametrize("page,expected_title", [(1, "1/3"), (2, "2/3"), (3, "3/3"),
                                                      (0, "1/3"), (-5, "1/3"), (99, "3/3")])
    async def test_pagination(self, page, expected_title):
        for k in range(60):
            dm.add_log(MANAGER, "manager", "x", None, f"n{k}")
        i = make_interaction(MANAGER)
        await self.cb(i, "all", page)
        emb = i.response.send_message.call_args.kwargs["embed"]
        assert expected_title in emb.title
        assert len(emb.description) <= 4096

    async def test_page_last_has_remainder(self):
        for k in range(60):
            dm.add_log(MANAGER, "manager", "x", None, f"n{k}")
        i = make_interaction(MANAGER)
        await self.cb(i, "all", 3)
        assert len(i.response.send_message.call_args.kwargs["embed"].description.splitlines()) == 10

    async def test_malformed_timestamp_does_not_crash(self):
        """BUG: timestamp inválido num log -> ValueError sem resposta."""
        dm.LOGS_FILE.write_text(json.dumps([{
            "timestamp": "lixo", "actor_id": "1", "actor_role": "manager",
            "action": "x", "target_id": None, "details": ""}]))
        i = make_interaction(MANAGER)
        await self.cb(i, "all")
        i.response.send_message.assert_awaited_once()

    async def test_entry_missing_keys_does_not_crash(self):
        """Entrada de log antiga/incompleta (sem actor_role)."""
        dm.LOGS_FILE.write_text(json.dumps([{"timestamp": "2025-01-01T10:00:00", "action": "x"}]))
        i = make_interaction(MANAGER)
        await self.cb(i, "manager")
        i.response.send_message.assert_awaited_once()


# ═════════════════════════════════════════════════════════════════════════════
# /certconfig
# ═════════════════════════════════════════════════════════════════════════════

class TestCertAddYear:
    cb = staticmethod(lambda *a, **k: bot.certconfig_addyear.callback(*a, **k))

    @pytest.mark.parametrize("uid", [ADMIN, NEEI, USER])
    async def test_only_managers(self, uid):
        i = make_interaction(uid)
        await self.cb(i, "2025/2026")
        assert "Managers" in msg(i)
        assert dm.get_allowed_years() == []

    @pytest.mark.parametrize("bad", ["2025", "2025-2026", "25/26", "2025/26", "abcd/efgh",
                                     "2025/2026/2027", "", "  ", "2025 / 2026", "20255/2026",
                                     "2025/2026\n"[:-1] + "x"])
    async def test_invalid_format(self, bad):
        i = make_interaction(MANAGER)
        await self.cb(i, bad)
        assert "Formato inválido" in msg(i) and ephemeral(i)
        assert dm.get_allowed_years() == []

    async def test_success_and_strip(self):
        i = make_interaction(MANAGER)
        await self.cb(i, "  2025/2026 ")
        assert dm.get_allowed_years() == ["2025/2026"]
        assert "2025/2026" in msg(i) and not ephemeral(i)
        assert last_log()["action"] == "certconfig_addyear"

    async def test_duplicate(self):
        i = make_interaction(MANAGER)
        await self.cb(i, "2025/2026")
        i2 = make_interaction(MANAGER)
        await self.cb(i2, "2025/2026")
        assert "já está" in msg(i2) and ephemeral(i2)
        assert dm.get_allowed_years() == ["2025/2026"]
        assert len(dm.get_logs()) == 1

    @pytest.mark.parametrize("bad", ["2025/2025", "2026/2025", "2025/2030", "0000/0000"])
    async def test_non_consecutive_years_rejected(self, bad):
        """BUG: só valida \\d{4}/\\d{4}; aceita anos letivos impossíveis."""
        i = make_interaction(MANAGER)
        await self.cb(i, bad)
        assert dm.get_allowed_years() == []

    async def test_unicode_digits_rejected(self):
        """BUG: \\d aceita dígitos Unicode (ex.: árabe-índicos); o parser nunca os reconheceria."""
        i = make_interaction(MANAGER)
        await self.cb(i, "٢٠٢٥/٢٠٢٦")
        assert dm.get_allowed_years() == []


class TestCertRemoveYear:
    cb = staticmethod(lambda *a, **k: bot.certconfig_removeyear.callback(*a, **k))

    @pytest.mark.parametrize("uid", [ADMIN, NEEI, USER])
    async def test_only_managers(self, uid):
        dm.add_allowed_year("2025/2026")
        i = make_interaction(uid)
        await self.cb(i, "2025/2026")
        assert "Managers" in msg(i)
        assert dm.get_allowed_years() == ["2025/2026"]

    async def test_not_in_list(self):
        i = make_interaction(MANAGER)
        await self.cb(i, "2025/2026")
        assert "não está" in msg(i) and ephemeral(i)

    async def test_success_remaining(self):
        dm.add_allowed_year("2025/2026")
        dm.add_allowed_year("2026/2027")
        i = make_interaction(MANAGER)
        await self.cb(i, " 2025/2026 ")
        assert dm.get_allowed_years() == ["2026/2027"]
        assert "2026/2027" in msg(i)
        assert last_log()["action"] == "certconfig_removeyear"

    async def test_remove_last_shows_disabled_message(self):
        dm.add_allowed_year("2025/2026")
        i = make_interaction(MANAGER)
        await self.cb(i, "2025/2026")
        assert "desativada" in msg(i)
        assert dm.get_allowed_years() == []


class TestCertListYears:
    cb = staticmethod(lambda *a, **k: bot.certconfig_listyears.callback(*a, **k))

    @pytest.mark.parametrize("uid", [NEEI, USER])
    async def test_permission(self, uid):
        i = make_interaction(uid, neei=(uid == NEEI))
        await self.cb(i)
        assert "permissão" in msg(i)

    @pytest.mark.parametrize("uid", [ADMIN, MANAGER])
    async def test_empty(self, uid):
        i = make_interaction(uid)
        await self.cb(i)
        emb = i.response.send_message.call_args.kwargs["embed"]
        assert "Nenhum configurado" in emb.fields[0].value
        assert "não configurado" in emb.fields[1].value
        assert ephemeral(i)

    async def test_with_data(self):
        dm.add_allowed_year("2025/2026")
        dm.set_cert_alert_channel_id(777)
        i = make_interaction(MANAGER)
        await self.cb(i)
        emb = i.response.send_message.call_args.kwargs["embed"]
        assert "2025/2026" in emb.fields[0].value
        assert "<#777>" in emb.fields[1].value


class TestCertAlertChannel:
    cb = staticmethod(lambda *a, **k: bot.certconfig_alertchannel.callback(*a, **k))

    @pytest.mark.parametrize("uid", [ADMIN, NEEI, USER])
    async def test_only_managers(self, uid):
        i = make_interaction(uid)
        await self.cb(i, MagicMock(id=5))
        assert "Managers" in msg(i)
        assert dm.get_cert_alert_channel_id() is None

    async def test_success(self):
        i = make_interaction(MANAGER)
        ch = MagicMock(id=123, mention="#alertas")
        await self.cb(i, ch)
        assert dm.get_cert_alert_channel_id() == 123
        assert "#alertas" in msg(i)
        assert last_log()["action"] == "certconfig_alertchannel"

    async def test_group_registered(self):
        assert bot.cert_config_group.name == "certconfig"
        names = {c.name for c in bot.cert_config_group.commands}
        assert names == {"addyear", "removeyear", "listyears", "alertchannel"}

    async def test_listyears_description_matches_permission(self):
        """Inconsistência: grupo diz 'Apenas Managers' mas listyears permite Admins."""
        # apenas documenta: admin consegue (comportamento atual) — ver relatório
        i = make_interaction(ADMIN)
        await bot.certconfig_listyears.callback(i)
        assert "embed" in i.response.send_message.call_args.kwargs


# ═════════════════════════════════════════════════════════════════════════════
# data_manager
# ═════════════════════════════════════════════════════════════════════════════

class TestDataManagerAdmins:
    def test_add_remove_is_admin(self):
        assert dm.is_admin(ADMIN)
        assert dm.add_admin("77") is True
        assert dm.add_admin("77") is False
        assert dm.is_admin("77")
        assert dm.remove_admin("77") is True
        assert dm.remove_admin("77") is False
        assert not dm.is_admin("77")

    def test_creates_files_and_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dm, "ADMINS_FILE", tmp_path / "sub" / "a.json")
        assert dm.load_admins() == []
        assert (tmp_path / "sub" / "a.json").exists()

    def test_int_vs_str_ids(self):
        assert not dm.is_admin(int(ADMIN))  # API espera str

    def test_missing_admins_key(self):
        dm.ADMINS_FILE.write_text("{}")
        assert dm.load_admins() == []

    def test_corrupt_admins_file_does_not_crash(self):
        """BUG: ficheiro admins.json corrompido -> JSONDecodeError em todos os comandos (logs/cert fazem fallback)."""
        dm.ADMINS_FILE.write_text("{not json")
        assert dm.load_admins() == []


class TestDataManagerLogs:
    def test_empty(self):
        assert dm.get_logs() == []

    def test_add_and_order_and_fields(self):
        dm.add_log("1", "manager", "a", "2", "ç unicode")
        dm.add_log("1", "manager", "b")
        logs = dm.get_logs()
        assert [l["action"] for l in logs] == ["a", "b"]
        assert logs[0]["details"] == "ç unicode" and logs[1]["target_id"] is None
        assert "T" in logs[0]["timestamp"]

    def test_corrupt_file_recovers_on_add(self):
        dm.LOGS_FILE.write_text("garbage")
        assert dm.get_logs() == []
        dm.add_log("1", "manager", "a")
        assert len(dm.get_logs()) == 1

    def test_logs_file_not_a_list(self):
        """Ficheiro JSON válido mas não-lista ({}) -> add_log falha com AttributeError."""
        dm.LOGS_FILE.write_text("{}")
        dm.add_log("1", "manager", "a")
        assert isinstance(dm.get_logs(), list)


class TestDataManagerCert:
    def test_defaults(self):
        assert dm.get_allowed_years() == []
        assert dm.get_cert_alert_channel_id() is None

    def test_years_add_remove(self):
        assert dm.add_allowed_year("2025/2026") is True
        assert dm.add_allowed_year("2025/2026") is False
        assert dm.add_allowed_year("2026/2027") is True
        assert dm.get_allowed_years() == ["2025/2026", "2026/2027"]
        assert dm.remove_allowed_year("2025/2026") is True
        assert dm.remove_allowed_year("2025/2026") is False
        assert dm.get_allowed_years() == ["2026/2027"]

    def test_alert_channel_set_get_clear(self):
        dm.set_cert_alert_channel_id(42)
        assert dm.get_cert_alert_channel_id() == 42
        dm.set_cert_alert_channel_id(None)
        assert dm.get_cert_alert_channel_id() is None

    def test_alert_channel_stored_as_string(self):
        dm.CERT_CONFIG_FILE.write_text(json.dumps({"allowed_years": [], "alert_channel_id": "55"}))
        assert dm.get_cert_alert_channel_id() == 55

    def test_old_file_missing_keys(self):
        dm.CERT_CONFIG_FILE.write_text("{}")
        assert dm.get_allowed_years() == []
        assert dm.get_cert_alert_channel_id() is None

    def test_corrupt_file_falls_back(self):
        dm.CERT_CONFIG_FILE.write_text("%%%")
        assert dm.get_allowed_years() == []

    def test_corrupt_then_add_overwrites_cleanly(self):
        dm.CERT_CONFIG_FILE.write_text("%%%")
        assert dm.add_allowed_year("2025/2026") is True
        assert dm.get_allowed_years() == ["2025/2026"]

    def test_default_dict_not_mutated(self):
        """O fallback não deve partilhar a lista do dict por defeito (shallow copy)."""
        dm.CERT_CONFIG_FILE.write_text("%%%")
        dm._load_cert_config()["allowed_years"].append("X")
        dm.CERT_CONFIG_FILE.write_text("%%%")
        assert dm._load_cert_config()["allowed_years"] == []

    def test_alert_channel_garbage_value(self):
        """BUG: valor não numérico em alert_channel_id -> ValueError não tratado."""
        dm.CERT_CONFIG_FILE.write_text(json.dumps({"allowed_years": [], "alert_channel_id": "abc"}))
        assert dm.get_cert_alert_channel_id() is None

    def test_real_data_untouched(self):
        assert "data" not in str(dm.ADMINS_FILE.parent) or "pytest" in str(dm.ADMINS_FILE)


# ─── Runner de testes async (sem depender de pytest-asyncio) ─────────────────

def _sync(fn):
    import asyncio, functools

    @functools.wraps(fn)
    def wrapper(*a, **k):
        return asyncio.run(fn(*a, **k))
    return wrapper


def _wrap_async_tests():
    import inspect
    for obj in list(globals().values()):
        if inspect.isclass(obj) and obj.__name__.startswith("Test"):
            for name, fn in list(vars(obj).items()):
                if name.startswith("test") and inspect.iscoroutinefunction(fn):
                    setattr(obj, name, _sync(fn))


_wrap_async_tests()
