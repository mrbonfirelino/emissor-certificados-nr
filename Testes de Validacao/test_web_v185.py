# -*- coding: utf-8 -*-
"""v1.85.0: anexos ao descartar (cintos), statcards de inspecoes no
dashboard e custos da frota por mes especifico (PDF/Excel)."""
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

import src.utils.paths as paths_mod
import src.core.cinto_repo as cr_mod
import src.core.frota_repo as fr_mod
import src.core.employee_repo as er_mod
import src.core.history_repo as hr_mod
import src.core.aso_repo as aso_mod
import src.core.integracao_repo as integ_mod
import src.web.app as app_mod

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="test_web_v185_"))
    paths_mod.get_data_dir = lambda: tmp
    for m in (er_mod, hr_mod, aso_mod, integ_mod, cr_mod, fr_mod):
        m.get_db_path = lambda: tmp / "certificados.db"
    app_mod.get_data_dir = lambda: tmp
    return tmp


def _login_admin(client):
    from src.web.users_repo import UsersRepository
    users = UsersRepository()
    uid = users.get_by_username("admin")["id"]
    prov = users.reset_password(uid)
    client.post("/login", data={"username": "admin", "password": prov},
                follow_redirects=False)
    client.post("/troca-senha", data={"atual": prov, "nova": "SenhaF0rte",
                                      "confirma": "SenhaF0rte"},
                follow_redirects=False)


def _criar_item(client, tipo="cinto", nome="Item V185", serie=""):
    serie = serie or f"V185-{nome[-4:]}"
    fab = "03/2023"
    r = client.post("/cintos/salvar", data={
        "id": "0", "tipo": tipo, "nome": nome, "marca": "MarcaX",
        "modelo": "ModX", "ca": "123" if tipo == "cinto" else "",
        "lote": "L1", "numero_serie": serie, "data_fabricacao": fab,
        "validade_meses": "60", "antichama": "nao", "observacoes": "",
    }, follow_redirects=False)
    assert r.status_code == 303, r.status_code
    import re
    m = re.search(r"/cintos/(\d+)", r.headers.get("location", ""))
    return int(m.group(1)) if m else None


