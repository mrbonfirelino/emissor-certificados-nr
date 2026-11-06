# Roadmap — NormaTech

> **Versão atual: 1.87.1** (ver `CHANGELOG.md`)

## Situação

Itens pendentes: nenhum no momento. O histórico detalhado de entregas está em [`CHANGELOG.md`](CHANGELOG.md).

## Correções (nov/2026 — v1.87.1)

| Item | Status |
|---|---|
| Feedback: arquivamento não funcionava (campos errados no popup e formulário sem destino) — corrigido para motivos padrão e personalizado | Concluído (v1.87.1) |
| Dashboard: statcard renomeado para "Feedbacks em aberto", pisca com fundo azul claro e texto em alto contraste | Concluído (v1.87.1) |
| /feedbacks: mensagem não aparece completa na lista — prévia + botão "Ler" com texto completo e anexos | Concluído (v1.87.1) |

## Novidades (nov/2026 — v1.87.0)

| Item | Descricao | Prioridade | Status |
|---|---|---|---|
| Sistema: botão e módulo de Feedback | Botão "FeedBack" roxo no header (visível em todas as paginas), abrindo popup para escrever erros/feedback com anexos (PDF/JPG/PNG, ate 8 arquivos de 50 MB). Feedbacks salvos em arquivos em data/feedbacks/ (horario e pagina automaticos). Admin le na pagina /feedbacks (acesso SOMENTE admin) e arquiva com motivo Realizado/Corrigido/Cancelado ou personalizado | Alta | Concluído (v1.87.0) |
| Dashboard: statcard de feedbacks nao atendidos | Statcard "Feedbacks abertos" no Dashboard, piscando em azul claro quando houver feedbacks nao atendidos; clicavel para /feedbacks (só admin ve) | Media | Concluído (v1.87.0) |
| Feedback: atalho e link no menu Sistema | Link "Feedbacks" na guia Sistema do menu + atalho personalizavel no dashboard | Baixa | Concluído (v1.87.0) |

## Correções (nov/2026 — v1.86.1)

| Item | Status |
|---|---|
| Listas de presença NR-01 e FDS: PDF na horizontal (paisagem), ocupando a folha inteira | Concluído (v1.86.1) |
| Listas de presença: garantia contra corte do conteúdo programático (NR-06 e demais) — altura de linha ajustada automaticamente | Concluído (v1.86.1) |

## Correções (nov/2026 — v1.86.2)

| Item | Status |
|---|---|
| Listas de presença: nomes/funções longos cortados na lateral — wrap ativado nos participantes + altura das linhas calculada + 1 página por folha | Concluído (v1.86.2) |

## Modelos disponíveis

NRs 01, 05, 06, 09, 10, 11, 12, 17, 18, 23 (Brigadista), 26, 33, 34, 35
+ FDS, PTA, Motoserra, Munck, Ponte Rolante, Direção Defensiva, CIPA.

## Histórico arquivado (resumo; detalhes em `CHANGELOG.md`)

- **2ª leva (out/2026, v1.73.1):** busca em tempo real global; área de Atalhos no dashboard.
- **3ª leva (out/2026, v1.74.0 → v1.76.0):** novos atalhos; NR-06/NR-18 carga e validade; layout e ações da ficha de veículo com popups; lista assinada em /presencas; crachá rápido na ficha; XLSX de /vencimentos formatado; filtros de certificados na ficha; carga/validade de templates persistentes; arquivar documento com popup; novos cards do dashboard (ASOs, bloqueados, presenças, cadastro básico).
- **Melhorias v1.76.1/v1.76.2:** ações da ficha de veículo em linha; pisca vermelho; paginação /frota/vencimentos; arquivados fora dos vencimentos; cards zerados sempre visíveis.
- **4ª leva (out/2026, v1.77.0):** permissoes por setor para statcards/atalhos; arquivar listas/certificados/EPIs; coluna "Nível de cadastro" com filtros.
- **5ª leva (out/2026, v1.78.0 → v1.86.0):** busca ASO e tipo padrao; filtros de cadastro; duplicidades com mescla (/funcionarios/duplicidades); foco das barras de pesquisa; filtros e paginacao de ASOs; consistencia de contagens de vencimentos; cards de vencidos/ASOs/cadastro incompleto/saidas; atalho de bloqueio; multiplos locais de backup; setor Seguranca arquiva funcionarios; cintos/talabartes (v1.83.0/v1.85.0); frota: export por mes, mes automatico, grafico com linha e tooltip por veiculo; certificados com data futura; lista de presenca avulsa; template FDS; NR-12 verificado.
- **Correções v1.80.1:** grupo de duplicidades apos mescla; card 30 dias alinhado a /vencimentos; filtros de /funcionarios em linha; botao Arquivar de /presencas em vermelho.
- **Alterações v1.80.2:** anexo assinado do certificado ate 30 MB.
- **Novidades v1.81.x:** aviso e-mail mensal de ASOs; botao "Incompletos (Excel)"; aviso de abastecimento antigo; otimizacao do dashboard; arquivados fora dos vencimentos.

## Histórico resumido (entregas)

- **Fase 1 — NRs e templates:** implementada.
- **Fase 2 (2.1–2.41):** implementada, incluindo Termo de Compromisso.
- **Fase UX / Permissões / Romaneios (v1.54.0 → v1.70.0):** implementada.
- **Itens out/2026 (v1.71.0 → v1.73.0):** busca sem acentos + barras maiores + correção "?" no menu Frota (v1.71.0); cards do dashboard por permissão/setor, card de certificados sem assinatura, aniversariantes recolhíveis e painel de statcards com borda (v1.72.0); regra de 1 certificado por NR dentro da validade com confirmação (v1.73.0).
- **Superados pelo Portal Web (não serão desenvolvidos):** Multiusuário/servidor (ver `docs/MULTIUSUARIO.md`); Interface GPU (ver `docs/UI_GPU.md`).

---

## Referências

- [`README.md`](README.md) — visão geral do projeto
- [`CHANGELOG.md`](CHANGELOG.md) — histórico detalhado de versões
- `templates/` — modelos de certificados
