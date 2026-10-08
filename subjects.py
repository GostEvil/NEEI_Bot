"""Disciplinas da licenciatura. O código tem o formato [ano][semestre][nº] (ex: 1101 = 1º ano, 1º sem)."""

SUBJECTS: dict[str, str] = {
    # 1º ano — 1º semestre
    "1101": "Álgebra Linear e Geometria Analítica",
    "1102": "Cálculo",
    "1103": "Fundamentos da Programação",
    "1104": "Sistemas Digitais",
    "1105": "Sistemas Embebidos",
    # 1º ano — 2º semestre
    "1201": "Arquitetura de Computadores",
    "1202": "Engenharia de Software",
    "1203": "Estatística",
    "1204": "Matemática Discreta",
    "1205": "Programação Imperativa",
    # 2º ano — 1º semestre
    "2101": "Bases de Dados",
    "2102": "Interação Pessoa-Computador",
    "2103": "Programação Orientada por Objetos",
    "2104": "Redes de Computadores I",
    "2105": "Sistemas Operativos",
    # 2º ano — 2º semestre
    "2201": "Algoritmos e Estruturas de Dados",
    "2202": "Ciência dos Dados",
    "2203": "Computação Gráfica",
    "2204": "Segurança da Informação (Opção)",
    "2205": "Redes de Computadores II",
    # 3º ano — 1º semestre
    "3101": "Aprendizagem Automática",
    "3102": "Desenvolvimento Multiplataforma",
    "3103": "Gestão de Sistemas e de Redes",
    "3104": "Laboratório de Desenvolvimento Web",
    "3105": "Unidade Livre IPB I",
    # 3º ano — 2º semestre
    "3201": "Cibersegurança",
    "3202": "Projeto Disciplina (Terminal)",
    "3203": "Sistemas Distribuídos",
    "3204": "Unidade Livre IPB II",
}


def subject_label(code: str) -> str:
    """Devolve '[1102] Cálculo' (ou o próprio texto se o código for desconhecido)."""
    return f"[{code}] {SUBJECTS[code]}" if code in SUBJECTS else code


def subjects_for_semester(semester: int) -> dict[str, str]:
    return {c: n for c, n in SUBJECTS.items() if c[1] == str(semester)}
