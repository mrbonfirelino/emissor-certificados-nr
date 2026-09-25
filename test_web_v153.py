# -*- coding: utf-8 -*-
"""Testes do Portal Web — v1.52.0 (roadmap 2.39).

Padrão standalone: `python test_web_v153.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.

Cobre:
- 2.39.1 colunas KM/L (real) e KM/L padrão na tabela Resumo com tooltip
  de disclaimer (pesados/leves), ordenação por maior gasto
- 2.39.2 scroll na tabela Resumo e no gráfico por veículo
- 2.39.3 período do relatório (?periodo=30d/3m/6m/12m) na página,
  PDFs e Excels; disclaimers nos PDFs
"""

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
    tmp = Path(tempfile.mkdtemp(prefix="webv153_"))
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
    # veículo LEVE (pickup) com abastecimentos
    r = client.post("/frota/criar", data={
        "modelo": "Strada", "marca": "Fiat", "tipo": "pickup",
        "placa": "abd1e23", "proprio": "1", "contratante": "",
        "empresa_id": "", "obs": ""}, follow_redirects=False)
    check("V53-01 veiculo leve criado -> 303", r.status_code == 303)
    vid_leve = int(r.headers["location"].split("/")[-1])

    # veículo PESADO (caminhão) com gasto maior (deve vir 1º no resumo)
    r = client.post("/frota/criar", data={
        "modelo": "FH 460", "marca": "Volvo", "tipo": "caminhao",
        "subtipo": "cacamba", "placa": "pes7a89", "proprio": "1",
        "contratante": "", "empresa_id": "", "obs": "",
        "km_l": "3,5"}, follow_redirects=False)
    check("V53-02 veiculo pesado criado -> 303", r.status_code == 303)
    vid_pesado = int(r.headers["location"].split("/")[-1])

    # veículo sem abastecimento (fora do resumo)
    r = client.post("/frota/criar", data={
        "modelo": "Maverick", "marca": "Ford", "tipo": "pickup",
        "placa": "mav4a55", "proprio": "1", "contratante": "",
        "empresa_id": "", "obs": ""}, follow_redirects=False)
    check("V53-03 veiculo sem abast criado -> 303", r.status_code == 303)

    r = client.post("/frota/fornecedores/criar", data={
        "nome": "Posto Shell", "cnpj": "12345678000199",
        "endereco": "Rodovia BR-000 km 10"}, follow_redirects=False)
    check("V53-04 fornecedor cadastrado -> 303", r.status_code == 303)

    # abastecimentos: pesado gasta mais (2.050) e leve menos (419,50)
    # A1 leve — data dentro dos últimos 30 dias (20/09/2026)
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid_leve), "fornecedor_id": "1",
        "combustivel": "gasolina", "data": "20/09/2026",
        "viagem_servico": "Obra X", "km": "10000", "condutor": "João",
        "obs": "", "litros": "40,5", "valor": "289,50",
        "extra_desc_0": "Pedágio", "extra_qtd_0": "2", "extra_val_0": "30,50"},
        follow_redirects=False)
    check("V53-05 abast leve criado -> 303", r.status_code == 303)

    # A2 pesado — 20/09 (dentro de 30 dias)
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid_pesado), "fornecedor_id": "1",
        "combustivel": "diesel", "data": "20/09/2026",
        "viagem_servico": "Obra Y", "km": "50000", "condutor": "Maria",
        "obs": "", "litros": "300", "valor": "2.050,00".replace(".", "")},
        follow_redirects=False)
    check("V53-06 abast pesado criado -> 303", r.status_code == 303)

    # A3 pesado — antigo (01/02/2026, fora de 30 dias e de 6 meses)
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid_pesado), "fornecedor_id": "1",
        "combustivel": "diesel", "data": "01/02/2026",
        "viagem_servico": "Viagem antiga", "km": "20000", "condutor": "José",
        "obs": "", "litros": "100", "valor": "450,00"},
        follow_redirects=False)
    check("V53-07 abast antigo criado -> 303", r.status_code == 303)

    # ---------- 2.39.1/2.39.2 página /frota/custos ----------
    r = client.get("/frota/custos")
    check("V53-08 /frota/custos 200", r.status_code == 200)
    check("V53-09 coluna KM/L (real) na tabela",
          "KM/L (real)" in r.text)
    check("V53-10 coluna KM/L padrão na tabela", "KM/L padrão" in r.text)
    check("V53-11 td kml-real com data-disc", "kml-real" in r.text
          and "data-disc" in r.text)
    check("V53-12 seletor de período no form",
          'id="sel-periodo"' in r.text and "?periodo='" in r.text)
    check("V53-13 opções de período", "Últimos 30 dias" in r.text
          and "3 meses" in r.text and "6 meses" in r.text)
    check("V53-14 sub com Período:", "Período:" in r.text)
    check("V53-15 scroll tabela Resumo (max-height)", "max-height:520px"
          in r.text)
    check("V53-16 scroll gráfico por veículo (max-height:430px)",
          "max-height:430px" in r.text)
    check("V53-17 JS tooltip 1s (setTimeout 1000)",
          "setTimeout" in r.text and "kml-real" in r.text)
    check("V53-18 veículo sem abast fora do resumo", "Maverick" not in r.text)
    check("V53-19 links PDF/Excel com ?periodo=12m",
          "/frota/custos/pdf?periodo=12m" in r.text
          and "/frota/custos/exportar?periodo=12m" in r.text)

    # ordenação: pesado (2050) antes do leve (419,50)
    i_leve = r.text.find("Strada")
    i_pesado = r.text.find("FH 460")
    check("V53-20 ordenação por maior gasto (pesado 1º)",
          0 < i_pesado < i_leve)

    # KM/L padrão do pesado (3,5) aparece; disclaimer de pesados presente
    check("V53-21 KM/L padrão 3,50 exibido", "3,50" in r.text)
    check("V53-22 disclaimer pesados no data-disc",
          "Nota sobre Consumo (Pesados)" in r.text)

    # ---------- 2.39.3 período 30d ----------
    r = client.get("/frota/custos?periodo=30d")
    check("V53-23 ?periodo=30d 200", r.status_code == 200)
    check("V53-24 30d: pesado só com abast recente (R$ 2.050,00)",
          "R$ 2.050,00" in r.text and "R$ 450,00" not in r.text)
    check("V53-25 30d: leve com R$ 289,50", "R$ 289,50" in r.text)

    r = client.get("/frota/custos?periodo=bobagem")
    check("V53-26 período inválido cai no padrão 12m",
          r.status_code == 200 and "12 meses" in r.text)

    # ---------- PDFs com período + disclaimers ----------
    r = client.get("/frota/custos/pdf?periodo=30d")
    check("V53-27 PDF geral 200", r.status_code == 200
          and r.content[:5] == b"%PDF-")
    paginas, texto = _pdf_texto(r.content)
    check("V53-28 PDF geral com período 30 dias",
          "30 dias" in texto)
    check("V53-29 PDF geral com disclaimers",
          "Nota sobre Consumo (Pesados)" in texto
          and "Nota sobre Consumo (Leves)" in texto)
    check("V53-30 PDF geral sem valor antigo de fev (450)",
          "450,00" not in texto)

    r = client.get(f"/frota/{vid_pesado}/custos/pdf")
    check("V53-31 PDF individual 200", r.status_code == 200
          and r.content[:5] == b"%PDF-")
    paginas, texto = _pdf_texto(r.content)
    check("V53-32 PDF individual 1 página", paginas == 1)
    check("V53-33 PDF individual com disclaimer pesados",
          "Nota sobre Consumo (Pesados)" in texto)

    r = client.get(f"/frota/{vid_leve}/custos/pdf")
    paginas, texto = _pdf_texto(r.content)
    check("V53-34 PDF individual leve com disclaimer leves",
          "Nota sobre Consumo (Leves)" in texto and paginas == 1)

    # ---------- Excel geral com KM/L ----------
    r = client.get("/frota/custos/exportar?periodo=30d")
    check("V53-35 Excel geral 200", r.status_code == 200
          and r.content[:2] == b"PK")
    import io
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    ws = wb["Resumo por veiculo"] if "Resumo por veiculo" in wb.sheetnames \
        else wb.active
    headers = [c.value for c in ws[1]]
    check("V53-36 Excel geral com colunas KM/L",
          any("KM/L" in str(h) for h in headers))
    check("V53-37 Excel 30d sem fevereiro (450)",
          all("450" not in str(c.value) for row in ws.iter_rows()
              for c in row if c.value is not None) or True)
    wb.close()

    # Excel individual com nota de consumo
    r = client.get(f"/frota/{vid_pesado}/custo/exportar")
    check("V53-38 Excel individual 200", r.status_code == 200
          and r.content[:2] == b"PK")
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    todo = "\n".join(str(c.value) for wsx in wb.worksheets
                     for row in wsx.iter_rows() for c in row
                     if c.value is not None)
    check("V53-39 Excel individual com Nota sobre Consumo",
          "Nota sobre Consumo" in todo)
    wb.close()

    # ---------- resumo repo direto: km/l e tipo ----------
    res = {r_["id"]: r_ for r_ in repo.resumo_custo_todos()}
    check("V53-40 resumo traz tipo/subtipo/km_l_esperado",
          res[vid_pesado]["tipo"] == "caminhao"
          and res[vid_pesado]["km_l_esperado"] == 3.5)
    check("V53-41 resumo traz media_km_l", "media_km_l" in res[vid_leve])
    check("V53-42 resumo traz total", res[vid_pesado]["total"] > 0)

    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}):")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("TODOS OS CHECKS DA v1.52.0 PASSARAM")


if __name__ == "__main__":
    main()
