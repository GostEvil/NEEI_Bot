"""
verificacao1.py — Comando Discord /verificacao1 para verificação por certificado.

Este módulo contém apenas a lógica de interação com o Discord.
O processamento do certificado está no pacote `verification/`.

Fluxo:
1. Utilizador invoca /verificacao1
2. Bot pede o certificado (resposta ephemeral)
3. Bot aguarda a próxima mensagem do utilizador no canal com attachment
4. Bot processa o certificado
5. Bot responde com resultado público genérico
6. Bot envia log privado no canal definido em CERTIFICATE_VERIFICATION_LOG_CHANNEL_ID

Privacidade:
- Mensagens públicas contêm apenas resultado (✅/❌) sem dados pessoais
- Dados pessoais são enviados apenas para o canal de log privado
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Optional

import discord
from discord import app_commands

import config
from verification.certificate import verify_certificate

logger = logging.getLogger(__name__)

# Timeout (segundos) para o utilizador enviar o certificado após /verificacao1
CERTIFICATE_UPLOAD_TIMEOUT_SECS = 120

# ─── Registo do Comando ───────────────────────────────────────────────────────


def register_verificacao1(bot: discord.ext.commands.Bot, guild_obj: discord.Object) -> None:
    """
    Regista o comando /verificacao1 no bot.

    Chamado a partir de bot.py — mantém a lógica separada do ficheiro principal.
    """

    @bot.tree.command(
        name="verificacao1",
        description="Inicia a verificação de aluno via Certificado Multiusos do IPB.",
        guild=guild_obj,
    )
    async def verificacao1(interaction: discord.Interaction):
        """Slash command /verificacao1."""
        await _handle_verificacao1(interaction, bot)


# ─── Handler principal ────────────────────────────────────────────────────────


async def _handle_verificacao1(
    interaction: discord.Interaction,
    bot: discord.ext.commands.Bot,
) -> None:
    """Lógica principal do fluxo /verificacao1."""

    # Verificar se o canal está configurado (opcional — pode ser qualquer canal)
    cert_channel_id = config.get_certificate_verification_channel_id()
    if cert_channel_id and interaction.channel_id != cert_channel_id:
        channel_mention = f"<#{cert_channel_id}>"
        await interaction.response.send_message(
            f"❌ Este comando só pode ser usado no canal {channel_mention}.",
            ephemeral=True,
        )
        return

    # 1. Pedir ao utilizador para enviar o certificado
    await interaction.response.send_message(
        "📄 **Verificação por Certificado Multiusos**\n\n"
        "Por favor, envia o teu **Certificado Multiusos** do Instituto Politécnico de Bragança.\n\n"
        "• Formatos aceites: **PDF, PNG, JPG, JPEG**\n"
        "• Tamanho máximo: **15 MB**\n"
        "• Tens **2 minutos** para enviar o ficheiro.\n\n"
        "⚠️ O ficheiro será processado localmente e apagado imediatamente após a verificação.",
        ephemeral=True,
    )

    # 2. Aguardar a mensagem com o attachment do utilizador
    def check(message: discord.Message) -> bool:
        return (
            message.author.id == interaction.user.id
            and message.channel.id == interaction.channel_id
            and len(message.attachments) > 0
        )

    try:
        user_message: discord.Message = await bot.wait_for(
            "message",
            check=check,
            timeout=CERTIFICATE_UPLOAD_TIMEOUT_SECS,
        )
    except asyncio.TimeoutError:
        try:
            await interaction.followup.send(
                "⏱️ Tempo esgotado. Usa `/verificacao1` novamente quando estiveres pronto.",
                ephemeral=True,
            )
        except Exception:
            pass
        return

    # 3. Processar o attachment
    attachment = user_message.attachments[0]

    # Enviar indicação de "a processar..." visível apenas ao utilizador
    try:
        processing_msg = await interaction.followup.send(
            "⏳ A processar o certificado… Aguarda um momento.",
            ephemeral=True,
        )
    except Exception:
        processing_msg = None

    try:
        # Descarregar bytes do ficheiro
        file_bytes = await attachment.read()
        mime_type = attachment.content_type  # pode ser None

        # Processar o certificado
        result = await verify_certificate(
            file_bytes=file_bytes,
            filename=attachment.filename,
            mime_type=mime_type,
        )

    except Exception as exc:
        logger.exception("Erro inesperado ao processar attachment: %s", exc)
        result = {"valid": False, "reason": "Erro interno ao processar o certificado."}

    # 4. Responder ao utilizador (mensagem pública genérica)
    if result.get("valid"):
        await _send_success_response(interaction, user_message, result)
        await _send_private_log(interaction, result, success=True)

        # 5. Alterar nickname do membro
        member = interaction.guild.get_member(interaction.user.id)
        if member:
            await _apply_nickname(interaction, member, result["nickname"])
    else:
        reason = result.get("reason", "Não foi possível validar o certificado.")
        # Mensagem pública sem dados pessoais
        await _send_failure_response(interaction, user_message)
        await _send_private_log(interaction, result, success=False, failure_reason=reason)

    # Apagar a mensagem de "a processar..." (se ainda existir)
    if processing_msg:
        try:
            await processing_msg.delete()
        except Exception:
            pass


# ─── Respostas Discord ────────────────────────────────────────────────────────


async def _send_success_response(
    interaction: discord.Interaction,
    user_message: discord.Message,
    result: dict,
) -> None:
    """Envia resposta pública de sucesso — sem dados pessoais."""
    try:
        embed = discord.Embed(
            title="✅ Certificado Verificado",
            description=(
                f"{interaction.user.mention}, o teu certificado foi validado com sucesso!\n"
                f"O teu nickname foi atualizado."
            ),
            color=discord.Color.green(),
        )
        await user_message.reply(embed=embed)
    except Exception as exc:
        logger.warning("Não foi possível enviar resposta de sucesso: %s", exc)


async def _send_failure_response(
    interaction: discord.Interaction,
    user_message: discord.Message,
) -> None:
    """Envia resposta pública de falha — sem dados pessoais nem razão técnica."""
    try:
        embed = discord.Embed(
            title="❌ Verificação sem sucesso",
            description=(
                f"{interaction.user.mention}, não foi possível validar o certificado.\n\n"
                "Certifica-te de que enviaste um **Certificado Multiusos** do IPB "
                "para o curso de **Engenharia Informática** e que o documento é legível."
            ),
            color=discord.Color.red(),
        )
        await user_message.reply(embed=embed)
    except Exception as exc:
        logger.warning("Não foi possível enviar resposta de falha: %s", exc)


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
        logger.error(
            "Erro HTTP ao alterar nickname de %s: %s",
            member.name,
            exc,
        )


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
        embed.add_field(name="Curso", value=result.get("course", "—"), inline=True)
        embed.add_field(name="Instituição", value=result.get("institution", "—"), inline=True)
        embed.add_field(name="Nickname Atribuído", value=result.get("nickname", "—"), inline=True)
    else:
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
