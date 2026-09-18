"""Testes v1.44.0 — 2.31: status do veículo, colunas, checklist branco,
abastecimento assinado, menu Segurança/Cadastros, dashboard.

Roda direto:  python test_web_v144.py
"""

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import src.utils.paths as paths_mod
import src.core.employee_repo as er_mod
import src.core.history_repo as hr_mod
import src.core.aso_repo as aso_mod
import src.core.integracao_repo as integ_mod
import src.core.frota_repo as fr_mod
from src.core.frota_repo import FrotaRepository
import src.core.certificate_service as cert_mod
import src.web.app as app_mod

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="test_web_v144_"))
    paths_mod.get_data_dir = lambda: tmp
    for m in (er_mod, hr_mod, aso_mod, integ_mod, fr_mod):
        m.get_db_path = lambda: tmp / "certificados.db"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA",
        empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste",
        instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
    app_mod.get_data_dir = lambda: tmp
    logo = tmp / "logo.png"
    try:
        from PIL import Image

        Image.new("RGB", (4, 4), (10, 60, 120)).save(logo, "PNG")
    except Exception:
        logo.write_bytes(b"\x89PNG\r\n\x1a\n")
    paths_mod.get_logo_path = lambda: logo
    try:
        import src.core.pdf_checklist as pchk_mod

        pchk_mod.get_logo_path = lambda: logo
    except Exception:
        pass
    return tmp


def _login_admin(client):
    from src.web.users_repo import UsersRepository

    users = UsersRepository()
    admin = users.get_by_username("admin")
    prov = users.reset_password(admin["id"])
    r = client.post("/login", data={"username": "admin", "password": prov},
                    follow_redirects=False)
    assert r.status_code == 303, r.status_code
    r = client.post("/troca-senha",
                    data={"atual": prov, "nova": "SenhaF0rte",
                          "confirma": "SenhaF0rte"},
                    follow_redirects=False)
    assert r.status_code == 303, r.status_code
    return users


