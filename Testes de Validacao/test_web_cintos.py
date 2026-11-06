# -*- coding: utf-8 -*-
# Testes do modulo Controle de Cintos e Talabartes (v1.83.0 / ajustes v1.84.0)
import sys
import tempfile
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

import src.utils.paths as paths_mod
import src.core.cinto_repo as cr_mod
import src.web.app as app_mod

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="test_web_cintos_"))
    paths_mod.get_data_dir = lambda: tmp
    cr_mod.get_db_path = lambda: tmp / "certificados.db"
    app_mod.get_data_dir = lambda: tmp
    return tmp


def _login_admin(client):
    from src.web.users_repo import UsersRepository
    users = UsersRepository()
    prov = users.reset_password(users.get_by_username("admin")["id"])
    client.post("/login", data={"username": "admin", "password": prov},
                follow_redirects=False)
    client.post("/troca-senha", data={"atual": prov, "nova": "SenhaF0rte",
                                      "confirma": "SenhaF0rte"},
                follow_redirects=False)


def _prox_inicial():
    """Proxima inspecao esperada para item novo: hoje + 3 meses (dd/mm/aaaa)."""
    d = cr_mod._add_months(date.today(), 3)
    return d.strftime("%d/%m/%Y")


def main():
    tmp = make_env()
    from src.web.app import create_app
    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    client = TestClient(app)
    _login_admin(client)

    # CT01: listagem + item no menu
    r = client.get("/cintos")
    check("CT01 GET /cintos 200 com 'Cintos e Talabartes'",
          r.status_code == 200 and "Cintos e Talabartes" in r.text)

    # CT02: formulario novo tem tipo (cinto/talabarte), nome e antichama sim/nao
    r = client.get("/cintos/novo")
    ok2 = (r.status_code == 200 and "/cintos/salvar" in r.text
           and 'name="tipo"' in r.text and 'value="talabarte"' in r.text
           and 'name="nome"' in r.text and 'value="sim"' in r.text
           and 'mm/aaaa' in r.text)
    check("CT02 form novo: tipo + nome + antichama SIM/NAO + mm/aaaa", ok2)

    # CT03: salvar talabarte SEM CA (CA nao e obrigatorio p/ talabarte)
    r = client.post("/cintos/salvar", data={
        "id": "0", "tipo": "talabarte", "nome": "Talabarte Alpha T1",
        "marca": "MarcaX", "modelo": "T1", "ca": "", "lote": "L1",
        "numero_serie": "SERIE-001", "data_fabricacao": "01/2024",
        "validade_meses": "60", "antichama": "sim", "observacoes": "",
    }, follow_redirects=False)
    ok3 = r.status_code == 303 and r.headers.get("location", "").endswith("/cintos/1")
    check("CT03 POST salvar talabarte sem CA -> 303 ficha", ok3)
    loc = r.headers.get("location", "/cintos/1")

    # CT04: ficha com codigo TALAB-0001, validade 01/01/2029, antichama e
    # inspecao inicial automatica (hoje + 3 meses)
    r = client.get(loc)
    check("CT04 ficha: TALAB-0001 + validade + antichama + inspecao inicial",
          r.status_code == 200 and "TALAB-0001" in r.text
          and "01/01/2029" in r.text and "Antichama" in r.text
          and _prox_inicial() in r.text and "sistema" in r.text)

    # CT05: cinto SEM CA rejeitado
    r = client.post("/cintos/salvar", data={
        "id": "0", "tipo": "cinto", "nome": "Cinto Sem CA", "marca": "Y",
        "modelo": "C1", "ca": "", "lote": "L2", "numero_serie": "S2",
        "data_fabricacao": "05/2024", "validade_meses": "60",
    }, follow_redirects=False)
    check("CT05 cinto sem CA rejeitado -> 303 /cintos/novo",
          r.status_code == 303 and r.headers.get("location", "").startswith("/cintos/novo")
          and "nome=Cinto+Sem+CA" in r.headers.get("location", ""))  # v1.84.1: repõe digitado via qs

    # CT06: cinto com CA aceito -> codigo CINTO-0001
    r = client.post("/cintos/salvar", data={
        "id": "0", "tipo": "cinto", "nome": "Cinto Paraquedas C1",
        "marca": "Y", "modelo": "C1", "ca": "359261", "lote": "L2",
        "numero_serie": "SERIE-002", "data_fabricacao": "05/2024",
        "validade_meses": "60", "antichama": "nao",
    }, follow_redirects=False)
    ok6 = r.status_code == 303 and r.headers.get("location", "").endswith("/cintos/2")
    r = client.get("/cintos/2")
    check("CT06 cinto com CA -> CINTO-0001 na ficha",
          ok6 and "CINTO-0001" in r.text)

    # CT07: serie duplicada rejeitada
    r = client.post("/cintos/salvar", data={
        "id": "0", "tipo": "cinto", "nome": "Dup", "marca": "Y", "modelo": "C1",
        "ca": "1", "lote": "L2", "numero_serie": "SERIE-001",
        "data_fabricacao": "05/2024", "validade_meses": "60",
    }, follow_redirects=False)
    check("CT07 serie duplicada -> 303 /cintos/novo",
          r.status_code == 303 and r.headers.get("location", "").startswith("/cintos/novo")
          and "numero_serie=SERIE-001" in r.headers.get("location", ""))

    # CT08: inspecao interna -> proxima = data + 3 meses
    r = client.post("/cintos/1/inspecao", data={
        "tipo": "interno", "data_inspecao": "20/10/2026", "texto": "OK geral",
    }, follow_redirects=False)
    check("CT08 POST inspecao -> 303", r.status_code == 303)
    r = client.get("/cintos/1")
    # v1.84.0: 'confirmo que o equipamento' tambem aparece no popup de saida,
    # entao basta checar a proxima inspecao (20/01/2027) na ficha
    check("CT09 proxima inspecao 20/01/2027 na ficha",
          "20/01/2027" in r.text)

    # CT10: filtro por tipo na listagem
    r = client.get("/cintos?tipo=talabarte")
    ok10 = "Talabarte Alpha T1" in r.text and "Cinto Paraquedas C1" not in r.text
    r = client.get("/cintos?tipo=cinto")
    ok10 = ok10 and ("Cinto Paraquedas C1" in r.text
                     and "Talabarte Alpha T1" not in r.text)
    check("CT10 filtro tipo cinto/talabarte", ok10)

    # CT11: saida SEM confirmacao de inspecao -> bloqueada
    r = client.post("/cintos/1/saida", data={
        "data": "28/10/2026", "destino": "Ternium - Rio Negro",
        "testado": "", "observacoes": "",
    }, follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT11 saida sem testado -> bloqueada com aviso",
          r.status_code == 303 and "apto para uso" in r2.text
          and "Registrar saída" in r2.text)

    # CT12: saida com teste/apto -> confirmacao registrada + localizacao
    r = client.post("/cintos/1/saida", data={
        "data": "28/10/2026", "destino": "Ternium - Rio Negro",
        "testado": "1", "observacoes": "",
    }, follow_redirects=False)
    check("CT12 POST saida -> 303", r.status_code == 303)
    r = client.get("/cintos/1")
    check("CT13 confirmacao de inspecao na saida + destino",
          "confirmo que o equipamento foi inspecionado" in r.text
          and "Ternium - Rio Negro" in r.text and "Registrar entrada" in r.text)

    # CT14: item com saida em aberto NAO pode ser descartado
    r = client.post("/cintos/1/arquivar", data={
        "acao": "arquivar", "motivo": "Desgaste real"},
        follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT14 descarte com saida aberta bloqueado",
          r.status_code == 303 and "saída em aberto" in r2.text)

    # CT15: saida dupla bloqueada
    r = client.post("/cintos/1/saida", data={
        "data": "28/10/2026", "destino": "Outro", "testado": "1",
        "observacoes": "",
    }, follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT15 saida dupla bloqueada com aviso",
          r.status_code == 303 and r.headers.get("location", "").endswith("/cintos/1")
          and "Registrar entrada" in r2.text)

    # CT16: entrada fecha a movimentacao, volta ao estoque
    r = client.post("/cintos/1/entrada", data={
        "data": "28/10/2026", "testado": "1", "resultado": "apto",
        "observacoes": "volta",
    }, follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT16 entrada registrada e localizacao Estoque",
          r.status_code == 303 and "Estoque" in r2.text)

    # --- v1.84.1: novos guardas e UX ---
    # CT16a: fabricacao no futuro rejeitada e formulario repoe o digitado
    r = client.post("/cintos/salvar", data={
        "id": "0", "tipo": "talabarte", "nome": "Talabarte Futuro",
        "marca": "ZF", "modelo": "TF1", "ca": "", "lote": "L9",
        "numero_serie": "SERIE-FUT", "data_fabricacao": "01/2099",
        "validade_meses": "60", "antichama": "nao",
    }, follow_redirects=False)
    loc = r.headers.get("location", "")
    r2 = client.get(loc)
    check("CT16a fabricacao futura rejeitada + repoe digitado",
          r.status_code == 303 and loc.startswith("/cintos/novo?")
          and "Talabarte+Futuro" in loc
          and "Talabarte Futuro" in r2.text and 'value="talabarte" selected' in r2.text)

    # CT16b: inspecao com data futura rejeitada
    r = client.post("/cintos/1/inspecao", data={
        "tipo": "interno", "data_inspecao": "01/01/2099", "texto": "x",
    }, follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT16b inspecao futura rejeitada",
          r.status_code == 303 and "não pode ser no futuro" in r2.text)

    # CT16c: saida com data futura rejeitada
    r = client.post("/cintos/1/saida", data={
        "data": "01/01/2099", "destino": "X", "testado": "1",
        "voltar": "lista",
    }, follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos"))
    check("CT16c saida futura rejeitada",
          r.status_code == 303 and "não pode ser no futuro" in r2.text)

    # CT16d: saida valida, depois inspecao fora do estoque bloqueada,
    # entrada futura/anterior rejeitada, entrada danificada ok
    r = client.post("/cintos/1/saida", data={
        "data": "27/10/2026", "destino": "Ternium - Rio Negro", "testado": "1",
        "voltar": "lista",
    }, follow_redirects=False)
    check("CT16d-1 saida ok (lista)", r.status_code == 303)
    r = client.post("/cintos/1/inspecao", data={
        "tipo": "interno", "data_inspecao": "27/10/2026", "texto": "fora",
    }, follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT16d-2 inspecao fora do estoque bloqueada",
          r.status_code == 303 and "no estoque" in r2.text)
    r = client.post("/cintos/1/entrada", data={
        "data": "01/01/2099", "testado": "1", "resultado": "apto",
    }, follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT16d-3 entrada futura rejeitada",
          r.status_code == 303 and "não pode ser no futuro" in r2.text)
    r = client.post("/cintos/1/entrada", data={
        "data": "20/10/2026", "testado": "1", "resultado": "apto",
    }, follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT16d-4 entrada anterior a saida rejeitada",
          r.status_code == 303 and "anterior" in r2.text)
    r = client.post("/cintos/1/entrada", data={
        "data": "28/10/2026", "testado": "1", "resultado": "danificado",
        "observacoes": "trava empenada",
    }, follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT16d-5 entrada danificada com aviso",
          r.status_code == 303 and "ATENÇÃO" in r2.text
          and "DANIFICADO" in r2.text)

    # CT17: busca por serie/nome; atalhos de saida/retorno na tabela
    r = client.get("/cintos?busca=SERIE-001")
    check("CT17a busca por serie", "Talabarte Alpha T1" in r.text)
    r = client.get("/cintos?busca=Alpha")
    check("CT17b busca por nome", "Talabarte Alpha T1" in r.text)
    r = client.get("/cintos")
    check("CT17c atalho de saida na tabela (popup grande)",
          "abrirDlgL('dlg-saida-l'" in r.text and "form-saidal" in r.text)

    # CT18: arquivar exige motivo
    r = client.post("/cintos/1/arquivar", data={"acao": "arquivar", "motivo": ""},
                    follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT18 arquivar sem motivo -> erro", r.status_code == 303
          and "Informe o motivo" in r2.text)

    # CT19: arquivar com motivo -> Descartado e fora da lista padrao
    r = client.post("/cintos/1/arquivar", data={
        "acao": "arquivar", "motivo": "Desgaste real"},
        follow_redirects=False)
    r2 = client.get(r.headers.get("location", "/cintos/1"))
    check("CT19 arquivado -> Descartado com motivo",
          "Descartado" in r2.text and "Desgaste real" in r2.text)
    r3 = client.get("/cintos")
    check("CT20a descartado some da listagem padrao",
          "Talabarte Alpha T1" not in r3.text)
    r4 = client.get("/cintos?arquivado=sim")
    check("CT20b descartado aparece em arquivado=sim",
          "Talabarte Alpha T1" in r4.text)

    # CT21: reativar
    r = client.post("/cintos/1/arquivar", data={"acao": "reativar", "motivo": ""},
                    follow_redirects=False)
    r2 = client.get("/cintos/1")
    check("CT21 reativar volta a lista ativa",
          "Descartado" not in r2.text)

    # CT22: editar item (form tem nome/tipo; salvar atualiza)
    r = client.get("/cintos/1/editar")
    ok22 = (r.status_code == 200 and 'name="modelo"' in r.text
            and 'name="nome"' in r.text and 'name="tipo"' in r.text)
    r = client.post("/cintos/salvar", data={
        "id": "1", "tipo": "talabarte", "nome": "Talabarte Alpha T1 EDITADO",
        "marca": "MarcaX", "modelo": "T1 EDITADO", "ca": "", "lote": "L1",
        "numero_serie": "SERIE-001", "data_fabricacao": "01/2024",
        "validade_meses": "60", "antichama": "sim",
    }, follow_redirects=False)
    r2 = client.get("/cintos/1")
    check("CT22 editar salva", ok22 and "T1 EDITADO" in r2.text
          and "TALAB-0001" in r2.text)

    # CT23: download de inspecao inexistente nao quebra
    r = client.get("/cintos/inspecao/999/download", follow_redirects=False)
    check("CT23 download inexistente tratado",
          r.status_code in (303, 404))

    print("\n" + "=" * 56)
    if FALHAS:
        print(f"FALHOU: {len(FALHAS)}")
        for f in FALHAS:
            print("  -", f)
    else:
        print("CINTOS: TODOS OS TESTES PASSARAM")
    print("=" * 56)
    sys.exit(1 if FALHAS else 0)


if __name__ == "__main__":
    main()
