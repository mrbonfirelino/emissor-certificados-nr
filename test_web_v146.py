"""Testes do Portal Web — v1.45.3.

Padrão standalone: `python test_web_v146.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.

Cobre:
- versão do sistema no header (login e páginas autenticadas)
- emissão individual: TMPLS embutido, sem window.location na troca de NR,
  extras dinâmicos, campo de data com máscara/calendário
- emissão em lote: restauração da seleção (sessionStorage), numéricos
- overlay: guard defaultPrevented no base.html
- máscaras js-data/js-num/js-dec/js-hora/js-tel/js-cnpj nos formulários
- validação server de CNPJ (frota + integrações), formato quando preenchido
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
    tmp = Path(tempfile.mkdtemp(prefix="webv146_"))
    tmp.mkdir(parents=True, exist_ok=True)
    import src.utils.paths as paths_mod
    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.certificate_service as cert_mod
    import src.core.pptx_certificate_service as pptx_cert_mod
    import src.web.app as app_mod

    paths_mod.get_data_dir = lambda: tmp
    er_mod.get_db_path = lambda: tmp / "certificados.db"
    hr_mod.get_db_path = lambda: tmp / "certificados.db"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
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

    # funcionários para os formulários de emissão renderizarem
    from src.core.employee_repo import EmployeeRepository
    er = EmployeeRepository(db_path=tmp / "certificados.db")
    er.create(nome="Ana Silva", cpf="529.982.247-25")
    er.create(nome="Bruno Souza", cpf="111.444.777-35")

    # ---------- 1. versão no header ----------
    r = client.get("/login")
    check("login 200", r.status_code == 200)
    check("login mostra versão v1.45.3", 'class="versao">v1.45.3<' in r.text)

    _login_admin(client, tmp)
    r = client.get("/")
    check("dashboard 200", r.status_code == 200)
    check("dashboard mostra versão no header",
          'class="versao">v1.45.3<' in r.text)

    base_html = _tpl("base.html")

    # ---------- 2. base.html: guard + helpers ----------
    check("base: guard defaultPrevented no listener genérico",
          "if (ev.defaultPrevented) return;" in base_html)
    check("base: calendário nativo (showPicker)", "showPicker" in base_html)
    check("base: helper reutilizável (normaTechMascaras)",
          "window.normaTechMascaras" in base_html)
    check("base: máscaras js-data/js-num/js-dec/js-hora/js-cnpj/js-tel",
          all(c in base_html for c in
              ("js-data", "js-num", "js-dec", "js-hora", "js-cnpj", "js-tel")))

    # ---------- 3. emissão individual ----------
    r = client.get("/certificados")
    check("certificados 200", r.status_code == 200)
    check("certificados: TMPLS embutido (JSON por NR)", "var TMPLS = {" in r.text)
    check("certificados: sem window.location na troca de NR",
          "window.location='/certificados?nr=" not in r.text)
    check("certificados: select de NR sem onchange",
          not re.search(r'<select id="nr"[^>]*onchange', r.text))
    check("certificados: container de extras dinâmicos",
          'id="extras-din"' in r.text)
    check("certificados: função aplicarNR presente",
          "function aplicarNR" in r.text)
    check("certificados: campo de data com js-data",
          re.search(r'name="data"[^>]*class="js-data"', r.text) is not None)
    check("certificados: validação de funcionário antes do envio",
          "Selecione o funcionário na busca." in r.text)

    # sem funcionário: servidor rejeita (overlay é guardado no client)
    r = client.post("/certificados/emitir", data={"funcionario_id": "",
                                                  "nr": "NR-35"})
    check("emitir sem funcionário -> redirect + flash",
          r.status_code == 303 and r.headers.get("location") == "/certificados")

    # ---------- 4. emissão em lote ----------
    r = client.get("/emissao-lote")
    check("lote 200", r.status_code == 200)
    check("lote: restaura seleção via sessionStorage",
          "sessionStorage.getItem('lote_sel')" in r.text
          and "sessionStorage.setItem('lote_sel'" in r.text)
    check("lote: select de NR sem submit inline",
          not re.search(r'<select id="nr"[^>]*onchange', r.text))
    check("lote: data global com js-data",
          re.search(r'name="data"[^>]*class="js-data"', r.text) is not None)
    check("lote: carga/validade globais viraram number",
          '<input type="number" id="carga" name="carga"' in r.text
          and '<input type="number" id="validade" name="validade"' in r.text)
    check("lote: data/carga/validade individuais blindadas",
          re.search(r'name="data_\d+" class="js-data"', r.text) is not None
          and '<input type="number" name="carga_' in r.text
          and '<input type="number" name="validade_' in r.text)

    # ---------- 5. máscaras nos formulários ----------
    f = _tpl("funcionario_form.html")
    check("funcionário: telefone js-tel", 'name="telefone" class="js-tel"' in f)
    check("funcionário: nascimento/admissão js-data",
          'id="nascimento" name="nascimento" class="js-data"' in f
          and 'id="admissao" name="admissao" class="js-data"' in f)
    check("funcionário: CPF continua com máscara própria",
          "maxlength=\"14\"" in f and "replace(/\\D/g" in f)

    check("ASO: data do exame js-data",
          'id="data_exame" name="data_exame" class="js-data"'
          in _tpl("aso_form.html"))

    epi = _tpl("epi_form.html")
    check("EPI: entrega js-data + qtd js-num",
          'id="data_emissao" name="data_emissao" class="js-data"' in epi
          and 'name="item_qtd_{{ i }}" class="js-num"' in epi)
    check("EPI: linhas dinâmicas religam máscaras",
          "normaTechMascaras(tr)" in epi and 'class="js-data" value="{{ hoje }}"' in epi)

    epif = _tpl("epi_ficha.html")
    check("EPI ficha: dev_qtd js-num + data devolução js-data",
          'class="js-num" placeholder="Ex.: 2"' in epif
          and 'name="data_devolucao" class="js-data"' in epif)

    check("crachás: data de emissão js-data",
          'name="data_emissao" class="js-data"' in _tpl("crachas_novo.html"))

    ab = _tpl("frota_abast_form.html")
    check("abastecimento: data js-data + litros/valor js-dec",
          'id="data" name="data" class="js-data"' in ab
          and 'id="litros" name="litros" class="js-dec"' in ab
          and 'id="valor" name="valor" class="js-dec"' in ab)

    ck = _tpl("frota_checklist_form.html")
    check("checklist: datas inicial/final js-data",
          'id="data_inicial" name="data_inicial" class="js-data"' in ck
          and 'id="data_final" name="data_final" class="js-data"' in ck)

    ff = _tpl("frota_form.html")
    check("frota form: fim de contrato js-data + km/l js-dec",
          'id="fim_contrato" name="fim_contrato" class="js-data"' in ff
          and 'id="km_l" name="km_l" class="js-dec"' in ff)
    check("frota form: campo ano continua livre (aceita 2021/2022)",
          'id="ano" name="ano"' in ff and 'id="ano" name="ano" class="js-num"' not in ff)

    ficha = _tpl("frota_ficha.html")
    check("frota ficha: script morto de máscaras removido",
          "_masc_d" not in ficha and ficha.rstrip().endswith("{% endblock %}"))
    check("frota ficha: saída/entrada com js-data e js-hora",
          'name="data_saida" class="js-data"' in ficha
          and 'name="hora" class="js-hora"' in ficha
          and 'name="data_entrada" class="js-data"' in ficha
          and 'name="hora_entrada" class="js-hora"' in ficha)
    check("frota ficha: laudos/manutenção com js-data",
          'name="emissao" class="js-data"' in ficha
          and 'name="validade" class="js-data"' in ficha
          and 'name="data_feito" class="js-data"' in ficha
          and 'name="data_ultima" class="js-data"' in ficha)

    nfs = _tpl("frota_nfs.html")
    check("NFs: data js-data + valores js-dec",
          'name="data_nf" class="js-data"' in nfs
          and 'name="litros" class="js-dec"' in nfs
          and 'name="valor" class="js-dec"' in nfs
          and 'name="valor_nf" class="js-dec"' in nfs)

    hist = _tpl("historico.html")
    check("histórico: filtros De/Até com js-data",
          'id="de" name="de" class="js-data"' in hist
          and 'id="ate" name="ate" class="js-data"' in hist)

    # ---------- 6. CNPJ: máscara + validação server ----------
    for tpl in ("empresas.html", "frota_empresas.html",
                "frota_fornecedores.html"):
        t = _tpl(tpl)
        check(f"{tpl}: campos de CNPJ com js-cnpj", 'class="js-cnpj"' in t)

    r = client.post("/frota/empresas/criar",
                    data={"nome": "Empresa Ruim", "cnpj": "12.345"})
    r = client.get("/frota/empresas")
    check("frota: CNPJ incompleto rejeitado com aviso",
          "CNPJ inválido" in r.text and "Empresa Ruim" not in r.text)

    r = client.post("/frota/empresas/criar",
                    data={"nome": "Empresa Boa LTDA", "cnpj": "12345678000199"})
    r = client.get("/frota/empresas")
    check("frota: CNPJ com 14 dígitos aceito",
          r.status_code == 200 and "Empresa Boa LTDA" in r.text)

    r = client.post("/frota/empresas/criar",
                    data={"nome": "Empresa Sem CNPJ", "cnpj": ""})
    r = client.get("/frota/empresas")
    check("frota: CNPJ vazio continua permitido",
          r.status_code == 200 and "Empresa Sem CNPJ" in r.text)

    r = client.post("/empresas/criar",
                    data={"nome": "Integra Ruim", "cnpj": "123"})
    r = client.get("/empresas")
    check("integrações: CNPJ inválido rejeitado",
          "CNPJ inválido" in r.text and "Integra Ruim" not in r.text)

    r = client.post("/empresas/criar",
                    data={"nome": "Integra Boa", "cnpj": "12345678000195"})
    r = client.get("/empresas")
    check("integrações: CNPJ válido aceito",
          r.status_code == 200 and "Integra Boa" in r.text)

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
