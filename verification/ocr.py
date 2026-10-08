"""
ocr.py — Extração de texto de PDFs e imagens.

Responsabilidades:
- Extrair texto directamente de PDFs que contenham texto embutido
- Converter páginas de PDFs digitalizados para imagem e aplicar OCR
- Aplicar OCR em imagens (PNG/JPG/JPEG)
- Limpar ficheiros temporários após uso

Depende de:
- pypdf  (extracção de texto nativo de PDFs)
- pdf2image + poppler  (renderizar PDFs para imagem)
- pytesseract + Pillow  (OCR)

Nota: o Tesseract e o Poppler precisam de estar instalados no sistema.
Ver README/TODO.md para instruções de instalação.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Constantes ──────────────────────────────────────────────────────────────

# Número mínimo de caracteres para considerar que o PDF tem texto embutido
MIN_TEXT_CHARS = 50

# Número máximo de páginas que o sistema aceita num PDF
MAX_PDF_PAGES = 10

# Timeout (segundos) para operações OCR por página
OCR_TIMEOUT_SECS = 30

# ─── Helpers internos ────────────────────────────────────────────────────────


def _import_pypdf():
    """Importa pypdf com mensagem de erro amigável."""
    try:
        import pypdf
        return pypdf
    except ImportError:
        raise ImportError(
            "pypdf não está instalado. Execute: pip install pypdf"
        )


def _import_pdf2image():
    """Importa pdf2image com mensagem de erro amigável."""
    try:
        from pdf2image import convert_from_path
        return convert_from_path
    except ImportError:
        raise ImportError(
            "pdf2image não está instalado. Execute: pip install pdf2image\n"
            "Também é necessário ter o Poppler instalado no sistema."
        )


def _import_pytesseract():
    """Importa pytesseract com mensagem de erro amigável."""
    try:
        import pytesseract
        return pytesseract
    except ImportError:
        raise ImportError(
            "pytesseract não está instalado. Execute: pip install pytesseract\n"
            "Também é necessário ter o Tesseract-OCR instalado no sistema."
        )


def _import_pillow():
    """Importa Pillow com mensagem de erro amigável."""
    try:
        from PIL import Image
        return Image
    except ImportError:
        raise ImportError(
            "Pillow não está instalado. Execute: pip install Pillow"
        )


# ─── Funções públicas ─────────────────────────────────────────────────────────


def extract_text_from_pdf_native(file_path: str | Path) -> str:
    """
    Tenta extrair texto embutido de um PDF usando pypdf.

    Retorna string vazia se o PDF não tiver texto suficiente
    (ex.: PDF digitalizado).
    """
    pypdf = _import_pypdf()
    file_path = Path(file_path)
    text_parts: list[str] = []

    try:
        reader = pypdf.PdfReader(str(file_path))
        num_pages = len(reader.pages)

        if num_pages > MAX_PDF_PAGES:
            logger.warning(
                "PDF tem %d páginas (máx: %d). Processando apenas as primeiras %d.",
                num_pages, MAX_PDF_PAGES, MAX_PDF_PAGES,
            )
            num_pages = MAX_PDF_PAGES

        for i, page in enumerate(reader.pages[:num_pages]):
            try:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
                logger.debug("Página %d: %d caracteres extraídos.", i + 1, len(page_text))
            except Exception as exc:
                logger.warning("Erro a extrair texto da página %d: %s", i + 1, exc)

    except Exception as exc:
        logger.error("Erro ao abrir PDF '%s': %s", file_path, exc)
        return ""

    full_text = "\n".join(text_parts).strip()
    logger.info("Extracção nativa de PDF: %d caracteres no total.", len(full_text))
    return full_text


def extract_text_from_pdf_ocr(file_path: str | Path) -> str:
    """
    Renderiza as páginas de um PDF como imagens e aplica OCR.

    Usado quando o PDF não contém texto embutido suficiente.
    Cria ficheiros temporários que são apagados no finally.
    """
    convert_from_path = _import_pdf2image()
    pytesseract = _import_pytesseract()

    file_path = Path(file_path)
    text_parts: list[str] = []
    tmp_image_paths: list[str] = []

    try:
        logger.info("Convertendo PDF para imagens para OCR: %s", file_path.name)
        images = convert_from_path(str(file_path), dpi=200, last_page=MAX_PDF_PAGES)

        if len(images) > MAX_PDF_PAGES:
            logger.warning(
                "PDF tem %d páginas — processando apenas as primeiras %d.",
                len(images), MAX_PDF_PAGES,
            )
            images = images[:MAX_PDF_PAGES]

        for i, image in enumerate(images):
            # Guardar imagem temporariamente para evitar manter em memória
            with tempfile.NamedTemporaryFile(
                suffix=".png", delete=False, prefix="cert_ocr_page_"
            ) as tmp:
                tmp_path = tmp.name

            try:
                image.save(tmp_path, format="PNG")
                tmp_image_paths.append(tmp_path)
                page_text = _run_ocr_on_image(tmp_path, pytesseract)
                text_parts.append(page_text)
                logger.debug("OCR página %d: %d caracteres.", i + 1, len(page_text))
            finally:
                # Apagar imagem temporária desta página imediatamente
                _safe_delete(tmp_path)
                if tmp_path in tmp_image_paths:
                    tmp_image_paths.remove(tmp_path)

    except Exception as exc:
        logger.error("Erro durante OCR de PDF '%s': %s", file_path.name, exc)
    finally:
        # Garantir limpeza de qualquer ficheiro temporário restante
        for path in tmp_image_paths:
            _safe_delete(path)

    return "\n".join(text_parts).strip()


def extract_text_from_image(file_path: str | Path) -> str:
    """
    Aplica OCR directamente a uma imagem (PNG/JPG/JPEG).
    """
    pytesseract = _import_pytesseract()
    file_path = Path(file_path)

    logger.info("A executar OCR na imagem: %s", file_path.name)
    return _run_ocr_on_image(str(file_path), pytesseract)


def extract_text(file_path: str | Path, mime_type: Optional[str] = None) -> str:
    """
    Ponto de entrada principal — escolhe a estratégia de extracção
    baseada no tipo de ficheiro.

    - PDF: tenta extracção nativa primeiro; se insuficiente, usa OCR.
    - Imagem (PNG/JPG/JPEG): OCR directo.

    Retorna o texto extraído (pode ser vazio se o processamento falhar).
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    is_pdf = suffix == ".pdf" or (mime_type and "pdf" in mime_type.lower())
    is_image = suffix in {".png", ".jpg", ".jpeg"} or (
        mime_type and mime_type.lower().startswith("image/")
    )

    if is_pdf:
        logger.info("Ficheiro é PDF. A tentar extracção nativa de texto…")
        native_text = extract_text_from_pdf_native(file_path)

        if len(native_text.strip()) >= MIN_TEXT_CHARS:
            logger.info(
                "Texto nativo suficiente (%d chars). A usar extracção directa.",
                len(native_text),
            )
            return native_text

        logger.info(
            "Texto nativo insuficiente (%d chars). A recorrer a OCR…",
            len(native_text.strip()),
        )
        return extract_text_from_pdf_ocr(file_path)

    elif is_image:
        logger.info("Ficheiro é imagem. A executar OCR directamente…")
        return extract_text_from_image(file_path)

    else:
        logger.error("Tipo de ficheiro não suportado: %s (mime: %s)", suffix, mime_type)
        raise ValueError(f"Tipo de ficheiro não suportado: {suffix}")


# ─── Utilitários internos ─────────────────────────────────────────────────────


def _run_ocr_on_image(file_path: str, pytesseract) -> str:
    """
    Corre pytesseract numa imagem e retorna o texto.

    Tenta em português primeiro, depois em inglês como fallback,
    pois o certificado pode ter texto em ambas as línguas.
    """
    Image = _import_pillow()

    try:
        img = Image.open(file_path)
        # Tentar português + inglês para melhor cobertura do certificado bilingue
        text = pytesseract.image_to_string(img, lang="por+eng", timeout=OCR_TIMEOUT_SECS)
        return text or ""
    except Exception as exc:
        logger.warning(
            "OCR com lang='por+eng' falhou: %s. A tentar sem especificar língua…", exc
        )

    try:
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, timeout=OCR_TIMEOUT_SECS)
        return text or ""
    except Exception as exc:
        logger.error("OCR falhou completamente em '%s': %s", file_path, exc)
        return ""


def _safe_delete(file_path: str | Path) -> None:
    """Apaga um ficheiro sem lançar excepção se não existir."""
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.debug("Ficheiro temporário apagado: %s", path)
    except Exception as exc:
        logger.warning("Não foi possível apagar ficheiro temporário '%s': %s", file_path, exc)
