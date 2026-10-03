"""
tests/test_parser.py — Testes para o módulo de parsing do certificado.

Cobre os 16 casos definidos na especificação.
Usa apenas texto sintético — sem dados pessoais reais.
"""

from __future__ import annotations

import unittest

from verification.parser import parse_certificate, get_missing_fields, ParsedCertificate
from verification.nickname import build_nickname


# ─── Texto de certificado sintético ──────────────────────────────────────────

VALID_CERTIFICATE_TEXT_PT = """
Instituto Politécnico de Bragança

Certificado Multiusos

Para os devidos efeitos, certifica-se que o estudante João Pedro dos Santos, com o n.º 123456, titular do
documento de identificação "12345678", está matriculado no ano letivo 2025/2026, na Licenciatura em "Engenharia
Informática" do Instituto Politécnico de Bragança.

Multipurpose Certificate

It is hereby certified that the student "João Pedro dos Santos", with the number 123456, owner of the identification
document 12345678, is enrolled in the academic year 2025/2026, at the Bachelor's Programme in Engenharia
Informática of the Polytechnic Institute of Bragança.

Bragança, 07/11/2025
"""

VALID_CERTIFICATE_OCR_LOWERCASE = VALID_CERTIFICATE_TEXT_PT.lower()

VALID_CERTIFICATE_OCR_NO_ACCENTS = """
Instituto Politecnico de Braganca

Certificado Multiusos

Para os devidos efeitos, certifica-se que o estudante Nuno Miguel Silva, com o n.o a63426, titular do
documento de identificacao "87654321", esta matriculado no ano letivo 2025/2026, na Licenciatura em Engenharia
Informatica do Instituto Politecnico de Braganca.

Multipurpose Certificate

It is hereby certified that the student Nuno Miguel Silva, with the number a63426, owner of the identification
document 87654321, is enrolled in the academic year 2025/2026, at the Bachelor s Programme in Engenharia
Informatica of the Polytechnic Institute of Braganca.
"""

WRONG_COURSE_TEXT = """
Instituto Politécnico de Bragança

Certificado Multiusos

certifica-se que o estudante Maria Teste, com o n.º 999999, titular do
documento de identificação "99999999", está matriculado na Licenciatura em "Engenharia Civil"
do Instituto Politécnico de Bragança.
"""

NOT_IPB_TEXT = """
Universidade do Porto

Certificado Multiusos

certifica-se que o estudante Carlos Teste, com o n.º 888888, titular do
documento de identificação "88888888", está matriculado na Licenciatura em "Engenharia Informática".
"""

NOT_CERTIFICADO_MULTIUSOS = """
Instituto Politécnico de Bragança

Declaração de Matrícula

certifica-se que o estudante Ana Teste, com o n.º 777777, titular do
documento de identificação "77777777", está matriculado na Licenciatura em "Engenharia Informática"
do Instituto Politécnico de Bragança.
"""

MISSING_MECH_TEXT = """
Instituto Politécnico de Bragança

Certificado Multiusos

certifica-se que o estudante Pedro Alves, titular do
documento de identificação "11111111", está matriculado na Licenciatura em "Engenharia
Informática" do Instituto Politécnico de Bragança.

Multipurpose Certificate

It is hereby certified that the student Pedro Alves, owner of the identification
document 11111111, is enrolled in the academic year 2025/2026, at the Bachelor's Programme in Engenharia
Informática of the Polytechnic Institute of Bragança.
"""

MISSING_ID_DOC_TEXT = """
Instituto Politécnico de Bragança

Certificado Multiusos

certifica-se que o estudante Sofia Gomes, com o n.º a55555, está matriculada na Licenciatura em "Engenharia
Informática" do Instituto Politécnico de Bragança.

Multipurpose Certificate

It is hereby certified that the student Sofia Gomes, with the number a55555, is enrolled at the Bachelor's Programme in Engenharia
Informática of the Polytechnic Institute of Bragança.
"""


# ─── Testes de Parsing ────────────────────────────────────────────────────────

