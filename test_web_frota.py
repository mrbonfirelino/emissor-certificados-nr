"""Testes web do modulo Frota (v1.33.0 — ROADMAP 2.29.1-2.29.4).

Padrao standalone: roda direto `python test_web_frota.py`.
Patches de paths ANTES de create_app (mesmo padrao test_web_fase3c).
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
from src.core.frota_repo import FrotaRepository, CHECKLIST_GRUPOS
import src.core.certificate_service as cert_mod
import src.web.app as app_mod

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="test_web_frota_"))
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


def main():
    tmp = make_env()
    from src.web.app import create_app
    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository
    from src.web.users_repo import UsersRepository

    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    EmployeeRepository()
    HistoryRepository()
    client = TestClient(app)
    _login_admin(client)

    print("\n--- Frota: lista e criacao de veiculos ---")
    r = client.get("/frota")
    check("FR01 GET /frota 200 com titulo", r.status_code == 200
          and "Frota" in r.text and "Novo ve" in r.text)

    r = client.post("/frota/criar", data={
        "modelo": "2428", "marca": "Mercedes", "tipo": "caminhao",
        "subtipo": "", "placa": "ABC1A23", "proprio": "1",
        "contratante": "", "empresa_id": "", "obs": ""},
        follow_redirects=False)
    check("FR02 caminhao sem subtipo -> form com erro", r.status_code == 200
          and "subtipo" in r.text.lower())

    r = client.post("/frota/criar", data={
        "modelo": "2428", "marca": "Mercedes", "tipo": "caminhao",
        "subtipo": "munck", "placa": "", "proprio": "1",
        "contratante": "", "empresa_id": "", "obs": ""},
        follow_redirects=False)
    check("FR03 caminhao sem placa -> form com erro", r.status_code == 200
          and "placa" in r.text.lower())

    r = client.post("/frota/criar", data={
        "modelo": "Empilhadeira 3t", "marca": "Toyota",
        "tipo": "empilhadeira", "placa": "XYZ9999", "proprio": "1",
        "contratante": "", "empresa_id": "", "obs": ""},
        follow_redirects=False)
    check("FR04 empilhadeira com placa -> erro (sem placa)",
          r.status_code == 200 and "n" in r.text and "placa" in r.text)

    r = client.post("/frota/criar", data={
        "modelo": "Strada", "marca": "Fiat", "tipo": "pickup",
        "placa": "abc1d23", "proprio": "1", "contratante": "",
        "empresa_id": "", "obs": ""}, follow_redirects=False)
    check("FR05 pickup ok -> 303 ficha", r.status_code == 303
          and r.headers["location"].startswith("/frota/"))
    vid = int(r.headers["location"].split("/")[-1])

    r = client.get(f"/frota/{vid}")
    check("FR06 ficha com placa uppercase", r.status_code == 200
          and "ABC1D23" in r.text and "Strada" in r.text)

    r = client.get("/frota?busca=strada")
    check("FR07 busca acha veiculo", r.status_code == 200
          and "ABC1D23" in r.text)
    r = client.get("/frota?busca=zzz-inexistente")
    check("FR08 busca vazia mostra vazio", r.status_code == 200
          and "Nenhum ve" in r.text)

    print("\n--- Empresas e possse ---")
    r = client.post("/frota/criar", data={
        "modelo": "SPTO", "marca": "", "tipo": "caminhao",
        "subtipo": "plataforma", "placa": "EEE9E99", "proprio": "0",
        "contratante": "", "empresa_id": "", "obs": ""},
        follow_redirects=False)
    check("FR09 alugado sem contratante -> erro", r.status_code == 200
          and "contratou" in r.text.lower())

    r = client.post("/frota/empresas/criar",
                    data={"nome": "Locadora X",
                          "cnpj": "22.333.444/0001-55"},
                    follow_redirects=False)
    check("FR10 empresa criada -> 303", r.status_code == 303)
    r = client.get("/frota/empresas")
    check("FR11 empresas lista", r.status_code == 200
          and "Locadora X" in r.text)
    r = client.post("/frota/empresas/criar", data={"nome": "locadora x",
                    "cnpj": ""}, follow_redirects=False)
    check("FR12 duplicada -> 303 flash", r.status_code == 303)
    r = client.get("/frota/empresas")
    check("FR13 flash de duplicada exibido", "já está cadastrada" in r.text)

    r = client.post("/frota/criar", data={
        "modelo": "Hilux", "marca": "Toyota", "tipo": "pickup",
        "placa": "BBB2C34", "proprio": "0", "contratante": "Locadora X",
        "empresa_id": "1", "obs": ""}, follow_redirects=False)
    check("FR14 alugado com contratante ok -> 303", r.status_code == 303)
    vid_alug = int(r.headers["location"].split("/")[-1])
    r = client.get(f"/frota/{vid_alug}")
    check("FR15 ficha mostra alugada + empresa", "Locadora X" in r.text)

    print("\n--- Documentos (pasta virtual) ---")
    r = client.post(f"/frota/{vid}/docs",
                    files={"arquivo": ("manual.txt", b"manual do veiculo",
                                       "text/plain")},
                    follow_redirects=False)
    check("FR16 upload doc -> 303", r.status_code == 303)
    r = client.get(f"/frota/{vid}")
    check("FR17 ficha lista doc", "manual.txt" in r.text)
    r = client.get(f"/frota/{vid}/docs/1/download")
    check("FR18 download doc", r.status_code == 200
          and b"manual" in r.content)
    r = client.post(f"/frota/{vid}/docs",
                    files={"arquivo": ("virus.exe", b"MZ",
                                       "application/octet-stream")},
                    follow_redirects=False)
    check("FR19 extensao bloqueada -> flash erro", r.status_code == 303)
    r = client.get(f"/frota/{vid}")
    check("FR20 flash de bloqueio exibido", "bloqueado" in r.text)

    print("\n--- Laudos com vencimento ---")
    r = client.post(f"/frota/{vid}/laudos",
                    data={"tipo": "crlv", "descricao": "2026",
                          "emissao": "01/03/2026", "validade": "01/03/2027"},
                    files={"arquivo": ("crlv.pdf", b"%PDF-1.4 fake",
                                       "application/pdf")},
                    follow_redirects=False)
    check("FR21 laudo criado -> 303", r.status_code == 303)
    r = client.get(f"/frota/{vid}")
    check("FR22 ficha lista laudo", "crlv.pdf" in r.text
          and "01/03/2027" in r.text)
    r = client.post(f"/frota/{vid}/laudos",
                    data={"tipo": "fumaca_preta", "descricao": "antigo",
                          "emissao": "01/01/2025", "validade": "01/01/2026"},
                    files={"arquivo": ("fumaca.pdf", b"%PDF-1.4 fake",
                                       "application/pdf")},
                    follow_redirects=False)
    check("FR23 laudo vencido criado", r.status_code == 303)
    r = client.get(f"/frota/{vid}")
    check("FR24 badge vencido na ficha", "vencido" in r.text)

    print("\n--- Movimentacoes (saida/entrada) ---")
    r = client.post(f"/frota/{vid}/movimentacoes",
                    data={"data_saida": "10/03/2026", "hora": "07:30",
                          "km_inicial": "10000", "destino": "Obra Y",
                          "motivo": "Entrega", "obs": "",
                          "motorista": "João", "autorizado_por": "Chefe"},
                    follow_redirects=False)
    check("FR25 saida registrada -> 303", r.status_code == 303)
    r = client.get(f"/frota/{vid}")
    check("FR26 mov aberta na ficha", "aberta" in r.text)
    mid = r.text.split("/frota/movimentacoes/")[1].split("/entrada")[0]
    r = client.post(f"/frota/movimentacoes/{mid}/entrada",
                    data={"data_entrada": "10/03/2026",
                          "hora_entrada": "12:00", "km_final": "9000"},
                    follow_redirects=False)
    check("FR27 km final < inicial -> flash erro", r.status_code == 303)
    r = client.get(f"/frota/{vid}")
    check("FR28 mensagem de km exibida", "menor" in r.text)
    r = client.post(f"/frota/movimentacoes/{mid}/entrada",
                    data={"data_entrada": "10/03/2026",
                          "hora_entrada": "12:00", "km_final": "10120"},
                    follow_redirects=False)
    check("FR29 entrada ok -> 303", r.status_code == 303)
    r = client.get(f"/frota/{vid}")
    check("FR30 km rodado na ficha", "120" in r.text)

    print("\n--- Fornecedores e abastecimentos ---")
    r = client.post("/frota/fornecedores/criar",
                    data={"nome": "Posto Centro",
                          "cnpj": "33.444.555/0001-66",
                          "endereco": "Av Principal, 100"},
                    follow_redirects=False)
    check("FR31 fornecedor criado -> 303", r.status_code == 303)
    r = client.get("/frota/fornecedores")
    check("FR32 fornecedores lista", r.status_code == 200
          and "Posto Centro" in r.text)
    r = client.get("/frota/abastecimentos/novo")
    check("FR33 form abastecimento ok", r.status_code == 200
          and "Posto Centro" in r.text)
    r = client.post("/frota/abastecimentos/criar",
                    data={"veiculo_id": str(vid), "fornecedor_id": "1",
                          "combustivel": "diesel", "data": "12/03/2026",
                          "viagem_servico": "Viagem Obra Y", "km": "10050",
                          "condutor": "João", "superior": "Chefe",
                          "obs": "Tanque cheio"}, follow_redirects=False)
    check("FR34 abastecimento criado -> 303", r.status_code == 303)
    r = client.get("/frota/abastecimentos")
    check("FR35 serial AB-2026-00001 na lista", "AB-2026-00001" in r.text)
    r = client.get("/frota/abastecimentos/1/pdf")
    check("FR36 PDF serve com assinaturas no layout", r.status_code == 200
          and r.content[:5] == b"%PDF-")
    r = client.get("/frota/abastecimentos/1/pdf/download")
    check("FR37 PDF download attachment", r.status_code == 200
          and "attachment" in r.headers.get("content-disposition", ""))

    print("\n--- v1.42: combustivel por tipo, valores depois, tags, movs, assinado ---")
    # carro não aceita diesel/arlá
    r = client.post("/frota/criar", data={
        "modelo": "Onix", "marca": "Chevrolet", "tipo": "carro",
        "placa": "CAR2B34", "proprio": "1", "contratante": "",
        "empresa_id": "", "obs": ""}, follow_redirects=False)
    vid_carro = int(r.headers["location"].split("/")[-1])
    r = client.post("/frota/abastecimentos/criar",
                    data={"veiculo_id": str(vid_carro), "fornecedor_id": "1",
                          "combustivel": "diesel", "data": "13/03/2026",
                          "km": "5000", "condutor": "Ana", "superior": "Chefe",
                          "obs": ""}, follow_redirects=False)
    check("FR42 carro com diesel -> form com erro", r.status_code == 200
          and "diesel" in r.text.lower())
    r = client.post("/frota/abastecimentos/criar",
                    data={"veiculo_id": str(vid_carro), "fornecedor_id": "1",
                          "combustivel": "gasolina", "data": "13/03/2026",
                          "km": "5000", "condutor": "Ana", "superior": "Chefe",
                          "obs": "", "litros": "", "valor": ""},
                    follow_redirects=False)
    check("FR43 carro com gasolina sem litros/valor -> 303",
          r.status_code == 303)
    r = client.post("/frota/abastecimentos/2/valores",
                    data={"litros": "40,5", "valor": "289,90"},
                    follow_redirects=False)
    check("FR44 valores completados depois -> 303", r.status_code == 303)
    a2 = FrotaRepository().get_abastecimento(2)
    check("FR45 litros/valor gravados", a2["litros"] == 40.5
          and a2["valor"] == 289.9)

    # tags em documentos
    r = client.post(f"/frota/{vid}/docs",
                    data={"tag": "manutencao"},
                    files={"arquivo": ("nf_oficina.pdf", b"%PDF-tag",
                                       "application/pdf")},
                    follow_redirects=False)
    check("FR46 doc com tag -> 303", r.status_code == 303)
    r = client.get(f"/frota/{vid}")
    check("FR47 tag aparece na ficha", "Manutenção (Nota Fiscal)" in r.text)

    # conflito: segunda saída com mov aberta bloqueia
    r = client.post(f"/frota/{vid}/movimentacoes",
                    data={"data_saida": "14/03/2026", "hora": "08:00",
                          "km_inicial": "11000", "motorista": "João",
                          "autorizado_por": "", "destino": "Obra X",
                          "motivo": "", "obs": ""},
                    follow_redirects=False)
    check("FR48 primeira saida -> 303", r.status_code == 303)
    r = client.post(f"/frota/{vid}/movimentacoes",
                    data={"data_saida": "15/03/2026", "hora": "09:00",
                          "km_inicial": "11500", "motorista": "Maria",
                          "autorizado_por": "", "destino": "", "motivo": "",
                          "obs": ""}, follow_redirects=False)
    check("FR49 saida com mov aberta -> flash erro", r.status_code == 303
          and "saída aberta" in client.get(f"/frota/{vid}").text)

    # checklist assinado de volta
    r = client.post(f"/frota/{vid}/checklist",
                    data={"data_inicial": "02/03/2026",
                          "data_final": "08/03/2026", "km_rodado": "800",
                          "motorista": "João", "lider": "Chefe",
                          "pode_operar": "S", **{f"item_{g[0]}.{i}_2a": "S"
                                                 for g in CHECKLIST_GRUPOS
                                                 for i, _ in g[2]}},
                    follow_redirects=False)
    check("FR50 checklist criado -> 303", r.status_code == 303)
    repo_chk = FrotaRepository()
    chk_id = repo_chk.list_checklists(vid)[0]["id"]
    r = client.post(f"/frota/checklists/{chk_id}/assinado",
                    files={"arquivo": ("assinado.jpg", b"\xff\xd8jpgfake",
                                       "image/jpeg")},
                    follow_redirects=False)
    check("FR51 checklist assinado anexado -> 303", r.status_code == 303)
    r = client.get(f"/frota/checklists/{chk_id}/assinado/download")
    check("FR52 assinado download", r.status_code == 200
          and b"\xff\xd8jpgfake" in r.content)

    # ver por página
    r = client.get("/frota?per=10")
    check("FR53 frota per=10 ok", r.status_code == 200
          and 'value="10"' in r.text)

    # import/export de veiculos (2.29.7)
    r = client.get("/frota/exportar")
    check("FR54 exportar xlsx", r.status_code == 200
          and r.content[:2] == b"PK" and "veiculos.xlsx"
          in r.headers.get("content-disposition", ""))
    import io as _io
    import openpyxl as _opx
    wb2 = _opx.Workbook(); ws2 = wb2.active
    ws2.append(["Modelo", "Marca", "Tipo", "Subtipo", "Placa", "Proprio",
                "Contratante", "Empresa", "Cor", "Carroceria", "Ano",
                "Fim do contrato", "KM/L esperado", "Obs"])
    ws2.append(["Hilux", "Toyota", "Pickup", "", "IMP3H45", "Sim", "", "", "", "", "2024", "", "", ""])
    ws2.append(["", "Sem modelo", "Carro", "", "", "Sim", "", "", "", "", "", "", "", ""])
    buf2 = _io.BytesIO(); wb2.save(buf2); wb2.close()
    r = client.post("/frota/importar",
                    files={"arquivo": ("veiculos.xlsx", buf2.getvalue(),
                                       "application/vnd.openxmlformats-"
                                       "officedocument.spreadsheetml.sheet")},
                    follow_redirects=False)
    check("FR55 importar -> 303", r.status_code == 303)
    r = client.get("/frota")
    check("FR56 veiculo importado na lista", "Hilux" in r.text)
    check("FR57 erro por linha no flash", "Linha 3" in r.text)

    print("\n--- Integracao Vencimentos/Dashboard ---")
    r = client.get("/vencimentos")
    check("FR38 vencimentos lista FROTA", "FROTA" in r.text
          and "CRLV" in r.text)
    st = HistoryRepository().get_dashboard_stats()
    check("FR39 dashboard soma laudo vencido", st["vencidos"] >= 1)
    r = client.get("/")
    check("FR40 dashboard 200", r.status_code == 200)

    print("\n--- Permissoes (consulta le, nao escreve) ---")
    users = UsersRepository()
    users.create_user("pedro", "Pedro Consulta", "consulta")
    mp = users.get_by_username("pedro")
    mpv = users.reset_password(mp["id"])
    c2 = TestClient(app=app)
    c2.post("/login", data={"username": "pedro", "password": mpv},
            follow_redirects=False)
    c2.post("/troca-senha", data={"atual": mpv, "nova": "SenhaC0nsulta",
                                  "confirma": "SenhaC0nsulta"},
            follow_redirects=False)
    r = c2.get("/frota")
    check("FR41 consulta ve frota", r.status_code == 200)
    r = c2.post("/frota/criar", data={"modelo": "X", "tipo": "carro",
                "placa": "XYZ1A23", "proprio": "1"}, follow_redirects=False)
    check("FR42 consulta nao cria (303 bloqueio)", r.status_code == 303)
    r = c2.get("/frota/empresas")
    check("FR43 consulta sem form de empresa",
          "empresas/criar" not in r.text)
    r = c2.get("/frota")
    check("FR44 consulta sem botoes de escrita", "/frota/novo" not in r.text)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHAS: {FALHAS}")
        sys.exit(1)
    print(f"TODOS OS 61 CHECKS DE FROTA PASSARAM")


if __name__ == "__main__":
    main()
