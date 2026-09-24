# -*- coding: utf-8 -*-
"""Testes do Portal Web — v1.49.0 (roadmap 2.36).

Padrão standalone: `python test_web_v150.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.

Cobre (refinamentos do dialog 'Custo e consumo' da ficha do veículo):
- 2.36.1 dialog dlg-custo maior (class="modal largo")
- 2.36.2 gráfico interativo: grupos .g-mes com data-comb/data-ext/data-litros,
  <title> nativo, classes b-comb/b-ext, rect captura, CSS .graf-tip e JS
  de tooltip no template
- 2.36.3 linha 'Itens extras' na tabela do resumo (abaixo de Custo por km)
- 2.36.4 botão 'Baixar gráfico (PNG)' (client-side, sem endpoint novo)
- regressão: criação com extras + desglose (v1.48.0) segue ok
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
    tmp = Path(tempfile.mkdtemp(prefix="webv150_"))
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


TPL_DIR = Path(__file__).parent / "src" / "web" / "templates"


def _tpl(nome):
    return (TPL_DIR / nome).read_text(encoding="utf-8")


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
    check("V50-01 veiculo criado -> 303", r.status_code == 303)
    vid = int(r.headers["location"].split("/")[-1])

    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "combustivel": "gasolina",
        "data": "05/09/2026", "viagem_servico": "Obra X", "km": "10000",
        "condutor": "João", "obs": "Tanque cheio",
        "litros": "40", "valor": "289,50",
        "extra_desc_0": "Pedágio", "extra_qtd_0": "2", "extra_val_0": "30,50"},
        follow_redirects=False)
    check("V50-02 abastecimento com extras criado -> 303", r.status_code == 303)

    r = client.post("/frota/abastecimentos/criar", data={
        "veiculo_id": str(vid), "combustivel": "gasolina",
        "data": "20/09/2026", "km": "10400", "condutor": "João",
        "litros": "20", "valor": "120,00"}, follow_redirects=False)
    check("V50-03 segundo abastecimento criado -> 303", r.status_code == 303)

    # ---------- 2.36.1 dialog largo ----------
    r = client.get(f"/frota/{vid}")
    check("V50-04 ficha 200", r.status_code == 200)
    check("V50-05 dlg-custo é 'modal largo'",
          '<dialog id="dlg-custo" class="modal largo">' in r.text)

    # ---------- 2.36.3 linha Itens extras na tabela ----------
    check("V50-06 linha 'Itens extras' com valor (30,50) na tabela",
          re.search(r"Itens extras</th><td>R\$ 30,50</td>", r.text) is not None)
    check("V50-07 'Itens extras' vem depois de 'Custo por km' na tabela",
          r.text.index("Custo por km") < r.text.index("Itens extras</th>")
          if "Custo por km" in r.text else
          r.text.index("Média KM/L") < r.text.index("Itens extras</th>"))
    check("V50-08 desglose no topo mantido (30,50)",
          "R$ 30,50" in r.text)

    # ---------- 2.36.2 gráfico interativo ----------
    check("V50-09 SVG presente com grupos g-mes", 'class="g-mes"' in r.text)
    check("V50-10 grupos com data-comb/data-ext/data-litros",
          all(a in r.text for a in ("data-comb=", "data-ext=", "data-litros=")))
    check("V50-11 valores por mês nos data-* (409,50 e 30,50)",
          'data-comb="409,50"' in r.text and 'data-ext="30,50"' in r.text)
    check("V50-12 barras com classes b-comb/b-ext",
          'class="b-comb"' in r.text and 'class="b-ext"' in r.text)
    check("V50-13 rect de captura por mês",
          'class="captura"' in r.text)
    check("V50-14 <title> nativo por mês", "<title>" in r.text)
    check("V50-15 SVG com width/height explícitos (export PNG)",
          re.search(r'<svg viewBox="0 0 720 260" width="720" height="260"',
                    r.text) is not None)
    check("V50-16 wrapper #graf-custo e tooltip #graf-tip",
          'id="graf-custo"' in r.text and 'id="graf-tip"' in r.text)

    # CSS global (F2)
    base = _tpl("base.html")
    check("V50-17 CSS .graf-tip no base.html", ".graf-tip" in base)
    check("V50-18 CSS hover .g-mes no base.html",
          ".g-mes:hover" in base and "cursor:crosshair" in base)

    # JS do template (tooltip)
    ficha_tpl = _tpl("frota_ficha.html")
    check("V50-19 JS tooltip usa dataset (comb/ext/litros)",
          all(a in ficha_tpl for a in ("g.dataset.comb", "g.dataset.ext",
                                       "g.dataset.litros")))

    # helpers diretos do router
    import importlib
    fr_router = importlib.import_module("src.web.routers.frota")
    # _svg_grafico_custo é closure de register(); valida via série do repo
    serie = repo.custo_serie_veiculo(vid)
    check("V50-20 série mensal com 12 pontos", len(serie) == 12)
    set09 = next(s for s in serie if s["mes"] == "2026-09")
    check("V50-21 série: set/2026 combustivel=409.50 extras=30.50 litros=60",
          abs(set09["combustivel"] - 409.50) < 0.01
          and abs(set09["extras"] - 30.50) < 0.01
          and abs(set09["litros"] - 60) < 0.01)

    # ---------- 2.36.4 botão PNG ----------
    check("V50-22 botão 'Baixar gráfico (PNG)' com id btn-graf-png",
          'id="btn-graf-png"' in r.text and "Baixar gráfico (PNG)" in r.text)
    check("V50-23 JS de export (XMLSerializer + canvas + toBlob)",
          all(a in ficha_tpl for a in ("XMLSerializer", "createElement('canvas')",
                                       "toBlob")))
    check("V50-24 fallback .svg quando canvas falha",
          "nome + '.svg'" in ficha_tpl)
    check("V50-25 nome do arquivo usa a placa",
          "custo_{{ v.placa or v.id }}" in ficha_tpl)

    # ---------- resumo com desglose (regressão v1.48.0) ----------
    resumo = repo.resumo_custo_veiculo(vid)
    check("V50-26 resumo.valor = 440.00 (comb+extras)",
          abs(resumo["valor"] - 440.00) < 0.01)
    check("V50-27 resumo.valor_combustivel = 409.50",
          abs(resumo["valor_combustivel"] - 409.50) < 0.01)
    check("V50-28 resumo.valor_extras = 30.50",
          abs(resumo["valor_extras"] - 30.50) < 0.01)

    # ---------- resultado ----------
    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}):")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("TODOS OS 28 CHECKS DA V1.49.0 PASSARAM")


if __name__ == "__main__":
    main()
