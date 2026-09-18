"""Armazenamento das funcoes cadastradas (data/funcoes.json).

Extraido de src/ui/pages/funcoes.py para que modulos do portal/importadores
possam usar sem arrastar customtkinter (o servidor nao tem interface
grafica). A pagina desktop importa daqui tambem.
"""

import json

from src.utils.paths import get_data_dir

FUNCOES_FILE = get_data_dir() / "funcoes.json"

DEFAULT_FUNCOES = []


def load_funcoes() -> list:
    if FUNCOES_FILE.exists():
        try:
            data = json.loads(FUNCOES_FILE.read_text(encoding="utf-8"))
            return data.get("funcoes", DEFAULT_FUNCOES)
        except Exception:
            pass
    return DEFAULT_FUNCOES


def save_funcoes(funcoes: list):
    FUNCOES_FILE.write_text(
        json.dumps({"funcoes": funcoes}, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
