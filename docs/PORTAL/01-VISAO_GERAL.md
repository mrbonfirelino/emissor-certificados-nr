# Portal Web NormaTech — Visão Geral (Documento Mestre)

> Status: **planejamento aprovado — implementação ainda não iniciada**.
> Público: TI/responsável pelo sistema.
> Índice completo da pasta: [00-INDICE.md](00-INDICE.md)

---

## 1. Objetivo

Transformar o NormaTech (aplicativo desktop CustomTkinter) em um **portal web
na rede local da empresa**, acessível por qualquer máquina via navegador, com:

- **Login/senha** por usuário
- **Permissões por módulo** (cada papel vê apenas o que deve)
- **Baixa manutenção** (sem serviços complexos, sem banco para administrar)
- Acesso simples: **`http://normatech:8000`**

O app desktop **continua funcionando em paralelo** durante e depois da
transição — os dois compartilham o mesmo banco de dados no servidor.

## 2. Estado atual (o que já temos a favor)

| Item | Situação |
|------|----------|
| `src/core/` | Lógica 100% desacoplada da interface: repositórios SQLite, serviços e geradores de PDF (ReportLab/python-pptx) em Python puro → **reaproveitáveis no servidor sem reescrita** |
| Banco de dados | SQLite em modo WAL, `busy_timeout` 30s, backups automáticos semanais + manuais já implementados (`BackupManager`) |
| Segurança | `argon2-cffi` já é dependência do projeto (reuso para o hash das senhas dos usuários) |
| Modelos de dados | Pydantic 2.x (`src/core/models.py`) → integração nativa com FastAPI |
| Documentação de base | `docs/MULTIUSUARIO.md` (estudo de cenários) e `docs/REDE.md` (riscos de SQLite em rede) já mapeavam este caminho |

## 3. Arquitetura escolhida

```
┌──────────────────────┐        http://normatech:8000
│  Máquinas da empresa  │ ────────────────────────────►  ┌───────────────────────────┐
│  (navegador, zero     │                                │  SERVIDOR (sempre ligado)  │
│   instalação)         │ ◄────────────────────────────  │  Windows + NSSM (serviço)  │
└──────────────────────┘         PDFs / páginas HTML     │                           │
                                                         │  FastAPI + Jinja2 + HTMX   │
                                                         │        │                   │
                                                         │  src/core/ (reaproveitado) │
                                                         │        │                   │
                                                         │  SQLite (data/ local)      │
                                                         │  + pastas data/certificados│
                                                         │    asos, epis, crachas...  │
                                                         └───────────────────────────┘
```

**Ponto-chave:** o risco de "SQLite em rede" (`docs/REDE.md`) existe quando
cada máquina abre o banco por compartilhamento. No portal, **um único processo
no servidor** acessa o banco no **disco local** dele — o problema de lock em
SMB desaparece por construção.

### Stack

| Camada | Escolha | Motivo |
|--------|---------|--------|
| Backend | **FastAPI** | Reusa os models Pydantic existentes; rotas finas sobre os repos atuais |
| Frontend | **Jinja2 + HTMX + Bootstrap** (vendidos, sem CDN) | Server-rendered, quase zero JavaScript, funciona sem internet |
| Sessão | Cookie assinado (SessionMiddleware do Starlette) | Simples, sem JWT/Redis |
| Senhas | **argon2-cffi** (já existe no projeto) | Zero dependência nova de segurança |
| Servidor HTTP | **waitress** | Produção em Windows, estável, sem compilador |
| Serviço Windows | **NSSM** | Auto-start no boot, auto-restart em falha, logs em arquivo |
| Banco | **SQLite/WAL no disco do servidor** (mantido — ver Decisão D3) | Zero administração |

### Novos pacotes (`requirements-web.txt`, a criar na Fase 1)

```
fastapi
waitress
jinja2
python-multipart      # uploads (fotos, documentos)
itsdangerous          # assinatura do cookie de sessão
```

## 4. Estrutura nova no projeto

```
src/web/
  app.py            # factory FastAPI, middlewares, registro de routers
  auth.py           # login/logout, usuário corrente, decorator require_permission
  permissions.py    # matriz papel × módulo
  routers/          # auth, dashboard, employees, certificates, aso, epi, crachas,
                    # blocking_cards, history, vencimentos, imports, integracoes,
                    # config, backup, users, audit
  templates/        # base.html, login.html, 1 página por módulo
  static/           # bootstrap + htmx vendidos, css do tema azul atual
run_web.py          # entrypoint: app + APScheduler de backup (reuso do BackupManager)
```

