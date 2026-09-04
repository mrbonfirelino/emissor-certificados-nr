import sys
from pathlib import Path


def get_project_root() -> Path:
    """Raiz do projeto (src/ -> project root). Funciona em dev e frozen."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    current = Path(__file__).resolve()
    while current.name != 'src' and current.parent != current:
        current = current.parent
    return current.parent if current.name == 'src' else current


def get_bundled_path() -> Path:
    """Pasta de recursos embutidos no executável (templates, assets, fonts)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return get_project_root()


def get_base_path() -> Path:
    """Alias para get_project_root() — mantido por compatibilidade."""
    return get_project_root()


def get_data_dir() -> Path:
    """Pasta de dados (ao lado do exe, para dados graváveis do usuário)."""
    base = get_project_root()
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_templates_dir() -> Path:
    """Pasta de templates (externa ao lado do exe, ou embutida no exe)."""
    if getattr(sys, 'frozen', False):
        external = get_project_root() / "templates"
        if external.exists():
            return external
    return get_bundled_path() / "templates"


def get_assets_dir() -> Path:
    """Pasta de assets (recursos embutidos no exe)."""
    return get_bundled_path() / "assets"


def get_db_path() -> Path:
    """Caminho do banco de dados SQLite."""
    return get_data_dir() / "certificados.db"


def get_backup_dir() -> Path:
    """Pasta de backups."""
    backup_dir = get_data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_fonts_dir() -> Path:
    """Pasta de fontes."""
    return get_assets_dir() / "fonts"


def get_logo_path() -> Path:
    """Caminho do logo."""
    return get_assets_dir() / "LOGO TIPO ALTEC.png"


def get_icon_path() -> Path:
    """Caminho do ícone .ico."""
    return get_assets_dir() / "logo.ico"


def get_config_dir() -> Path:
    """Pasta de configuração do usuário (para restore.key)."""
    return get_data_dir()


def get_certificados_dir() -> Path:
    """Pasta de certificados emitidos (data/certificados, por funcionário/NR)."""
    cert_dir = get_data_dir() / "certificados"
    cert_dir.mkdir(parents=True, exist_ok=True)
    return cert_dir


def get_legacy_certificados_dir() -> Path:
    """Pasta antiga de certificados (raiz/CERTIFICADOS) — usada só na migração."""
    return get_project_root() / "CERTIFICADOS"


def get_cartoes_dir() -> Path:
    """Pasta de cartões de bloqueio (data/cartoes)."""
    cartoes_dir = get_data_dir() / "cartoes"
    cartoes_dir.mkdir(parents=True, exist_ok=True)
    return cartoes_dir


def get_assinados_dir() -> Path:
    """Pasta de certificados assinados exportados (data/assinados)."""
    assinados_dir = get_data_dir() / "assinados"
    assinados_dir.mkdir(parents=True, exist_ok=True)
    return assinados_dir


def get_asos_dir() -> Path:
    """Pasta de ASOs gerados (data/asos, por funcionário)."""
    asos_dir = get_data_dir() / "asos"
    asos_dir.mkdir(parents=True, exist_ok=True)
    return asos_dir


def get_epis_dir() -> Path:
    """Pasta de fichas de EPI (data/epis, por funcionário)."""
    epis_dir = get_data_dir() / "epis"
    epis_dir.mkdir(parents=True, exist_ok=True)
    return epis_dir


def get_crachas_dir() -> Path:
    """Pasta de crachás de identificação (data/crachas, por funcionário)."""
    crachas_dir = get_data_dir() / "crachas"
    crachas_dir.mkdir(parents=True, exist_ok=True)
    return crachas_dir