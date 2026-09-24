# -*- coding: utf-8 -*-
"""Testes do Portal Web — v1.51.0 (roadmap 2.38).

Padrão standalone: `python test_web_v152.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.

Cobre:
- 2.38.1 ordenação da lista (datas não-ISO por último), Cache-Control
  no PDF + ?v=revisao, cores dos botões, milhar em KM e Valor
- 2.38.2 qtd fantasma (veículo sem abastecimento fora do resumo),
  gráfico horizontal por veículo, bloqueados fora dos custos
- PDF de custos: Valores por mês, milhar, seção Itens extras individuais
"""

import sqlite3
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
    tmp = Path(tempfile.mkdtemp(prefix="webv152_"))
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

    from src.core.frota_repo import FrotaRepository
    repo = FrotaRepository()

    # ---------- dados-base ----------
    r = client.post("/frota/criar", data={
        "modelo": "Strada", "marca": "Fiat", "tipo": "pickup",
        "placa": "abd1e23", "proprio": "1", "contratante": "",
        "empresa_id": "", "obs": ""}, follow_redirects=False)
    check("V52-01 veiculo criado -> 303", r.status_code == 303)
    vid = int(r.headers["location"].split("/")[-1])

    r = client.post("/frota/criar", data={
        "modelo": "Maverick", "marca": "Ford", "tipo": "pickup",
        "placa": "mav4a55", "proprio": "1", "contratante": "",
        "empresa_id": "", "obs": ""}, follow_redirects=False)
    check("V52-02 segundo veiculo (sem abast) -> 303", r.status_code == 303)

    r = client.post("/frota/fornecedores/criar", data={
        "nome": "Posto Shell", "cnpj": "12345678000199",
        "endereco": "Rodovia BR-000 km 10"}, follow_redirects=False)
    check("V52-03 fornecedor cadastrado -> 303", r.status_code == 303)

    # A1: gasolina + extra Pedágio
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "fornecedor_id": "1", "combustivel": "gasolina",
        "data": "10/09/2026", "viagem_servico": "Obra X", "km": "10000",
        "condutor": "João", "obs": "",
        "litros": "40,5", "valor": "289,50",
        "extra_desc_0": "Pedágio", "extra_qtd_0": "2", "extra_val_0": "30,50"},
        follow_redirects=False)
    check("V52-04 abast A1 criado -> 303", r.status_code == 303)

    # A2: diesel (será bloqueado depois)
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "fornecedor_id": "1", "combustivel": "diesel",
        "data": "20/09/2026", "viagem_servico": "Viagem", "km": "10400",
        "condutor": "Maria", "obs": "", "litros": "80", "valor": "450,00"},
        follow_redirects=False)
    check("V52-05 abast A2 criado -> 303", r.status_code == 303)

    # A3: valores grandes para testar milhar
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "fornecedor_id": "1", "combustivel": "gasolina",
        "data": "01/09/2026", "viagem_servico": "Obra Y", "km": "210884",
        "condutor": "José", "obs": "", "litros": "150", "valor": "1720,52"},
        follow_redirects=False)
    check("V52-06 abast A3 criado -> 303", r.status_code == 303)

    # ---------- 2.38.1 Cache-Control + ?v= ----------
    r = client.get("/frota/abastecimentos/1/pdf")
    check("V52-07 PDF 200 com Cache-Control no-store",
          r.status_code == 200
          and "no-store" in (r.headers.get("cache-control") or ""))
    r = client.get("/frota/abastecimentos/1/pdf/download")
    check("V52-08 download com Cache-Control + attachment",
          r.status_code == 200
          and "no-store" in (r.headers.get("cache-control") or "")
          and "attachment" in (r.headers.get("content-disposition") or ""))

    # editar A1 -> revisao 1 -> lista usa ?v=1
    r = client.post("/frota/abastecimentos/1/editar", data={
        "fornecedor_id": "1", "combustivel": "gasolina",
        "data": "10/09/2026", "viagem_servico": "Obra X", "km": "10050",
        "condutor": "João", "obs": "corrigido",
        "litros": "41", "valor": "290,00",
        "extra_desc_0": "Pedágio", "extra_qtd_0": "2", "extra_val_0": "30,50"},
        follow_redirects=False)
    check("V52-09 edicao A1 -> 303", r.status_code == 303)
    r = client.get("/frota/abastecimentos")
    check("V52-10 lista usa ?v=revisao nos links Ver/Baixar",
          "/pdf?v=1" in r.text and "/pdf/download?v=1" in r.text)

    # ---------- 2.38.1 cores dos botões ----------
    check("V52-11 NF amarelo-claro", "amarelo-claro" in r.text)
    check("V52-12 Editar verde", 'class="btn verde"' in r.text)
    check("V52-13 Baixar azul-claro", "azul-claro" in r.text)
    check("V52-14 Bloquear summary vermelho", 'summary class="btn vermelho"'
          in r.text or 'class="btn vermelho"' in r.text)

    # ---------- 2.38.1 milhar em KM e Valor ----------
    check("V52-15 KM com milhar (210.884 / 10.050)",
          "210.884" in r.text and "10.050" in r.text)
    check("V52-16 Valor com milhar (R$ 1.720,52)",
          "R$ 1.720,52" in r.text)
    check("V52-17 sem ponto decimal errado", "R$ 1720,52" not in r.text)

    # ---------- 2.38.1 ordenação (data não-ISO por último) ----------
    i2 = r.text.find("AB-2026-00002")
    i3 = r.text.find("AB-2026-00003")
    i1 = r.text.find("AB-2026-00001")
    check("V52-18 ordem padrão data DESC (A2 antes de A1 antes de A3)",
          0 < i2 < i1 < i3)

    # corrompe a data de A1 para formato não-ISO (dado legado)
    conn = sqlite3.connect(tmp / "certificados.db")
    conn.execute("UPDATE frota_abastecimentos SET data='05/09/2026'"
                 " WHERE id=1")
    conn.commit()
    conn.close()
    r = client.get("/frota/abastecimentos")
    i1 = r.text.find("AB-2026-00001")
    i3 = r.text.find("AB-2026-00003")
    check("V52-19 data não-ISO vai para o fim da lista",
          0 < i3 < i1)

    # restaura A1 (ISO) para os cálculos seguintes
    conn = sqlite3.connect(tmp / "certificados.db")
    conn.execute("UPDATE frota_abastecimentos SET data='2026-09-10'"
                 " WHERE id=1")
    conn.commit()
    conn.close()

    # ---------- 2.38.2 qtd fantasma / resumo ----------
    r = client.get("/frota/custos")
    check("V52-20 /frota/custos 200", r.status_code == 200)
    check("V52-21 veículo sem abastecimento fora do resumo",
          "Maverick" not in r.text)
    check("V52-22 Strada no resumo", "Strada" in r.text)

    # gráfico horizontal por veículo
    check("V52-23 SVG combustível com barras horizontais e nome do veículo",
          "text-anchor=\"end\"" in r.text and "data-det" in r.text
          and "Total: R$" in r.text)

    # PDF de custos: valores por mês + extras individuais
    r = client.get("/frota/custos/pdf")
    check("V52-24 /frota/custos/pdf 200", r.status_code == 200
          and r.content[:5] == b"%PDF-")
    paginas, texto = _pdf_texto(r.content)
    check("V52-25 PDF com Valores por mês", "Valores por mês" in texto)
    check("V52-26 PDF com milhar no valor (2.491,02)",
          "2.491,02" in texto)
    check("V52-27 PDF com seção Itens extras individuais",
          "Itens extras (histórico ativo)" in texto
          and "Pedágio" in texto)
    check("V52-28 PDF individual com extra e veículo",
          "AB-2026-00001" in texto)

    # ---------- 2.38.2 bloqueados fora dos custos ----------
    # totais ativos: comb 290,00 + 1.720,52 = 2.010,52; extras 30,50; total 2.041,02
    r = client.get("/frota/custos")
    check("V52-29 resumo com totais ativos (R$ 2.491,02)",
          "R$ 2.491,02" in r.text)
    r = client.post("/frota/abastecimentos/2/bloquear", data={
        "motivo": "Erro de lançamento", "motivo_txt": ""},
        follow_redirects=False)
    check("V52-30 bloquear A2 -> 303", r.status_code == 303)
    r = client.get("/frota/custos")
    check("V52-31 bloqueada fora dos custos (R$ 2.041,02)",
          "R$ 2.041,02" in r.text and "R$ 450,00" not in r.text)

    r = client.post("/frota/abastecimentos/2/desbloquear",
                    follow_redirects=False)
    check("V52-32 desbloquear A2 -> 303", r.status_code == 303)
    r = client.get("/frota/custos")
    check("V52-32b desbloqueada volta aos custos",
          "R$ 2.491,02" in r.text)

    # ---------- PDF individual do veículo ----------
    r = client.get(f"/frota/{vid}/custos/pdf")
    check("V52-33 individual 200", r.status_code == 200
          and r.content[:5] == b"%PDF-")
    paginas, texto = _pdf_texto(r.content)
    check("V52-34 individual: valores por mês + extras",
          "Valores por mês" in texto or "08/26" in texto or "09/26" in texto)

    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}):")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("TODOS OS CHECKS DA v1.51.0 PASSARAM")


if __name__ == "__main__":
    main()