Cada router apenas **orquestra**: rota → repo/service existente → template.
Nenhuma lógica de negócio nova é escrita.

## 5. Módulos do portal (1:1 com as telas atuais)

Dashboard • Funcionários • Certificados • ASO • EPI • Crachás •
Cartões de Bloqueio • Histórico • Vencimentos • Importações • Integrações •
Configurações • Backup • **Usuários** (novo) • **Auditoria** (novo)

## 6. Autenticação e permissões

- Tabelas novas: `users` (username, password_hash Argon2, nome, papel, ativo)
  e `audit_log` (usuário, ação, alvo, timestamp)
- 1º boot do servidor cria o usuário `admin` com senha provisória; troca
  forçada no primeiro login
- 3 papéis fixos; o admin pode ajustar o acesso de cada papel por módulo na
  tela Usuários

### Matriz inicial de permissões

| Módulo | Admin | Emissor | Consulta |
|--------|:-:|:-:|:-:|
| Dashboard | ✓ | ✓ | ✓ |
| Funcionários / Certificados / Histórico / Vencimentos | ✓ | ✓ | só ver |
| ASO / EPI / Crachás | ✓ | ✓ | só ver |
| Importações / Integrações / Cartões de Bloqueio | ✓ | ✓ | ✗ |
| Configurações / Backup / Usuários / Auditoria | ✓ | ✗ | ✗ |

O menu lateral renderiza só os módulos permitidos **e** as rotas são bloqueadas
no backend (defesa em profundidade).

## 7. Decisões Registradas

Cada decisão tem: contexto → decisão → consequência. Alterar uma decisão
significa editar esta seção e registrar o motivo.

### D1 — Framework web: FastAPI + Jinja2 + HTMX
- **Contexto:** precisamos de um portal com login/permissões e baixa manutenção.
- **Alternativas descartadas:** Django (exigiria reescrever todos os repos para
  ORM), Flask (ok, mas sem integração nativa com os models Pydantic já
  existentes), React/Vue SPA (muito mais código e manutenção de build).
- **Decisão:** FastAPI com páginas server-rendered (Jinja2) e HTMX para
  interatividade.
- **Consequência:** `src/core/` permanece intocado; frontend sem build step.

### D2 — HTTP na rede interna + hostname `normatech` (sem HTTPS na fase 1)
- **Contexto:** o requisito é **nenhum aviso ou bloqueio** para o usuário.
- **Análise:** avisos de certificado só existem com HTTPS. HTTPS "sem avisos"
  exige instalar um certificado raiz interno em cada máquina (GPO/domínio) —
  manutenção contínua. Em HTTP puro, `http://normatech:8000` abre sem
  bloqueios; o navegador exibe apenas um "Não seguro" informativo no canto da
  barra de endereço (não impede nada).
- **Decisão:** HTTP na LAN confiável + servidor renomeado para `NORMATECH`
  (resolução por NetBIOS/broadcast; opcional: registro DNS no roteador ou
  entrada no `hosts` como fallback — ver [02-DEPLOY_SERVIDOR.md](02-DEPLOY_SERVIDOR.md) §6).
- **Risco aceito:** tráfego (incl. senha de login) é legível por quem estiver
  farejando a rede interna. Mitigações: senhas fortes, rate-limit no login,
  acesso restrito à rede interna.
- **Caminho futuro:** se o portal precisar de acesso externo (VPN/fora da
  empresa), reverte-se esta decisão com certificado interno via GPO.

### D3 — Banco de dados: manter SQLite (comparativo com PostgreSQL)

| Critério | SQLite (atual) | PostgreSQL |
|----------|---------------|------------|
| Instalação | Nenhuma — é um arquivo | Serviço dedicado (instalação, senha, porta) |
| Manutenção | ~zero | Updates periódicos, vacuum, monitoramento |
| Backup | Copiar/gzip do arquivo — **já implementado** (`BackupManager`) | pg_dump / rotina nova |
| Concorrência | WAL: 1 escritor por vez, leituras paralelas — **folgado p/ 2–10 usuários** | Centenas de escritas simultâneas |
| Migração do código | **Zero** — repos já são SQLite | Adaptar ~6 repos + driver + testes |
| Risco neste porte | Baixíssimo | Overhead desnecessário |

