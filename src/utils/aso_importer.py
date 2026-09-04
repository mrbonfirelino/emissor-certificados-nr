"""Importacao em lote de ASOs a partir de planilha Excel (v1.12.0).

Colunas: A Nome | B CPF (opcional) | C Tipo | D Data Exame | E Validade Meses (opcional)
Modelo: MODELOS DE IMPORTACAO/MODELO ASO.xlsx
"""

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Tuple

from src.core.aso_repo import ASO_TIPOS
from src.utils.text_utils import normalize_text

TIPO_NORMALIZADO = {normalize_text(t): t for t in ASO_TIPOS}


def _parse_tipo(val) -> str:
    if val is None:
        raise ValueError("tipo de ASO vazio")
    chave = normalize_text(str(val))
    for k, oficial in TIPO_NORMALIZADO.items():
        if chave == k or chave == k.replace(" ", ""):
            return oficial
    raise ValueError(f"tipo de ASO invalido ({val}) - use um dos: {', '.join(ASO_TIPOS)}")


def _parse_data(val) -> str:
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    s = str(val or "").strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"data do exame invalida ({val}) - use dd/mm/aaaa")


def _parse_validade(val) -> int:
    if val is None or str(val).strip() == "":
        return 12
    try:
        meses = int(float(str(val).strip()))
    except ValueError:
        raise ValueError(f"validade invalida ({val}) - use um numero de meses")
    if meses < 1 or meses > 120:
        raise ValueError("validade deve estar entre 1 e 120 meses")
    return meses


def _so_digitos(val) -> str:
    return "".join(ch for ch in str(val or "") if ch.isdigit())


def import_asos_from_excel(filepath, aso_repo, employee_repo) -> Dict[str, List]:
    """Importa ASOs em lote. Retorna {'criados': [...], 'erros': n, 'detalhes': [...]}."""
    import openpyxl

    from src.core.aso_pdf_generator import generate_aso_pdf
    from src.core.network_sync import run_async, sync_aso
    from src.utils.paths import get_data_dir
    from src.utils.folder_utils import employee_folder_name

    criados: List[str] = []
    detalhes: List[str] = []

    employees = employee_repo.get_all(limit=1000000)
    por_cpf = {_so_digitos(e.cpf): e for e in employees if e.cpf}
    por_nome = {normalize_text(e.nome): e for e in employees}
    pastas = {e.id: employee_folder_name(e, employees) for e in employees}

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active
    linhas = list(ws.iter_rows(values_only=True))
    wb.close()

    for i, row in enumerate(linhas[1:], start=2):
        try:
            if not row or all(c is None or str(c).strip() == "" for c in row[:5]):
                continue
            nome = str(row[0] or "").strip()
            cpf_digitos = _so_digitos(row[1] if len(row) > 1 else "")
            tipo = _parse_tipo(row[2] if len(row) > 2 else None)
            data_exame = _parse_data(row[3] if len(row) > 3 else None)
            validade = _parse_validade(row[4] if len(row) > 4 else None)

            if not nome:
                raise ValueError("nome vazio")

            emp = None
            if cpf_digitos:
                emp = por_cpf.get(cpf_digitos)
            if emp is None:
                emp = por_nome.get(normalize_text(nome))
            if emp is None:
                raise ValueError(f"funcionario '{nome}' nao encontrado (cadastre antes de importar)")

            aso_number = aso_repo.next_aso_number()
            destino = get_data_dir() / "asos" / pastas[emp.id]
            destino.mkdir(parents=True, exist_ok=True)
            pdf_path = str(destino / f"{aso_number}.pdf")
            generate_aso_pdf(pdf_path, aso_number, emp, tipo, data_exame, validade)
            aso_id = aso_repo.save(aso_number, emp.id, tipo, data_exame, validade, pdf_path)

            try:
                run_async(sync_aso, aso_repo.get_by_id(aso_id), emp)
            except Exception:
                pass

            criados.append(f"{aso_number} - {emp.nome} ({tipo})")
        except ValueError as e:
            detalhes.append(f"Linha {i}: {e}")
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("importar-aso", e)
            detalhes.append(f"Linha {i}: erro inesperado ({e})")

    return {"criados": criados, "erros": len(detalhes), "detalhes": detalhes}
