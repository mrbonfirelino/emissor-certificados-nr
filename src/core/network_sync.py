"""
Espelhamento de documentos em pasta de rede (v1.8.0).

Estrutura no destino (quando ativado em Configuracoes):
    {caminho}/
      {Funcionario}/
        Certificados/{NR}/CERT-...pdf
        Certificados/{NR}/00_Certificados_OLD/...        <- certificados vencidos
        Cartoes/CARTAO_...pdf
        Certificados Assinados/CERT-..._assinado.pdf|jpg|png
        Outros/CNH.PNG ...
      Cartoes_Gerais/                                    <- PDFs de lote

Regras:
- Todas as operacoes sao best-effort: falha na rede NUNCA bloqueia a operacao
  local (apenas toast + log em data/error.log).
- Certificado vencido (data_fim + validade do template < hoje) vai para
  00_Certificados_OLD; se ja existir copia na pasta atual, ela e MOVIDA.
"""

import shutil
import threading
from datetime import date
from pathlib import Path
from typing import Optional

from dateutil.relativedelta import relativedelta

from src.core.app_settings import get_setting
from src.utils.error_log import log_error
from src.utils.folder_utils import employee_folder_name, sanitize_folder_name
from src.utils.paths import get_assinados_dir, get_cartoes_dir


# ── Configuracao ──────────────────────────────────────────────

def rede_ativo() -> bool:
    return bool(get_setting("rede_documentos_ativo", False))


def rede_caminho() -> Optional[Path]:
    raw = str(get_setting("rede_documentos_caminho", "") or "").strip()
    return Path(raw) if raw else None


def _destino() -> Optional[Path]:
    if not rede_ativo():
        return None
    return rede_caminho()


def _notify_fail(o_que: str, exc: Exception):
    from src.utils.notifications import notify
    notify("NormaTech - Rede indisponivel",
           f"Nao foi possivel salvar {o_que} na pasta de rede.")
    log_error("rede-sync", exc)


def run_async(fn, *args):
    """Roda a sincronizacao em thread daemon (nao trava a UI)."""
    threading.Thread(target=fn, args=args, daemon=True).start()


# ── Helpers ───────────────────────────────────────────────────

def _employees_all(repo) -> list:
    return repo.get_all(limit=1000000)


def _cert_vencido(cert) -> bool:
    from src.core.template_loader import load_nr_template
    try:
        tmpl = load_nr_template(cert.nr_code)
        validade = tmpl.validade_meses if tmpl else 12
        return date.fromisoformat(cert.data_fim) + relativedelta(months=validade) < date.today()
    except Exception:
        return False


def _func_dir(destino: Path, employee, all_emps) -> Path:
    return destino / employee_folder_name(employee, all_emps)


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


# ── Sincronizacao de item unico (com toast em falha) ─────────

def sync_certificate(cert, employee=None) -> bool:
    destino = _destino()
    if not destino:
        return False
    try:
        from src.core.employee_repo import EmployeeRepository
        repo = EmployeeRepository()
        employee = employee or repo.get_by_id(cert.employee_id)
        if employee:
            pasta = employee_folder_name(employee, _employees_all(repo))
        else:
            pasta = sanitize_folder_name(cert.funcionario_nome or "SEM_NOME")
        _sync_certificate_inner(destino, pasta, cert)
        return True
    except Exception as e:
        _notify_fail(f"o certificado {cert.cert_number}", e)
        return False


def _sync_certificate_inner(destino: Path, pasta: str, cert) -> None:
    if not cert.pdf_path:
        return
    src = Path(cert.pdf_path)
    if not src.exists():
        return
    fname = src.name
    nr = sanitize_folder_name(cert.nr_code or "NR")
    base_dir = destino / pasta / "Certificados" / nr
    if _cert_vencido(cert):
        atual = base_dir / fname
        old = base_dir / "00_Certificados_OLD" / fname
        old.parent.mkdir(parents=True, exist_ok=True)
        if atual.exists():
            atual.replace(old)
        _copy_file(src, old)
    else:
        _copy_file(src, base_dir / fname)


def sync_card(pdf_path, employee) -> bool:
    destino = _destino()
    if not destino:
        return False
    try:
        from src.core.employee_repo import EmployeeRepository
        repo = EmployeeRepository()
        pasta = employee_folder_name(employee, _employees_all(repo))
        _copy_file(Path(pdf_path), destino / pasta / "Cartoes" / Path(pdf_path).name)
        return True
    except Exception as e:
        _notify_fail(f"o cartao de {employee.nome}", e)
        return False


def sync_card_lote(pdf_path) -> bool:
    destino = _destino()
    if not destino:
        return False
    try:
        _copy_file(Path(pdf_path), destino / "Cartoes_Gerais" / Path(pdf_path).name)
        return True
    except Exception as e:
        _notify_fail("o PDF de cartoes em lote", e)
        return False