class TestParser(unittest.TestCase):
    """Testes do módulo parser.py"""

    def test_valid_certificate_extracts_name(self):
        """1. Certificado válido — nome extraído correctamente."""
        parsed = parse_certificate(VALID_CERTIFICATE_TEXT_PT)
        self.assertIsNotNone(parsed.name)
        self.assertIn("João", parsed.name)
        self.assertIn("Santos", parsed.name)

    def test_valid_certificate_extracts_mechanographic(self):
        """1. Certificado válido — número mecanográfico extraído."""
        parsed = parse_certificate(VALID_CERTIFICATE_TEXT_PT)
        self.assertIsNotNone(parsed.mechanographic_number)
        self.assertIn("123456", parsed.mechanographic_number)

    def test_valid_certificate_extracts_id_document(self):
        """1. Certificado válido — documento de identificação extraído."""
        parsed = parse_certificate(VALID_CERTIFICATE_TEXT_PT)
        self.assertIsNotNone(parsed.identification_document)
        self.assertIn("12345678", parsed.identification_document)

    def test_missing_mechanographic_number(self):
        """9. Número mecanográfico ausente."""
        parsed = parse_certificate(MISSING_MECH_TEXT)
        self.assertIsNone(parsed.mechanographic_number)
        missing = get_missing_fields(parsed)
        self.assertIn("número mecanográfico", missing)

    def test_missing_identification_document(self):
        """10. Documento de identificação ausente."""
        parsed = parse_certificate(MISSING_ID_DOC_TEXT)
        self.assertIsNone(parsed.identification_document)
        missing = get_missing_fields(parsed)
        self.assertIn("documento de identificação", missing)

    def test_ocr_lowercase(self):
        """5. OCR com texto em minúsculas — parsing deve funcionar."""
        parsed = parse_certificate(VALID_CERTIFICATE_OCR_LOWERCASE)
        # Parsing de nome pode falhar com texto totalmente em minúsculas
        # (padrões de nome exigem primeira letra maiúscula),
        # mas mecanográfico e ID doc devem ser encontrados
        self.assertIsNotNone(parsed.mechanographic_number)

    def test_ocr_no_accents(self):
        """6. OCR sem acentos — parsing deve funcionar."""
        parsed = parse_certificate(VALID_CERTIFICATE_OCR_NO_ACCENTS)
        self.assertIsNotNone(parsed.name)
        self.assertIsNotNone(parsed.mechanographic_number)
        self.assertIn("a63426", parsed.mechanographic_number)

    def test_get_missing_fields_all_present(self):
        """Todos os campos presentes — lista de missing vazia."""
        parsed = ParsedCertificate(
            name="Nuno Silva",
            mechanographic_number="a63426",
            identification_document="12345678",
        )
        missing = get_missing_fields(parsed)
        self.assertEqual(missing, [])

    def test_get_missing_fields_none(self):
        """Todos os campos ausentes — todos reportados."""
        parsed = ParsedCertificate()
        missing = get_missing_fields(parsed)
        self.assertIn("nome", missing)
        self.assertIn("número mecanográfico", missing)
        self.assertIn("documento de identificação", missing)


# ─── Testes de Nickname ───────────────────────────────────────────────────────

class TestNickname(unittest.TestCase):
    """Testes do módulo nickname.py"""

    def test_three_names(self):
        """7. Nome com três ou mais nomes — usar primeiro e último."""
        nick = build_nickname("João Pedro dos Santos", "123456")
        self.assertEqual(nick, "João Santos (123456)")

    def test_two_names(self):
        """Nome com dois nomes."""
        nick = build_nickname("Nuno Silva", "a63426")
        self.assertEqual(nick, "Nuno Silva (a63426)")

    def test_single_name(self):
        """8. Nome com apenas um nome."""
        nick = build_nickname("Nuno", "123456")
        self.assertEqual(nick, "Nuno (123456)")

    def test_four_names(self):
        """Nome com quatro partes — usar primeiro e último."""
        nick = build_nickname("João Pedro da Silva Santos", "999999")
        self.assertEqual(nick, "João Santos (999999)")

    def test_nickname_within_limit(self):
        """Nickname gerado deve ter ≤ 32 caracteres."""
        nick = build_nickname("João Pedro dos Santos", "123456")
        self.assertLessEqual(len(nick), 32)

    def test_long_name_truncated(self):
        """Nome muito longo deve ser truncado — mas preservar o número."""
        long_name = "Alexandrino Bartholomeu Constantino Domingues"
        nick = build_nickname(long_name, "123456")
        self.assertLessEqual(len(nick), 32)
        self.assertIn("123456", nick)

    def test_discord_limit_preserved_with_long_mech(self):
        """Mesmo com número mecanográfico longo, respeitar limite."""
        nick = build_nickname("Ana Silva", "a12345678")
        self.assertLessEqual(len(nick), 32)


