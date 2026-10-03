"""
nickname.py — Gera o nickname Discord a partir do nome completo e número mecanográfico.

Formato: "Primeiro Último (NúmeroMecanográfico)"

Regras:
- Primeiro elemento do nome → primeiro nome
- Último elemento do nome → último nome
- Nomes intermédios são ignorados para o nickname
- Se apenas um nome, usa esse nome
- Truncamento seguro sem remover o número mecanográfico

Limite do Discord: 32 caracteres para nicknames.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Limite de caracteres para nicknames no Discord
DISCORD_NICKNAME_LIMIT = 32


def build_nickname(full_name: str, mechanographic_number: str) -> str:
    """
    Gera o nickname Discord no formato "Primeiro Último (NúmeroMecanográfico)".

    Args:
        full_name: Nome completo do aluno (ex: "João Pedro dos Santos")
        mechanographic_number: Número mecanográfico (ex: "a64716" ou "64716")

    Returns:
        Nickname formatado, respeitando o limite de 32 caracteres do Discord.

    Exemplos:
        "João Pedro dos Santos" + "123456" → "João Santos (123456)"
        "Nuno Miguel Silva" + "a63426"     → "Nuno Silva (a63426)"
        "Nuno" + "123456"                  → "Nuno (123456)"
    """
    parts = full_name.strip().split()
    parts = [p for p in parts if p]  # remover strings vazias

    if not parts:
        # Nome completamente vazio — usar fallback seguro
        logger.warning("Nome vazio recebido em build_nickname.")
        nickname = f"Aluno ({mechanographic_number})"
        return _truncate_nickname(nickname, mechanographic_number)

    if len(parts) == 1:
        name_part = parts[0]
    else:
        # Primeiro e último, ignorar intermédios
        name_part = f"{parts[0]} {parts[-1]}"

    nickname = f"{name_part} ({mechanographic_number})"

    # Verificar limite e truncar se necessário
    if len(nickname) > DISCORD_NICKNAME_LIMIT:
        nickname = _truncate_nickname(nickname, mechanographic_number)

    logger.debug("Nickname gerado: '%s' (%d chars)", nickname, len(nickname))
    return nickname


def _truncate_nickname(nickname: str, mechanographic_number: str) -> str:
    """
    Trunca o nickname ao limite do Discord, preservando sempre
    o número mecanográfico entre parênteses.

    Estratégia:
    1. O sufixo "(NúmeroMecanográfico)" é fixo e nunca truncado.
    2. A parte do nome é truncada até caber, com "…" se necessário.

    Se mesmo assim não couber (número mecanográfico demasiado longo),
    retorna apenas "(NúmeroMecanográfico)" truncado.
    """
    suffix = f"({mechanographic_number})"
    # Espaço entre nome e sufixo
    available_for_name = DISCORD_NICKNAME_LIMIT - len(suffix) - 1  # -1 para o espaço

    if available_for_name <= 0:
        # Número mecanográfico tão longo que não há espaço para o nome
        logger.warning(
            "Número mecanográfico demasiado longo para caber no nickname: %s",
            mechanographic_number,
        )
        return suffix[:DISCORD_NICKNAME_LIMIT]

    # Extrair a parte do nome (antes do sufixo)
    name_part = nickname[: nickname.rfind(" (")].strip() if " (" in nickname else nickname

    if len(name_part) > available_for_name:
        # Truncar o nome com "…"
        name_part = name_part[: available_for_name - 1].rstrip() + "…"

    truncated = f"{name_part} {suffix}"
    logger.warning(
        "Nickname truncado de '%s' para '%s' (%d chars)",
        nickname,
        truncated,
        len(truncated),
    )
    return truncated