def salvar_assinado(cert, data: bytes, tipo: str, employee=None) -> bool:
    """Grava copia local (data/assinados) e espelha na rede."""
    ext = {"pdf": "pdf", "jpg": "jpg", "jpeg": "jpg", "png": "png"}.get((tipo or "pdf").lower(), "pdf")
    fname = f"{cert.cert_number}_assinado.{ext}"
    destino = _destino()
    try:
        from src.core.employee_repo import EmployeeRepository
        repo = EmployeeRepository()
        employee = employee or repo.get_by_id(cert.employee_id)
        pasta = (employee_folder_name(employee, _employees_all(repo))
                 if employee else sanitize_folder_name(cert.funcionario_nome or "SEM_NOME"))
        local = get_assinados_dir() / pasta / fname
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)
    except Exception as e:
        log_error("assinado-local", e)
    if not destino:
        return False
    try:
        from src.core.employee_repo import EmployeeRepository
        repo = EmployeeRepository()
        employee = employee or repo.get_by_id(cert.employee_id)
        pasta = (employee_folder_name(employee, _employees_all(repo))
                 if employee else sanitize_folder_name(cert.funcionario_nome or "SEM_NOME"))
        _copy_bytes(destino / pasta / "Certificados Assinados" / fname, data)
        return True
    except Exception as e:
        _notify_fail(f"o assinado de {cert.cert_number}", e)
        return False


def sync_doc(filename: str, data: bytes, employee) -> bool:
    destino = _destino()
    if not destino:
        return False
    try:
        from src.core.employee_repo import EmployeeRepository
        repo = EmployeeRepository()
        pasta = employee_folder_name(employee, _employees_all(repo))
        _copy_bytes(destino / pasta / "Outros" / Path(filename).name, data)
        return True
    except Exception as e:
        _notify_fail(f"o documento {filename}", e)
        return False


def remove_doc_network(filename: str, employee) -> bool:
    destino = _destino()
    if not destino:
        return False
    try:
        from src.core.employee_repo import EmployeeRepository
        repo = EmployeeRepository()
        pasta = employee_folder_name(employee, _employees_all(repo))
        alvo = destino / pasta / "Outros" / Path(filename).name
        if alvo.exists():
            alvo.unlink()
        return True
    except Exception as e:
        _notify_fail(f"ao remover {filename} da rede", e)
        return False


def _copy_bytes(dst: Path, data: bytes) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)


# ── Sincronizacao completa (startup / manual) ────────────────

def sync_all(notify_success: bool = False) -> dict:
    """Espelha tudo: certificados, cartoes, assinados e outros docs.

    Usa helpers internos (sem toast por item); um unico toast se houver erros.
    """
    stats = {"copiados": 0, "erros": 0}
    destino = _destino()
    if not destino:
        return stats
    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository
    try:
        emp_repo = EmployeeRepository()
        hist = HistoryRepository()
        employees = _employees_all(emp_repo)
    except Exception as e:
        _notify_fail("a sincronizacao completa", e)
        return stats

    for emp in employees:
        pasta = employee_folder_name(emp, employees)
        try:
            certs = hist.get_by_employee(emp.id)
        except Exception as e:
            log_error("rede-sync", e)
            stats["erros"] += 1
            certs = []
        for cert in certs:
            try:
                _sync_certificate_inner(destino, pasta, cert)
                stats["copiados"] += 1
            except Exception as e:
                log_error("rede-sync", e)
                stats["erros"] += 1
            if cert.has_signed_doc:
                try:
                    res = hist.get_signed_doc(cert.id)
                    if res:
                        data, tipo = res
                        ext = {"pdf": "pdf", "jpg": "jpg", "jpeg": "jpg", "png": "png"}.get(tipo, "pdf")
                        _copy_bytes(destino / pasta / "Certificados Assinados"
                                    / f"{cert.cert_number}_assinado.{ext}", bytes(data))
                        stats["copiados"] += 1
                except Exception as e:
                    log_error("rede-sync", e)
                    stats["erros"] += 1
        try:
            for doc in emp_repo.list_docs(emp.id):
                res = emp_repo.get_doc(doc["id"])
                if res:
                    _, fname, dados, _tipo = res
                    _copy_bytes(destino / pasta / "Outros" / fname, bytes(dados))
                    stats["copiados"] += 1
        except Exception as e:
            log_error("rede-sync", e)
            stats["erros"] += 1
        try:
            cart_dir = get_cartoes_dir() / pasta
            if cart_dir.exists():
                for f in cart_dir.glob("*.pdf"):
                    _copy_file(f, destino / pasta / "Cartoes" / f.name)
                    stats["copiados"] += 1
        except Exception as e:
            log_error("rede-sync", e)
            stats["erros"] += 1

    try:
        lote_dir = get_cartoes_dir() / "LOTES"
        if lote_dir.exists():
            for f in lote_dir.glob("*.pdf"):
                _copy_file(f, destino / "Cartoes_Gerais" / f.name)
                stats["copiados"] += 1
    except Exception as e:
        log_error("rede-sync", e)
        stats["erros"] += 1

    from src.utils.notifications import notify
    if stats["erros"]:
        notify("NormaTech - Sincronizacao",
               f"{stats['erros']} arquivo(s) nao foram salvos na pasta de rede.")
    elif notify_success and stats["copiados"]:
        notify("NormaTech - Sincronizacao",
               f"{stats['copiados']} arquivo(s) espelhados na pasta de rede.")
    return stats
