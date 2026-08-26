import json
from pathlib import Path
from typing import Optional
from src.core.models import CompanyConfig
from src.utils.paths import get_data_dir


CONFIG_FILE = get_data_dir() / "company_config.json"
RESTORE_KEY_FILE = get_data_dir() / "restore.key"


def load_company_config() -> Optional[CompanyConfig]:
    """Carrega configuração da empresa do arquivo JSON."""
    if not CONFIG_FILE.exists():
        return None
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        return CompanyConfig(**data)
    except Exception:
        return None


def save_company_config(config: CompanyConfig) -> bool:
    """Salva configuração da empresa no arquivo JSON."""
    try:
        CONFIG_FILE.write_text(
            json.dumps(config.model_dump(mode='json'), indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        return True
    except Exception as e:
        import traceback
        print(f"[ERRO save_company_config] {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


def is_configured() -> bool:
    """Sempre retorna True - dados fixos da empresa."""
    return True


DEFAULT_RESTORE_PASSWORD = "Joaopedro2309"


def ensure_default_restore_password() -> bool:
    """Garante que a senha de restauração padrão esteja configurada."""
    if has_restore_password():
        return True
    return set_restore_password(DEFAULT_RESTORE_PASSWORD)


# --- Restore Password (hash armazenado) ---
import argon2

_ph = argon2.PasswordHasher()


def set_restore_password(password: str) -> bool:
    """Define a senha de restauração (hash Argon2)."""
    try:
        hash_str = _ph.hash(password)
        RESTORE_KEY_FILE.write_text(hash_str, encoding='utf-8')
        return True
    except Exception:
        return False


def verify_restore_password(password: str) -> bool:
    """Verifica a senha de restauração."""
    if not RESTORE_KEY_FILE.exists():
        return False
    try:
        stored_hash = RESTORE_KEY_FILE.read_text(encoding='utf-8').strip()
        _ph.verify(stored_hash, password)
        return True
    except Exception:
        return False


def has_restore_password() -> bool:
    """Verifica se já existe senha de restauração configurada."""
    return RESTORE_KEY_FILE.exists()