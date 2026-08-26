import json
from pathlib import Path
from typing import Dict, List, Optional
from src.core.models import NRTemplate, LayoutConfig
from src.utils.paths import get_templates_dir, get_assets_dir


def load_layout_config() -> LayoutConfig:
    """Carrega configuração de layout visual."""
    layout_path = get_templates_dir() / "_layout.json"
    if layout_path.exists():
        try:
            data = json.loads(layout_path.read_text(encoding='utf-8'))
            return LayoutConfig(**data)
        except Exception:
            pass
    # Fallback padrão
    return LayoutConfig()


def load_nr_template(nr_code: str) -> Optional[NRTemplate]:
    """Carrega template de um NR específico."""
    template_path = get_templates_dir() / f"{nr_code}.template.json"
    if not template_path.exists():
        return None
    try:
        data = json.loads(template_path.read_text(encoding='utf-8'))
        return NRTemplate(**data)
    except Exception as e:
        print(f"Erro ao carregar template {nr_code}: {e}")
        return None


def list_available_nrs() -> List[str]:
    """Lista códigos de NRs disponíveis (arquivos .template.json)."""
    templates_dir = get_templates_dir()
    nrs = []
    for f in templates_dir.glob("NR-*.template.json"):
        nr_code = f.stem.replace(".template", "")
        nrs.append(nr_code)
    return sorted(nrs)


def load_all_templates() -> Dict[str, NRTemplate]:
    """Carrega todos os templates disponíveis."""
    templates = {}
    for nr_code in list_available_nrs():
        template = load_nr_template(nr_code)
        if template:
            templates[nr_code] = template
    return templates


def get_template_description(nr_code: str) -> str:
    """Retorna descrição padrão do NR para exibição na UI."""
    template = load_nr_template(nr_code)
    if template:
        return f"{template.nr_code} - {template.nr_name}"
    return nr_code