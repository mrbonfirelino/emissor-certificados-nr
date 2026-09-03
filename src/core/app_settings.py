"""
Preferencias do aplicativo (data/app_settings.json).

Segue o padrao do font_scale.json: JSON simples em get_data_dir(),
com defaults centralizados e merge automatico para chaves novas.
"""

import json
from typing import Any, Dict

from src.utils.paths import get_data_dir

SETTINGS_FILE = get_data_dir() / "app_settings.json"

DEFAULTS: Dict[str, Any] = {
    "notificacoes_ativas": True,
    "backup_intervalo_min": 15,
    "backup_duplo": True,
    "backup_rede_ativo": True,
    "backup_rede_caminho": r"Z:\SEGURANÇA\NORMATECH-BACKUP",
    "painel_inicial_visivel": True,
}


def load_app_settings() -> Dict[str, Any]:
    """Carrega settings com defaults para chaves ausentes."""
    settings = dict(DEFAULTS)
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                settings.update({k: v for k, v in data.items() if k in DEFAULTS})
    except Exception:
        pass
    return settings


def save_app_settings(settings: Dict[str, Any]) -> None:
    """Salva apenas chaves conhecidas (defaults como base)."""
    data = dict(DEFAULTS)
    data.update({k: v for k, v in settings.items() if k in DEFAULTS})
    try:
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_setting(key: str, default: Any = None) -> Any:
    return load_app_settings().get(key, DEFAULTS.get(key, default))


def set_setting(key: str, value: Any) -> None:
    settings = load_app_settings()
    settings[key] = value
    save_app_settings(settings)
