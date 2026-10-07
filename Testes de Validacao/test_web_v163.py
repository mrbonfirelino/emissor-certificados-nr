# -*- coding: utf-8 -*-
"""Testes do Portal Web - v1.63.0 (itens altos do roadmap novo).

Cobre:
- Checkbox 'Treinamento de varios dias' corrigido (930): ternario nos
  templates certificados.html e emissao_lote.html
- Dashboard: card grande de Vencimentos removido; stat-card unico
  'Vencem em 30 dias' visivel apenas para setor seguranca (926)
- MOTW: helper remover_motw existe e nao levanta em arquivo comum (932)
- Fallback PPTX logado: 'pptx-fallback' presente no certificate_service (933)
- Romaneios: estado vazio explicativo na lista (934)
- Usuarios: card 'Permissoes por setor' compacto em tabela (928)
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHA'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="webv163_"))
    tmp.mkdir(parents=True, exist_ok=True)
    import src.utils.paths as paths_mod
    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.frota_repo as fr_mod
    import src.core.config as config_mod
    import src.web.app as app_mod

    paths_mod.get_data_dir = lambda: tmp
    er_mod.get_db_path = lambda: tmp / "certificados.db"
    hr_mod.get_db_path = lambda: tmp / "certificados.db"
    fr_mod.get_db_path = lambda: tmp / "certificados.db"
    config_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
    app_mod.get_data_dir = lambda: tmp
    import src.web.users_repo as users_mod
    users_mod.get_db_path = lambda: tmp / "certificados.db"
    import src.core.romaneio_repo as rom_mod
    rom_mod.get_db_path = lambda: tmp / "certificados.db"

    from src.web.app import create_app
    from fastapi.testclient import TestClient
    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    client = TestClient(app, follow_redirects=False)
    return client, tmp


def _login_admin(client, tmp):
    from src.core.employee_repo import EmployeeRepository
    from src.core.frota_repo import FrotaRepository
    EmployeeRepository()
    FrotaRepository()
    txt = (tmp / "web_admin_provisorio.txt").read_text(encoding="utf-8")
    prov = [l.split(":")[1].strip() for l in txt.splitlines()
            if l.startswith("SENHA PROVISORIA")][0]
    client.post("/login", data={"username": "admin", "password": prov})
    client.post("/troca-senha", data={"atual": prov, "nova": "nova1630",
                                      "confirma": "nova1630"})
    return prov


def main():
    print("=== v1.63.0: fixes altos (930/926/932/933/934/928) ===")
    raiz = Path(__file__).resolve().parent.parent
    tpl = raiz / "src" / "web" / "templates"

    # 930: checkbox multi-dia corrigido
    for t in ("certificados.html", "emissao_lote.html"):
        src_t = (tpl / t).read_text(encoding="utf-8")
        check(f"V63-1 {t}: ternario corrigido",
              "this.checked ? 'block' : 'none'" in src_t)
        check(f"V63-2 {t}: campo-inicio oculto por padrao (checkbox desligado)",
              ('style="display:{% if form_salvo' in src_t)
              or 'id="campo-inicio" style="display:none;"' in src_t)

    # 932: remover_motw
    from src.utils.com_pdf_errors import remover_motw  # noqa
    check("V63-3 remover_motw importavel", True)
    f = tmp_txt = Path(tempfile.mkdtemp(prefix="motw_")) / "a.txt"
    f.write_text("x", encoding="utf-8")
    try:
        remover_motw(f)
        check("V63-4 remover_motw no-op sem MOTW", True)
    except Exception:
        check("V63-4 remover_motw no-op sem MOTW", False)
    for py in ("presenca_generator.py", "romaneio_pdf.py",
               "pptx_card_service.py", "pptx_certificate_service.py"):
        check(f"V63-5 {py} chama remover_motw",
              "remover_motw" in (raiz / "src" / "core" / py).read_text(encoding="utf-8"))
    check("V63-6 bat com Unblock-File",
          "Unblock-File" in (raiz / "deploy" / "web" / "ATUALIZAR_PORTAL.bat")
          .read_text(encoding="utf-8", errors="replace"))

    # 933: fallback logado
    check("V63-7 pptx-fallback no certificate_service",
          "pptx-fallback" in (raiz / "src" / "core" / "certificate_service.py")
          .read_text(encoding="utf-8"))

    # web
    client, tmp = make_env()
    _login_admin(client, tmp)

    # admin vira setor seguranca para ver o card de vencimentos
    from src.web.users_repo import UsersRepository
    users = UsersRepository()
    uid = [u["id"] for u in users.list_users() if u["username"] == "admin"][0]
    users.set_setor(uid, "seguranca")

    r = client.get("/")
    check("V63-8 dashboard 200", r.status_code == 200)
    html = r.text
    check("V63-9 stat-card Vencem em 30 dias presente (setor seguranca)",
          "Vencem em 30 dias (vencimentos)" in html)
    check("V63-10 card grande de Vencimentos removido",
          "Vencimentos</h2>" not in html)  # itens_urgentes agora aparece no JS do sino (941)

    # consulta sem setor nao ve o card
    users.set_setor(uid, "")
    r2 = client.get("/")
    check("V63-11 dashboard sem setor: card oculto",
          "(vencimentos)" not in r2.text)

    # 934: romaneios lista com estado vazio explicativo
    r3 = client.get("/romaneios")
    check("V63-12 /romaneios 200", r3.status_code == 200)
    if "Nenhum romaneio" not in r3.text:
        print("    [debug] /romaneios trecho:", r3.text[-400:].replace("\n", " "))
    check("V63-13 /romaneios estado vazio explicativo",
          "Nenhum romaneio" in r3.text and "Novo Romaneio" in r3.text)

    # 928: permissoes por setor em tabela compacta
    r4 = client.get("/usuarios")
    check("V63-14 /usuarios 200", r4.status_code == 200)
    check("V63-15 card setor usa tabela",
          "Permiss" in r4.text and "permissoes-setor" in r4.text
          and "por setor" in r4.text and ">Acesso</th>" in r4.text)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHAS:")
        for f2 in FALHAS:
            print(" -", f2)
        sys.exit(1)
    print("TODOS OS CHECKS DA v1.63.0 PASSARAM.")


if __name__ == "__main__":
    main()

