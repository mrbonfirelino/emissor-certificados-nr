from pathlib import Path


def export_employees_to_excel(employee_repo, output_path: str) -> int:
    """Exporta funcionarios para Excel. Retorna quantidade exportada."""
    try:
        import openpyxl
    except ImportError:
        raise ImportError("Biblioteca openpyxl nao instalada. pip install openpyxl")

    employees = employee_repo.get_all(limit=10000)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Funcionarios"
    ws.append(["ID", "Nome", "CPF", "Telefone", "Data Nascimento", "Tipo Sanguineo",
               "Data Admissao", "Registro CTPS", "CNH EAR", "Funcao", "Data Cadastro"])

    def iso_to_br(v):
        if v and len(v) == 10 and v[4] == "-":
            return f"{v[8:10]}/{v[5:7]}/{v[0:4]}"
        return v or ""

    for emp in employees:
        ws.append([
            emp.id, emp.nome, emp.cpf, emp.telefone or "",
            iso_to_br(getattr(emp, "data_nascimento", None)),
            getattr(emp, "tipo_sanguineo", None) or "",
            iso_to_br(getattr(emp, "data_admissao", None)),
            getattr(emp, "registro_ctps", None) or "",
            "Sim" if getattr(emp, "cnh_ear", False) else "Nao",
            emp.funcao or "", emp.created_at or ""
        ])

    # Ajusta largura das colunas
    widths = [8, 40, 18, 16, 16, 14, 16, 16, 10, 30, 20]
    for letra, w in zip("ABCDEFGHIJK", widths):
        ws.column_dimensions[letra].width = w

    wb.save(output_path)
    wb.close()
    return len(employees)
