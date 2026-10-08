"""
certificate.py — Coordena o processo completo de verificação de certificado.

Fluxo:
1. Validação do ficheiro (extensão, MIME, tamanho)
2. Extracção de texto (PDF nativo → OCR PDF → OCR imagem)
3. Validação do documento (tipo, instituição, curso)
4. Extracção de dados pessoais (nome, nº mecanográfico, doc. identificação)
5. Geração do nickname Discord
6. Limpeza de ficheiros temporários

Resultado:
    {"valid": True, "name": ..., "mechanographic_number": ...,
     "identification_document": ..., "course": ..., "institution": ...,
     "nickname": ...}
ou
    {"valid": False, "reason": "..."}
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Any

from .ocr import _safe_delete, extract_text
from .parser import ParsedCertificate, get_missing_fields, parse_certificate
from .validator import validate_document
from .nickname import build_nickname

logger = logging.getLogger(__name__)

# ─── Constantes de Segurança ──────────────────────────────────────────────────

# Tamanho máximo do ficheiro: 15 MB
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024

# Extensões aceites
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}

# MIME types aceites
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
}

# ─── Tipo de retorno ──────────────────────────────────────────────────────────

CertificateResult = dict[str, Any]


# ─── Função principal ─────────────────────────────────────────────────────────


async def verify_certificate(
    file_bytes: bytes,
    filename: str,
    mime_type: str | None = None,
    allowed_years: list[str] | None = None,
) -> CertificateResult:
    """
    Verifica um certificado a partir dos seus bytes.

    Args:
        file_bytes:    Conteúdo binário do ficheiro.
        filename:      Nome do ficheiro (usado para determinar a extensão).
        mime_type:     MIME type reportado pelo Discord (pode ser None).
        allowed_years: Lista de anos letivos aceites (ex: ['2025/2026']).
                       Se None ou lista vazia, a verificação de ano é ignorada.

    Returns:
        Dicionário com "valid": True e os dados extraídos,
        ou "valid": False com "reason" genérica.
        Em caso de ano letivo inválido, inclui também "year_mismatch": True
        e "academic_year" com o ano encontrado no certificado.
    """
    tmp_path: str | None = None

    try:
        # 1. Validar ficheiro antes de o processar
        validation_error = _validate_file_metadata(filename, mime_type, len(file_bytes))
        if validation_error:
            return {"valid": False, "reason": validation_error}

        # 2. Escrever para ficheiro temporário
        suffix = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(
            suffix=suffix, delete=False, prefix="cert_verify_"
        ) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        logger.info(
            "Certificado guardado temporariamente em '%s' (%d bytes).",
            tmp_path,
            len(file_bytes),
        )

        # 3. Extrair texto
        try:
            text = await asyncio.to_thread(extract_text, tmp_path, mime_type)
        except ValueError as exc:
            logger.warning("Tipo de ficheiro não suportado: %s", exc)
            return {"valid": False, "reason": "Tipo de ficheiro não suportado."}
        except Exception as exc:
            logger.error("Erro durante extracção de texto: %s", exc)
            return {
                "valid": False,
                "reason": "Não foi possível ler o conteúdo do documento.",
            }

        if not text or len(text.strip()) < 20:
            return {
                "valid": False,
                "reason": "O documento não contém texto legível suficiente.",
            }

        # 4. Validar documento
        validation = validate_document(text)
        if not validation.valid:
            logger.info("Documento inválido: %s", validation.reason)
            # Motivo genérico para o utilizador — sem dados pessoais
            return {
                "valid": False,
                "reason": (
                    "O documento não corresponde a um Certificado Multiusos "
                    "do Instituto Politécnico de Bragança para Engenharia Informática."
                ),
            }

        # 5. Extrair dados pessoais
        parsed = parse_certificate(text)
        missing = get_missing_fields(parsed)

        if missing:
            logger.warning("Campos em falta no certificado: %s", missing)
            return {
                "valid": False,
                "reason": (
                    f"Não foi possível extrair os seguintes campos do certificado: "
                    f"{', '.join(missing)}. Certifica-te que o documento é legível."
                ),
            }

        # 6. Verificar ano letivo (se a configuração tiver anos definidos)
        if allowed_years:
            cert_year = parsed.academic_year
            if not cert_year or not _year_is_allowed(cert_year, allowed_years):
                logger.info(
                    "Ano letivo '%s' não está na lista de anos permitidos: %s",
                    cert_year,
                    allowed_years,
                )
                return {
                    "valid": False,
                    "year_mismatch": True,
                    "academic_year": cert_year,
                    "name": parsed.name,
                    "mechanographic_number": parsed.mechanographic_number,
                    "reason": (
                        "O certificado não é do ano letivo correto. "
                        "Apenas são aceites: " + ", ".join(allowed_years) + "."
                    ),
                }

        # 7. Gerar nickname
        nickname = build_nickname(parsed.name, parsed.mechanographic_number)

        logger.info(
            "Verificação concluída com sucesso para '%s' (%s) — ano letivo: %s.",
            parsed.name,
            parsed.mechanographic_number,
            parsed.academic_year or "desconhecido",
        )

        return {
            "valid": True,
            "name": parsed.name,
            "mechanographic_number": parsed.mechanographic_number,
            "identification_document": parsed.identification_document,
            "academic_year": parsed.academic_year,
            "course": parsed.course,
            "institution": parsed.institution,
            "nickname": nickname,
        }

    except Exception as exc:
        logger.exception("Erro inesperado durante verify_certificate: %s", exc)
        return {
            "valid": False,
            "reason": "Ocorreu um erro interno ao processar o certificado.",
        }

    finally:
        # Sempre apagar o ficheiro temporário, mesmo em caso de excepção
        if tmp_path:
            _safe_delete(tmp_path)
            logger.debug("Ficheiro temporário principal apagado: %s", tmp_path)


# ─── Validação de Metadados ───────────────────────────────────────────────────


def _validate_file_metadata(
    filename: str, mime_type: str | None, file_size: int
) -> str | None:
    """
    Valida extensão, MIME type e tamanho do ficheiro.

    Retorna None se tudo estiver correcto, ou uma mensagem de erro genérica.
    """
    # Validar extensão
    suffix = Path(filename).suffix.lower()
    if not suffix or suffix not in ALLOWED_EXTENSIONS:
        logger.warning("Extensão não permitida: '%s'", suffix)
        return (
            f"Formato de ficheiro não aceite (`{suffix or 'sem extensão'}`). "
            f"Aceito: PDF, PNG, JPG, JPEG."
        )

    # Validar MIME type (se disponível)
    if mime_type:
        # Normalizar (remover parâmetros como "; charset=utf-8")
        mime_base = mime_type.split(";")[0].strip().lower()
        if mime_base not in ALLOWED_MIME_TYPES:
            logger.warning("MIME type não permitido: '%s'", mime_type)
            return f"Tipo de ficheiro não aceite (`{mime_type}`)."
    else:
        # Tentar inferir o MIME type a partir da extensão como verificação adicional
        guessed_mime, _ = mimetypes.guess_type(filename)
        if guessed_mime and guessed_mime.split(";")[0].lower() not in ALLOWED_MIME_TYPES:
            logger.warning("MIME type inferido não permitido: '%s'", guessed_mime)
            return "Tipo de ficheiro não reconhecido."

    # Validar tamanho
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        logger.warning("Ficheiro demasiado grande: %.2f MB (máx: %.0f MB)", size_mb, max_mb)
        return f"O ficheiro é demasiado grande ({size_mb:.1f} MB). Máximo: {max_mb:.0f} MB."

    return None


def _year_is_allowed(cert_year: str, allowed_years: list[str]) -> bool:
    """
    Verifica se o ano letivo extraído do certificado consta na lista de anos permitidos.

    Normaliza ambos os lados para tolerar pequenas diferenças de formatação
    (ex: "2025 / 2026" vs "2025/2026").
    """
    def _normalize_year(y: str) -> str:
        return y.replace(" ", "").strip()

    cert_normalized = _normalize_year(cert_year)
    return any(_normalize_year(y) == cert_normalized for y in allowed_years)
