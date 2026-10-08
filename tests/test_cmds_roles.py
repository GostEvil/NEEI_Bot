"""Testes (com mocks) dos slash commands de roles/admin/verificacao de bot.py.

Nao liga ao Discord, nao toca em data/*.json nem no .env reais.
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Variaveis de ambiente falsas ANTES de importar config/bot
# (load_dotenv nao sobrepoe variaveis ja definidas).
os.environ["DISCORD_TOKEN"] = "fake-token"
os.environ["GUILD_ID"] = "111"
os.environ["MANAGER_IDS"] = "1,2"
os.environ["NEEI_ROLE_NAME"] = "NEEI"
os.environ["VERIFY_ROLE_ID"] = ""
os.environ["TARGET_CHANNEL_ID"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import discord  # noqa: E402

import config  # noqa: E402
import data_manager  # noqa: E402
import bot as botmod  # noqa: E402

MANAGER_ID = 1
ADMIN_ID = 50
NEEI_ID = 60
USER_ID = 70
TARGET_ID = 99


def run(coro):
    return asyncio.run(coro)


def cb(cmd):
    return cmd.callback


# ───────────────────────── fixtures / helpers ─────────────────────────

@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Redireciona data_manager para tmp e mocka escrita no .env."""
    monkeypatch.setattr(data_manager, "ADMINS_FILE", tmp_path / "admins.json")
    monkeypatch.setattr(data_manager, "LOGS_FILE", tmp_path / "logs.json")
    monkeypatch.setattr(data_manager, "CERT_CONFIG_FILE", tmp_path / "cert.json")
    monkeypatch.setenv("MANAGER_IDS", "1,2")
    monkeypatch.setenv("NEEI_ROLE_NAME", "NEEI")
    monkeypatch.setenv("VERIFY_ROLE_ID", "")
    set_key = MagicMock()
    monkeypatch.setattr(config, "set_verify_role_id", set_key)
    # Garantia extra: dotenv.set_key nunca escreve no .env real
    monkeypatch.setattr("dotenv.set_key", MagicMock())
    yield tmp_path


def make_role(name, rid=500, members=None):
    r = MagicMock()
    r.name = name
    r.id = rid
    r.mention = f"<@&{rid}>"
    r.members = members or []
    r.color = discord.Color.default()
    return r


def make_member(uid, roles=None, name=None):
    m = MagicMock()
    m.id = uid
    m.name = name or f"user{uid}"
    m.mention = f"<@{uid}>"
    m.roles = list(roles or [])
    m.add_roles = AsyncMock()
    m.remove_roles = AsyncMock()
    return m


def make_interaction(uid, roles=None, guild_roles=None, members=None):
    i = MagicMock()
    i.user = make_member(uid, roles)
    i.response.send_message = AsyncMock()
    g = MagicMock()
    g.roles = list(guild_roles or [])
    g.get_role = lambda rid: next((r for r in g.roles if r.id == rid), None)
    mm = members or {}
    g.get_member = lambda mid: mm.get(mid)
    i.guild = g
    return i


def sent(i):
    """(args, kwargs) da primeira chamada a send_message."""
    i.response.send_message.assert_awaited_once()
    return i.response.send_message.await_args


def text(i):
    a, k = sent(i)
    return a[0] if a else ""


def forbidden():
    return discord.Forbidden(MagicMock(status=403, reason="Forbidden"), "no perms")


def http_exc():
    return discord.HTTPException(MagicMock(status=500, reason="boom"), "boom")


def last_log():
    logs = data_manager.get_logs()
    return logs[-1] if logs else None


def caller(kind):
    """Devolve (uid, roles) para cada nivel de permissao."""
    neei = make_role("NEEI", 10)
    if kind == "manager":
        return MANAGER_ID, []
    if kind == "admin":
        data_manager.add_admin(str(ADMIN_ID))
        return ADMIN_ID, []
    if kind == "neei":
        return NEEI_ID, [neei]
    return USER_ID, []


# ───────────────────────── registo dos comandos ─────────────────────────

def test_commands_registered():
    names = {c.name for c in botmod.bot.tree.get_commands(guild=botmod.guild_obj)}
    for n in ["neeigive", "neeiremove", "admingive", "adminremove", "verify",
              "unverify", "config", "listadmin", "listneei"]:
        assert n in names


# ───────────────────────── get_user_role ─────────────────────────

@pytest.mark.parametrize("kind", ["manager", "admin", "neei", "user"])
def test_get_user_role(kind):
    uid, roles = caller(kind)
    i = make_interaction(uid, roles)
    assert botmod.get_user_role(i) == kind


