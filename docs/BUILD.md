# Guia de Build - NormaTech

Documento completo do processo de build, configurações e distribuição do executável.

---

## 1. Pré-requisitos

| Item | Versão usada | Observação |
|------|--------------|------------|
| Python | 3.11.x (testado com 3.11.0) | Obrigatório 64-bit |
| PyInstaller | 6.8.0 | Incluído no requirements.txt |
| Windows | 10/11 | Build e execução são Windows-only |

Instalar dependências em ambiente limpo:

```powershell
pip install -r requirements.txt
```

O `requirements.txt` inclui todas as bibliotecas: `customtkinter` (UI), `reportlab` (PDF), `pymupdf` (preview), `pillow` (fotos 3x4), `openpyxl` (Excel), `pydantic` (modelos), `apscheduler` (backup automático), `argon2-cffi` (senha de restauração), `python-dateutil` (validade de certificados).

---

## 2. Regra de ouro antes de buildar

**Feche o NormaTech.exe antes de rodar a build.** O script limpa a pasta `dist/` e, se o exe estiver aberto, o Windows bloqueia a exclusão:

```
PermissionError: [WinError 5] Acesso negado: 'dist\NormaTech\NormaTech.exe'
```

Para matar o processo pela linha de comando:

```powershell
taskkill /F /IM NormaTech.exe
```

> Nota: o projeto fica dentro do OneDrive. Durante a build a sincronização pode deixar o processo mais lento — é normal.

---

## 3. Comando de build

Na raiz do projeto:

```powershell
python build/build_exe.py
```

Tempo aproximado:
- **onedir (modo atual, testes):** 2–3 minutos
- **onefile (release):** ~5 minutos

---

## 4. Modos de build

A configuração está em `build/build_exe.py`, linhas 34–39:

### Modo atual — onedir + sem UPX (recomendado para testes)

```python
'--onedir',
'--windowed',
'--noupx',
```

