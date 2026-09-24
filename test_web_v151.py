# -*- coding: utf-8 -*-
"""Testes do Portal Web — v1.50.0 (roadmap 2.37).

Padrão standalone: `python test_web_v151.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.

Cobre:
- 2.37.1 PDF de abastecimento SEM valores (extras só Descrição+Qtde,
  sem TOTAL GERAL) e SEM marcas de revisão (REV fica só no sistema)
- 2.37.1 posto temporário (usar_tmp + nome + CNPJ) sem cadastro em
  fornecedores; aparece na lista e no PDF
- 2.37.2 página /frota/custos com 2 gráficos SVG e resumo
- 2.37.2 /frota/custos/pdf (todos, >= 2 páginas) e
  /frota/{id}/custos/pdf (individual, 1 página) via fitz
- 2.37.3 formatação com vírgula (dec/brl) na lista de abastecimentos
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
    tmp = Path(tempfile.mkdtemp(prefix="webv151_"))
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
    check("V51-01 veiculo criado -> 303", r.status_code == 303)
    vid = int(r.headers["location"].split("/")[-1])

    r = client.post("/frota/fornecedores/criar", data={
        "nome": "Posto Shell", "cnpj": "12345678000199",
        "endereco": "Rodovia BR-000 km 10"}, follow_redirects=False)
    check("V51-02 fornecedor cadastrado -> 303", r.status_code == 303)

    # abastecimento com extra (com valor) via fornecedor cadastrado
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "fornecedor_id": "1", "combustivel": "gasolina",
        "data": "05/09/2026", "viagem_servico": "Obra X", "km": "10000",
        "condutor": "João", "obs": "",
        "litros": "40,5", "valor": "289,50",
        "extra_desc_0": "Pedágio", "extra_qtd_0": "2", "extra_val_0": "30,50"},
        follow_redirects=False)
    check("V51-03 abastecimento criado -> 303", r.status_code == 303)

    # ---------- 2.37.1 PDF sem valores ----------
    r = client.get("/frota/abastecimentos/1/pdf")
    check("V51-04 PDF abastecimento 200", r.status_code == 200)
    paginas, texto = _pdf_texto(r.content)
    check("V51-05 PDF tem ITENS EXTRAS + Pedágio",
          "ITENS EXTRAS" in texto and "Pedágio" in texto)
    check("V51-06 PDF sem TOTAL GERAL (2.37.1)", "TOTAL GERAL" not in texto)
    check("V51-07 PDF sem valores R$ do extra", "30,50" not in texto
          and "R$" not in texto.split("Condutor")[0].split("ITENS")[0])

    # editar -> revisao interna 1, PDF continua sem REV
    r = client.post("/frota/abastecimentos/1/editar", data={
        "fornecedor_id": "1", "combustivel": "gasolina",
        "data": "06/09/2026", "viagem_servico": "Obra X", "km": "10100",
        "condutor": "João", "obs": "corrigido",
        "litros": "41", "valor": "290,00",
        "extra_desc_0": "Pedágio", "extra_qtd_0": "3", "extra_val_0": "31,00"},
        follow_redirects=False)
    check("V51-08 edicao -> 303", r.status_code == 303)
    ficha = repo.get_abastecimento(1)
    check("V51-09 revisao interna = 1 (só no sistema)",
          int(ficha.get("revisao") or 0) == 1)
    r = client.get("/frota/abastecimentos/1/pdf")
    paginas, texto = _pdf_texto(r.content)
    check("V51-10 PDF sem marcas REV (2.37.1)", "REV" not in texto)
    check("V51-11 PDF atualizado com obs corrigido", "corrigido" in texto)

    # ---------- 2.37.1 posto temporário ----------
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "usar_tmp": "1",
        "tmp_fornecedor": "Posto KM 220", "tmp_cnpj": "98765432000155",
        "combustivel": "diesel", "data": "20/09/2026",
        "viagem_servico": "Viagem interior", "km": "10400",
        "condutor": "Maria", "obs": "", "litros": "80", "valor": "450,00"},
        follow_redirects=False)
    check("V51-12 abastecimento posto temporario -> 303", r.status_code == 303)

    forn_nomes = [f["nome"] for f in repo.list_fornecedores()]
    check("V51-13 posto temporario NAO criado em fornecedores",
          "Posto KM 220" not in forn_nomes)

    r = client.get("/frota/abastecimentos")
    check("V51-14 lista mostra posto temporario", "Posto KM 220" in r.text)

    r = client.get("/frota/abastecimentos/2/pdf")
    paginas, texto = _pdf_texto(r.content)
    check("V51-15 PDF do abast com posto temporario", "Posto KM 220" in texto)

    # validacoes do posto temporario
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "usar_tmp": "1", "tmp_fornecedor": "",
        "tmp_cnpj": "", "combustivel": "diesel", "data": "21/09/2026",
        "km": "10500", "condutor": "Maria"}, follow_redirects=False)
    check("V51-16 tmp sem nome -> form com erro (200)",
          r.status_code == 200
          and "Informe o nome do posto temporário" in r.text)
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "usar_tmp": "1",
        "tmp_fornecedor": "Posto X", "tmp_cnpj": "123",
        "combustivel": "diesel", "data": "21/09/2026",
        "km": "10500", "condutor": "Maria"}, follow_redirects=False)
    check("V51-17 tmp cnpj invalido -> form com erro (200)",
          r.status_code == 200 and "Posto temporário:" in r.text)

    # form tem o checkbox e os campos
    r = client.get("/frota/abastecimentos/novo")
    check("V51-18 form com checkbox usar_tmp",
          'id="usar_tmp"' in r.text and 'name="tmp_fornecedor"' in r.text
          and 'name="tmp_cnpj"' in r.text)

    # ---------- 2.37.3 vírgula na lista ----------
    r = client.get("/frota/abastecimentos")
    check("V51-19 Litros com vírgula (41,00 / 80,00)",
          "41,00" in r.text and "80,00" in r.text)
    check("V51-20 Valor com vírgula (R$ 290,00 / R$ 450,00)",
          "R$ 290,00" in r.text and "R$ 450,00" in r.text)
    check("V51-21 sem ponto decimal no valor", "R$ 289.50" not in r.text
          and "R$ 450.00" not in r.text)

    # ---------- 2.37.2 página /frota/custos ----------
    r = client.get("/frota/custos")
    check("V51-22 /frota/custos 200", r.status_code == 200)
    check("V51-23 dois gráficos SVG (mês + combustível)",
          r.text.count("<svg") >= 2 and "graf-meses" in r.text
          and "graf-comb" in r.text)
    check("V51-24 SVG com tooltips g-mes/data-det",
          r.text.count('class="g-mes"') >= 2 and "data-det" in r.text)
    check("V51-25 resumo com Strada e desglose (R$ 740,00 + R$ 31,00)",
          "Strada" in r.text and "R$ 740,00" in r.text
          and "R$ 31,00" in r.text and "R$ 771,00" in r.text)
    check("V51-26 botões PNG + PDF + Excel",
          "data-png" in r.text and "/frota/custos/pdf" in r.text
          and "/frota/custos/exportar" in r.text)

    # ---------- 2.37.2 PDF de custos ----------
    r = client.get("/frota/custos/pdf")
    check("V51-27 /frota/custos/pdf 200 PDF", r.status_code == 200
          and r.content[:5] == b"%PDF-")
    paginas, texto = _pdf_texto(r.content)
    check("V51-28 todos: >=2 paginas e titulo",
          paginas >= 2 and "RELATÓRIO DE CUSTOS" in texto)

    r = client.get(f"/frota/{vid}/custos/pdf")
    check("V51-29 individual 200 PDF", r.status_code == 200
          and r.content[:5] == b"%PDF-")
    paginas, texto = _pdf_texto(r.content)
    check("V51-30 individual: 1 pagina com veiculo",
          paginas == 1 and "RELATÓRIO DE CUSTOS" in texto
          and "abd1e23" in texto.lower())

    r = client.get("/frota/99999/custos/pdf")
    check("V51-31 individual veiculo inexistente -> 404", r.status_code == 404)

    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}):")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("TODOS OS 31 CHECKS DA v1.50.0 PASSARAM")


if __name__ == "__main__":
    main()