def main():
    tmp = make_env()
    from src.web.app import create_app

    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    client = TestClient(app, follow_redirects=False)
    _login_admin(client)
    repo = FrotaRepository()

    ontem = (date.today() - timedelta(days=1)).isoformat()
    v1 = repo.add_veiculo("New Fiesta", "Ford", "caminhao", "munck",
                          "KWK-6C02", True, "", None)
    repo.add_mov_saida(v1, date.today().isoformat(), "07:00", 1000,
                       "OBRA X", "Serviço", "", "JOÃO", "Chefia")
    v2 = repo.add_veiculo("Hilux", "Toyota", "pickup", "", "ABC1D23",
                          True, "", None)
    v3 = repo.add_veiculo("Strada", "Fiat", "pickup", "", "GHI2E34",
                          False, "LOCADORA Y", None,
                          fim_contrato_aluguel=ontem)

    # ---- lista: status derivado + colunas simplificadas ----
    r = client.get("/frota")
    t = r.text
    check("V01 lista 200", r.status_code == 200)
    check("V02 Em Viagem + b-azul", "Em Viagem" in t and "b-azul" in t)
    check("V03 motorista JOÃO na lista", "JOÃO" in t)
    check("V04 destino OBRA X na lista", "OBRA X" in t)
    check("V05 Disponível + b-verde", "Disponível" in t and "b-verde" in t)
    check("V06 Indisponível (contrato vencido) + b-cinza",
          "Indisponível" in t and "b-cinza" in t)
    check("V07 veículo simplificado PLACA - Marca Modelo",
          "KWK-6C02 - " in t)
    check("V08 coluna Placa removida", "<th>Placa</th>" not in t)
    check("V09 coluna Ano/Cor removida", "<th>Ano/Cor</th>" not in t)
    check("V10 colunas Motorista/Destino", "<th>Motorista</th>" in t
          and "<th>Destino</th>" in t)
    check("V11 scrollbar na lista", "max-height:560px" in t
          and "overflow-y:auto" in t)

    # ---- checklist em branco (pré-preenchido) ----
    antes = len(repo.list_checklists(v1))
    r = client.get(f"/frota/{v1}/checklist/branco")
    check("V12 checklist branco 303", r.status_code == 303)
    lst = repo.list_checklists(v1)
    check("V13 registro criado", len(lst) == antes + 1)
    chk = max(lst, key=lambda c: c["id"])
    r2 = client.get(f"/frota/{v1}")
    check("V14 flash com serial CKL",
          f"Checklist {chk['serial']}" in r2.text
          and "preenchimento manual" in r2.text)
    pdf = Path(chk["pdf_path"]) if chk.get("pdf_path") else None
    check("V15 PDF do checklist branco válido",
          pdf is not None and pdf.exists()
          and pdf.read_bytes()[:5] == b"%PDF-")

    # ---- abastecimento assinado ----
    r = client.post("/frota/abastecimentos/criar",
                    data={"veiculo_id": str(v2), "fornecedor_id": "",
                          "data": "16/09/2026", "combustivel": "diesel",
                          "viagem_servico": "Viagem teste", "km": "15000",
                          "condutor": "PEDRO", "superior": "Chefia",
                          "obs": "", "litros": "", "valor": ""})
    check("V16 abast criado", r.status_code == 303)
    abasts = repo.list_abastecimentos("", 100, 0)[0]
    aid = max(a["id"] for a in abasts)
    bytes_png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    r = client.post(f"/frota/abastecimentos/{aid}/assinado",
                    files={"arquivo": ("assin.png", bytes_png, "image/png")})
    check("V17 upload assinado 303", r.status_code == 303)
    anexo = repo.get_abast_signed(aid)
    check("V18 anexo gravado", anexo is not None
          and anexo["assinado_filename"] == "assin.png")
    r = client.get(f"/frota/abastecimentos/{aid}/assinado/download")
    check("V19 download 200 mesmo conteúdo",
          r.status_code == 200 and r.content == bytes_png)
    r = client.post(f"/frota/abastecimentos/{aid}/assinado/excluir")
    check("V20 excluir 303", r.status_code == 303)
    check("V21 anexo removido", repo.get_abast_signed(aid) is None)

    # ---- menu Estrutura A ----
    r = client.get("/certificados")
    t = r.text
    check("V22 grupo Segurança", "Segurança" in t)
    check("V23 Ficha de EPIs (EPI renomeado)",
          "Ficha de EPIs" in t and ">EPI</a>" not in t)
    check("V24 botão Gestão de Frota", "Gestão de Frota" in t)

    # ---- dashboard ----
    r = client.get("/")
    t = r.text
    check("V25 atalho Vencimentos", "/vencimentos" in t)
    check("V26 scrollbar aniversariantes", "max-height:220px" in t)

    # ---- consulta vê mas não escreve ----
    users = _login_users()
    users.create_user("pedro", "Pedro Consulta", "consulta")
    prov = users.reset_password(users.get_by_username("pedro")["id"])
    client.post("/logout", follow_redirects=False)
    client.post("/login", data={"username": "pedro", "password": prov},
                follow_redirects=False)
    client.post("/troca-senha",
                data={"atual": prov, "nova": "SenhaF0rte",
                      "confirma": "SenhaF0rte"}, follow_redirects=False)
    check("V27 consulta vê /frota", client.get("/frota").status_code == 200)
    r = client.post(f"/frota/abastecimentos/{aid}/assinado",
                    files={"arquivo": ("x.png", bytes_png, "image/png")})
    check("V28 consulta não anexa (303)", r.status_code == 303
          and repo.get_abast_signed(aid) is None)

    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}): {', '.join(FALHAS)}")
        sys.exit(1)
    print("TESTES V144 OK")


def _login_users():
    from src.web.users_repo import UsersRepository

    return UsersRepository()


if __name__ == "__main__":
    main()
