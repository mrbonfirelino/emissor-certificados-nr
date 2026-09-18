"""Testes do CPF tolerante — v1.45.2.

Padrão standalone: `python test_cpf_tolerante.py`.

Contexto: um funcionário com CPF 211.323.497-22 (dígito verificador
inválido, gravado por versão antiga/importação) derrubava a listagem
/funcionarios do portal com ValidationError do pydantic.

Cobre:
- validar_cpf aceita qualquer 11 dígitos (DV inválido incluído)
- validar_cpf rejeita 10/12 dígitos, lixo não numérico e dígitos repetidos
- Employee valida CPF com DV inválido e formata
- Linha legado inválida no banco (cpf de 3 dígitos, telefone lixo)
  NÃO derruba get_all — fallback model_construct + log
- Importação de planilha com CPF de DV inválido funciona
- Portal: form aceita CPF com DV inválido (via validar_cpf relaxado)
"""

import sys
import tempfile
from pathlib import Path

FALHAS = []


def check(nome, ok):
    print(f"[{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def main():
    from src.utils.validators import validar_cpf, formatar_cpf
    from src.core.models import Employee

    # 1) validar_cpf — formato apenas --------------------------------------
    check("1. validar_cpf aceita DV invalido (caso do servidor)",
          validar_cpf("211.323.497-22") is True)
    check("2. validar_cpf aceita numeros puros",
          validar_cpf("52998224725") is True)
    check("3. validar_cpf aceita DV errado qualquer",
          validar_cpf("123.456.789-00") is True)
    check("4. validar_cpf rejeita 10 digitos", validar_cpf("1234567890") is False)
    check("5. validar_cpf rejeita 12 digitos", validar_cpf("123456789012") is False)
    check("6. validar_cpf rejeita repetidos 111.111.111-11",
          validar_cpf("111.111.111-11") is False)
    check("7. validar_cpf rejeita letras", validar_cpf("abcdefghijk") is False)
    check("8. validar_cpf rejeita vazio", validar_cpf("") is False)

    # 2) modelo Employee ----------------------------------------------------
    e = Employee(nome="Servidor Teste", cpf="211.323.497-22")
    check("9. Employee aceita CPF com DV invalido",
          e.cpf == "211.323.497-22")
    check("10. formatar_cpf mantem formato", formatar_cpf("21132349722")
          == "211.323.497-22")
    e2 = Employee(nome="Sem CPF")
    check("11. Employee aceita sem CPF", e2.cpf is None)

    # 3) linha legado invalida no banco nao derruba a leitura ---------------
    from src.core.employee_repo import EmployeeRepository
    fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fd.close()
    er = EmployeeRepository(Path(fd.name))
    with er._get_conn() as conn:
        conn.execute(
            "INSERT INTO employees (nome, cpf, telefone) VALUES (?, ?, ?)",
            ("Legado Ruim", "123", "lixo-telefone"))
        conn.commit()
    emps = er.get_all(limit=100)
    check("12. get_all sobrevive a linha invalida (1 funcionario)",
          len(emps) == 1)
    emp = emps[0]
    check("13. nome preservado no fallback", emp.nome == "Legado Ruim")
    check("14. cpf bruto preservado no fallback", emp.cpf == "123")
    check("15. display_name funciona no fallback",
          isinstance(emp.display_name(), str) and emp.display_name() != "")

    # 4) importacao com DV invalido -----------------------------------------
    from src.utils.excel_importer import import_employees_from_excel
    wb_path = _xlsx_tmp([
        ["Servidor DV Ruim", "211.323.497-22", "Eletricista", "", "", "", "", "", ""],
        ["Outro Func", "12345678901", "Auxiliar", "", "", "", "", "", ""],
    ])
    importados, duplicados, erros, erros_detalhe = import_employees_from_excel(
        wb_path, er)
    check("16. planilha importa os 2 com DV invalido", importados == 2
          and not erros)
    emp_db = er.get_all(limit=100)
    alvo = [x for x in emp_db if x.nome == "Servidor DV Ruim"]
    check("17. CPF DV invalido persistiu formatado",
          len(alvo) == 1 and alvo[0].cpf == "211.323.497-22")

    # 5) rejeitados continuam rejeitados na importacao ----------------------
    wb2 = _xlsx_tmp([
        ["Curto", "123", "Aux", "", "", "", "", "", ""],
        ["Longo", "123456789012", "Aux", "", "", "", "", "", ""],
    ])
    importados2, _, erros2, detalhes2 = import_employees_from_excel(wb2, er)
    check("18. cpf curto/longo rejeitados na planilha",
          importados2 == 0 and erros2 == 2 and len(detalhes2) == 2)

    # 6) portal: validar_cpf relaxado libera o form (mesma funcao do router)
    #    employees.py:48 usa validar_cpf — com 11 digitos DV-invalido passa
    check("19. router portal aceitaria 211.323.497-22",
          validar_cpf("211.323.497-22") is True)
    check("20. router portal rejeitaria 111.111.111-11",
          validar_cpf("111.111.111-11") is False)

    print()
    if FALHAS:
        print(f"FALHAS: {len(FALHAS)}")
        for f in FALHAS:
            print(f"  - {f}")
        sys.exit(1)
    print("Tudo OK (20 checks) — v1.45.2 CPF tolerante.")


def _xlsx_tmp(linhas):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Nome", "CPF", "Funcao", "Telefone", "Data Nascimento",
               "Tipo Sanguineo", "Data Admissao", "Registro CTPS", "CNH EAR"])
    for l in linhas:
        ws.append(l)
    fd = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(fd.name)
    wb.close()
    return fd.name


if __name__ == "__main__":
    main()
