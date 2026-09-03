# CI com GitHub Actions — Plano (documento)

> Status: **planejado** (não implementado). Quando aprovado, criar o arquivo
> `.github/workflows/tests.yml` com o conteúdo da seção "Workflow proposto".

## Objetivo

Rodar a suíte de testes unitários a cada push/PR, garantindo regressões
detectadas antes do build do exe.

## O que roda no CI (e o que não)

| Suíte | No CI? | Motivo |
|-------|--------|--------|
| `test_history_filters.py` | Sim | puro SQLite temporário |
| `test_signed_docs.py` | Sim | puro SQLite temporário |
| `test_vencimentos.py` | Sim | lógica pura |
| `test_photo_importer.py` | Sim | arquivos temporários |
| `test_backup.py` | Sim | SQLite + pastas temporárias |
| `test_pptx_cards.py --unit` | Sim | python-pptx puro (sem COM) |
| `test_scan.py` | Parcial | `pages_to_pdf` precisa `fitz`; parte WIA é mock |
| `test_cert_number.py` | Sim | gera PDF com ReportLab + lê com PyMuPDF |
| `test_pptx_cards.py --e2e` | **Não** | exige PowerPoint instalado |
| `test_layout.py` | Sim | depende dos templates do repo |

Dependências do runner: `pip install -r requirements.txt` já cobre tudo
(reportlab, pymupdf, python-pptx, openpyxl, Pillow etc.).

## Workflow proposto

```yaml
name: tests
on:
  push:
    branches: [main]
  pull_request:

jobs:
  unit:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - name: Suítes unitárias
        shell: pwsh
        run: |
          python test_history_filters.py
          python test_signed_docs.py
          python test_vencimentos.py
          python test_photo_importer.py
          python test_backup.py
          python test_cert_number.py
          python test_scan.py
          python test_layout.py
          python test_pptx_cards.py --unit
```

Notas:
- Runner **windows** porque os paths/registro (backup, impressão) são
  específicos do Windows; Linux falharia em partes do `test_backup`
- Se o tempo de setup pesar, migrar para `ubuntu` depois de isolar os
  testes que dependem do Windows
- Badge no README: `![tests](https://github.com/mrbonfirelino/emissor-certificados-nr/actions/workflows/tests.yml/badge.svg)`

## Próximos passos quando aprovar

1. Commitar `.github/workflows/tests.yml`
2. Conferir a 1ª execução na aba Actions
3. (Opcional) job `build` que roda PyInstaller onedir em tag `v*` e publica
   o artefato zip — requer cuidado: exe ~172MB, usar retention-days curto