- Saída: `dist\NormaTech\NormaTech.exe` (pasta com ~165 MB de DLLs/_internal)
- Build mais rápida, depuração mais fácil, inicialização do exe mais rápida
- Distribuição: copiar a **pasta inteira** `NormaTech\`

### Modo release — onefile

Trocar as linhas por:

```python
'--onefile',
'--windowed',
```

- Saída: `dist\NormaTech.exe` (arquivo único, ~78 MB)
- Extração temporária a cada inicialização (abre mais devagar)
- Distribuição: enviar só o arquivo (+ pastas `data\` e `templates\` do lado)

---

## 5. O que o script de build faz (passo a passo)

Arquivo: `build/build_exe.py`

1. **Limpeza** — remove `dist\`, `build\work\` e `src\assets\` (duplicado) antes de começar.
2. **Ícone** — usa `assets\logo.ico` (se ausente, usa ícone padrão e imprime aviso).
3. **Empacotamento** (`--add-data`):
   - `templates\` → dentro do exe (templates de NR embutidos)
   - `assets\` → dentro do exe (logo, fontes, ícone)
   - `setuptools\_vendor\` → dentro do exe (veja runtime hook abaixo)
4. **Runtime hook** `build/rthook_jaraco.py` — registra o caminho do `setuptools/_vendor` no `sys.path` para que `import jaraco.text` e `pkg_resources` funcionem dentro do exe (o PyInstaller não resolve esse namespace package sozinho).
5. **Hidden imports** — `customtkinter`, `reportlab`, `pydantic`, `apscheduler`, `argon2`, `PIL`, `jaraco.*`, `packaging.*`, `platformdirs`, `pkg_resources`, `openpyxl`, `fitz`, `pymupdf`, `pydantic_settings` (imports dinâmicos que o analisador não detecta).
6. **Exclusões** (`--exclude-module`) — `torch`, `tensorflow`, `sklearn`, `scipy`, `pandas`, `cv2`, `boto3`, `grpc`, etc. Evita arrastar dependências pesadas que existem no ambiente mas não são usadas.
7. **Cópia de dados de runtime** para `dist\data\` e `dist\NormaTech\data\`:
   - `data\certificados.db` (banco)
   - `data\company_config.json`
   - `data\funcoes.json`
8. **Cópia de templates externos** — `copytree` de `templates\` inteiro (incluindo subpasta `templates\cards\`) para `dist\templates\` e `dist\NormaTech\templates\`. Templates ficam **fora** do exe para edição sem recompilar.

---

## 6. Estrutura de pastas

```
EMISSOR DE CERTIFICADOS NR\
├── build\
│   ├── build_exe.py          # script de build (edita aqui p/ onefile/onedir)
│   ├── rthook_jaraco.py      # runtime hook do PyInstaller
│   └── CertificadosNR.spec   # gerado automaticamente
├── src\
│   ├── main.py               # entrypoint
│   ├── core\                 # regras de negócio (repos, services, PDF, cartões)
│   ├── ui\                   # páginas, componentes, estilos
│   └── utils\                # validadores, foto 3x4, paths, excel
├── templates\
│   ├── *.template.json       # 17 templates de NR
│   ├── _layout.json          # layout do certificado (margens, fontes, cores)
│   └── cards\
│       └── ALTEC.card.json   # template do cartão de bloqueio (90x120mm)
├── assets\                   # logo.ico, LOGO TIPO ALTEC.png, fontes
├── data\                     # certificados.db, company_config.json, funcoes.json
│   ├── backups\              # backups automáticos (.db.gz)
│   ├── certificados\         # PDFs por funcionário/NR (v1.8.0)
│   ├── cartoes\              # cartões por funcionário + LOTES (v1.8.0)
│   └── assinados\            # docs assinados exportados por funcionário (v1.8.0)
├── dist\                     # SAÍDA DA BUILD
└── CERTIFICADOS\             # legado (v1.7.x) — migrado automaticamente p/ data\
```

### Runtime (quando empacotado)

O app procura dados **ao lado do exe** (`src/utils/paths.py`):

| Pasta | Conteúdo | Editável sem rebuild? |
|-------|----------|----------------------|
| `data\` | banco SQLite, config da empresa, funções, backups | banco evolui sozinho; config sim |
| `data\certificados\` | PDFs emitidos por `{Funcionario}\{NR}` | saída do app (v1.8.0) |
| `data\cartoes\` | cartões `{Funcionario}\` + `LOTES\` | saída do app (v1.8.0) |
| `data\assinados\` | assinados exportados `{Funcionario}\` | saída do app (v1.8.0) |
| `templates\` | JSONs de NR + `_layout.json` + `cards\*.card.json` + `cards\pptx\` (PPTX) | **SIM** — editar e reiniciar o app |
| `assets\` | embutidos no exe (via `_MEIPASS`) | não |
| `CERTIFICADOS\` | legado v1.7.x — migração automática no 1º boot (v1.8.0) | migração única |

---

## 7. Adicionar novo modelo de cartão de bloqueio (sem rebuild)

### Modelo JSON (ReportLab)

1. Copiar `templates\cards\ALTEC.card.json` → `templates\cards\{CODIGO}.card.json`
2. Editar:
   - `card_code`: identificador (ex: `PETROBRAS`)
   - `cliente_nome`: nome que aparece na geração
   - `card_width_mm` / `card_height_mm`: tamanho do cartão (o app calcula **automaticamente** quantos cabem por folha A4)
   - `logo_cliente.enabled: true` + `path` (arquivo em `templates\cards\logos\`)
   - posições/medidas das seções em mm
3. Reiniciar o app — o menu Cartões detecta o novo modelo no dropdown.

### Modelo PPTX (PowerPoint)

1. Colocar o `.pptx` preparado + `{CODIGO}.card.json` em `templates\cards\pptx\`
   (convenções de tokens/nomes de shapes: ver `docs\PPTX_TEMPLATES.md`)
2. Reiniciar o app — aparece junto com os JSON no dropdown.

**Importante (exe):** templates PPTX exigem **Microsoft PowerPoint instalado**
na máquina do usuário (conversão via COM). `comtypes` já entra no exe; nada de
extra para empacotar. Templates JSON continuam funcionando sem Office.

---

## 8. Avisos normais da build (inofensivos)

| Aviso | Causa | Ação |
|-------|-------|------|
| `rapidfuzz.__pyinstaller has no attribute get_hook_dirs` | hook de entry-point de outro pacote | ignorar |
| `Failed to collect submodules ... packaging.licenses` | vendor do setuptools | ignorar |
| `PydanticExperimentalWarning` | pydantic | ignorar |
| `The fitz API is deprecated` | PyMuPDF (usamos via `fitz`) | ignorar |
| `Hidden import "pysqlite2"/"MySQLdb" not found` | hooks opcionais de SQLAlchemy | ignorar |
| `Could not find an up-to-date installation of packaging` | licensificação | ignorar |

Relatório completo de warnings: `build\work\NormaTech\warn-NormaTech.txt`

---

## 9. Problemas comuns

| Problema | Causa | Solução |
|----------|-------|---------|
| `PermissionError: WinError 5 Acesso negado` | exe aberto travando `dist\` | `taskkill /F /IM NormaTech.exe` e rebuildar |
| Build muito lenta | OneDrive sincronizando a pasta `dist\` | aguardar, ou pausar sincronização |
| Exe abre e fecha na hora (onefile) | ver traceback rodando o build console: trocar `--windowed` por `--console` temporariamente | debugar e reverter |
| Antivírus bloqueia o exe | falso positivo comum do PyInstaller | adicionar exclusão |
| Templates não aparecem no exe | pasta `templates\` não copiada ao lado do exe | conferir item 5.8 |

---

## 10. Checklist de distribuição

Para entregar a um usuário final (modo onedir):

1. Buildar (`python build/build_exe.py`)
2. Compactar/enviar a pasta `dist\NormaTech\` **inteira**
3. Instruções ao usuário: extrair em pasta local (ex: `C:\NormaTech`), executar `NormaTech.exe`
4. Primeira execução cria `CERTIFICADOS\` e `data\backups\` automaticamente
5. Para atualizar templates depois: substituir apenas os JSONs em `templates\`
