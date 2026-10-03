import os
from dotenv import load_dotenv

load_dotenv()


def get_token() -> str:
    token = os.getenv("DISCORD_TOKEN", "")
    if not token:
        raise ValueError("DISCORD_TOKEN não está definido no ficheiro .env")
    return token


def get_guild_id() -> int:
    guild_id = os.getenv("GUILD_ID", "")
    if not guild_id:
        raise ValueError("GUILD_ID não está definido no ficheiro .env")
    return int(guild_id)


def get_manager_ids() -> list[str]:
    """
    Carrega os IDs dos managers a partir da variável MANAGER_IDS no .env.
    Formato esperado: MANAGER_IDS=123456789,987654321
    """
    raw = os.getenv("MANAGER_IDS", "")
    if not raw:
        raise ValueError("MANAGER_IDS não está definido no ficheiro .env")
    return [uid.strip() for uid in raw.split(",") if uid.strip()]


def get_neei_role_name() -> str:
    return os.getenv("NEEI_ROLE_NAME", "NEEI")


def get_target_channel_id() -> int | None:
    """Retorna o ID do canal de destino definido no .env (opcional)."""
    channel_id = os.getenv("TARGET_CHANNEL_ID", "").strip()
    if channel_id and channel_id.isdigit():
        return int(channel_id)
    return None


def is_manager(user_id: str) -> bool:
    """Verifica se um user_id pertence a um manager definido no .env."""
    return user_id in get_manager_ids()


def get_verify_role_id() -> int | None:
    """Retorna o ID do cargo de verificação, se configurado."""
    role_id = os.getenv("VERIFY_ROLE_ID", "").strip()
    if role_id and role_id.isdigit():
        return int(role_id)
    return None


def get_certificate_verification_channel_id() -> int | None:
    """Retorna o ID do canal onde o comando /verificacao1 pode ser usado (opcional)."""
    channel_id = os.getenv("CERTIFICATE_VERIFICATION_CHANNEL_ID", "").strip()
    if channel_id and channel_id.isdigit():
        return int(channel_id)
    return None


def get_certificate_verification_log_channel_id() -> int | None:
    """Retorna o ID do canal privado de logs da Verificação 1."""
    channel_id = os.getenv("CERTIFICATE_VERIFICATION_LOG_CHANNEL_ID", "").strip()
    if channel_id and channel_id.isdigit():
        return int(channel_id)
    return None


def set_verify_role_id(role_id: int):
    """Define o ID do cargo de verificação no .env."""
    from dotenv import set_key, find_dotenv
    dotenv_path = find_dotenv()
    if not dotenv_path:
        dotenv_path = ".env"
    set_key(dotenv_path, "VERIFY_ROLE_ID", str(role_id))
    os.environ["VERIFY_ROLE_ID"] = str(role_id)

