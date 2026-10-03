"""
parser.py — Extrai dados pessoais do texto do Certificado Multiusos do IPB.

Extrai:
- Nome completo do aluno
- Número mecanográfico (ex: a64716, 64716)
- Número do documento de identificação
- Ano letivo (ex: 2025/2026)

A extracção usa regex adaptadas ao formato do certificado, com tolerância
a variações de OCR.

O certificado tem duas secções: português e inglês. O parser tenta extrair
os dados de qualquer uma das secções.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Estruturas de dados ──────────────────────────────────────────────────────


@dataclass
class ParsedCertificate:
    """Dados extraídos do certificado."""
    name: Optional[str] = None
    mechanographic_number: Optional[str] = None
    identification_document: Optional[str] = None
    academic_year: Optional[str] = None
    course: str = "Engenharia Informática"
    institution: str = "Instituto Politécnico de Bragança"


# ─── Padrões Regex ────────────────────────────────────────────────────────────

# Padrão para o número mecanográfico do IPB:
# formato típico: a64716, A64716, a 64716, a-64716
# também pode aparecer apenas como número: 64716
_MECH_PATTERNS = [
    # "com o n.º XXXXX" ou "com o n.o XXXXX" ou "with the number XXXXX"
    r"(?:com\s+o\s+n[.\s°oO]*[.º]?\s*)([aA]?\s*\d{5,6})",
    r"(?:with\s+the\s+number\s*)([aA]?\s*\d{5,6})",
    # número mecanográfico isolado precedido de "n.º" ou "nº"
    r"n[.\s]?[oOº°]\s*[:\s]?\s*([aA]?\s*\d{5,6})",
    # formato "a12345" em qualquer sítio
    r"\b([aA]\d{5,6})\b",
]

# Padrão para número de documento de identificação (BI/CC/Passaporte)
# BI: 8 dígitos; CC: 8 dígitos + letra + 2 dígitos; Passaporte: letra + 6 dígitos
_ID_PATTERNS = [
    # "titular do documento de identificação XXXXXXXX" (secção PT)
    r"(?:titular\s+do\s+documento\s+de\s+identifica[cç][aã]o\s*[\"«»]?\s*)([A-Z0-9]{6,12})",
    # "owner of the identification document XXXXXXXX" (secção EN)
    r"(?:owner\s+of\s+the\s+identification\s+document\s*[\"«»]?\s*)([A-Z0-9]{6,12})",
    # "documento de identificação" seguido de número entre aspas ou separadores
    r"identifica[cç][aã]o\s*[\"«»\s]*([A-Z0-9]{6,12})",
    # CC português: XXXXXXXX N ZZ (ex: 12345678 4 ZZ4)
    r"\b(\d{8}\s*\d\s*[A-Z]{2}\d)\b",
    # BI simples: 8 dígitos
    r"\b(\d{8})\b",
]

# Padrão para o nome do aluno
# No certificado PT: "certifica-se que o estudante NOME COMPLETO, com o n.º"
# No certificado EN: "certified that the student NOME COMPLETO, with the number"
_NAME_PATTERNS = [
    # Secção portuguesa
    r"(?:certifica-?se\s+que\s+o\s+estudante\s+)([A-ZÀ-Ž][a-zA-ZÀ-ž\s]{5,60}?)(?:\s*,\s*com|\s+com\s+o\s+n)",
    # Secção inglesa (nome pode estar entre aspas)
    r"(?:certified\s+that\s+the\s+student\s+[\"«»]?)([A-ZÀ-Ž][a-zA-ZÀ-ž\s]{5,60}?)(?:[\"«»]?\s*,?\s*with)",
    # Fallback: após "o estudante" ou "the student"
    r"(?:o\s+estudante|the\s+student)\s+[\"«»]?([A-ZÀ-Ž][a-zA-ZÀ-ž\s]{5,60}?)(?:[\"«»]?[\s,])",
]

# Padrões para o ano letivo
# PT: "no ano letivo 2025/2026"
# EN: "in the academic year 2025/2026" ou "academic year 2025/2026"
_YEAR_PATTERNS = [
    r"(?:ano\s+letivo|ano\s+acad[eé]mico)\s+(\d{4}/\d{4})",
    r"(?:academic\s+year)\s+(\d{4}/\d{4})",
    # fallback genérico: qualquer par AAAA/AAAA no documento
    r"\b(\d{4}/\d{4})\b",
]


# ─── Funções Públicas ──────────────────────────────────────────────────────────


def parse_certificate(text: str) -> ParsedCertificate:
    """
    Extrai os dados do certificado a partir do texto (nativo ou OCR).

    Devolve um ParsedCertificate com os campos preenchidos que foi possível extrair.
    Campos não encontrados ficam como None.
    """
    result = ParsedCertificate()

    if not text or not text.strip():
        logger.warning("Texto vazio passado ao parser.")
        return result

    # Normalizar para matching (manter caso original para o nome)
    normalized = _normalize_for_matching(text)

    result.name = _extract_name(text, normalized)
    result.mechanographic_number = _extract_mechanographic_number(text, normalized)
    result.identification_document = _extract_identification_document(text, normalized)
    result.academic_year = _extract_academic_year(text, normalized)

    logger.info(
        "Parsing concluído — nome: %s | mech: %s | id_doc: %s | ano: %s",
        bool(result.name),
        bool(result.mechanographic_number),
        bool(result.identification_document),
        result.academic_year or "n/a",
    )
    return result


def get_missing_fields(parsed: ParsedCertificate) -> list[str]:
    """
    Retorna a lista de campos obrigatórios que não foram encontrados.
    """
    missing = []
    if not parsed.name:
        missing.append("nome")
    if not parsed.mechanographic_number:
        missing.append("número mecanográfico")
    if not parsed.identification_document:
        missing.append("documento de identificação")
    return missing


# ─── Funções Internas ──────────────────────────────────────────────────────────


def _normalize_for_matching(text: str) -> str:
    """
    Normaliza o texto para uso em regex de matching.
    - Colapsa espaços e quebras de linha
    - Mantém acentos (para regex com classes de caracteres)
    - Minúsculas
    """
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    return text.lower()


def _normalize_name(name: str) -> str:
    """Limpa o nome extraído: remove espaços extra, aspas, etc."""
    name = name.strip().strip("\"«»'")
    name = re.sub(r"\s+", " ", name)
    # Capitalizar correctamente (Title Case mas com partículas em minúsculas)
    parts = name.split()
    particles = {"de", "da", "do", "das", "dos", "e", "a", "o", "com"}
    result = []
    for i, part in enumerate(parts):
        if i == 0 or part.lower() not in particles:
            result.append(part.capitalize())
        else:
            result.append(part.lower())
    return " ".join(result)


def _extract_name(original_text: str, normalized: str) -> Optional[str]:
    """Extrai o nome completo do aluno."""
    for pattern in _NAME_PATTERNS:
        try:
            # Usar o texto original para preservar acentos e capitalização
            match = re.search(pattern, original_text, re.IGNORECASE | re.UNICODE)
            if match:
                name = match.group(1).strip()
                if len(name) >= 3:  # nome mínimo razoável
                    cleaned = _normalize_name(name)
                    logger.debug("Nome encontrado com padrão '%s': '%s'", pattern[:30], cleaned)
                    return cleaned
        except re.error as exc:
            logger.warning("Erro no padrão de nome '%s': %s", pattern[:30], exc)

    logger.warning("Nome não encontrado no documento.")
    return None


def _extract_mechanographic_number(original_text: str, normalized: str) -> Optional[str]:
    """
    Extrai o número mecanográfico.

    Normaliza para o formato "aXXXXX" (minúsculas), ou apenas os dígitos
    se não houver prefixo de letra.
    """
    for pattern in _MECH_PATTERNS:
        try:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                raw = match.group(1).strip().replace(" ", "").replace("-", "")
                # Normalizar: garantir que começa com 'a' se tiver prefixo
                if raw and raw[0].lower() == "a":
                    normalized_num = "a" + raw[1:]
                else:
                    normalized_num = raw
                logger.debug("Número mecanográfico encontrado: '%s'", normalized_num)
                return normalized_num
        except re.error as exc:
            logger.warning("Erro no padrão mecanográfico '%s': %s", pattern[:30], exc)

    logger.warning("Número mecanográfico não encontrado.")
    return None


def _extract_identification_document(original_text: str, normalized: str) -> Optional[str]:
    """
    Extrai o número do documento de identificação.

    Tenta primeiro as expressões contextuais (mais fiáveis),
    depois os padrões genéricos.
    """
    for pattern in _ID_PATTERNS:
        try:
            # Usar texto original para preservar letras maiúsculas
            match = re.search(pattern, original_text, re.IGNORECASE)
            if match:
                raw = match.group(1).strip().replace(" ", "")
                if len(raw) >= 6:  # comprimento mínimo razoável
                    logger.debug("Documento de identificação encontrado: '%s'", raw[:4] + "****")
                    return raw.upper()
        except re.error as exc:
            logger.warning("Erro no padrão de ID '%s': %s", pattern[:30], exc)

    logger.warning("Documento de identificação não encontrado.")
    return None


def _extract_academic_year(original_text: str, normalized: str) -> Optional[str]:
    """
    Extrai o ano letivo do certificado (ex: "2025/2026").

    Tenta padrões contextuais primeiro ("ano letivo AAAA/AAAA"),
    depois um padrão genérico de fallback.
    """
    for pattern in _YEAR_PATTERNS:
        try:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                year = match.group(1).strip()
                logger.debug("Ano letivo encontrado: '%s'", year)
                return year
        except re.error as exc:
            logger.warning("Erro no padrão de ano '%s': %s", pattern[:30], exc)

    logger.warning("Ano letivo não encontrado no documento.")
    return None
