import re
import threading
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


def parse_date(value) -> Optional[date]:
    """Tenta converter multiplos formatos de data para date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def read_batch_spreadsheet(filepath: str) -> Tuple[List[Dict], List[str]]:
    """
    Le planilha Excel com colunas: Nome, NR, Data.
    Retorna (rows, errors).
    Cada row: {"nome": str, "nr_code": str, "data": date}
    """
    try:
        import openpyxl
    except ImportError:
        return [], ["Biblioteca openpyxl nao instalada"]

    path = Path(filepath)
    if not path.exists():
        return [], [f"Arquivo nao encontrado: {filepath}"]

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        return [], [f"Erro ao abrir arquivo: {e}"]

    rows = []
    errors = []

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row or all(c is None for c in row):
            continue

        nome = str(row[0]).strip() if row[0] else ""
        nr_code = str(row[1]).strip().upper() if len(row) > 1 and row[1] else ""
        data = parse_date(row[2] if len(row) > 2 else None)

        if not nome:
            errors.append(f"Linha {i+1}: nome vazio")
            continue
        if not nr_code:
            errors.append(f"Linha {i+1}: NR vazio")
            continue
        if not data:
            errors.append(f"Linha {i+1}: data invalida ({row[2] if len(row) > 2 else 'vazio'})")
            continue

        rows.append({"nome": nome, "nr_code": nr_code, "data": data})

    wb.close()
    return rows, errors


def check_missing_employees(rows: List[Dict], employee_repo) -> List[str]:
    """Verifica quais funcionarios do lote nao existem no sistema. Retorna lista de nomes."""
    missing = set()
    for row in rows:
        nome = row["nome"]
        employees = employee_repo.search(nome, limit=5)
        found = False
        for e in employees:
            if e.nome.lower() == nome.lower():
                found = True
                break
        if not found:
            missing.add(nome)
    return sorted(missing)


def _process_one(row: Dict, employee_repo, certificate_service) -> Dict:
    """Processa uma unica linha. Retorna dict com resultado."""
    try:
        return _process_one_inner(row, employee_repo, certificate_service)
    except Exception as e:
        return {"status": "erro", "idx": row.get("idx", 0), "total": row.get("total", 0),
                "nome": row["nome"], "nr_code": row["nr_code"],
                "msg": f"Erro inesperado para '{row['nome']}' - {e}"}


def _process_one_inner(row: Dict, employee_repo, certificate_service) -> Dict:
    """Processa uma unica linha (interno)."""
    from src.core.template_loader import load_nr_template

    idx = row.get("idx", 0)
    total = row.get("total", 0)
    nome = row["nome"]
    nr_code = row["nr_code"]
    data = row["data"]

    template = load_nr_template(nr_code)
    if not template:
        return {"status": "erro", "idx": idx, "total": total, "nome": nome,
                "nr_code": nr_code, "msg": f"NR '{nr_code}' nao encontrado"}

    employees = employee_repo.search(nome, limit=5)
    emp = None
    for e in employees:
        if e.nome.lower() == nome.lower():
            emp = e
            break
    if not emp and employees:
        emp = employees[0]

    if not emp:
        emp_id = employee_repo.create(nome, None)
        if emp_id:
            emp = employee_repo.get_by_id(emp_id)

    if not emp:
        return {"status": "erro", "idx": idx, "total": total, "nome": nome,
                "nr_code": nr_code, "msg": f"Nao foi possivel criar funcionario '{nome}'"}

    if not emp.cpf or not emp.cpf.strip():
        try:
            from src.core.models import CertificateRecord
            cert_number = certificate_service.history.next_certificate_number()
            record = CertificateRecord(
                cert_number=cert_number,
                nr_code=nr_code,
                employee_id=emp.id,
                funcionario_nome=emp.nome,
                funcionario_cpf=emp.cpf or "",
                data_inicio=data.isoformat(),
                data_fim=data.isoformat(),
                carga_horaria=template.carga_horaria_minima,
                descricao_treinamento=template.descricao_padrao,
                campos_extra="{}",
                pdf_path=None
            )
            certificate_service.history.save(record)
            return {"status": "reg", "idx": idx, "total": total, "nome": nome,
                    "nr_code": nr_code, "cert_number": cert_number,
                    "msg": f"{cert_number} {nr_code} {nome} - Registrado sem PDF (sem CPF)"}
        except Exception as e:
            return {"status": "erro", "idx": idx, "total": total, "nome": nome,
                    "nr_code": nr_code, "msg": f"Erro ao registrar '{nome}' - {e}"}

    try:
        pdf_path = certificate_service.generate_certificate(
            nr_code=nr_code,
            employee=emp,
            data_treinamento=data,
            carga_horaria=template.carga_horaria_minima,
            descricao_treinamento=template.descricao_padrao,
            campos_extra={}
        )
        cert_number = pdf_path.stem.split("_")[0] if pdf_path else "???"
        return {"status": "ok", "idx": idx, "total": total, "nome": nome,
                "nr_code": nr_code, "cert_number": cert_number,
                "msg": f"{cert_number} {nr_code} {nome} - PDF gerado"}
    except Exception as e:
        return {"status": "erro", "idx": idx, "total": total, "nome": nome,
                "nr_code": nr_code, "msg": f"Erro ao gerar para '{nome}' - {e}"}


def generate_batch_certificates(
    rows: List[Dict],
    employee_repo,
    certificate_service,
    on_progress=None,
    on_log=None,
    max_workers=2
) -> Dict:
    """
    Gera certificados em lote com paralelismo.
    Retorna {"gerados", "registrados_sem_pdf", "erros", "log"}
    """
    total = len(rows)
    for i, row in enumerate(rows):
        row["idx"] = i + 1
        row["total"] = total

    log = []
    gerados = 0
    registrados_sem_pdf = 0
    erros = []

    def _worker(r):
        return _process_one(r, employee_repo, certificate_service)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_worker, row): row for row in rows}

        for future in as_completed(futures):
            result = future.result()

            status = result["status"]
            msg = result["msg"]

            if status == "ok":
                gerados += 1
                prefix = "OK"
            elif status == "reg":
                registrados_sem_pdf += 1
                prefix = "REG"
            else:
                erros.append(msg)
                prefix = "ERRO"

            log_entry = f"[{result['idx']}/{result['total']}] {prefix}: {msg}"
            log.append(log_entry)

            if on_log:
                on_log(log_entry)
            if on_progress:
                on_progress(result["idx"], result["total"], result["nome"])

    return {
        "gerados": gerados,
        "registrados_sem_pdf": registrados_sem_pdf,
        "erros": erros,
        "log": log
    }
