"""Testes do Portal Web — v1.46.0 (roadmap 2.33).

Padrão standalone: `python test_web_v147.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.

Cobre:
- 2.33.3: PDF ausente regenerado na hora (mesmo numero, sem novo registro),
  avisos de impedimento (sem CPF / modelo / empresa) na listagem e no detalhe
- 2.33.4: permissoes dinamicas (papel + excecao por usuario), aplicadas sem
  re-login; UI em /usuarios
- 2.33.2: ficha do veiculo com dialogs (todas as secoes) e situacao atual
"""

import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

FALHAS = []


def check(nome, ok):
    print(f"[{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def _trocar_senha(client, atual, nova="SenhaF0rte"):
    return client.post("/troca-senha", data={"atual": atual, "nova": nova,
                                             "confirma": nova})


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="webv147_"))
    tmp.mkdir(parents=True, exist_ok=True)
    import src.utils.paths as paths_mod
    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.frota_repo as fr_mod
    import src.core.certificate_service as cert_mod
    import src.core.pptx_certificate_service as pptx_cert_mod
    import src.web.users_repo as users_repo_mod
    import src.web.app as app_mod

    paths_mod.get_data_dir = lambda: tmp
    er_mod.get_db_path = lambda: tmp / "certificados.db"
    hr_mod.get_db_path = lambda: tmp / "certificados.db"
    fr_mod.get_db_path = lambda: tmp / "certificados.db"
    users_repo_mod.get_db_path = lambda: tmp / "certificados.db"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
    from src.core.models import NRTemplate
    _TPL = NRTemplate(nr_code="NR-35", nr_name="Trabalho em Altura",
                      descricao_padrao="Treinamento",
                      texto_certificado="Treinamento valido.")
    cert_mod.load_nr_template = lambda codigo: _TPL if codigo == "NR-35" else None
    pptx_cert_mod.get_templates_dir = lambda: tmp / "sem-templates-pptx"
    app_mod.get_data_dir = lambda: tmp

    from src.web.app import create_app
    from fastapi.testclient import TestClient
    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    client = TestClient(app, follow_redirects=False)
    return client, tmp


def _login_admin(client, tmp):
    txt = (tmp / "web_admin_provisorio.txt").read_text(encoding="utf-8")
    prov = [l.split(":")[1].strip() for l in txt.splitlines()
            if l.startswith("SENHA PROVISORIA")][0]
    client.post("/login", data={"username": "admin", "password": prov})
    _trocar_senha(client, prov)


TPL_DIR = Path(__file__).parent / "src" / "web" / "templates"


def _tpl(nome):
    return (TPL_DIR / nome).read_text(encoding="utf-8")


