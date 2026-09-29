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


def is_manager(user_id: str) -> bool:
    """Verifica se um user_id pertence a um manager definido no .env."""
    return user_id in get_manager_ids()
