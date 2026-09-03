"""Nome de pasta seguro para funcionarios (local e rede)."""

_INVALID = '\\/:*?"<>|'


def sanitize_folder_name(name: str) -> str:
    """Remove caracteres invalidos do Windows e espaços duplicados."""
    for ch in _INVALID:
        name = (name or "").replace(ch, " ")
    return " ".join(name.split()).strip() or "SEM_NOME"


def employee_folder_name(employee, all_employees) -> str:
    """Pasta do funcionario; anexa CPF (ou id) apenas em colisao de nomes."""
    base = sanitize_folder_name(employee.nome or "")
    # Windows e case-insensitive: compara em minusculas
    colisao = any(
        e.id != employee.id and sanitize_folder_name(e.nome or "").casefold() == base.casefold()
        for e in (all_employees or [])
    )
    if colisao:
        cpf = (employee.cpf or "").strip()
        suffix = cpf if cpf else f"id{employee.id}"
        return f"{base} ({suffix})"
    return base