def main():
    client, tmp = make_env()

    from src.core.employee_repo import EmployeeRepository
    er = EmployeeRepository(db_path=tmp / "certificados.db")
    ana = er.create(nome="Ana Silva", cpf="529.982.247-25")
    sem_cpf = er.create(nome="Bruno SemCPF", cpf=None)

    # registros de certificado: um regeneravel, um sem CPF (caso REG)
    from src.core.models import CertificateRecord
    from src.core.history_repo import HistoryRepository
    hr = HistoryRepository()
    hr.save(CertificateRecord(
        cert_number="CERT-990001", nr_code="NR-35", employee_id=ana,
        funcionario_nome="Ana Silva", funcionario_cpf="529.982.247-25",
        data_inicio="2026-09-01", data_fim="2026-09-01", carga_horaria=8,
        descricao_treinamento="Treinamento", campos_extra="{}", pdf_path=None))
    hr.save(CertificateRecord(
        cert_number="CERT-990002", nr_code="NR-35", employee_id=sem_cpf,
        funcionario_nome="Bruno SemCPF", funcionario_cpf="",
        data_inicio="2026-09-01", data_fim="2026-09-01", carga_horaria=8,
        descricao_treinamento="Treinamento", campos_extra="{}", pdf_path=None))

    _login_admin(client, tmp)

    # ================= 2.33.3 — PDF regenerar na hora =================
    r = client.get("/historico")
    check("histórico 200", r.status_code == 200)
    check("histórico: badge Sem PDF para registro sem arquivo",
          "Sem PDF" in r.text and "/historico/CERT-990001/regenerar" in r.text)
    check("histórico: botão Gerar só para quem escreve (admin vê)",
          ">Gerar</button>" in r.text)

    r = client.post("/historico/CERT-990001/regenerar")
    check("POST regenerar -> 303", r.status_code == 303)
    r = client.get("/historico")
    check("histórico: flash de sucesso",
          "PDF do certificado CERT-990001 gerado com sucesso." in r.text)
    rec1 = hr.get_by_number("CERT-990001")
    check("regenerar: pdf_path gravado e arquivo existe",
          bool(rec1.pdf_path) and Path(rec1.pdf_path).exists())
    check("regenerar: mesmo numero, sem novo registro",
          rec1.cert_number == "CERT-990001"
          and hr.count_all() == 2)
    check("histórico: linha regenerada volta a mostrar PDF",
          "/historico/CERT-990001/pdf" in r.text
          and "/historico/CERT-990001/regenerar" not in r.text)

    r = client.post("/historico/CERT-990002/regenerar")
    r = client.get("/historico")
    check("regenerar sem CPF: motivo exibido", "sem CPF" in r.text)

    r = client.get("/historico/CERT-990002/ver")
    check("ver com regeneração impossível -> redirect com flash",
          r.status_code == 303 and r.headers.get("location") == "/historico")

    r = client.get("/certificados/CERT-990002")
    check("detalhe: aviso + motivo sem CPF + botão Gerar",
          "PDF não encontrado" in r.text and "Gerar PDF agora" in r.text
          and "sem CPF" in r.text)

    r = client.get("/certificados/CERT-990001")
    check("detalhe regenerado: botões Ver/Baixar, sem botão Gerar",
          "Ver no navegador" in r.text and "Baixar PDF" in r.text
          and "Gerar PDF agora" not in r.text)

    # ================= 2.33.4 — permissões dinâmicas =================
    from src.web.permissions import pode, pode_usuario
    from src.web.users_repo import UsersRepository
    users_repo = UsersRepository()

    r = client.get("/usuarios")
    check("usuários 200", r.status_code == 200)
    check("usuários: card Permissões por papel",
          "Permissões por papel" in r.text)
    check("usuários: checkbox módulo×papel (importacoes__emissor)",
          'name="perm_importacoes__emissor"' in r.text)
    check("usuários: admin fixo desabilitado (usuarios/config)",
          'checked disabled title="Admin sempre mantém acesso"' in r.text)
    check("usuários: exceções por usuário (exc_)",
          'name="exc_importacoes"' in r.text)

    check("padrão: emissor pode importacoes", pode("emissor", "importacoes"))

    r = client.post("/usuarios/permissoes",
                    data={"perm_importacoes__admin": "1"})
    check("POST permissões -> 303", r.status_code == 303)
    check("bloqueio de papel aplica SEM re-login",
          pode("emissor", "importacoes") is False)

    uid, _prov = users_repo.create_user("joao", "João", "emissor")
    check("exceção: usuário herda bloqueio do papel",
          pode_usuario({"id": uid, "papel": "emissor"}, "importacoes") is False)

    r = client.post(f"/usuarios/{uid}/permissoes",
                    data={"exc_importacoes": "1"})
    check("exceção Permitir concede ao usuário",
          pode_usuario({"id": uid, "papel": "emissor"}, "importacoes") is True)

    r = client.post(f"/usuarios/{uid}/permissoes",
                    data={"exc_importacoes": "0"})
    check("exceção Negar prevalece sobre o papel",
          pode_usuario({"id": uid, "papel": "emissor"}, "importacoes") is False)

    r = client.post(f"/usuarios/{uid}/permissoes", data={"exc_importacoes": ""})
    r = client.post("/usuarios/permissoes/padrao")
    check("restaurar padrão devolve acesso do papel",
          pode("emissor", "importacoes") is True
          and pode_usuario({"id": uid, "papel": "emissor"},
                           "importacoes") is True)

    r = client.get("/usuarios")
    check("usuários: select com Padrão do papel/Permitir/Negar",
          "Padrão do papel" in r.text and ">Permitir<" in r.text
          and ">Negar<" in r.text)

    # ================= 2.33.2 — ficha com dialogs =================
    base_html = _tpl("base.html")
    check("base: CSS .modal.largo", ".modal.largo" in base_html)
    check("base: JS data-abre-dlg / data-fecha-dlg",
          "data-abre-dlg" in base_html and "data-fecha-dlg" in base_html)

    from src.core.frota_repo import FrotaRepository
    fr = FrotaRepository()
    vid = fr.add_veiculo(modelo="Fiorino", marca="Fiat", tipo="carro",
                         subtipo="", placa="ABC1D23", proprio=True,
                         contratante="", empresa_id=None)

    r = client.get(f"/frota/{vid}")
    check("ficha 200", r.status_code == 200)
    for dlg in ("dlg-docs", "dlg-laudos", "dlg-movs", "dlg-abasts",
                "dlg-custo", "dlg-checklists", "dlg-manut"):
        if f'id="{dlg}"' not in r.text:
            check(f"ficha: dialog {dlg} presente", False)
    check("ficha: 7 dialogs presentes",
          all(f'id="{d}"' in r.text for d in
              ("dlg-docs", "dlg-laudos", "dlg-movs", "dlg-abasts",
               "dlg-custo", "dlg-checklists", "dlg-manut")))
    check("ficha: toolbar com data-abre-dlg",
          "data-abre-dlg" in r.text)
    check("ficha: situação atual (badge Disponível)",
          "Disponível" in r.text)
    check("ficha: cabeçalho exibe motorista atual quando houver",
          "{% if v.motorista_atual %} · Motorista: <b>{{ v.motorista_atual }}</b>"
          in _tpl("frota_ficha.html"))

    ficha = _tpl("frota_ficha.html")
    check("ficha template: 7 dialogs largos (custo virou largo na v1.49.0)",
          len(re.findall(r'<dialog id="dlg-[a-z]+" class="modal largo">',
                         ficha)) == 7
          and len(re.findall(r'<dialog id="dlg-[a-z]+" class="modal">',
                             ficha)) == 0)
    check("ficha template: sem details.card de seções antigas",
          'details class="card"' not in ficha)

    # ---------- resultado ----------
    print()
    if FALHAS:
        print(f"FALHAS: {len(FALHAS)}")
        for f_ in FALHAS:
            print("  -", f_)
        sys.exit(1)
    print("Tudo OK.")


if __name__ == "__main__":
    main()
