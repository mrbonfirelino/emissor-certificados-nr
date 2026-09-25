# -*- coding: utf-8 -*-
"""Testes do Portal Web — v1.53.0 (roadmap 2.40).

Padrão standalone: `python test_web_v154.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.

Cobre:
- 2.40.1 backfill de extras_total (JSON legado com total NULL entra nos
  custos) e normalização de datas não-ISO (registro aparecia fora dos
  relatórios)
- 2.40.2 marca d'água CANCELADO no PDF de solicitação bloqueada
  (servida/regenerada na hora) e PDF limpo após desbloquear
- 2.40.3 menu único "Opções" (⋯) na lista de abastecimentos
- 2.40.4 protótipo standalone com 2 cópias por folha A4
"""

import sqlite3
import subprocess
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
    tmp = Path(tempfile.mkdtemp(prefix="webv154_"))
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


def _pdf_texto(content: bytes):
    import fitz
    doc = fitz.open(stream=content, filetype="pdf")
    texto = "\n".join(p.get_text() for p in doc)
    return len(doc), texto


def main():
    client, tmp = make_env()
    _login_admin(client, tmp)

    db = tmp / "certificados.db"

    # ---------- 2.40.1 backfill (registro legado com JSON + total NULL) ----
    from src.core.frota_repo import FrotaRepository
    repo0 = FrotaRepository()
    vid = repo0.add_veiculo("Strada", "Fiat", "pickup", "", "ABD1E23",
                            1, None, None)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            "INSERT INTO frota_abastecimentos (serial, veiculo_id,"
            " fornecedor_id, combustivel, data, viagem_servico, km,"
            " condutor, obs, litros, valor, extras, extras_total)"
            " VALUES ('AB-2026-00001', ?, 1, 'gasolina', '05/09/2026',"
            " 'Obra X', 10000, 'João', '', 40.5, 289.5, ?, NULL)",
            (vid, '[{"desc": "Óleo 15W40", "qtd": "3", "valor": "37,00"}]'))
        rid = conn.execute("SELECT MAX(id) FROM frota_abastecimentos"
                           ).fetchone()[0]

    # nova instância roda o backfill do _migrar
    repo = FrotaRepository()
    row = dict(repo.get_abastecimento(rid))
    check("V54-01 backfill extras_total = 111,00",
          abs(float(row["extras_total"] or 0) - 111.0) < 0.01)
    check("V54-02 data não-ISO normalizada p/ ISO",
          row["data"] == "2026-09-05")

    serie = repo.custo_serie_veiculo(vid)
    setember = [s for s in serie if s["mes"] == "2026-09"]
    check("V54-03 legado entra na série mensal", len(setember) == 1)
    if setember:
        check("V54-04 série soma valor + extras (400,50)",
              abs(setember[0]["combustivel"] + setember[0]["extras"] - 400.5)
              < 0.01)
    resumo = repo.resumo_custo_todos()
    rvid = [r for r in resumo if r["id"] == vid][0]
    check("V54-05 resumo com desglose (comb 289,50 + extras 111,00)",
          abs(rvid["combustivel"] - 289.5) < 0.01
          and abs(rvid["extras"] - 111.0) < 0.01)
    check("V54-06 resumo total = 400,50", abs(rvid["total"] - 400.5) < 0.01)

    # ---------- 2.40.2 watermark CANCELADO ----------
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "fornecedor_id": "1", "combustivel": "diesel",
        "data": "20/09/2026", "viagem_servico": "Viagem", "km": "10400",
        "condutor": "Maria", "obs": "", "litros": "80", "valor": "450,00"},
        follow_redirects=False)
    check("V54-07 abast A2 criado -> 303", r.status_code == 303)

    r = client.get("/frota/abastecimentos/2/pdf")
    check("V54-08 PDF ativo servido", r.status_code == 200)
    _pag, txt = _pdf_texto(r.content)
    check("V54-09 PDF ativo SEM marca", "CANCELADO" not in txt)

    r = client.post("/frota/abastecimentos/2/bloquear",
                    data={"motivo": "Cancelado"}, follow_redirects=False)
    check("V54-10 bloquear -> 303", r.status_code == 303)

    r = client.get("/frota/abastecimentos/2/pdf")
    check("V54-11 PDF bloqueado servido", r.status_code == 200)
    _pag, txt = _pdf_texto(r.content)
    check("V54-12 PDF bloqueado COM marca CANCELADO", "CANCELADO" in txt)

    r = client.get("/frota/abastecimentos/2/pdf/download")
    check("V54-13 download PDF bloqueado 200", r.status_code == 200)
    _pag, txt = _pdf_texto(r.content)
    check("V54-14 download COM marca", "CANCELADO" in txt)

    r = client.post("/frota/abastecimentos/2/desbloquear",
                    follow_redirects=False)
    check("V54-15 desbloquear -> 303", r.status_code == 303)
    r = client.get("/frota/abastecimentos/2/pdf")
    _pag, txt = _pdf_texto(r.content)
    check("V54-16 PDF limpo após desbloquear", "CANCELADO" not in txt)

    # ---------- 2.40.3 menu Opções ----------
    r = client.get("/frota/abastecimentos")
    check("V54-17 página 200", r.status_code == 200)
    check("V54-18 coluna Opções no thead", "<th>Opções</th>" in r.text)
    check("V54-19 botão único Opções",
          "\u22ef Op\u00e7\u00f5es" in r.text)
    check("V54-20 um anexo-pop por linha (>= 2 na página)",
          r.text.count('details class="anexo-pop"') >= 2)
    check("V54-21 NF / valores dentro do menu",
          ">NF / valores</a>" in r.text)
    check("V54-22 Editar dentro do menu", ">Editar</a>" in r.text)
    check("V54-23 Ver PDF dentro do menu", ">Ver PDF</a>" in r.text)
    check("V54-24 Baixar PDF dentro do menu", ">Baixar PDF</a>" in r.text)
    check("V54-25 select de motivo no menu", 'name="motivo"' in r.text)

    # bloquear A2 e conferir menu de bloqueada (Desbloquear, sem Bloquear)
    r = client.post("/frota/abastecimentos/2/bloquear",
                    data={"motivo": "Cancelado"}, follow_redirects=False)
    check("V54-26 bloquear A2 -> 303", r.status_code == 303)
    r = client.get("/frota/abastecimentos")
    check("V54-27 Desbloquear no menu de bloqueada",
          ">Desbloquear</button>" in r.text)

    # ---------- 2.40.4 protótipo standalone ----------
    raiz = Path(__file__).resolve().parent
    r = subprocess.run([sys.executable, "prototipo_abastecimento_2vias.py"],
                       capture_output=True, text=True, cwd=str(raiz))
    check("V54-28 protótipo executou sem erro", r.returncode == 0)
    proto = raiz / "prototipo_abastecimento_2vias.pdf"
    check("V54-29 protótipo salvo na raiz", proto.exists())
    if proto.exists():
        import fitz
        doc = fitz.open(str(proto))
        t = "\n".join(p.get_text() for p in doc)
        check("V54-30 protótipo com 1 página", doc.page_count == 1)
        check("V54-31 protótipo com VIA 1", "VIA 1 DE 2" in t)
        check("V54-32 protótipo com VIA 2", "VIA 2 DE 2" in t)
        check("V54-33 protótipo com itens extras", "Óleo 15W40" in t)
        check("V54-34 protótipo com dados da solicitação",
              "AB-2026-00042" in t)
        doc.close()
    else:
        check("V54-30 protótipo com 1 página", False)
        check("V54-31 protótipo com VIA 1", False)
        check("V54-32 protótipo com VIA 2", False)
        check("V54-33 protótipo com itens extras", False)
        check("V54-34 protótipo com dados da solicitação", False)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHAS:")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("TODOS OS 34 CHECKS DA v1.53.0 PASSARAM.")


if __name__ == "__main__":
    main()
