"""
Migracao unica (v1.8.0): reorganiza o armazenamento local.

Antes:  {raiz}/CERTIFICADOS/{Nome_com_underscores}/CERT-...pdf
        {raiz}/CERTIFICADOS/CARTOES/{CODE}/*.pdf
Depois: data/certificados/{Funcionario}/{NR}/CERT-...pdf
        data/cartoes/{Funcionario}/CARTAO_...pdf
        data/cartoes/LOTES/CARTOES_...pdf
        (arquivos sem correspondencia -> pastas _ORFAOS)

Atualiza certificates.pdf_path no banco. Guard idempotente via
app_settings ("migracao_pastas_v2"). Pasta antiga permanece (vazia).
Params de injecao (legacy_dir/cert_root/cartoes_root/settings/db_path)
existem para os testes.
"""

import shutil
from pathlib import Path

from src.utils.error_log import log_error
from src.utils.folder_utils import employee_folder_name, sanitize_folder_name
from src.utils.paths import get_cartoes_dir, get_certificados_dir, get_legacy_certificados_dir
from src.utils.text_utils import normalize_text


def migrate_storage_if_needed(
    legacy_dir: Path = None,
    cert_root: Path = None,
    cartoes_root: Path = None,
    settings=None,
    db_path: Path = None,
) -> dict:
    stats = {"certificados": 0, "cartoes": 0, "orfaos": 0, "bd_atualizados": 0}
    if settings is None:
        from src.core.app_settings import get_setting, set_setting
    else:
        get_setting, set_setting = settings
    legacy = Path(legacy_dir) if legacy_dir else get_legacy_certificados_dir()
    cert_root = Path(cert_root) if cert_root else get_certificados_dir()
    cartoes_root = Path(cartoes_root) if cartoes_root else get_cartoes_dir()

    if bool(get_setting("migracao_pastas_v2", False)):
        return stats
    if not legacy.exists():
        set_setting("migracao_pastas_v2", True)
        return stats

    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository
    emp_repo = EmployeeRepository(db_path=db_path)
    hist = HistoryRepository(db_path=db_path)
    employees = emp_repo.get_all(limit=1000000)
    pasta_por_id = {e.id: employee_folder_name(e, employees) for e in employees}

    try:
        # 1. Certificados: {legacy}/{nome}/CERT-{n}_{NR}_{nome}.pdf
        for cert in hist.get_all(limit=1000000, offset=0):
            if not cert.pdf_path:
                continue
            src = Path(cert.pdf_path)
            if not src.exists():
                continue
            nr = sanitize_folder_name(cert.nr_code or "NR")
            pasta = pasta_por_id.get(cert.employee_id) or sanitize_folder_name(cert.funcionario_nome or "SEM_NOME")
            dst = cert_root / pasta / nr / src.name
            if src.parent.resolve() == dst.parent.resolve():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            with hist._get_conn() as conn:
                conn.execute("UPDATE certificates SET pdf_path = ? WHERE id = ?", (str(dst), cert.id))
            stats["certificados"] += 1
            stats["bd_atualizados"] += 1

        # subpastas que sobraram (arquivos sem registro no banco)
        for child in legacy.iterdir():
            if child.is_dir() and child.name.upper() != "CARTOES":
                for f in child.rglob("*.pdf"):
                    dst = cert_root / "_ORFAOS" / child.name / f.name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(dst))
                    stats["orfaos"] += 1

        # 2. Cartoes: {legacy}/CARTOES/{CODE}/...
        cartoes_legacy = legacy / "CARTOES"
        if cartoes_legacy.exists():
            nome_para_pasta = {
                normalize_text(e.nome or ""): employee_folder_name(e, employees)
                for e in employees
            }
            for f in cartoes_legacy.rglob("*.pdf"):
                if f.name.upper().startswith("CARTOES_"):
                    dst = cartoes_root / "LOTES" / f.name
                else:
                    # CARTAO_{nome}_{code}.pdf -> casar por nome
                    stem = f.stem
                    pasta = None
                    if stem.upper().startswith("CARTAO_"):
                        mid = stem[len("CARTAO_"):]
                        partes = mid.rsplit("_", 1)
                        nome_norm = normalize_text(partes[0].replace("_", " ") if partes else mid)
                        pasta = nome_para_pasta.get(nome_norm)
                    if not pasta:
                        pasta = "_ORFAOS"
                    dst = cartoes_root / pasta / f.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dst))
                stats["cartoes"] += 1
    except Exception as e:
        log_error("migracao-storage", e)
        return stats

    set_setting("migracao_pastas_v2", True)
    return stats
