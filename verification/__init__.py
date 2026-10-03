"""
Módulo de Verificação 1 — Certificado Multiusos do IPB.

Este pacote é responsável por:
- Extrair texto de PDFs e imagens (OCR)
- Validar que o documento é um Certificado Multiusos do IPB / Engenharia Informática
- Extrair nome, número mecanográfico e documento de identificação
- Gerar o nickname Discord no formato "Primeiro Último (NúmeroMecanográfico)"
- Coordenar todo o processo de verificação

A Verificação 2 (autenticação pelo sistema interno do IPB) é da responsabilidade
de um segundo bot separado. Ver TODO.md para detalhes.
"""

from .certificate import verify_certificate

__all__ = ["verify_certificate"]
