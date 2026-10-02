import json
import os
from pathlib import Path

# Caminho para o ficheiro de dados dos admins
ADMINS_FILE = Path("data/admins.json")


def _ensure_file():
    """Garante que o ficheiro e a pasta existem."""
    ADMINS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ADMINS_FILE.exists():
        ADMINS_FILE.write_text(json.dumps({"admins": []}, indent=2))


def load_admins() -> list[str]:
    """Carrega a lista de IDs de admins do ficheiro."""
    _ensure_file()
    data = json.loads(ADMINS_FILE.read_text())
    return data.get("admins", [])


def save_admins(admins: list[str]) -> None:
    """Guarda a lista de IDs de admins no ficheiro."""
    _ensure_file()
    ADMINS_FILE.write_text(json.dumps({"admins": admins}, indent=2))


def add_admin(user_id: str) -> bool:
    """
    Adiciona um admin à lista.
    Retorna True se adicionado com sucesso, False se já existia.
    """
    admins = load_admins()
    if user_id in admins:
        return False
    admins.append(user_id)
    save_admins(admins)
    return True


def remove_admin(user_id: str) -> bool:
    """
    Remove um admin da lista.
    Retorna True se removido com sucesso, False se não existia.
    """
    admins = load_admins()
    if user_id not in admins:
        return False
    admins.remove(user_id)
    save_admins(admins)
    return True


def is_admin(user_id: str) -> bool:
    """Verifica se um utilizador é admin."""
    return user_id in load_admins()
