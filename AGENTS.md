# AGENTS.md — NormaTech (Emissor de Certificados NR)

Portal web FastAPI (servido por waitress) para emissão de certificados NR, gestão de frota, EPIs, ASO, presenças, cartões e feedbacks. Português-BR em toda a UI e mensagens de commit.

## Comandos
- Subir portal: `python run_web.py` (flags: `--host`, `--port`, `--reset-admin`, `--sem-backup`)
- Testes: `python -m pytest tests/ -x -q`
- Versão atual: `src/version.py` → `APP_VERSION` (atualizar a cada release + entrada no CHANGELOG.md)

## Mapa do código
- `run_web.py` — entrypoint FastAPI + waitress
- `src/core/` — serviços, repositórios, geradores de PDF (incl. assinatura)
- `src/ui/` — componentes e páginas (tkinter legado/desktop)
- `src/utils/` — utilitários
- `src/web/` — portal web: `app.py`, `auth.py`, `jobs.py`, `permissions.py`, `users_repo.py`, `routers/` (~21 routers), `templates/`
- `data/` — banco de dados e arquivos do usuário (NUNCA apagar/substituir)
- `docs/` — documentação, incluindo histórico antigo do changelog

## Regras importantes
- **NUNCA ler `CHANGELOG.md` ou `docs/changelog-arquivo.md` por inteiro** (grandes). Usar busca (grep) por versão/palavra-chave; ler no máximo as primeiras ~100 linhas. `CHANGELOG.md` = 10 versões mais recentes; `docs/changelog-arquivo.md` = todo o resto (v1.29–v1.82.0).
- Escopo de buscas (grep/glob) em `src/` e `tests/` — não buscar na raiz (há muitos arquivos binários).
- Novas versões: adicionar entrada no topo de `CHANGELOG.md`, bump em `src/version.py`.
- Releases geram `ATUALIZACAO PORTAL vX.Y.Z.zip` com `LEIA-ME-ATUALIZACAO.txt` (seção `NOVIDADES vX` = changelog user-facing da versão).
- Banco de dados: backups automáticos em `backups/` (dumps .gz). Não versionar `data/`.