- **Decisão:** manter SQLite. O desktop e o portal no **mesmo servidor/mesmo
  disco** convivem bem (WAL + busy_timeout 30s).
- **Gatilhos para reavaliar (migração futura p/ PostgreSQL):** mais de ~30
  usuários simultâneos; múltiplas instâncias do servidor; relatórios pesados
  concorrentes com emissão. Os repos ficam isolados, então a migração é uma
  tarefa delimitada.

### D4 — Scanner: árvore de decisão (cenário: scanner USB no PC da técnica)

Detalhes completos em [04-SCANNER.md](04-SCANNER.md). Resumo:

1. **Upload manual** — sempre disponível, zero configuração (fallback universal)
2. **NormaAgent** no PC da técnica — mini-aplicativo local que o portal chama
   via `localhost`; reutiliza o `scanner_wia.py` existente; ela digitaliza
   direto do navegador. **Alvo plug-n-play** para o cenário atual
3. **Scanner no servidor (futuro)** — endpoint de digitalização server-side
   via WIA; qualquer pessoa com permissão digitaliza do próprio navegador.
   Requer spike técnico (WIA em serviço/sessão 0)
4. **Scan-to-folder** — apenas se um dia a empresa tiver multifuncional de rede

### D5 — Uploads de arquivos
- Limite: **50 MB por arquivo**
- Extensões: **livres** (com validação básica de conteúdo para imagens/PDF
  onde for crítico)
- Fotos de funcionários, documentos assinados, ASOs etc. seguem essa regra.

### D6 — App desktop mantido em paralelo
- O desktop continua instalável e funcional; no servidor, os dois compartilham
  o mesmo `data/`.
- Recursos exclusivos do desktop no futuro próximo: scanner WIA local,
  notificações toast do Windows (no portal, alertas ficam no dashboard).
- Congelamento gradual: novas funcionalidades nascem no portal.

## 8. Fases de implementação

| Fase | Entrega | Critério de pronto |
|------|---------|--------------------|
| **0** | Documentação (esta pasta) | ✅ Feita |
| **1** | Esqueleto web: app.py, login, users/roles, dashboard read-only, run_web.py + NSSM | Portal abre em 2 máquinas com login funcionando |
| **2** ✅ Feita (v1.25.0)  Núcleo de valor: Funcionários (CRUD + foto), Certificados (emissão + PDF + download), Histórico com filtros | Técnica emite um certificado pelo navegador |
| **3** | ASO, EPI, Crachás, Cartões, Vencimentos, Importações Excel/CSV | Desktop não é mais necessário no dia a dia |
| **4** | Admin: Configurações, Backup na tela, Gestão de usuários, audit_log, NormaAgent | Fechamento do ciclo + auditoria ativa |

## 9. Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| Servidor desligado = portal fora | Máquina dedicada sempre ligada; auto-restart do serviço (NSSM); backup restaura em outra máquina se o hardware morrer |
| Concorrência SQLite | WAL + busy_timeout 30s já configurados; porte atual (2–10 pessoas) folga; monitorar `database is locked` no error.log |
| WIA em serviço (sessão 0) pode falhar | NormaAgent roda na sessão do usuário (fora do serviço); spike documentado no [04-SCANNER.md](04-SCANNER.md) antes da opção server-side |
| Senhas fracas | Mínimo de complexidade + troca no 1º login + rate-limit |
| Upload malicioso | Limite de tamanho + servir arquivos com `Content-Disposition` (sem execução) |
| Projeto em pasta sincronizada (OneDrive etc.) no servidor | Verificação obrigatória no deploy ([02-DEPLOY_SERVIDOR.md](02-DEPLOY_SERVIDOR.md) §2) |

## 10. Melhorias futuras (fora de escopo atual)

- Login integrado ao Active Directory do Windows (se a empresa tiver domínio)
- eSCL/AirScan (digitalizar de qualquer scanner de rede direto do portal)
- QR code de autenticidade nos certificados (já planejado em `docs/QR_CODE.md`)
- Assinatura digital ICP-Brasil (`docs/ASSINATURA_DIGITAL.md`)
