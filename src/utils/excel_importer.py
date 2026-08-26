import re
from pathlib import Path
from typing import Tuple, List


def _normalize_cpf(val) -> str:
    """Extrai apenas digitos de um valor CPF."""
    if val is None:
        return ""
    s = str(val).strip()
    return re.sub(r'\D', '', s)


def _normalize_name(val) -> str:
    """Extrai e limpa nome."""
    if val is None:
        return ""
    return str(val).strip()


def _is_valid_cpf_digits(cpf: str) -> bool:
    """Valida se tem 11 digitos (validacao basica de formato)."""
    return len(cpf) == 11 and cpf.isdigit()


def import_employees_from_excel(
    filepath: str,
    employee_repo,
    name_col: int = 0,
    cpf_col: int = 1,
    skip_header: bool = True
) -> Tuple[int, int, int, List[str]]:
    """
    Importa funcionarios de um arquivo Excel (.xlsx).

    Retorna (importados, duplicados, erros, erros_detalhe).
    - importados: numero de novos funcionarios cadastrados
    - duplicados: CPFs que ja existiam no banco
    - erros: linhas com dados invalidos
    - erros_detalhe: lista de mensagens de erro por linha
    """
    try:
        import openpyxl
    except ImportError:
        return 0, 0, 0, ["Biblioteca openpyxl nao instalada. Instale com: pip install openpyxl"]

    path = Path(filepath)
    if not path.exists():
        return 0, 0, 0, [f"Arquivo nao encontrado: {filepath}"]

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        return 0, 0, 0, [f"Erro ao abrir arquivo: {e}"]

    imported = 0
    duplicates = 0
    errors = 0
    error_details = []

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 and skip_header:
            continue

        if not row or all(c is None for c in row):
            continue

        try:
            name_val = row[name_col] if name_col < len(row) else None
            cpf_val = row[cpf_col] if cpf_col < len(row) else None
        except IndexError:
            errors += 1
            error_details.append(f"Linha {i+1}: coluna fora do intervalo")
            continue

        name = _normalize_name(name_val)
        cpf = _normalize_cpf(cpf_val)

        if not name:
            errors += 1
            error_details.append(f"Linha {i+1}: nome vazio")
            continue

        if not _is_valid_cpf_digits(cpf):
            errors += 1
            error_details.append(f"Linha {i+1}: CPF invalido ({cpf_val})")
            continue

        # Formata CPF: XXX.XXX.XXX-XX
        cpf_formatted = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

        result = employee_repo.create(name, cpf_formatted)
        if result:
            imported += 1
        else:
            duplicates += 1

    wb.close()
    return imported, duplicates, errors, error_details
