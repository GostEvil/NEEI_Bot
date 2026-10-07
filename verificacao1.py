"""
verificacao1.py — Comando Discord /verificacao1 para verificação por certificado.

Este módulo contém apenas a lógica de interação com o Discord.
O processamento do certificado está no pacote `verification/`.

Fluxo:
1. Utilizador invoca /verificacao1 certificado:<ficheiro>
2. Bot processa o certificado imediatamente (sem wait_for — não requer message_content intent)
3. Bot responde com resultado público genérico (ephemeral durante processamento)
4. Bot envia log privado no canal definido em CERTIFICATE_VERIFICATION_LOG_CHANNEL_ID

Privacidade:
- Mensagens públicas contêm apenas resultado (✅/❌) sem dados pessoais
- Dados pessoais são enviados apenas para o canal de log privado
"""

from __future__ import annotations

import datetime
import logging
from typing import Optional

import discord
from discord import app_commands

import config
import data_manager
from verification.certificate import verify_certificate

logger = logging.getLogger(__name__)

# ─── Registo do Comando ───────────────────────────────────────────────────────


def register_verificacao1(bot: discord.ext.commands.Bot, guild_obj: discord.Object) -> None:
    """
    Regista o comando /verificacao1 no bot.

    Chamado a partir de bot.py — mantém a lógica separada do ficheiro principal.
    O ficheiro é passado directamente como parâmetro do slash command,
    eliminando a necessidade do intent privilegiado message_content.
    """

    @bot.tree.command(
        name="verificacao1",
        description="Verificação de aluno via Certificado Multiusos do IPB.",
        guild=guild_obj,
    )
    @app_commands.describe(
        certificado="O teu Certificado Multiusos do IPB (PDF, PNG, JPG ou JPEG)"
    )
    async def verificacao1(
        interaction: discord.Interaction,
        certificado: discord.Attachment,
    ):
        """Slash command /verificacao1 — o ficheiro é passado directamente."""
        await _handle_verificacao1(interaction, certificado)


# ─── Handler principal ────────────────────────────────────────────────────────


async def _handle_verificacao1(
    interaction: discord.Interaction,
    attachment: discord.Attachment,
) -> None:
    """Lógica principal do fluxo /verificacao1."""

    # Verificar se o canal está configurado (opcional)
    cert_channel_id = config.get_certificate_verification_channel_id()
    if cert_channel_id and interaction.channel_id != cert_channel_id:
        channel_mention = f"<#{cert_channel_id}>"
        await interaction.response.send_message(
            f"❌ Este comando só pode ser usado no canal {channel_mention}.",
            ephemeral=True,
        )
        return

    # Deferir a resposta imediatamente (processamento pode demorar)
    # ephemeral=False para que a resposta final seja visível no canal
    await interaction.response.defer(thinking=True)

    # Carregar anos letivos permitidos
    allowed_years = data_manager.get_allowed_years()  # lista vazia = sem restrição de ano

    # Processar o attachment
    try:
        file_bytes = await attachment.read()
        mime_type = attachment.content_type  # pode ser None

        result = await verify_certificate(
            file_bytes=file_bytes,
            filename=attachment.filename,
            mime_type=mime_type,
            allowed_years=allowed_years or None,
        )
    except Exception as exc:
        logger.exception("Erro inesperado ao processar attachment: %s", exc)
        result = {"valid": False, "reason": "Erro interno ao processar o certificado."}

    # Responder ao utilizador e enviar log
    if result.get("valid"):
        await _send_success_response(interaction, result)
        await _send_private_log(interaction, result, success=True)

        # Alterar nickname e atribuir cargo de verificação
        member = interaction.guild.get_member(interaction.user.id)
        if member:
            await _apply_nickname(interaction, member, result["nickname"])
            await _apply_verify_role(interaction, member)
    elif result.get("year_mismatch"):
        # Certificado válido, mas ano letivo não é aceite
        await _send_failure_response(interaction)
        await _send_year_mismatch_alert(interaction, result)
        await _send_private_log(interaction, result, success=False,
                                failure_reason=result.get("reason"))
    else:
        reason = result.get("reason", "Não foi possível validar o certificado.")
        await _send_failure_response(interaction)
        await _send_private_log(interaction, result, success=False, failure_reason=reason)


# ─── Respostas Discord ────────────────────────────────────────────────────────