def main():
    tmp = make_env()
    from src.web.app import create_app
    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    client = TestClient(app)
    _login_admin(client)

    # ---------- parte 1: anexos ao descartar ----------
    print("== Cintos: anexos ao descartar ==")
    iid = _criar_item(client, nome="ABCD")
    check("V185-01 item criado", bool(iid))
    fake_pdf = b"%PDF-1.4 fake" + b"x" * 200
    r = client.post(f"/cintos/{iid}/arquivar",
                    data={"motivo": "Desgaste real", "acao": "arquivar"},
                    files=[("anexos", ("foto_descarte.jpg", fake_pdf, "image/jpeg"))],
                    follow_redirects=False)
    check("V185-02 arquivar com anexo -> 303", r.status_code == 303)
    r2 = client.get(f"/cintos/{iid}")
    check("V185-03 ficha mostra 'Anexos do descarte'",
          "Anexos do descarte" in r2.text and "foto_descarte.jpg" in r2.text)
    check("V185-04 ficha Descartado", "Descartado" in r2.text)
    # download do anexo
    from src.core.cinto_repo import CintoRepository
    repo = CintoRepository()
    anexos = repo.list_descarte_anexos(iid)
    check("V185-05 anexo salvo no banco", len(anexos) == 1)
    if anexos:
        r3 = client.get(f"/cintos/descarte/{anexos[0]['id']}/download")
        check("V185-06 download do anexo OK",
              r3.status_code == 200 and fake_pdf in r3.content)
    else:
        check("V185-06 download do anexo OK", False)
    # formato invalido
    iid2 = _criar_item(client, nome="WXYZ")
    r = client.post(f"/cintos/{iid2}/arquivar",
                    data={"motivo": "descarte", "acao": "arquivar"},
                    files=[("anexos", ("ruim.exe", b"MZ...", "application/x-msdownload"))],
                    follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos"))
    check("V185-07 formato invalido rejeitado",
          r.status_code == 303 and "não permitido" in r2.text)
    # reativar limpa? (anexo permanece no banco — apenas nao listado enquanto ativo)
    client.post(f"/cintos/{iid2}/arquivar", data={"motivo": "", "acao": "reativar"},
                follow_redirects=False)
    r2 = client.get(f"/cintos/{iid2}")
    check("V185-08 reativado sem secao de anexos",
          "Anexos do descarte" not in r2.text)

    # ---------- parte 2: statcards dashboard ----------
    print("== Dashboard: statcards de inspeções (cintos) ==")
    r = client.get("/")
    check("V185-09 dashboard lista card proximas",
          "Inspeções de cintos próximas (30 dias)" in r.text)
    check("V185-10 dashboard lista card atrasadas",
          "Inspeções de cintos atrasadas" in r.text)
    check("V185-11 cards linkam /cintos", 'href="/cintos"' in r.text)
    cr = CintoRepository()
    cc = cr.counts_situacao()
    check("V185-12 counts_situacao tem chaves",
          all(k in cc for k in ("insp_vencidas", "insp_proximas")))
    # um item ATIVO com inspecao cuja proxima caia nos proximos 30 dias
    from datetime import date, timedelta
    cr.add_inspecao(cinto_id=iid2, data_inspecao=date.today().strftime("%d/%m/%Y"),
                    proxima_inspecao=(date.today() + timedelta(days=10)).strftime("%d/%m/%Y"),
                    tipo="interno", texto="reinspecao programada")
    cc2 = cr.counts_situacao()
    check("V185-13 inspecao em ate 30 dias conta como proxima",
          cc2["insp_proximas"] >= 1)

    # ---------- parte 3: custos da frota por mes ----------
    print("== Frota: custos por mês específico ==")
    # cria veiculo + abastecimento no mes passado
    r = client.post("/frota/criar", data={
        "modelo": "Strada V185", "marca": "Fiat", "tipo": "pickup",
        "placa": "AAA1A23", "proprio": "1", "contratante": "",
        "empresa_id": "", "obs": ""}, follow_redirects=False)
    check("V185-14 veiculo criado (303)",
          r.status_code == 303 and r.headers.get("location", "").startswith("/frota/"))
    import re as _re
    mv = _re.search(r"/frota/(\d+)", r.headers.get("location", ""))
    vid = int(mv.group(1)) if mv else 0
    check("V185-15 veiculo tem id", vid > 0)
    d_br = (date.today() - timedelta(days=20)).strftime("%d/%m/%Y")
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "fornecedor_id": "1",
        "combustivel": "diesel", "data": d_br,
        "viagem_servico": "Viagem V185", "km": "10050",
        "condutor": "Joao", "superior": "Chefe", "obs": ""},
        follow_redirects=False)
    check("V185-15b abastecimento criado (303)", r.status_code == 303)
    r = client.get("/frota/custos")
    check("V185-16 pagina custos 200", r.status_code == 200)
    mm = (date.today() - timedelta(days=20)).strftime("%m/%Y")
    r = client.get("/frota/custos", params={"mes": mm})
    check("V185-17 custos ?mes= 200", r.status_code == 200)
    check("V185-18 rotulo do mes na pagina", f"Mês {mm}" in r.text)
    r = client.get("/frota/custos", params={"mes": "13/2099"},
                   follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/frota/custos"))
    check("V185-19 mes invalido -> flash + redirect",
          r.status_code == 303 and "inválido" in r2.text)
    r = client.get("/frota/custos/pdf", params={"mes": mm})
    check("V185-20 PDF do mes 200 pdf",
          r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf"))
    check("V185-21 nome do PDF com mes",
          mm.replace("/", "-") in r.headers.get("content-disposition", ""))
    r = client.get("/frota/custos/exportar", params={"mes": mm})
    check("V185-22 Excel do mes 200 xlsx",
          r.status_code == 200
          and r.headers.get("content-type", "").startswith("application/vnd"))
    check("V185-23 nome do Excel com mes",
          mm.replace("/", "-") in r.headers.get("content-disposition", ""))
    # sem mes continua funcionando (periodo)
    r = client.get("/frota/custos/pdf")
    check("V185-24 PDF sem mes 200", r.status_code == 200)
    r = client.get("/frota/custos/exportar")
    check("V185-25 Excel sem mes 200", r.status_code == 200)
    # PDF por veiculo com mes
    r = client.get(f"/frota/{vid}/custos/pdf", params={"mes": mm})
    check("V185-26 PDF por veiculo com mes 200",
          r.status_code == 200
          and r.headers.get("content-type", "").startswith("application/pdf"))

    # ---------- v1.85.1: refinements ----------
    print("== Frota: refinamentos v1.85.1 ==")
    r = client.get("/frota/custos")
    check("V185-27 seletor month + Baixar Pacote na pagina",
          'type="month"' in r.text and "Baixar Pacote" in r.text
          and "lnk-zip" in r.text)
    # serie do mes especifico tem exatamente 1 ponto (bug do PDF mostrando
    # meses ate o mes atual)
    from datetime import date as _d
    _mes_n, _ano = (int(x) for x in mm.split("/"))  # mm = mm/aaaa
    _aa, _mm2 = _ano, _mes_n
    _de = f"{_aa:04d}-{_mm2:02d}-01"
    _ate = f"{_aa:04d}-{_mm2:02d}-28"
    fr = fr_mod.FrotaRepository()
    serie = fr.custo_serie_todos(meses=24, de=_de, ate=_ate)
    check("V185-28 serie do mes especifico tem 1 mes",
          len(serie) == 1 and serie[0]["mes"] == f"{_aa:04d}-{_mm2:02d}"
          and bool(serie[0]["por_veiculo"]))
    sv = fr.custo_serie_veiculo(vid, meses=24, de=_de, ate=_ate)
    check("V185-29 serie do veiculo no mes especifico tem 1 mes",
          len(sv) == 1 and sv[0]["mes"] == f"{_aa:04d}-{_mm2:02d}")
    # pacote ZIP
    import io
    import zipfile as _zip
    r = client.get("/frota/custos/pacote", params={"mes": mm})
    cd = r.headers.get("content-disposition", "")
    check("V185-30 pacote com mes 200 zip",
          r.status_code == 200
          and r.headers.get("content-type") == "application/zip"
          and mm.replace("/", "-") in cd)
    try:
        zf = _zip.ZipFile(io.BytesIO(r.content))
        nomes = zf.namelist()
        ok_zip = (len(nomes) == 2
                  and any(n.endswith(".pdf") for n in nomes)
                  and any(n.endswith(".xlsx") for n in nomes))
    except Exception:
        ok_zip = False
    check("V185-31 ZIP tem PDF + Excel", ok_zip)
    r = client.get("/frota/custos/pacote")
    check("V185-32 pacote sem mes 200 zip",
          r.status_code == 200
          and r.headers.get("content-type") == "application/zip")
    r = client.get("/frota/custos/pacote", params={"mes": "13/2099"},
                   follow_redirects=False)
    check("V185-33 pacote mes invalido -> flash redirect",
          r.status_code == 303)

    print()
    if FALHAS:
        print("V185 FALHAS:", FALHAS)
        sys.exit(1)
    print("V185: TODOS OS TESTES PASSARAM")
    sys.exit(0)


if __name__ == "__main__":
    main()