# ───────────────────────── /neeigive + /neeiremove ─────────────────────────

class TestNeeiGive:
    cmd = staticmethod(lambda: cb(botmod.neeigive))

    @pytest.mark.parametrize("kind", ["user", "neei"])
    def test_no_permission(self, kind):
        uid, roles = caller(kind)
        i = make_interaction(uid, roles, [make_role("NEEI", 10)])
        t = make_member(TARGET_ID)
        run(self.cmd()(i, t))
        assert "permissão" in text(i)
        assert sent(i)[1]["ephemeral"] is True
        t.add_roles.assert_not_awaited()

    def test_role_missing(self):
        i = make_interaction(MANAGER_ID, guild_roles=[make_role("Outro")])
        t = make_member(TARGET_ID)
        run(self.cmd()(i, t))
        assert "Não foi encontrado" in text(i)
        t.add_roles.assert_not_awaited()

    def test_already_has(self):
        role = make_role("NEEI", 10)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID, [role])
        run(self.cmd()(i, t))
        assert "já tem" in text(i)
        t.add_roles.assert_not_awaited()

    @pytest.mark.parametrize("kind", ["manager", "admin"])
    def test_success(self, kind):
        uid, roles = caller(kind)
        role = make_role("NEEI", 10)
        i = make_interaction(uid, roles, [role])
        t = make_member(TARGET_ID)
        run(self.cmd()(i, t))
        t.add_roles.assert_awaited_once()
        assert t.add_roles.await_args.args[0] is role
        assert "sucesso" in text(i)
        lg = last_log()
        assert lg["action"] == "neeigive" and lg["actor_role"] == kind

    def test_forbidden(self):
        role = make_role("NEEI", 10)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID)
        t.add_roles.side_effect = forbidden()
        run(self.cmd()(i, t))
        assert "permissões suficientes" in text(i)
        assert last_log() is None

    def test_http_exception(self):
        role = make_role("NEEI", 10)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID)
        t.add_roles.side_effect = http_exc()
        run(self.cmd()(i, t))
        assert "erro inesperado" in text(i)


class TestNeeiRemove:
    cmd = staticmethod(lambda: cb(botmod.neeiremove))

    @pytest.mark.parametrize("kind", ["user", "neei"])
    def test_no_permission(self, kind):
        uid, roles = caller(kind)
        i = make_interaction(uid, roles, [make_role("NEEI", 10)])
        t = make_member(TARGET_ID)
        run(self.cmd()(i, t))
        assert "permissão" in text(i)
        t.remove_roles.assert_not_awaited()

    def test_role_missing(self):
        i = make_interaction(MANAGER_ID, guild_roles=[])
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert "Não foi encontrado" in text(i)

    def test_target_lacks_role(self):
        role = make_role("NEEI", 10)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID)
        run(self.cmd()(i, t))
        assert "não tem o cargo" in text(i)
        t.remove_roles.assert_not_awaited()

    @pytest.mark.parametrize("kind", ["manager", "admin"])
    def test_success(self, kind):
        uid, roles = caller(kind)
        role = make_role("NEEI", 10)
        i = make_interaction(uid, roles, [role])
        t = make_member(TARGET_ID, [role])
        run(self.cmd()(i, t))
        t.remove_roles.assert_awaited_once()
        assert "removido com sucesso" in text(i)
        assert last_log()["action"] == "neeiremove"

    def test_forbidden(self):
        role = make_role("NEEI", 10)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID, [role])
        t.remove_roles.side_effect = forbidden()
        run(self.cmd()(i, t))
        assert "permissões suficientes" in text(i)

    def test_http_exception(self):
        role = make_role("NEEI", 10)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID, [role])
        t.remove_roles.side_effect = http_exc()
        run(self.cmd()(i, t))
        assert "erro inesperado" in text(i)


# ───────────────────────── /admingive + /adminremove ─────────────────────────

class TestAdminGive:
    cmd = staticmethod(lambda: cb(botmod.admingive))

    @pytest.mark.parametrize("kind", ["user", "neei", "admin"])
    def test_only_manager(self, kind):
        uid, roles = caller(kind)
        i = make_interaction(uid, roles)
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert "Apenas os **Managers**" in text(i)
        assert not data_manager.is_admin(str(TARGET_ID))

    def test_target_is_manager(self):
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i, make_member(2)))
        assert "já é um **Manager**" in text(i)
        assert not data_manager.is_admin("2")

    def test_already_admin(self):
        data_manager.add_admin(str(TARGET_ID))
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert "já é um **Admin**" in text(i)
        assert data_manager.load_admins().count(str(TARGET_ID)) == 1

    def test_success(self):
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert data_manager.is_admin(str(TARGET_ID))
        assert "adicionado como **Admin**" in text(i)
        assert last_log()["action"] == "admingive"


