# -*- coding: utf-8 -*-
"""Roda todos os testes desta pasta a partir da raiz do projeto.

Uso:  & .\.venv\Scripts\python.exe "Testes de Validacao\RODAR_TODOS.py"
      (ou: python RODAR_TODOS.py [nome_parcial]  -- filtra por substring)
"""
import io
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")

filtro = sys.argv[1] if len(sys.argv) > 1 else ""
testes = sorted(AQUI.glob("test_*.py"))
if filtro:
    testes = [t for t in testes if filtro.lower() in t.name.lower()]

print(f"Executando {len(testes)} teste(s) de {AQUI.name}...")
falhas, ok, pulos = [], [], []
for t in testes:
    ini = time.time()
    try:
        r = subprocess.run(
            [sys.executable, str(t)], cwd=str(ROOT), capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=300, env={**__import__('os').environ, 'PYTHONPATH': str(ROOT)})
        dt = time.time() - ini
        if r.returncode == 0:
            ok.append(t.name)
            print(f"PASS  {t.name} ({dt:.1f}s)")
        else:
            falhas.append(t.name)
            ult = (r.stdout or "").strip().splitlines()[-3:]
            err = (r.stderr or "").strip().splitlines()[-3:]
            print(f"FAIL  {t.name} ({dt:.1f}s)")
            for ln in ult + err:
                print(f"      {ln.strip()[:160]}")
    except subprocess.TimeoutExpired:
        falhas.append(t.name)
        print(f"TIMEOUT {t.name} (>300s)")

print()
print(f"RESUMO: {len(ok)} passou, {len(falhas)} falhou de {len(testes)}")
if falhas:
    print("FALHARAM:")
    for f in falhas:
        print("  -", f)
sys.exit(1 if falhas else 0)
