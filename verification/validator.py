"""
validator.py — Valida que o documento é um Certificado Multiusos do IPB
               para o curso de Engenharia Informática.

A validação usa normalização de texto para tolerar:
- diferenças de maiúsculas/minúsculas
- acentos ausentes ou trocados (comum em OCR)
- espaços e quebras de linha extra
- pequenos erros de OCR em letras individuais

Mas não é demasiado permissiva: exige evidências de TODOS os três critérios
(tipo de documento, instituição, curso).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Constantes de Validação ──────────────────────────────────────────────────

# Strings obrigatórias — cada grupo contém variantes aceitáveis (incluindo erros OCR comuns)
REQUIRED_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "certificado_multiusos",
        [
            "certificado multiusos",
            "certificado multi-usos",
            "certificado mulfiusos",      # OCR: t → f
            "certificado multiu5os",      # OCR: s → 5
            "multipurpose certificate",   # versão inglesa do mesmo certificado
        ],
    ),
    (
        "instituto_politecnico_braganca",
        [
            "instituto politecnico de braganca",
            "instituto politecnico braganca",
            "instituto polite cnico de braganca",
            "polytechnic institute of braganca",
            "polytechnic institute of bragança",
            "instituto politecnico de braganca",   # sem cedilha (normalizado)
        ],
    ),
    (
        "engenharia_informatica",
        [
            "engenharia informatica",
            "engenharia informática",
            "licenciatura em engenharia informatica",
            "bachelor's programme in engenharia informatica",
            "bachelor s programme in engenharia informatica",
        ],
    ),
]


@dataclass
class ValidationResult:
    """Resultado da validação do documento."""
    valid: bool
    reason: Optional[str] = None
    matched_criteria: Optional[list[str]] = None


# ─── Funções Públicas ─────────────────────────────────────────────────────────


def validate_document(text: str) -> ValidationResult:
    """
    Valida que o texto extraído corresponde a um Certificado Multiusos do IPB
    para o curso de Engenharia Informática.

    Retorna ValidationResult com valid=True se todos os critérios foram satisfeitos,
    ou valid=False com o motivo da falha.
    """
    if not text or not text.strip():
        return ValidationResult(valid=False, reason="O documento não contém texto legível.")

    normalized = _normalize_text(text)
    logger.debug("Texto normalizado (%d chars) para validação.", len(normalized))

    matched: list[str] = []
    missing: list[str] = []

    for criterion_key, variants in REQUIRED_PATTERNS:
        found = False
        for variant in variants:
            normalized_variant = _normalize_text(variant)
            if _fuzzy_contains(normalized, normalized_variant):
                found = True
                logger.debug("Critério '%s' satisfeito com variante: '%s'", criterion_key, variant)
                break

        if found:
            matched.append(criterion_key)
        else:
            missing.append(criterion_key)
            logger.info("Critério '%s' NÃO encontrado no documento.", criterion_key)

    if missing:
        reason = _build_failure_reason(missing)
        return ValidationResult(valid=False, reason=reason, matched_criteria=matched)

    logger.info("Documento validado com sucesso. Critérios satisfeitos: %s", matched)
    return ValidationResult(valid=True, matched_criteria=matched)


# ─── Funções Internas ─────────────────────────────────────────────────────────


def _normalize_text(text: str) -> str:
    """
    Normaliza texto para comparação tolerante:
    - converte para minúsculas
    - remove acentos (NFD → remove diacríticos)
    - colapsa espaços múltiplos e quebras de linha
    - remove pontuação irrelevante (mantém letras, dígitos, espaços)
    """
    # Normalizar unicode (NFD decompõe letras acentuadas)
    text = unicodedata.normalize("NFD", text)
    # Remover diacríticos (categoria Mn = Mark, Nonspacing)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Minúsculas
    text = text.lower()
    # Substituir quebras de linha e tabulações por espaço
    text = re.sub(r"[\r\n\t]+", " ", text)
    # Remover caracteres que não sejam letras, dígitos ou espaços
    # (manter apóstrofo para "bachelor's")
    text = re.sub(r"[^\w\s']", " ", text)
    # Colapsar espaços múltiplos
    text = re.sub(r" +", " ", text).strip()
    return text


def _fuzzy_contains(haystack: str, needle: str, max_errors: int = 2) -> bool:
    """
    Verifica se 'needle' aparece em 'haystack', permitindo até 'max_errors'
    substituições de caractere (para tolerar erros de OCR residuais).

    Para needles curtas (≤ 8 chars), usa correspondência exacta.
    Para needles longas, usa uma janela deslizante com contagem de erros.
    """
    if not needle:
        return False

    # Correspondência exacta primeiro (mais rápida)
    if needle in haystack:
        return True

    n = len(needle)
    h = len(haystack)

    if n > h:
        return False

    # Para needles curtas, não fazer fuzzy (evita falsos positivos)
    if n <= 8:
        return False

    # Janela deslizante com tolerância a erros
    for i in range(h - n + 1):
        window = haystack[i : i + n]
        errors = sum(1 for a, b in zip(window, needle) if a != b)
        if errors <= max_errors:
            return True

    return False


def _build_failure_reason(missing: list[str]) -> str:
    """Constrói uma mensagem de erro legível baseada nos critérios em falta."""
    messages = {
        "certificado_multiusos": "O documento não parece ser um Certificado Multiusos.",
        "instituto_politecnico_braganca": (
            "O documento não parece pertencer ao Instituto Politécnico de Bragança."
        ),
        "engenharia_informatica": (
            "O documento não indica o curso de Engenharia Informática."
        ),
    }
    parts = [messages.get(m, f"Critério '{m}' não satisfeito.") for m in missing]
    return " ".join(parts)