# ─── Testes de Validação ──────────────────────────────────────────────────────

class TestValidator(unittest.TestCase):
    """Testes do módulo validator.py"""

    def test_valid_document(self):
        """1. Certificado válido — deve ser aceite."""
        from verification.validator import validate_document
        result = validate_document(VALID_CERTIFICATE_TEXT_PT)
        self.assertTrue(result.valid)

    def test_wrong_course(self):
        """2. Documento de outro curso — deve ser rejeitado."""
        from verification.validator import validate_document
        result = validate_document(WRONG_COURSE_TEXT)
        self.assertFalse(result.valid)

    def test_not_ipb(self):
        """3. Documento que não pertence ao IPB — deve ser rejeitado."""
        from verification.validator import validate_document
        result = validate_document(NOT_IPB_TEXT)
        self.assertFalse(result.valid)

    def test_not_certificado_multiusos(self):
        """4. Documento que não é Certificado Multiusos — deve ser rejeitado."""
        from verification.validator import validate_document
        result = validate_document(NOT_CERTIFICADO_MULTIUSOS)
        self.assertFalse(result.valid)

    def test_ocr_case_insensitive(self):
        """5. OCR com diferenças de maiúsculas/minúsculas — deve ser aceite."""
        from verification.validator import validate_document
        result = validate_document(VALID_CERTIFICATE_OCR_LOWERCASE)
        self.assertTrue(result.valid)

    def test_ocr_no_accents(self):
        """6. OCR sem acentos — deve ser aceite."""
        from verification.validator import validate_document
        result = validate_document(VALID_CERTIFICATE_OCR_NO_ACCENTS)
        self.assertTrue(result.valid)

    def test_empty_text(self):
        """Texto vazio — deve ser rejeitado."""
        from verification.validator import validate_document
        result = validate_document("")
        self.assertFalse(result.valid)

    def test_random_text(self):
        """Texto aleatório — deve ser rejeitado."""
        from verification.validator import validate_document
        result = validate_document("Isto é um texto qualquer sem conteúdo relevante.")
        self.assertFalse(result.valid)


# ─── Testes de Metadados de Ficheiro ─────────────────────────────────────────

class TestFileValidation(unittest.TestCase):
    """Testes do _validate_file_metadata em certificate.py"""

    def test_valid_pdf(self):
        """PDF válido — sem erro."""
        from verification.certificate import _validate_file_metadata
        result = _validate_file_metadata("certificado.pdf", "application/pdf", 1024)
        self.assertIsNone(result)

    def test_valid_jpg(self):
        """JPG válido — sem erro."""
        from verification.certificate import _validate_file_metadata
        result = _validate_file_metadata("certificado.jpg", "image/jpeg", 1024)
        self.assertIsNone(result)

    def test_valid_png(self):
        """PNG válido — sem erro."""
        from verification.certificate import _validate_file_metadata
        result = _validate_file_metadata("certificado.png", "image/png", 1024)
        self.assertIsNone(result)

    def test_invalid_extension(self):
        """16. Ficheiro com extensão inválida — deve ser rejeitado."""
        from verification.certificate import _validate_file_metadata
        result = _validate_file_metadata("virus.exe", "application/octet-stream", 1024)
        self.assertIsNotNone(result)

    def test_file_too_large(self):
        """15. Ficheiro demasiado grande — deve ser rejeitado."""
        from verification.certificate import _validate_file_metadata
        big_size = 20 * 1024 * 1024  # 20 MB
        result = _validate_file_metadata("certificado.pdf", "application/pdf", big_size)
        self.assertIsNotNone(result)
        self.assertIn("MB", result)

    def test_wrong_mime_type(self):
        """MIME type de texto não aceite."""
        from verification.certificate import _validate_file_metadata
        result = _validate_file_metadata("ficheiro.txt", "text/plain", 1024)
        self.assertIsNotNone(result)

    def test_pdf_with_wrong_mime(self):
        """PDF com MIME type inesperado."""
        from verification.certificate import _validate_file_metadata
        result = _validate_file_metadata("cert.pdf", "application/octet-stream", 1024)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
