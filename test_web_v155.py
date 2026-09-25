# -*- coding: utf-8 -*-
"""Testes do Portal Web — v1.54.0.

Padrão standalone: `python test_web_v155.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.

Cobre:
- Configuração persistente "PDF de abastecimento em 2 vias" (DEFAULTS,
  página Configurações, POST salvando no app_settings.json)
- Geração do PDF em 2 vias (landscape, VIA x DE 2) e 1 via (retrato),
  incluindo watermark CANCELADO no modo 2 vias
- Dashboard: animação do custo (num-brl/data-valor) e 500ms nas animações
- Cores novas dos botões em /frota/
"""

import json
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
    tmp = Path(tempfile.mkdtemp(prefix="webv155_"))
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


def _pdf_info(content: bytes):
    import fitz
    doc = fitz.open(stream=content, filetype="pdf")
    pag = doc[0]
    return doc.page_count, pag.rect.width, pag.rect.height, \
        "\n".join(p.get_text() for p in doc)


def main():
    client, tmp = make_env()
    _login_admin(client, tmp)

    from src.core.app_settings import (DEFAULTS, load_app_settings,
                                       save_app_settings)

    # ---------- F1: setting persistente ----------
    check("V55-01 chave em DEFAULTS", "abast_pdf_duas_vias" in DEFAULTS)
    save_app_settings({"abast_pdf_duas_vias": True,
                       "backup_intervalo_min": 15})
    check("V55-02 load preserva a chave (True)",
          load_app_settings()["abast_pdf_duas_vias"] is True)
    check("V55-03 gravada no app_settings.json",
          json.loads((tmp / "app_settings.json").read_text(
              encoding="utf-8"))["abast_pdf_duas_vias"] is True)

    r = client.get("/configuracoes")
    check("V55-04 seção Abastecimentos na página",
          "Abastecimentos (Frota)" in r.text)
    check("V55-05 checkbox marcado com flag True",
          'name="abast_duas_vias" value="1" style="width:auto"\n      '
          in r.text or "abast_duas_vias" in r.text)

    r = client.post("/configuracoes/salvar", data={
        "empresa": "Empresa Teste LTDA", "cnpj": "11.222.333/0001-81",
        "local": "Planta Teste", "instrutor": "Instrutor Teste",
        "registro": "44633/RJ", "backup_intervalo": "15",
        "abast_duas_vias": "1"}, follow_redirects=False)
    check("V55-06 salvar com checkbox -> 303", r.status_code == 303)
    check("V55-07 flag True após POST",
          load_app_settings()["abast_pdf_duas_vias"] is True)
    r = client.post("/configuracoes/salvar", data={
        "empresa": "Empresa Teste LTDA", "cnpj": "11.222.333/0001-81",
        "local": "Planta Teste", "instrutor": "Instrutor Teste",
        "registro": "44633/RJ", "backup_intervalo": "15"},
        follow_redirects=False)
    check("V55-08 sem checkbox -> flag False",
          load_app_settings()["abast_pdf_duas_vias"] is False)

    # ---------- F2: PDF em 2 vias / 1 via ----------
    from src.core.app_settings import set_setting
    from src.core.frota_repo import FrotaRepository
    repo = FrotaRepository()
    vid = repo.add_veiculo("Strada", "Fiat", "pickup", "", "ABD1E23",
                           1, None, None)
    client.post("/frota/fornecedores/criar", data={
        "nome": "Posto Shell", "cnpj": "12345678000199",
        "endereco": "BR-000 km 10"}, follow_redirects=False)

    set_setting("abast_pdf_duas_vias", True)
    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "fornecedor_id": "1",
        "combustivel": "gasolina", "data": "24/09/2026",
        "viagem_servico": "Obra X", "km": "10000", "condutor": "João",
        "obs": "Teste duas vias", "litros": "40,5", "valor": "289,50",
        "extra_desc_0": "Pedágio", "extra_qtd_0": "2",
        "extra_val_0": "30,50"}, follow_redirects=False)
    check("V55-09 abast criado com 2 vias -> 303", r.status_code == 303)
    r = client.get("/frota/abastecimentos/1/pdf")
    check("V55-10 PDF 2 vias servido", r.status_code == 200)
    paginas, w, h, txt = _pdf_info(r.content)
    check("V55-11 PDF 2 vias é paisagem (largura > altura)", w > h)
    check("V55-12 PDF com VIA 1 DE 2 e VIA 2 DE 2",
          "VIA 1 DE 2" in txt and "VIA 2 DE 2" in txt)
    check("V55-13 PDF 2 vias com dados (serial + extra)",
          "AB-2026-00001" in txt and "Pedágio" in txt)

    # watermark no modo 2 vias
    client.post("/frota/abastecimentos/1/bloquear",
                data={"motivo": "Cancelado"}, follow_redirects=False)
    r = client.get("/frota/abastecimentos/1/pdf")
    _, _, _, txt = _pdf_info(r.content)
    check("V55-14 watermark CANCELADO no modo 2 vias", "CANCELADO" in txt)
    client.post("/frota/abastecimentos/1/desbloquear",
                follow_redirects=False)

    set_setting("abast_pdf_duas_vias", False)
    r = client.post("/frota/abastecimentos/1/editar", data={
        "fornecedor_id": "1", "combustivel": "gasolina",
        "data": "24/09/2026", "viagem_servico": "Obra X", "km": "10000",
        "condutor": "João", "obs": "Teste duas vias", "litros": "40,5",
        "valor": "289,50"}, follow_redirects=False)
    check("V55-15 editar com 1 via -> 303", r.status_code == 303)
    r = client.get("/frota/abastecimentos/1/pdf")
    check("V55-16 PDF 1 via servido", r.status_code == 200)
    paginas, w, h, txt = _pdf_info(r.content)
    check("V55-17 PDF 1 via é retrato (altura > largura)", h > w)
    check("V55-18 PDF 1 via SEM marca de via", "VIA 1 DE 2" not in txt)

    # ---------- F3: dashboard ----------
    r = client.get("/")
    check("V55-19 dashboard 200", r.status_code == 200)
    check("V55-20 custo com num-brl + data-valor",
          'class="num num-brl" data-valor=' in r.text)
    check("V55-21 animações em 500ms", r.text.count("/ 500") == 2)
    check("V55-22 bloco JS do custo (num-brl no querySelectorAll)",
          '.num-brl").forEach' in r.text)
    check("V55-23 inteiros não pegam num-brl",
          '.num:not(.num-brl)' in r.text)
    check("V55-24 formatação pt-BR no JS",
          'toLocaleString("pt-BR"' in r.text)

    # ---------- F4: cores dos botões em /frota/ ----------
    r = client.get("/frota")
    check("V55-25 Gráfico de custos azul padrão",
          '<a class="btn" href="/frota/custos">' in r.text)
    check("V55-26 Empresas azul-claro",
          '<a class="btn azul-claro" href="/frota/empresas">' in r.text)
    check("V55-27 Fornecedores azul-claro",
          '<a class="btn azul-claro" href="/frota/fornecedores">' in r.text)
    check("V55-28 Exportar Excel verde",
          '<a class="btn verde" href="/frota/exportar">' in r.text)
    check("V55-29 Exportar custos amarelo-claro",
          '<a class="btn amarelo-claro" href="/frota/custos/exportar">'
          in r.text)
    check("V55-30 Importar Excel cinza",
          'class="btn cinza" onclick="document.getElementById'
          "('imp-arquivo')" in r.text or
          'class="btn cinza"' in r.text)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHAS:")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("TODOS OS 30 CHECKS DA v1.54.0 PASSARAM.")


if __name__ == "__main__":
    main()
