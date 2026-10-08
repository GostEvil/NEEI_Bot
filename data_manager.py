import copy
import json
import os
import datetime
from pathlib import Path

# Caminho para o ficheiro de dados dos admins
ADMINS_FILE = Path("data/admins.json")
LOGS_FILE = Path("data/logs.json")
CERT_CONFIG_FILE = Path("data/cert_config.json")


def _atomic_write(path: Path, content: str) -> None:
    """Escreve para um .tmp e substitui o ficheiro final (evita ficheiros corrompidos)."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _ensure_file():
    """Garante que o ficheiro e a pasta existem."""
    ADMINS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ADMINS_FILE.exists():
        ADMINS_FILE.write_text(json.dumps({"admins": []}, indent=2))


def load_admins() -> list[str]:
    """Carrega a lista de IDs de admins do ficheiro."""
    _ensure_file()
    try:
        data = json.loads(ADMINS_FILE.read_text(encoding="utf-8"))
        admins = data.get("admins", [])
        return admins if isinstance(admins, list) else []
    except Exception:
        return []


def save_admins(admins: list[str]) -> None:
    """Guarda a lista de IDs de admins no ficheiro."""
    _ensure_file()
    _atomic_write(ADMINS_FILE, json.dumps({"admins": admins}, indent=2))


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
    if not isinstance(logs, list):
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
    _atomic_write(LOGS_FILE, json.dumps(logs, indent=2, ensure_ascii=False))


def get_logs() -> list[dict]:
    """Retorna todos os logs registados."""
    _ensure_logs_file()
    try:
        logs = json.loads(LOGS_FILE.read_text(encoding="utf-8"))
        return logs if isinstance(logs, list) else []
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────
# Configuração da Verificação 1 (anos letivos + canal de alerta)
# ─────────────────────────────────────────────────────────────

_CERT_CONFIG_DEFAULT = {"allowed_years": [], "alert_channel_id": None}


def _ensure_cert_config_file() -> None:
    """Garante que o ficheiro de configuração de certificados existe."""
    CERT_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CERT_CONFIG_FILE.exists():
        CERT_CONFIG_FILE.write_text(
            json.dumps(_CERT_CONFIG_DEFAULT, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _load_cert_config() -> dict:
    """Carrega a configuração de certificados do ficheiro."""
    _ensure_cert_config_file()
    try:
        data = json.loads(CERT_CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return copy.deepcopy(_CERT_CONFIG_DEFAULT)
        # Garantir chaves esperadas mesmo que o ficheiro seja antigo
        data.setdefault("allowed_years", [])
        data.setdefault("alert_channel_id", None)
        return data
    except Exception:
        return copy.deepcopy(_CERT_CONFIG_DEFAULT)


def _save_cert_config(data: dict) -> None:
    """Guarda a configuração de certificados no ficheiro."""
    _ensure_cert_config_file()
    _atomic_write(CERT_CONFIG_FILE, json.dumps(data, indent=2, ensure_ascii=False))


def get_allowed_years() -> list[str]:
    """Retorna a lista de anos letivos permitidos (ex: ['2025/2026', '2026/2027'])."""
    years = _load_cert_config()["allowed_years"]
    return years if isinstance(years, list) else []


def add_allowed_year(year: str) -> bool:
    """
    Adiciona um ano letivo à lista de anos permitidos.
    Retorna True se adicionado, False se já existia.
    """
    data = _load_cert_config()
    if year in data["allowed_years"]:
        return False
    data["allowed_years"].append(year)
    _save_cert_config(data)
    return True


def remove_allowed_year(year: str) -> bool:
    """
    Remove um ano letivo da lista de anos permitidos.
    Retorna True se removido, False se não existia.
    """
    data = _load_cert_config()
    if year not in data["allowed_years"]:
        return False
    data["allowed_years"].remove(year)
    _save_cert_config(data)
    return True


def get_cert_alert_channel_id() -> int | None:
    """Retorna o ID do canal de alerta para certificados com ano inválido."""
    raw = _load_cert_config()["alert_channel_id"]
    try:
        return int(raw) if raw else None
    except (TypeError, ValueError):
        return None


def set_cert_alert_channel_id(channel_id: int | None) -> None:
    """Define o ID do canal de alerta para certificados com ano inválido."""
    data = _load_cert_config()
    data["alert_channel_id"] = channel_id
    _save_cert_config(data)


# ─────────────────────────────────────────────────────────────
# Controlo de duplicados (nº mecanográfico -> utilizador Discord)
# ─────────────────────────────────────────────────────────────

VERIFIED_FILE = Path("data/verified.json")


def _load_verified() -> dict:
    try:
        data = json.loads(VERIFIED_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_verified_owner(mech_number: str) -> str | None:
    """Retorna o ID Discord que já verificou este nº mecanográfico (ou None)."""
    return _load_verified().get(mech_number.lower())


def register_verified(mech_number: str, user_id: str) -> None:
    """Associa um nº mecanográfico ao utilizador Discord que o verificou."""
    VERIFIED_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = _load_verified()
    data[mech_number.lower()] = str(user_id)
    _atomic_write(VERIFIED_FILE, json.dumps(data, indent=2, ensure_ascii=False))


# ─────────────────────────────────────────────────────────────
# Calendário de avaliações (/calendario)
# ─────────────────────────────────────────────────────────────

CALENDAR_FILE = Path("data/calendar.json")


def _load_calendar() -> list[dict]:
    try:
        data = json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def get_calendar() -> list[dict]:
    """Retorna todos os eventos do calendário, ordenados por data."""
    return sorted(_load_calendar(), key=lambda e: e.get("date", ""))


def add_calendar_event(kind: str, subject: str, date: str) -> bool:
    """
    Adiciona um evento (date em ISO AAAA-MM-DD).
    Retorna True se adicionado, False se já existia.
    """
    events = _load_calendar()
    key = (kind, subject.lower(), date)
    if any((e["kind"], e["subject"].lower(), e["date"]) == key for e in events):
        return False
    events.append({"kind": kind, "subject": subject, "date": date})
    CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(CALENDAR_FILE, json.dumps(events, indent=2, ensure_ascii=False))
    return True


def remove_calendar_event(kind: str, subject: str, date: str) -> bool:
    """Remove um evento. Retorna True se removido, False se não existia."""
    events = _load_calendar()
    key = (kind, subject.lower(), date)
    kept = [e for e in events if (e["kind"], e["subject"].lower(), e["date"]) != key]
    if len(kept) == len(events):
        return False
    _atomic_write(CALENDAR_FILE, json.dumps(kept, indent=2, ensure_ascii=False))
    return True


CALENDAR_CONFIG_FILE = Path("data/calendar_config.json")


def get_calendar_channel_id() -> int | None:
    """Retorna o ID do canal onde o bot publica os eventos do calendário."""
    try:
        data = json.loads(CALENDAR_CONFIG_FILE.read_text(encoding="utf-8"))
        return int(data["channel_id"]) if data.get("channel_id") else None
    except Exception:
        return None


def set_calendar_channel_id(channel_id: int | None) -> None:
    """Define o ID do canal onde o bot publica os eventos do calendário."""
    CALENDAR_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(CALENDAR_CONFIG_FILE, json.dumps({"channel_id": channel_id}, indent=2))