async def _send_success_response(
    interaction: discord.Interaction,
    result: dict,
) -> None:
    """Envia resposta de sucesso — sem dados pessoais."""
    embed = discord.Embed(
        title="✅ Certificado Verificado",
        description=(
            f"{interaction.user.mention}, o teu certificado foi validado com sucesso!\n"
            "O teu nickname foi atualizado."
        ),
        color=discord.Color.green(),
    )
    try:
        await interaction.followup.send(embed=embed)
    except Exception as exc:
        logger.warning("Não foi possível enviar resposta de sucesso: %s", exc)


async def _send_failure_response(
    interaction: discord.Interaction,
) -> None:
    """Envia resposta de falha — sem dados pessoais nem razão técnica."""
    embed = discord.Embed(
        title="❌ Verificação sem sucesso",
        description=(
            f"{interaction.user.mention}, não foi possível validar o certificado.\n\n"
            "Certifica-te de que enviaste um **Certificado Multiusos** do IPB "
            "para o curso de **Engenharia Informática** e que o documento é legível."
        ),
        color=discord.Color.red(),
    )
    try:
        await interaction.followup.send(embed=embed)
    except Exception as exc:
        logger.warning("Não foi possível enviar resposta de falha: %s", exc)


async def _send_year_mismatch_alert(
    interaction: discord.Interaction,
    result: dict,
) -> None:
    """
    Envia um alerta para o canal configurado quando o utilizador envia um certificado
    cujo ano letivo não está na lista de anos aceites.

    O canal de alerta é configurado pelo manager via /certconfig alertchannel.
    """
    alert_channel_id = data_manager.get_cert_alert_channel_id()
    if not alert_channel_id:
        logger.warning(
            "Canal de alerta de ano inválido não configurado (use /certconfig alertchannel)."
        )
        return

    alert_channel = interaction.guild.get_channel(alert_channel_id)
    if alert_channel is None:
        try:
            alert_channel = await interaction.guild.fetch_channel(alert_channel_id)
        except Exception as exc:
            logger.error("Não foi possível encontrar o canal de alerta (ID: %s): %s",
                         alert_channel_id, exc)
            return

    cert_year = result.get("academic_year") or "desconhecido"
    allowed = data_manager.get_allowed_years()
    allowed_str = ", ".join(allowed) if allowed else "nenhum configurado"

    embed = discord.Embed(
        title="⚠️ Tentativa com Certificado de Ano Inválido",
        description=(
            f"{interaction.user.mention} tentou verificar-se com um certificado "
            f"do ano letivo **{cert_year}**, que não está na lista de anos aceites."
        ),
        color=discord.Color.orange(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.add_field(
        name="Utilizador",
        value=f"{interaction.user.mention}\nID: `{interaction.user.id}`",
        inline=True,
    )
    embed.add_field(name="Ano no Certificado", value=f"`{cert_year}`", inline=True)
    embed.add_field(name="Anos Aceites", value=f"`{allowed_str}`", inline=True)
    if result.get("name"):
        embed.add_field(name="Nome (extraído)", value=result["name"], inline=True)
    if result.get("mechanographic_number"):
        embed.add_field(name="Nº Mecanográfico", value=result["mechanographic_number"], inline=True)
    embed.set_footer(text=f"Canal: #{interaction.channel}")

    try:
        await alert_channel.send(embed=embed)
        logger.info("Alerta de ano inválido enviado para canal #%s.", alert_channel_id)
    except discord.Forbidden:
        logger.error("Sem permissão para enviar no canal de alerta (ID: %s).", alert_channel_id)
    except Exception as exc:
        logger.error("Erro ao enviar alerta de ano inválido: %s", exc)


async def _apply_nickname(
    interaction: discord.Interaction,
    member: discord.Member,
    nickname: str,
) -> None:
    """
    Tenta alterar o nickname do membro.

    Trata graciosamente:
    - falta de permissão do bot
    - hierarquia de cargos
    - utilizador ser o proprietário do servidor
    - nickname já correcto
    """
    if member.display_name == nickname:
        logger.info("Nickname já está correcto: '%s'. Sem alteração.", nickname)
        return

    try:
        await member.edit(nick=nickname, reason="Verificação 1 — Certificado Multiusos IPB")
        logger.info(
            "Nickname de %s (%s) alterado para '%s'.",
            member.name,
            member.id,
            nickname,
        )
    except discord.Forbidden:
        logger.warning(
            "Sem permissão para alterar nickname de %s (%s). "
            "Verificar hierarquia de cargos.",
            member.name,
            member.id,
        )
        try:
            await interaction.followup.send(
                "⚠️ O certificado foi validado, mas o bot não tem permissão para "
                "alterar o teu nickname. Contacta um administrador.",
                ephemeral=True,
            )
        except Exception:
            pass
    except discord.HTTPException as exc:
        logger.error("Erro HTTP ao alterar nickname de %s: %s", member.name, exc)


async def _apply_verify_role(
    interaction: discord.Interaction,
    member: discord.Member,
) -> None:
    """
    Atribui ao membro o cargo de verificação configurado via /config.

    Trata graciosamente:
    - cargo não configurado ou já inexistente no servidor
    - falta de permissão do bot / hierarquia de cargos
    - membro já ter o cargo
    """
    role_id = config.get_verify_role_id()
    if not role_id:
        logger.warning("Cargo de verificação não configurado (use /config).")
        return

    role = interaction.guild.get_role(role_id)
    if role is None:
        logger.error("Cargo de verificação (ID: %s) não encontrado no servidor.", role_id)
        return

    if role in member.roles:
        logger.info("%s (%s) já tem o cargo '%s'.", member.name, member.id, role.name)
        return

    try:
        await member.add_roles(role, reason="Verificação 1 — Certificado Multiusos IPB")
        logger.info("Cargo '%s' atribuído a %s (%s).", role.name, member.name, member.id)
    except discord.Forbidden:
        logger.warning(
            "Sem permissão para atribuir o cargo '%s' a %s (%s). "
            "Verificar hierarquia de cargos.",
            role.name,
            member.name,
            member.id,
        )
        try:
            await interaction.followup.send(
                "⚠️ O certificado foi validado, mas o bot não tem permissão para "
                "atribuir o cargo de verificação. Contacta um administrador.",
                ephemeral=True,
            )
        except Exception:
            pass
    except discord.HTTPException as exc:
        logger.error("Erro HTTP ao atribuir cargo a %s: %s", member.name, exc)


async def _send_private_log(
    interaction: discord.Interaction,
    result: dict,
    success: bool,
    failure_reason: Optional[str] = None,
) -> None:
    """
    Envia um embed com os dados da verificação para o canal de log privado.

    Inclui dados pessoais — apenas acessível no canal privado configurado.
    """
    log_channel_id = config.get_certificate_verification_log_channel_id()
    if not log_channel_id:
        logger.warning(
            "CERTIFICATE_VERIFICATION_LOG_CHANNEL_ID não configurado. "
            "Log de certificado não enviado."
        )
        return

    log_channel = interaction.guild.get_channel(log_channel_id)
    if log_channel is None:
        try:
            log_channel = await interaction.guild.fetch_channel(log_channel_id)
        except Exception as exc:
            logger.error(
                "Não foi possível encontrar o canal de log (ID: %s): %s",
                log_channel_id,
                exc,
            )
            return

    now = datetime.datetime.now(datetime.timezone.utc)
    color = discord.Color.green() if success else discord.Color.red()
    estado = "✅ Validado" if success else "❌ Rejeitado"

    embed = discord.Embed(
        title="📄 Verificação de Certificado",
        color=color,
        timestamp=now,
    )
    embed.add_field(
        name="Discord",
        value=f"{interaction.user.mention}\nID: `{interaction.user.id}`",
        inline=False,
    )

    if success:
        embed.add_field(name="Nome", value=result.get("name", "—"), inline=True)
        embed.add_field(
            name="Nº Mecanográfico",
            value=result.get("mechanographic_number", "—"),
            inline=True,
        )
        embed.add_field(
            name="Doc. Identificação",
            value=result.get("identification_document", "—"),
            inline=True,
        )
        embed.add_field(name="Ano Letivo", value=result.get("academic_year", "—"), inline=True)
        embed.add_field(name="Curso", value=result.get("course", "—"), inline=True)
        embed.add_field(name="Instituição", value=result.get("institution", "—"), inline=True)
        embed.add_field(name="Nickname Atribuído", value=result.get("nickname", "—"), inline=True)
    else:
        if result.get("academic_year"):
            embed.add_field(name="Ano no Certificado", value=result["academic_year"], inline=True)
        embed.add_field(
            name="Motivo da Rejeição",
            value=failure_reason or "Não especificado.",
            inline=False,
        )

    embed.add_field(name="Estado", value=estado, inline=False)
    embed.set_footer(text=f"Canal: #{interaction.channel}")

    try:
        await log_channel.send(embed=embed)
        logger.info("Log de verificação enviado para canal #%s.", log_channel_id)
    except discord.Forbidden:
        logger.error(
            "Sem permissão para enviar mensagem no canal de log (ID: %s).",
            log_channel_id,
        )
    except Exception as exc:
        logger.error("Erro ao enviar log de verificação: %s", exc)
