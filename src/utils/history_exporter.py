from pathlib import Path
from typing import List

from src.core.models import CertificateRecord

HEADERS = ["Numero", "NR", "Funcionario", "CPF", "Data Inicio", "Data Fim",
           "Carga (h)", "Descricao", "Assinado"]

_COL_WIDTHS = [14, 8, 40, 18, 14, 14, 10, 50, 10]


def _to_matrix(certs: List[CertificateRecord]) -> list:
    matrix = [HEADERS]
    for c in certs:
        matrix.append([
            c.cert_number,
            c.nr_code,
            c.funcionario_nome,
            c.funcionario_cpf or "",
            c.data_inicio,
            c.data_fim,
            c.carga_horaria,
            c.descricao_treinamento,
            "SIM" if c.has_signed_doc else "-",
        ])
    return matrix


def export_certificates_to_file(certs: List[CertificateRecord], output_path: str) -> int:
    """Exporta certificados para .xlsx ou .csv (pela extensao). Retorna quantidade exportada."""
    ext = Path(output_path).suffix.lower()
    matrix = _to_matrix(certs)
    if ext == ".csv":
        _export_csv(matrix, output_path)
    else:
        _export_xlsx(matrix, output_path)
    return max(len(matrix) - 1, 0)


def _export_csv(matrix: list, output_path: str):
    import csv
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerows(matrix)


def _export_xlsx(matrix: list, output_path: str):
    try:
        import openpyxl
    except ImportError:
        raise ImportError("Biblioteca openpyxl nao instalada. pip install openpyxl")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Historico"
    for row in matrix:
        ws.append(row)
    for i, width in enumerate(_COL_WIDTHS, start=1):
        ws.column_dimensions[chr(64 + i)].width = width
    wb.save(output_path)
    wb.close()
