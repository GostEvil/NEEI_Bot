"""Testes (com mocks) do fluxo /verificacao1 (verificacao1._handle_verificacao1).

Nao liga ao Discord, nao toca em data/*.json nem no .env reais:
- verify_certificate e mockado;
- data_manager.CERT_CONFIG_FILE aponta para um ficheiro temporario;
- config le variaveis de ambiente (monkeypatch).
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DISCORD_TOKEN", "fake-token")
os.environ.setdefault("GUILD_ID", "111")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import discord  # noqa: E402

import data_manager  # noqa: E402
import verificacao1 as v1  # noqa: E402

CERT_CHANNEL = 500
LOG_CHANNEL = 600
ALERT_CHANNEL = 700
ROLE_ID = 900
USER_ID = 42

VALID_RESULT = {
    "valid": True,
    "name": "Joao Silva",
    "mechanographic_number": "a64716",
    "identification_document": "12345678",
    "academic_year": "2025/2026",
    "course": "Engenharia Informatica",
    "institution": "Instituto Politecnico de Braganca",
    "nickname": "Joao Silva (a64716)",
}


def run(coro):
    return asyncio.run(coro)


def _forbidden():
    resp = MagicMock()
    resp.status = 403
    resp.reason = "Forbidden"
    return discord.Forbidden(resp, "Missing Permissions")


class Env:
    """Agrupa os mocks de um teste."""

    def __init__(self, tmp_path, monkeypatch):
        # data_manager -> ficheiro temporario
        self.cfg_file = tmp_path / "cert_config.json"
        monkeypatch.setattr(data_manager, "CERT_CONFIG_FILE", self.cfg_file)
        self.set_cfg(allowed_years=[], alert_channel_id=ALERT_CHANNEL)

        # config via env
        for k in ("CERTIFICATE_VERIFICATION_CHANNEL_ID", "VERIFY_ROLE_ID"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("CERTIFICATE_VERIFICATION_LOG_CHANNEL_ID", str(LOG_CHANNEL))
        monkeypatch.setenv("VERIFY_ROLE_ID", str(ROLE_ID))
        self.monkeypatch = monkeypatch

        # Discord mocks
        self.log_channel = MagicMock()
        self.log_channel.send = AsyncMock()
        self.alert_channel = MagicMock()
        self.alert_channel.send = AsyncMock()

        self.role = MagicMock()
        self.role.name = "Verificado"

        self.member = MagicMock()
        self.member.id = USER_ID
        self.member.name = "user"
        self.member.display_name = "OldName"
        self.member.roles = []
        self.member.edit = AsyncMock()
        self.member.add_roles = AsyncMock()

        channels = {LOG_CHANNEL: self.log_channel, ALERT_CHANNEL: self.alert_channel}
        self.guild = MagicMock()
        self.guild.get_channel = MagicMock(side_effect=lambda cid: channels.get(cid))
        self.guild.fetch_channel = AsyncMock(side_effect=discord.NotFound(MagicMock(status=404), "nf"))
        self.guild.get_role = MagicMock(side_effect=lambda rid: self.role if rid == ROLE_ID else None)
        self.guild.get_member = MagicMock(return_value=self.member)

        self.interaction = MagicMock()
        self.interaction.channel_id = CERT_CHANNEL
        self.interaction.channel = "cert-channel"
        self.interaction.user = MagicMock()
        self.interaction.user.id = USER_ID
        self.interaction.user.mention = f"<@{USER_ID}>"
        self.interaction.guild = self.guild
        self.interaction.response.send_message = AsyncMock()
        self.interaction.response.defer = AsyncMock()
        self.interaction.followup.send = AsyncMock()

        self.attachment = MagicMock()
        self.attachment.read = AsyncMock(return_value=b"%PDF-fake")
        self.attachment.content_type = "application/pdf"
        self.attachment.filename = "cert.pdf"

    def set_cfg(self, **kw):
        self.cfg_file.write_text(json.dumps(kw), encoding="utf-8")

    def handle(self, result=None, side_effect=None):
        vc = AsyncMock(return_value=result, side_effect=side_effect)
        self.vc = vc
        with patch.object(v1, "verify_certificate", vc):
            run(v1._handle_verificacao1(self.interaction, self.attachment))

    def followup_titles(self):
        titles = []
        for c in self.interaction.followup.send.call_args_list:
            emb = c.kwargs.get("embed")
            if emb is not None:
                titles.append(emb.title)
        return titles


@pytest.fixture
def env(tmp_path, monkeypatch):
    return Env(tmp_path, monkeypatch)


# ─── Sucesso ─────────────────────────────────────────────────────────────────


def test_valid_certificate_sets_nickname_and_role(env):
    env.handle(dict(VALID_RESULT))

    env.interaction.response.defer.assert_awaited_once()
    assert "✅ Certificado Verificado" in env.followup_titles()
    env.member.edit.assert_awaited_once()
    assert env.member.edit.await_args.kwargs["nick"] == "Joao Silva (a64716)"
    env.member.add_roles.assert_awaited_once()
    assert env.member.add_roles.await_args.args[0] is env.role
    env.guild.get_role.assert_called_with(ROLE_ID)
    # log privado enviado, verde
    env.log_channel.send.assert_awaited_once()
    emb = env.log_channel.send.await_args.kwargs["embed"]
    assert "Validado" in [f.value for f in emb.fields][-1]
    # sem alerta de ano
    env.alert_channel.send.assert_not_awaited()


def test_valid_certificate_no_allowed_years_passes_none(env):
    env.handle(dict(VALID_RESULT))
    assert env.vc.await_args.kwargs["allowed_years"] is None
    assert env.vc.await_args.kwargs["filename"] == "cert.pdf"
    assert env.vc.await_args.kwargs["mime_type"] == "application/pdf"


def test_allowed_years_forwarded(env):
    env.set_cfg(allowed_years=["2025/2026"], alert_channel_id=ALERT_CHANNEL)
    env.handle(dict(VALID_RESULT))
    assert env.vc.await_args.kwargs["allowed_years"] == ["2025/2026"]


def test_nickname_already_correct_skips_edit_but_still_assigns_role(env):
    env.member.display_name = "Joao Silva (a64716)"
    env.handle(dict(VALID_RESULT))
    env.member.edit.assert_not_awaited()
    env.member.add_roles.assert_awaited_once()


def test_member_already_has_role_not_reassigned(env):
    env.member.roles = [env.role]
    env.handle(dict(VALID_RESULT))
    env.member.add_roles.assert_not_awaited()
    env.member.edit.assert_awaited_once()


# ─── Role ────────────────────────────────────────────────────────────────────


def test_role_not_configured(env, monkeypatch):
    monkeypatch.delenv("VERIFY_ROLE_ID", raising=False)
    env.handle(dict(VALID_RESULT))
    env.member.add_roles.assert_not_awaited()
    env.guild.get_role.assert_not_called()
    # nickname e resposta de sucesso continuam a funcionar
    env.member.edit.assert_awaited_once()
    assert "✅ Certificado Verificado" in env.followup_titles()


def test_role_not_found_in_guild(env, monkeypatch):
    monkeypatch.setenv("VERIFY_ROLE_ID", "12345")  # nao existe no guild
    env.handle(dict(VALID_RESULT))
    env.guild.get_role.assert_called_with(12345)
    env.member.add_roles.assert_not_awaited()
    env.member.edit.assert_awaited_once()


def test_role_forbidden_sends_ephemeral_warning(env):
    env.member.add_roles.side_effect = _forbidden()
    env.handle(dict(VALID_RESULT))
    env.member.add_roles.assert_awaited_once()
    warnings = [
        c for c in env.interaction.followup.send.call_args_list
        if c.kwargs.get("ephemeral") and "cargo" in (c.args[0] if c.args else "")
    ]
    assert len(warnings) == 1


def test_role_http_exception_is_swallowed(env):
    resp = MagicMock(status=500, reason="err")
    env.member.add_roles.side_effect = discord.HTTPException(resp, "boom")
    env.handle(dict(VALID_RESULT))  # nao deve levantar
    env.member.add_roles.assert_awaited_once()


def test_nickname_forbidden_still_assigns_role(env):
    env.member.edit.side_effect = _forbidden()
    env.handle(dict(VALID_RESULT))
    env.member.add_roles.assert_awaited_once()
    warnings = [
        c for c in env.interaction.followup.send.call_args_list
        if c.kwargs.get("ephemeral") and "nickname" in (c.args[0] if c.args else "")
    ]
    assert len(warnings) == 1


def test_member_not_in_cache_skips_nickname_and_role(env):
    """Documenta comportamento: get_member None -> sucesso anunciado mas nada aplicado."""
    env.guild.get_member.return_value = None
    env.handle(dict(VALID_RESULT))
    env.member.edit.assert_not_awaited()
    env.member.add_roles.assert_not_awaited()
    assert "✅ Certificado Verificado" in env.followup_titles()


# ─── Canal errado ────────────────────────────────────────────────────────────


def test_wrong_channel(env, monkeypatch):
    monkeypatch.setenv("CERTIFICATE_VERIFICATION_CHANNEL_ID", str(CERT_CHANNEL))
    env.interaction.channel_id = 1
    env.handle(dict(VALID_RESULT))
    env.interaction.response.send_message.assert_awaited_once()
    assert env.interaction.response.send_message.await_args.kwargs["ephemeral"] is True
    env.interaction.response.defer.assert_not_awaited()
    env.vc.assert_not_awaited()
    env.member.edit.assert_not_awaited()
    env.member.add_roles.assert_not_awaited()


def test_right_channel_configured(env, monkeypatch):
    monkeypatch.setenv("CERTIFICATE_VERIFICATION_CHANNEL_ID", str(CERT_CHANNEL))
    env.handle(dict(VALID_RESULT))
    env.interaction.response.send_message.assert_not_awaited()
    env.member.add_roles.assert_awaited_once()


# ─── Ano letivo ──────────────────────────────────────────────────────────────


def test_year_mismatch_sends_alert_and_no_role(env):
    env.set_cfg(allowed_years=["2025/2026"], alert_channel_id=ALERT_CHANNEL)
    result = {
        "valid": False,
        "year_mismatch": True,
        "academic_year": "2023/2024",
        "name": "Joao Silva",
        "mechanographic_number": "a64716",
        "reason": "ano errado",
    }
    env.handle(result)
    assert "❌ Verificação sem sucesso" in env.followup_titles()
    env.alert_channel.send.assert_awaited_once()
    emb = env.alert_channel.send.await_args.kwargs["embed"]
    values = " ".join(f.value for f in emb.fields)
    assert "2023/2024" in values and "2025/2026" in values
    env.log_channel.send.assert_awaited_once()
    env.member.edit.assert_not_awaited()
    env.member.add_roles.assert_not_awaited()


def test_year_mismatch_alert_channel_not_configured(env):
    env.set_cfg(allowed_years=["2025/2026"], alert_channel_id=None)
    env.handle({"valid": False, "year_mismatch": True, "academic_year": None, "reason": "x"})
    env.alert_channel.send.assert_not_awaited()
    env.log_channel.send.assert_awaited_once()  # log privado continua
    env.member.add_roles.assert_not_awaited()


def test_year_mismatch_alert_forbidden_does_not_break(env):
    env.set_cfg(allowed_years=["2025/2026"], alert_channel_id=ALERT_CHANNEL)
    env.alert_channel.send.side_effect = _forbidden()
    env.handle({"valid": False, "year_mismatch": True, "academic_year": "2020/2021", "reason": "x"})
    env.log_channel.send.assert_awaited_once()


# ─── Inválido / erro ─────────────────────────────────────────────────────────


def test_invalid_certificate(env):
    env.handle({"valid": False, "reason": "O documento nao e certificado."})
    assert "❌ Verificação sem sucesso" in env.followup_titles()
    env.alert_channel.send.assert_not_awaited()
    env.log_channel.send.assert_awaited_once()
    emb = env.log_channel.send.await_args.kwargs["embed"]
    assert any("certificado" in f.value for f in emb.fields)
    env.member.edit.assert_not_awaited()
    env.member.add_roles.assert_not_awaited()


def test_internal_exception_in_verify(env):
    env.handle(side_effect=RuntimeError("boom"))
    assert "❌ Verificação sem sucesso" in env.followup_titles()
    env.member.add_roles.assert_not_awaited()
    env.member.edit.assert_not_awaited()
    emb = env.log_channel.send.await_args.kwargs["embed"]
    assert any("Erro interno" in f.value for f in emb.fields)


def test_attachment_read_exception(env):
    env.attachment.read.side_effect = OSError("net")
    env.handle(dict(VALID_RESULT))
    env.vc.assert_not_awaited()
    assert "❌ Verificação sem sucesso" in env.followup_titles()
    env.member.add_roles.assert_not_awaited()


def test_log_channel_not_configured_still_applies_role(env, monkeypatch):
    monkeypatch.delenv("CERTIFICATE_VERIFICATION_LOG_CHANNEL_ID", raising=False)
    env.handle(dict(VALID_RESULT))
    env.log_channel.send.assert_not_awaited()
    env.member.add_roles.assert_awaited_once()


def test_log_channel_send_forbidden_still_applies_role(env):
    env.log_channel.send.side_effect = _forbidden()
    env.handle(dict(VALID_RESULT))
    env.member.add_roles.assert_awaited_once()


def test_valid_result_without_academic_year_still_gives_role(env):
    """academic_year=None (sem restricao de anos): o log nao deve rebentar
    e o cargo tem de ser atribuido."""
    r = dict(VALID_RESULT)
    r["academic_year"] = None
    env.handle(r)
    env.member.add_roles.assert_awaited_once()


def test_real_config_files_untouched(env):
    # garante que o teste nao usa o ficheiro real
    assert data_manager.CERT_CONFIG_FILE == env.cfg_file
