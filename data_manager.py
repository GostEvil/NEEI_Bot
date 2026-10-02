import json
import os
import datetime
from pathlib import Path

# Caminho para o ficheiro de dados dos admins
ADMINS_FILE = Path("data/admins.json")
LOGS_FILE = Path("data/logs.json")


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


def _ensure_logs_file():
    """Garante que o ficheiro de logs existe."""
    LOGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOGS_FILE.exists():
        LOGS_FILE.write_text(json.dumps([], indent=2))


def add_log(actor_id: str, actor_role: str, action: str, target_id: str = None, details: str = ""):
    """Adiciona um registo aos logs."""
    _ensure_logs_file()
    try:
        logs = json.loads(LOGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        logs = []
    
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "target_id": target_id,
        "details": details
    }
    logs.append(log_entry)
    LOGS_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


def get_logs() -> list[dict]:
    """Retorna todos os logs registados."""
    _ensure_logs_file()
    try:
        return json.loads(LOGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
