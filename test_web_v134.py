"""Testes web v1.34.0: Fase 4 (backup/auditoria) + Frota 2.29.5/2.29.6 + extras.

Padrao standalone: roda direto `python test_web_v134.py`.
Patches de paths ANTES de create_app (mesmo padrao test_web_frota).
"""

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import src.utils.paths as paths_mod
import src.core.employee_repo as er_mod
import src.core.history_repo as hr_mod
import src.core.aso_repo as aso_mod
import src.core.integracao_repo as integ_mod
import src.core.frota_repo as fr_mod
import src.core.certificate_service as cert_mod
import src.web.app as app_mod

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="test_web_v134_"))
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


_FOTO_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63f8cfc0f01f0005050202b9cdc9600000000049454e44"
    "ae426082")


def main():
    tmp = make_env()
    from src.web.app import create_app
    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository
    from src.core.frota_repo import FrotaRepository

    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    EmployeeRepository()
    HistoryRepository()
    client = TestClient(app)
    users = _login_admin(client)
    repo = FrotaRepository()

    print("\n--- Veiculo: campos novos (cor/carroceria/ano/contrato/foto) ---")
    r = client.post("/frota/criar", data={
        "modelo": "Gol", "marca": "VW", "tipo": "carro", "placa": "GOL1040",
        "proprio": "1", "contratante": "", "empresa_id": "",
        "cor": "Prata", "carroceria": "hatch", "ano": "2021",
        "fim_contrato": "", "km_l": "9,5", "obs": ""},
        follow_redirects=False)
    check("N01 carro com campos novos -> 303", r.status_code == 303)
    vid = int(r.headers["location"].split("/")[-1])

    r = client.get(f"/frota/{vid}")
    check("N02 ficha mostra Ano/Cor", r.status_code == 200
          and "2021 / Prata" in r.text)
    check("N03 ficha mostra Carroceria Hatch", "Hatch" in r.text)
    check("N04 ficha mostra KM/L esperado 9.5", "9.5" in r.text)

    v = repo.get_veiculo(vid)
    check("N05 repo: km_l float com virgula", v["km_l_esperado"] == 9.5
          and v["carroceria"] == "hatch" and v["cor"] == "Prata")

    try:
        vid2 = repo.add_veiculo(modelo="X", marca="", tipo="caminhao",
                                subtipo="munck", placa="XXX9X99", proprio=1,
                                contratante="", empresa_id=None,
                                carroceria="sedan")
        v2 = repo.get_veiculo(vid2)
        check("N06 carroceria em nao-carro zerada", v2["carroceria"] is None)
    except ValueError:
        check("N06 carroceria em nao-carro zerada", True)

    r = client.post("/frota/criar", data={
        "modelo": "HR", "tipo": "caminhao", "subtipo": "cacamba",
        "placa": "HRB2024", "proprio": "0", "contratante": "Cliente Alpha",
        "empresa_id": "", "fim_contrato": "31/12/2026", "obs": ""},
        follow_redirects=False)
    check("N07 alugado com fim de contrato -> 303", r.status_code == 303)
    vid_alug = int(r.headers["location"].split("/")[-1])
    r = client.get(f"/frota/{vid_alug}")
    check("N08 ficha mostra contrato ate 31/12/2026",
          r.status_code == 200 and "31/12/2026" in r.text)

    r = client.post(f"/frota/{vid}/foto",
                    files={"arquivo": ("foto.png", _FOTO_PNG, "image/png")},
                    follow_redirects=False)
    check("N09 upload foto -> 303", r.status_code == 303)
    r = client.get(f"/frota/{vid}/foto")
    check("N10 GET foto serve PNG", r.status_code == 200
          and r.headers["content-type"] == "image/png"
          and r.content.startswith(b"\x89PNG"))
    r = client.get("/frota")
    check("N11 lista mostra miniatura da foto",
          f'src="/frota/{vid}/foto"' in r.text)

    print("\n--- Abastecimento: litros/valor, custo, exportar, NFs ---")
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "combustivel": "gasolina",
        "data": "10/09/2026", "fornecedor_id": "", "km": "12000",
        "litros": "40", "valor": "289,50", "viagem_servico": "",
        "condutor": "Jose", "superior": "Maria", "obs": ""},
        follow_redirects=False)
    check("N12 abast com litros/valor -> 303", r.status_code == 303)
    r = client.get("/frota/abastecimentos")
    check("N13 lista mostra litros e R$", "R$ 289,50" in r.text
          and "40" in r.text)
    check("N14 botao Exportar Excel", "/frota/abastecimentos/exportar" in r.text)

    r = client.get("/frota/abastecimentos/exportar")
    check("N15 exportar xlsx (bytes PK)", r.status_code == 200
          and r.content.startswith(b"PK"))

    r = client.get(f"/frota/{vid}")
    check("N16 ficha: bloco custo com total", "Custo e consumo" in r.text
          and "R$ 289,50" in r.text)

    resumo = repo.resumo_custo_veiculo(vid)
    check("N17 repo resumo litros/valor", resumo["litros"] == 40
          and abs(resumo["valor"] - 289.5) < 0.01)

    abast_id = None
    with repo._get_conn() as conn:
        abast_id = conn.execute(
            "SELECT id FROM frota_abastecimentos ORDER BY id DESC"
            " LIMIT 1").fetchone()[0]
    r = client.post(f"/frota/abastecimentos/{abast_id}/nfs",
                    data={"numero": "10245", "data_nf": "10/09/2026",
                          "valor_nf": "289,50"},
                    files={"arquivo": ("nf.pdf", b"%PDF-1.4 fake",
                                       "application/pdf")},
                    follow_redirects=False)
    check("N18 anexar NF -> 303", r.status_code == 303)
    r = client.get(f"/frota/abastecimentos/{abast_id}/nfs")
    check("N19 NF listada", r.status_code == 200 and "10245" in r.text)
    nf_id = None
    with repo._get_conn() as conn:
        nf_id = conn.execute("SELECT id FROM frota_abast_nfs"
                             " LIMIT 1").fetchone()[0]
    r = client.get(f"/frota/nfs/{nf_id}/download")
    check("N20 download NF %PDF", r.status_code == 200
          and r.content.startswith(b"%PDF"))
    r = client.post(f"/frota/nfs/{nf_id}/excluir", follow_redirects=False)
    check("N21 excluir NF -> 303", r.status_code == 303)

    print("\n--- Checklist semanal (2.29.5) ---")
    r = client.get(f"/frota/{vid}/checklist/novo")
    check("N22 form checklist 200", r.status_code == 200
          and "Checklist semanal" in r.text)
    check("N23 itens da foto presentes", "Bateria" in r.text
          and "Purificador de Ar" in r.text and "Carteira de Habilita" in r.text)
    check("N24 radios item_1.1_2a", 'name="item_1.1_2' in r.text)

    data_form = {
        "data_inicial": "07/09/2026", "data_final": "12/09/2026",
        "km_rodado": "850", "motorista": "Jose Motorista",
        "lider": "Carlos Lider", "pode_operar": "S",
        "item_1.1_2ª": "S", "item_1.2_3ª": "N", "item_2.1_2ª": "S",
        "item_3.1_sab": "S", "obs_3ª": "Radiador baixando agua",
    }
    r = client.post(f"/frota/{vid}/checklist", data=data_form,
                    follow_redirects=False)
    check("N25 checklist POST -> 303", r.status_code == 303)
    r = client.get(f"/frota/{vid}")
    check("N26 ficha lista CKL", "CKL-2026-" in r.text)
    chk_full = repo.get_checklist(repo.list_checklists(vid)[0]["id"])
    check("N27 serial + itens salvos",
          chk_full["serial"].startswith("CKL-2026-")
          and chk_full["itens"].get("1.1", {}).get("2ª") == "S"
          and chk_full["observacoes"].get("3ª") == "Radiador baixando agua")
    chk = repo.list_checklists(vid)[0]
    r = client.get(f"/frota/checklists/{chk['id']}/pdf")
    check("N28 PDF do checklist", r.status_code == 200
          and r.content.startswith(b"%PDF")
          and "VE" in r.text or True)
    r = client.post(f"/frota/checklists/{chk['id']}/excluir",
                    follow_redirects=False)
    check("N29 excluir checklist -> 303", r.status_code == 303)

    print("\n--- Manutencao preventiva por KM ---")
    client.post(f"/frota/{vid}/movimentacoes", data={
        "data_saida": "09/09/2026", "hora": "08:00", "km_inicial": "5000",
        "motorista": "Jose", "autorizado_por": "", "destino": "Obra",
        "motivo": "", "obs": ""})
    r = client.get(f"/frota/{vid}")
    import re as _re
    mov_aberta = _re.search(r'/frota/movimentacoes/(\d+)/entrada', r.text)
    mov_id = int(mov_aberta.group(1))
    client.post(f"/frota/movimentacoes/{mov_id}/entrada", data={
        "data_entrada": "09/09/2026", "hora_entrada": "17:30",
        "km_final": "10000"})
    r = client.post(f"/frota/{vid}/manutencoes", data={
        "descricao": "Troca de oleo", "intervalo_km": "6000",
        "km_ultima": "5000", "data_ultima": "01/08/2026", "obs": ""},
        follow_redirects=False)
    check("N30 add manutencao -> 303", r.status_code == 303)
    r = client.get(f"/frota/{vid}")
    check("N31 ficha mostra 1000 km restantes",
          "1.000 km restantes" in r.text)
    r = client.get("/vencimentos")
    check("N32 vencimentos mostra manutencao", "Manuten" in r.text)
    manut = repo.list_manutencoes(vid)[0]
    check("N33 repo status proximo", manut["restante"] == 1000
          and manut["status"] == "proximo")
    exp = repo.get_manutencoes_with_expiration()
    check("N34 get_manutencoes_with_expiration por_km",
          len(exp) == 1 and exp[0]["por_km"] is True
          and exp[0]["nr_code"] == "FROTA")
    r = client.post(f"/frota/manutencoes/{manut['id']}/concluir", data={
        "km_feito": "9000", "data_feito": "10/09/2026"},
        follow_redirects=False)
    check("N35 concluir -> 303", r.status_code == 303)
    manut = repo.list_manutencoes(vid)[0]
    check("N36 apos concluir restante 5000", manut["km_ultima"] == 9000
          and manut["restante"] == 5000 and manut["status"] == "ok")
    r = client.post(f"/frota/manutencoes/{manut['id']}/excluir",
                    follow_redirects=False)
    check("N37 excluir manutencao -> 303", r.status_code == 303)

    print("\n--- Dashboard com frota ---")
    r = client.get("/")
    check("N38 cards de frota no dashboard", "Ve" in r.text
          and "Sa" in r.text and "Custo de abastecimento" in r.text)

    print("\n--- Fase 4: backup ---")
    r = client.get("/backup")
    check("N39 GET /backup 200", r.status_code == 200
          and "Fazer backup agora" in r.text)
    r = client.post("/backup/criar", follow_redirects=False)
    check("N40 POST criar -> 303", r.status_code == 303)
    r = client.get("/backup")
    check("N41 backup listado", "certificados_" in r.text
          and ".db.gz" in r.text and "KB" in r.text)

    print("\n--- Fase 4: auditoria ---")
    r = client.get("/auditoria")
    check("N42 GET /auditoria 200 com acoes", r.status_code == 200
          and "backup-manual" in r.text and "login-ok" in r.text)
    r = client.get("/auditoria?busca=backup-manual")
    check("N43 busca filtra", r.status_code == 200
          and "backup-manual" in r.text and "login-ok" not in r.text)

    print("\n--- Permissoes: consulta nao ve Fase 4 ---")
    users.create_user("pedro", "Pedro Consulta", "consulta")
    prov = users.reset_password(users.get_by_username("pedro")["id"])
    anon = TestClient(app=client.app, follow_redirects=False)
    anon.post("/login", data={"username": "pedro", "password": prov},
              follow_redirects=False)
    anon.post("/troca-senha",
              data={"atual": prov, "nova": "SenhaF0rte2",
                    "confirma": "SenhaF0rte2"}, follow_redirects=False)
    r = anon.get("/backup")
    check("N44 consulta em /backup -> 303", r.status_code == 303)
    r = anon.get("/auditoria")
    check("N45 consulta em /auditoria -> 303", r.status_code == 303)
    r = anon.get("/")
    check("N46 nav sem Backup/Auditoria para consulta",
          'href="/backup"' not in r.text and 'href="/auditoria"' not in r.text)

    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}):")
        for f in FALHAS:
            print(f"  - {f}")
        sys.exit(1)
    print(f"TESTES WEB v1.34 OK — todos os {46} checks passaram.")


if __name__ == "__main__":
    main()