class TestAdminRemove:
    cmd = staticmethod(lambda: cb(botmod.adminremove))

    @pytest.mark.parametrize("kind", ["user", "neei", "admin"])
    def test_only_manager(self, kind):
        uid, roles = caller(kind)
        data_manager.add_admin(str(TARGET_ID))
        i = make_interaction(uid, roles)
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert "Apenas os **Managers**" in text(i)
        assert data_manager.is_admin(str(TARGET_ID))

    def test_target_is_manager(self):
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i, make_member(2)))
        assert "não pode ser removido" in text(i)

    def test_not_admin(self):
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert "não é um **Admin**" in text(i)

    def test_success(self):
        data_manager.add_admin(str(TARGET_ID))
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert not data_manager.is_admin(str(TARGET_ID))
        assert "removidas" in text(i)
        assert last_log()["action"] == "adminremove"


# ───────────────────────── /verify + /unverify ─────────────────────────

class TestVerify:
    cmd = staticmethod(lambda: cb(botmod.verify))

    @pytest.mark.parametrize("kind", ["user", "neei"])
    def test_no_permission(self, kind):
        uid, roles = caller(kind)
        i = make_interaction(uid, roles)
        t = make_member(TARGET_ID)
        run(self.cmd()(i, t))
        assert "permissão" in text(i)
        t.add_roles.assert_not_awaited()

    def test_not_configured(self, monkeypatch):
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert "não está configurado" in text(i)

    def test_configured_role_not_in_guild(self, monkeypatch):
        monkeypatch.setenv("VERIFY_ROLE_ID", "777")
        i = make_interaction(MANAGER_ID, guild_roles=[])
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert "não está configurado" in text(i)

    def test_already_has(self, monkeypatch):
        monkeypatch.setenv("VERIFY_ROLE_ID", "777")
        role = make_role("Verificado", 777)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID, [role])
        run(self.cmd()(i, t))
        assert "já tem" in text(i)
        t.add_roles.assert_not_awaited()

    @pytest.mark.parametrize("kind", ["manager", "admin"])
    def test_success(self, monkeypatch, kind):
        monkeypatch.setenv("VERIFY_ROLE_ID", "777")
        uid, roles = caller(kind)
        role = make_role("Verificado", 777)
        i = make_interaction(uid, roles, [role])
        t = make_member(TARGET_ID)
        run(self.cmd()(i, t))
        t.add_roles.assert_awaited_once()
        assert "atribuído" in text(i)
        assert last_log()["action"] == "verify"

    def test_forbidden(self, monkeypatch):
        monkeypatch.setenv("VERIFY_ROLE_ID", "777")
        role = make_role("Verificado", 777)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID)
        t.add_roles.side_effect = forbidden()
        run(self.cmd()(i, t))
        assert "hierarquia" in text(i)

    def test_generic_error(self, monkeypatch):
        monkeypatch.setenv("VERIFY_ROLE_ID", "777")
        role = make_role("Verificado", 777)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID)
        t.add_roles.side_effect = RuntimeError("x")
        run(self.cmd()(i, t))
        assert "Ocorreu um erro" in text(i)


class TestUnverify:
    cmd = staticmethod(lambda: cb(botmod.unverify))

    @pytest.mark.parametrize("kind", ["user", "neei"])
    def test_no_permission(self, kind):
        uid, roles = caller(kind)
        i = make_interaction(uid, roles)
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert "permissão" in text(i)

    def test_not_configured(self):
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i, make_member(TARGET_ID)))
        assert "não está configurado" in text(i)

    def test_target_lacks_role(self, monkeypatch):
        monkeypatch.setenv("VERIFY_ROLE_ID", "777")
        role = make_role("Verificado", 777)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID)
        run(self.cmd()(i, t))
        assert "não tem o cargo" in text(i)
        t.remove_roles.assert_not_awaited()

    @pytest.mark.parametrize("kind", ["manager", "admin"])
    def test_success(self, monkeypatch, kind):
        monkeypatch.setenv("VERIFY_ROLE_ID", "777")
        uid, roles = caller(kind)
        role = make_role("Verificado", 777)
        i = make_interaction(uid, roles, [role])
        t = make_member(TARGET_ID, [role])
        run(self.cmd()(i, t))
        t.remove_roles.assert_awaited_once()
        assert "removida" in text(i)
        assert last_log()["action"] == "unverify"

    def test_forbidden(self, monkeypatch):
        monkeypatch.setenv("VERIFY_ROLE_ID", "777")
        role = make_role("Verificado", 777)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID, [role])
        t.remove_roles.side_effect = forbidden()
        run(self.cmd()(i, t))
        assert "permissões" in text(i)

    def test_generic_error(self, monkeypatch):
        monkeypatch.setenv("VERIFY_ROLE_ID", "777")
        role = make_role("Verificado", 777)
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        t = make_member(TARGET_ID, [role])
        t.remove_roles.side_effect = RuntimeError("x")
        run(self.cmd()(i, t))
        assert "Ocorreu um erro" in text(i)


