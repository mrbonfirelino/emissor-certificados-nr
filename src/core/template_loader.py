import json
from pathlib import Path
from typing import Dict, List, Optional
from src.core.models import NRTemplate, LayoutConfig
from src.utils.paths import get_templates_dir, get_assets_dir, get_data_dir

# v1.75.0: personalizacoes de template (carga/validade) persistem em data/,
# fora do alcance do robocopy /MIR das atualizacoes.
_OVERRIDES_PATH = get_data_dir() / "template_overrides.json"
_OVERRIDABLE = ("carga_horaria_minima", "validade_meses")


def load_template_overrides() -> Dict[str, dict]:
    try:
        return json.loads(_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_template_override(nr_code: str, **campos) -> None:
    """Grava campos que devem sobreviver a atualizacoes do app."""
    ov = load_template_overrides()
    ent = ov.get(nr_code, {})
    for k, v in campos.items():
        if k in _OVERRIDABLE and v is not None:
            ent[k] = v
    if ent:
        ov[nr_code] = ent
    try:
        _OVERRIDES_PATH.write_text(
            json.dumps(ov, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"Erro ao gravar overrides de template: {e}")


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
        # v1.75.0: aplica overrides persistentes (sobrevivem a atualizacoes)
        ov = load_template_overrides().get(nr_code, {})
        for k in _OVERRIDABLE:
            if k in ov:
                data[k] = ov[k]
        return NRTemplate(**data)
    except Exception as e:
        print(f"Erro ao carregar template {nr_code}: {e}")
        return None


def list_available_nrs() -> List[str]:
    """Lista códigos de templates disponíveis (arquivos .template.json)."""
    templates_dir = get_templates_dir()
    nrs = []
    for f in templates_dir.glob("*.template.json"):
        nr_code = f.stem.replace(".template", "")
        nrs.append(nr_code)
    return sorted(nrs)


_all_templates_cache: Optional[Dict[str, NRTemplate]] = None
_all_templates_sig: Optional[tuple] = None


def load_all_templates() -> Dict[str, NRTemplate]:
    """Carrega todos os templates disponíveis.

    v1.81.2: cache em memória revalidado pela assinatura (mtime dos
    arquivos + overrides) — editar template continua valendo na hora,
    mas o painel deixa de reler ~30 JSONs em cada requisição."""
    global _all_templates_cache, _all_templates_sig
    templates_dir = get_templates_dir()
    sig_parts = []
    for f in sorted(templates_dir.glob("*.template.json")):
        try:
            sig_parts.append((f.name, f.stat().st_mtime_ns))
        except OSError:
            pass
    try:
        ov = load_template_overrides()
        sig_parts.append(("__overrides__", repr(sorted(ov.items()))))
    except Exception:
        sig_parts.append(("__overrides__", ""))
    sig = tuple(sig_parts)
    if _all_templates_cache is not None and _all_templates_sig == sig:
        return _all_templates_cache
    templates = {}
    for nr_code in list_available_nrs():
        template = load_nr_template(nr_code)
        if template:
            templates[nr_code] = template
    _all_templates_cache = templates
    _all_templates_sig = sig
    return templates


def get_template_description(nr_code: str) -> str:
    """Retorna descrição padrão do NR para exibição na UI."""
    template = load_nr_template(nr_code)
    if template:
        return f"{template.nr_code} - {template.nr_name}"
    return nr_code