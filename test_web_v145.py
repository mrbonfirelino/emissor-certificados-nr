"""Testes do Portal Web — v1.45.0 (ROADMAP 2.31.4/2.32).

Padrão standalone: `python test_web_v145.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.

Cobre:
- emissão em lote como job de fundo (fetch) com polling /jobs/{id}
- erro de validação via fetch volta JSON
- importação de fotos em massa no portal (casamento CPF/nome + confirmação)
- menu trocado (grupo "Funcionários" com item "Cadastros")
- template de abastecimento sem campo "superior"; PDF com "Aprovado"
"""

import io
import re
import sys
import tempfile
import time
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


def _png_bytes():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (120, 160), (200, 180, 160)).save(buf, "PNG")
    return buf.getvalue()


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="webv145_"))
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


def _aguardar_job(client, jid, timeout_s=20):
    fim = time.time() + timeout_s
    while time.time() < fim:
        r = client.get(f"/jobs/{jid}")
        if r.status_code == 200:
            s = r.json()
            if s.get("status") in ("concluido", "erro"):
                return s
        time.sleep(0.05)
    return {"status": "timeout"}


def main():
    client, tmp = make_env()
    from src.core.employee_repo import EmployeeRepository
    from src.core.template_loader import load_all_templates
    er = EmployeeRepository()
    tmpl = load_all_templates()["NR-35"]

    _login_admin(client, tmp)

    id1 = er.create("Lote Um da Silva", "529.982.247-25", "Eletricista")
    id2 = er.create("Lote Dois Souza", "111.444.777-35", "Mecânico")
    check("1. funcionarios criados", bool(id1 and id2))

    # menu trocado (2.31.4) -----------------------------------------------
    r = client.get("/")
    check("2. grupo Funcionarios no menu",
          "Funcionários ▾" in r.text)
    check("3. item Cadastros no grupo", ">Cadastros<" in r.text)
    check("4. item antigo Funcionarios sumiu do menu",
          ">Funcionários</a>" not in r.text.replace(">Cadastros</a>", ""))

    # job de emissão em lote via fetch (2.32.1) ----------------------------
    r = client.post("/emissao-lote/emitir",
                    headers={"X-Requested-With": "fetch"},
                    data={"nr": "NR-35", "data": "11/09/2026", "carga": "8",
                          "validade": "12", "descricao": tmpl.descricao_padrao,
                          "sel_%d" % id1: "1", "sel_%d" % id2: "1"})
    j = r.json()
    check("5. fetch lote responde JSON com job",
          r.status_code == 200 and j.get("ok") and j.get("job"))
    status = _aguardar_job(client, j["job"])
    check("6. job concluido", status.get("status") == "concluido")
    check("7. progresso 100%", status.get("pct") == 100)
    check("8. sem erros no job", status.get("n_erros") == 0)
    red = status.get("redirect", "")
    check("9. redirect do resultado", red.startswith("/emissao-lote/resultado/"))
    r = client.get(red)
    check("10. pagina de resultado 200",
          r.status_code == 200 and "CERT-" in r.text)

    # validação via fetch volta JSON ---------------------------------------
    r = client.post("/emissao-lote/emitir",
                    headers={"X-Requested-With": "fetch"},
                    data={"nr": "NR-35", "data": "11/09/2026", "carga": "8",
                          "validade": "12",
                          "descricao": tmpl.descricao_padrao})
    j = r.json()
    check("11. fetch sem selecionados: JSON ok=False",
          r.status_code == 200 and j.get("ok") is False
          and "funcionário" in j.get("erro", ""))

    # importação de fotos em massa (2.32.1) --------------------------------
    id3 = er.create("Joao Da Silva", None, "Pedreiro")
    png = _png_bytes()
    r = client.post("/funcionarios/importar-fotos",
                    files=[("fotos", ("52998224725.png", png, "image/png")),
                           ("fotos", ("JOAO DA SILVA.png", png, "image/png")),
                           ("fotos", ("Nao Cadastrado.png", png, "image/png"))])
    check("12. pagina de conferencia 200", r.status_code == 200)
    check("13. funcionario listado na conferencia",
          "Lote Um da Silva" in r.text and "Joao Da Silva" in r.text)
    m = re.search(r'name="token" value="([^"]+)"', r.text)
    check("14. token de sessao presente", bool(m))
    token = m.group(1) if m else ""
    check("15. nao casado listado com motivo", "Nao Cadastrado.png" in r.text)
    r = client.get(f"/funcionarios/importar-fotos/preview/{token}/0")
    check("15b. preview da foto 200",
          r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"))

    r = client.post("/funcionarios/importar-fotos/confirmar",
                    data={"token": token, "aplicar_0": "on",
                          "aplicar_1": "on"})
    check("16. confirmacao redireciona",
          r.status_code == 303 and "/funcionarios" in r.headers.get("location", ""))
    e1 = er.get_by_id(id1)
    e3 = er.get_by_id(id3)
    check("17. foto aplicada (CPF)", bool(e1.foto))
    check("18. foto aplicada (nome)", bool(e3.foto))
    r = client.get(f"/funcionarios/{id1}/foto")
    check("19. foto servida", r.status_code == 200)

    # abastecimento sem aprovador (2.32.2) ---------------------------------
    tpl_path = Path("src/web/templates/frota_abast_form.html")
    texto = tpl_path.read_text(encoding="utf-8")
    check("20. form sem campo superior", 'name="superior"' not in texto)

    import src.core.pdf_abastecimento as pdf_abast_mod
    pasta_abast = tmp / "abastecimentos"
    pasta_abast.mkdir(parents=True, exist_ok=True)
    pdf_abast_mod.get_abastecimentos_dir = lambda: pasta_abast
    pdf_abast_mod.get_logo_path = lambda: None
    pdf_path = pdf_abast_mod.gerar_pdf_abastecimento({
        "serial": "AB-2026-00001", "data_br": "17/09/2026",
        "veiculo": {"modelo": "New Fiesta", "placa": "KWK-6C02"},
        "fornecedor": {"nome": "Posto Teste"},
        "combustivel": "gasolina", "condutor": "João Condutor",
        "viagem_servico": "Viagem teste", "km": 100000, "obs": "",
        "config": SimpleNamespace(empresa_nome="Empresa Teste LTDA",
                                  empresa_cnpj="11.222.333/0001-81",
                                  local_treinamento="Planta Teste"),
    })
    check("20b. pdf gerado no tmp", Path(pdf_path).is_relative_to(tmp))
    import fitz
    with fitz.open(pdf_path) as doc:
        texto_pdf = "".join(p.get_text() for p in doc)
    check("21. PDF tem Aprovado", "Aprovado" in texto_pdf)
    check("22. PDF sem nome do aprovador",
          "Aprovação (superior)" not in texto_pdf
          and "Superior" not in texto_pdf.replace("Aprovação do Superior", ""))

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHAS: " + "; ".join(FALHAS))
        return 1
    print(f"{24} checks v1.45.0 OK")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
