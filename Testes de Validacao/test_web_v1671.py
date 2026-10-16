# -*- coding: utf-8 -*-
"""Testes v1.67.1: e-mail (prontidao), limpeza de previews, export historico."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils import email_report  # noqa: E402
from src.utils import paths as paths_mod  # noqa: E402

n_ok = 0
n_fail = 0

def check(nome, cond):
    global n_ok, n_fail
    if cond:
        n_ok += 1
        print(f"  OK  {nome}")
    else:
        n_fail += 1
        print(f" FALHA {nome}")

# V671-1: deve_enviar_hoje com cfg desativada
check("V671-1 deve_enviar_hoje cfg inativa = False",
      email_report.deve_enviar_hoje({"report_ativo": False}) is False)

# V671-2: ativa sem host/destinos = False
check("V671-2 deve_enviar_hoje sem host = False",
      email_report.deve_enviar_hoje({"report_ativo": True, "smtp_host": ""}) is False)

# V671-3: ativa com host/destinos e nunca enviado = True
check("V671-3 deve_enviar_hoje primeiro envio = True",
      email_report.deve_enviar_hoje({"report_ativo": True, "smtp_host": "smtp.x.com",
                                     "report_destinatarios": "a@x.com"}) is True)

# V671-4: enviado ha 10 dias, mensal = False
from datetime import date, timedelta
check("V671-4 mensal recente = False",
      email_report.deve_enviar_hoje({"report_ativo": True, "smtp_host": "s",
                                     "report_destinatarios": "a@x.com",
                                     "report_periodicidade": "mensal",
                                     "report_ultimo_envio":
                                         (date.today() - timedelta(days=10)).isoformat()}) is False)

# V671-5: enviado ha 40 dias, mensal = True
check("V671-5 mensal vencido = True",
      email_report.deve_enviar_hoje({"report_ativo": True, "smtp_host": "s",
                                     "report_destinatarios": "a@x.com",
                                     "report_periodicidade": "mensal",
                                     "report_ultimo_envio":
                                         (date.today() - timedelta(days=40)).isoformat()}) is True)

# V671-6: testar_conexao sem host = (False, msg amigavel)
ok, msg = email_report.testar_conexao({"smtp_host": ""})
check("V671-6 testar_conexao sem host", ok is False and "SMTP" in msg)

# V671-7/8: limpar_previews apaga antigo e mantem recente
tmp = Path(tempfile.mkdtemp())
prev = tmp / "_previews"
prev.mkdir()
antigo = prev / "velho.pdf"
recente = prev / "novo.pdf"
antigo.write_bytes(b"x")
recente.write_bytes(b"y")
velho_ts = time.time() - 30 * 86400
import os
os.utime(antigo, (velho_ts, velho_ts))
orig = paths_mod.get_data_dir
paths_mod.get_data_dir = lambda: tmp
email_report.get_data_dir = lambda: tmp
try:
    n = email_report.limpar_previews(max_dias=7)
finally:
    paths_mod.get_data_dir = orig
    email_report.get_data_dir = orig
check("V671-7 limpar_previews apagou antigo", n == 1 and not antigo.exists())
check("V671-8 limpar_previews manteve recente", recente.exists())

# V671-9: report_ultimo_envio nos DEFAULTS
from src.core.app_settings import DEFAULTS
check("V671-9 DEFAULTS tem report_ultimo_envio", "report_ultimo_envio" in DEFAULTS)

# V671-10: gerar_relatorio_html nao explode sem DB de itens? (usa DB real; so testa funcao existe)
check("V671-10 gerar_relatorio_vencimentos_html callable",
      callable(email_report.gerar_relatorio_vencimentos_html))

print(f"\nRESUMO v1671: {n_ok} ok, {n_fail} falha(s)")
sys.exit(1 if n_fail else 0)