# ───────────────────────── /config ─────────────────────────

class TestConfig:
    cmd = staticmethod(lambda: cb(botmod.config_command))

    @pytest.mark.parametrize("kind", ["user", "neei", "admin"])
    def test_only_manager(self, kind):
        uid, roles = caller(kind)
        i = make_interaction(uid, roles)
        run(self.cmd()(i, make_role("V", 777)))
        assert "Apenas os **Managers**" in text(i)
        config.set_verify_role_id.assert_not_called()

    def test_success(self):
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i, make_role("V", 777)))
        config.set_verify_role_id.assert_called_once_with(777)
        assert "configurado" in text(i)
        lg = last_log()
        assert lg["action"] == "config" and lg["target_id"] is None

    def test_set_key_error(self):
        config.set_verify_role_id.side_effect = OSError("disk")
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i, make_role("V", 777)))
        assert "erro ao guardar" in text(i)


# ───────────────────────── /listadmin ─────────────────────────

class TestListAdmin:
    cmd = staticmethod(lambda: cb(botmod.listadmin))

    def test_user_denied(self):
        i = make_interaction(USER_ID)
        run(self.cmd()(i))
        assert "NEEI" in text(i)
        assert sent(i)[1]["ephemeral"] is True

    @pytest.mark.parametrize("kind", ["neei", "admin", "manager"])
    def test_allowed(self, kind):
        uid, roles = caller(kind)
        data_manager.add_admin("50")
        data_manager.add_admin("51")
        m1 = make_member(1, name="boss")
        members = {1: m1, 50: make_member(50, name="adm")}
        i = make_interaction(uid, roles, members=members)
        run(self.cmd()(i))
        emb = sent(i)[1]["embed"]
        vals = {f.name: f.value for f in emb.fields}
        mg = next(v for k, v in vals.items() if "Managers" in k)
        ad = next(v for k, v in vals.items() if "Admins" in k)
        assert "boss" in mg and "ID: `2`" in mg  # 2 nao esta no servidor
        assert "adm" in ad and "ID: `51`" in ad

    def test_empty_admins(self):
        i = make_interaction(MANAGER_ID)
        run(self.cmd()(i))
        emb = sent(i)[1]["embed"]
        assert any("Nenhum admin" in f.value for f in emb.fields)


# ───────────────────────── /listneei ─────────────────────────

class TestListNeei:
    cmd = staticmethod(lambda: cb(botmod.listneei))

    def test_user_denied(self):
        i = make_interaction(USER_ID)
        run(self.cmd()(i))
        assert "Apenas membros" in text(i)

    def test_role_missing(self):
        i = make_interaction(MANAGER_ID, guild_roles=[])
        run(self.cmd()(i))
        assert "Não foi encontrado" in text(i)

    def test_no_members(self):
        i = make_interaction(MANAGER_ID, guild_roles=[make_role("NEEI", 10)])
        run(self.cmd()(i))
        assert "Nenhum membro" in text(i)

    @pytest.mark.parametrize("kind", ["neei", "admin", "manager"])
    def test_success(self, kind):
        uid, roles = caller(kind)
        role = make_role("NEEI", 10, members=[make_member(k) for k in range(100, 103)])
        i = make_interaction(uid, roles, [role])
        run(self.cmd()(i))
        emb = sent(i)[1]["embed"]
        assert "user100" in emb.description
        assert "Total: 3" in emb.footer.text
        assert not emb.fields

    def test_truncated_over_25(self):
        role = make_role("NEEI", 10, members=[make_member(k) for k in range(200, 230)])
        i = make_interaction(MANAGER_ID, guild_roles=[role])
        run(self.cmd()(i))
        emb = sent(i)[1]["embed"]
        assert emb.description.count("•") == 25
        assert emb.fields and "truncada" in emb.fields[0].name
