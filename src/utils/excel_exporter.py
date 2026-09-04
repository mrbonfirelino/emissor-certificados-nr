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
    ws.append(["ID", "Nome", "CPF", "Telefone", "Data Nascimento", "Funcao", "Data Cadastro"])

    for emp in employees:
        nasc = emp.data_nascimento or ""
        if nasc and len(nasc) == 10 and nasc[4] == "-":
            nasc = f"{nasc[8:10]}/{nasc[5:7]}/{nasc[0:4]}"
        ws.append([emp.id, emp.nome, emp.cpf, emp.telefone or "", nasc, emp.funcao or "", emp.created_at or ""])

    # Ajusta largura das colunas
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 40
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 16
    ws.column_dimensions['E'].width = 16
    ws.column_dimensions['F'].width = 30
    ws.column_dimensions['G'].width = 20

    wb.save(output_path)
    wb.close()
    return len(employees)
