# Changelog

## [1.5.1] - 2026-09-03

### Corrigido
- **Autocomplete de funcionários não fecha mais sozinho**: removidos os
  timers de fechamento automático (FocusOut 250ms e watchdog 300ms) que
  faziam a lista sumir durante a emissão; agora a lista fecha apenas por
  ação explícita — clique fora, Esc, seleção de funcionário ou minimizar —
  com um fallback de segurança de 60 segundos
- **Número do certificado em todas as folhas**: "CERT-XXXX" agora é
  impresso no canto inferior direito de todas as páginas do PDF (antes
  só na primeira); assinaturas continuam apenas na página 1

### Adicionado
- Teste `test_cert_number.py`: valida presença do número em todas as
  páginas de um certificado multi-página

## [1.5.0] - 2026-09-01

### Adicionado
- **Digitalização direta no app** (roadmap 2.9): botão "Digitalizar" por
  certificado no histórico abre tela dedicada com:
  - **Escanear no scanner** via WIA (comtypes — sem dependências novas;
    cancelamento e ausência de scanner tratados com mensagem clara + error.log)
  - **Escolher arquivo / foto** do celular (JPG/PNG/PDF)
  - **Multi-página**: loop de páginas combinadas em **um único PDF** anexado
  - **Ajustes de imagem**: girar ±90°, brilho, contraste e **recorte por
    arraste** no preview (com desfazer)
  - Preview antes de confirmar; inserção pelo mesmo fluxo do item 2.8
    (substitui scan anterior)
- **Novo ícone do programa** ("ICONE RECORTADO"): `assets/logo.ico` convertido
  para ICO verdadeiro multi-resolução (16–256px) — o anterior era um JPEG
  renomeado e não funcionava; `setup_assets.py` regenera a partir da imagem

### Pendente (roadmap 2.9)
- Histórico de digitalizações (múltiplos scans por certificado) — exige
  mudança de esquema do banco

## [1.4.0] - 2026-09-01

### Corrigido
- **Erro ao abrir Certificados** ("bind_all is not allowed"): o clique-global do
  autocomplete usava `bind_all` dos widgets CTk (proibido pelo CustomTkinter) —
  trocado por binding direto no Tcl com `%W`, sem o guard e sem colisões

### Adicionado
- **Log de erros central** (`data/error.log`): captura exceções de callbacks do
  tkinter e de threads de trabalho (antes invisíveis no exe), com contexto,
  traceback e truncamento automático (1MB → últimos 256KB)
- **Toast de vencimentos ao abrir**: certificados que vencem nos próximos 7
  dias (contagem na notificação; respeita o toggle de notificações)
- **Ações nos cards de Vencimentos**: "Emitir" abre Certificados com o
  funcionário pré-selecionado; "Histórico" abre o Histórico com a busca
  preenchida (clique nos botões não expande/colapsa o card)
- **Importar fotos em massa** (aba Funcionários): escolhe uma pasta, casa por
  CPF (11 dígitos no nome do arquivo) ou nome exato (ignora acentos/caixa) e
  mostra janela de conferência com miniatura, status adicionar/substituir e
  checkboxes antes de aplicar (corte 3x4 automático)
- **Backup em rede (drive mapeado)**: destino configurável (padrão
  `Z:\SEGURANÇA\NORMATECH-BACKUP`), ativo por padrão e tolerante — drive fora
  do ar pula com aviso no `backup.log` sem interromper o backup local
- **Documentos de planejamento**: `docs/INSTALADOR.md` (script Inno Setup
  completo pronto para uso) e `docs/ASSINATURA_DIGITAL.md` (PAdES/ICP-Brasil,
  opções, arquitetura e fases)

### Alterado
- **Restauração de backup reinicia o app automaticamente** (`os.execv`) em vez
  de apenas fechar
- Configurações ganham "Backup em rede" (toggle + caminho editável)

## [1.3.3] - 2026-09-01

### Corrigido
- **Autocomplete de funcionários**: a lista agora permanece aberta até o
  usuário tirar o foco ou clicar fora (antes o watchdog fechava cedo demais);
  removida a checagem de janela ativa que causava fechamento precoce; novo
  gatilho global de clique-fora
- **Filtro de vencimentos (7/15/30/90 dias)**: certificados já vencidos
  apareciam nos filtros de período futuro — agora cada filtro exige
  `0 ≤ dias ≤ limite` (vencidos só em "Vencidos"/"Todos"); lógica extraída
  para `filter_certs` testável

### Alterado
- **Backup externo em dois destinos**: além do histórico local, cada backup é
  copiado para `Documentos\NormaTech-Backup` e `C:\NormaTech-Backup` (pastas
  criadas automaticamente; falha num destino não interrompe os outros e fica
  registrada no `data/backup.log`); retenção igual à local aplicada nos
  destinos; antiga `Documents\BackupsNormaTech` descontinuada

### Adicionado
- `docs/SUGESTOES.md`: lista priorizada de melhorias (rede, log de erros,
  toast de vencimentos, CI, instalador, validador de templates etc.)
- `test_vencimentos.py`: testes do filtro por período/NR/busca

## [1.3.2] - 2026-09-01

### Corrigido
- **Autocomplete de funcionários flutuante**: dropdown ganhava watchdog (250ms)
  que o fecha se o app minimizar, outro programa ficar em foco, ou mouse/foco
  saírem do campo; fecha imediato ao minimizar (`<Unmap>`) e acompanha a janela
  ao mover (`<Configure>`); seleção usa o cache da lista exibida (sem re-buscar)
- **Erro "bad stickiness value 'center'" ao anexar assinado**: badge "ASSINADO"
  usava `sticky="center"` (inválido no tkinter) — o anexo era salvo, mas o
  refresh da lista quebrava. Corrigido para centrar via grid padrão

### Alterado
- **Busca mais fluida (CPU fraca)**: as abas Funcionários, Histórico, Cartões e
  Vencimentos agora pesquisam somente no **Enter** ou no novo botão **Buscar**
  — fim do re-render por tecla digitada (autocomplete do certificado segue ao
  vivo, máximo 10 resultados)

### Adicionado
- **Busca na aba Funções**: barra com o mesmo padrão (Enter + Buscar + X),
  filtro client-side com edição/exclusão mapeadas para o índice original
- `docs/UI_GPU.md`: estudo de interface com aceleração GPU (Flet/Flutter,
  PySide6+QML, Dear PyGui, Tauri/Electron) para o cenário CPU fraca + GPU
  integrada, com recomendação e quick-wins

## [1.3.1] - 2026-09-01

### Corrigido
- **Matrícula pedida só onde precisa**: nova flag `matricula_obrigatoria` por
  template — LOTOTO não pede mais (campo some da revisão; espaço fica em branco);
  ArcelorMittal continua obrigatória
- **CSN dentro do quadrado**: ajuste por caixa com fonte uniforme reduzida
  (~9pt) e limite de linhas por campo (`wrap_max_lines`): nome em até 2 linhas,
  Dpto/Empresa em 1 — o excedente é apagado (ex.: "JUNIOR" do nome de teste)
- **Impressão (WinError 1155)**: cascata — verbo "print" do Windows → leitor
  padrão com flag de impressão (Acrobat `/p /h`, Foxit `/p`, SumatraPDF
  `-print-dialog`, abrindo já na janela de imprimir) → último recurso abre o PDF
- **Preview de certificado sem CPF**: mensagem amigável em vez do erro
  `CertificateData.funcionario_cpf` (a emissão já bloqueava; o preview não validava)
- **Backup automático em sessões curtas**: jobs com avaliação imediata no
  startup via metadados (`last_periodic_backup`) — intervalo de 15 min passa a
  valer também para quem abre o app por poucos minutos; semanal idem
- **Log de backups** (`data/backup.log`): falhas deixam de ser invisíveis no exe
- **Rodapé da tela de cartões**: ações divididas em 2 linhas — todos os botões
  visíveis sem esticar a janela
- **Tela de backups**: refresh ao abrir + auto-refresh a cada 30s; tipo
  "Periódico" reconhecido na lista

## [1.3.0] - 2026-09-01

### Adicionado
- **Revisão da Emissão** (substitui o popup simples): abre sempre antes de Gerar e
  Preview, com edição de **nome, função, telefone e foto** por funcionário
  (cópias transitórias — nada grava no cadastro), setor do lote, papel
  Líder/Liderado e matrícula obrigatória
- **"Voltar e Editar" no Preview**: reabre a revisão com as edições preservadas e
  regenera o preview até o resultado ficar bom
- **Quebra de linha** (word_wrap) para nome/função nos templates PPTX com
  auto-shrink vertical: reduz a fonte em passos de 0,5pt até as linhas caberem
- **Modo clip** (`text_fit: "clip"`, usado no LOTOTO): sem quebra e sem redução —
  o texto que passar do limite do campo é cortado

### Corrigido
- **ALTEC-PEQUENO com 8 cartões por folha**: shapes do 8º cartão (adicionados
  manualmente) renomeados para `CARD8_*` — antes os dois últimos cartões saíam
  com os dados do 7º funcionário
- Shape de função do cartão 3 do ALTEC-PEQUENO estava nomeado como NOME
  (funcionava por token, corrigido por clareza); tolerância da tabela de
  posições da preparação reduzida (0,45 → 0,35) para evitar esse tipo de troca
- Script de preparação agora reproduz o 8º cartão e a posição das fotos da
  linha 2 ajustada pelo usuário (regenerações futuras não desfazem a edição)

## [1.2.0] - 2026-08-31

### Adicionado
- **Certificados assinados (escaneados)**: anexar PDF/JPG/PNG (ate 10MB) ao certificado
  pelo historico (BLOB no banco, incluido nos backups), com indicador "ASSINADO",
  download, substituicao e remocao — migracao automatica do banco
- **Backup periodico**: a cada 15 min (configuravel em 1-720) enquanto o app esta aberto,
  com retencao propria (ultimos 32) separada dos 12 manuais/semanais
- **Backup duplo**: copia adicional automatica em `Documentos\BackupsCertificados` (toggle)
- **Notificacoes Windows (toast)**: emissao de cartoes, importacao em lote e backups
  concluidos — com fallback silencioso e toggle nas configuracoes
- **Pagina Configuracoes na navegacao**: estava inacessivel; agora entrada fixa na
  sidebar com secoes Preferencias (notificacoes) e Backups (intervalo + duplo)
- **Importacao de lista de bloqueios por Excel** (A=Nome, B=CPF): casa com o cadastro
  por CPF/nome e marca a selecao na tela de cartoes
- **Preview de cartoes antes de gerar**: abre o PDF temporario no visualizador interno
  com botoes Imprimir / Gerar PDF Definitivo
- **Impressao direta**: botao Imprimir (impressora padrao do Windows) no resultado e no preview
- `data/app_settings.json`: preferencias do app (notificacoes, intervalo de backup, backup duplo)
- Testes novos: `test_signed_docs.py`, `test_backup.py` (snapshot WAL, retencao, duplo)

### Alterado
- **Matricula removida do cadastro de funcionarios**: o numero tem validade e e exclusivo
  da emissao (ArcelorMittal/LOTOTO) — agora obrigatoria no popup de geracao, sem fallback
  de CPF e sem persistencia; coluna SQLite antiga e ignorada sem risco
- Backup (todos os tipos) usa **snapshot consistente via SQLite backup API** — corrige
  perda potencial de dados em WAL ao copiar o `.db` direto
- Restauracao de backup remove `-wal`/`-shm` residuais ao substituir o banco

### Documentacao
- `docs/REDE.md`: riscos e checklist de validacao do uso em drive mapeado
- ROADMAP atualizado (FASE 1 e seções concluidas identificadas na auditoria)

## [1.1.0] - 2026-08-31

### Adicionado
- **Cartões de bloqueio via template PPTX** (alternativo ao JSON, transparente no dropdown):
  - `src/core/pptx_card_service.py`: preenchimento por tokens, troca de foto (blob swap + crop 3x4),
    conversão PDF via PowerPoint COM (uma sessão por lote), merge e recorte "1 cartão por página" (PyMuPDF)
  - Tokens dinâmicos: `{{NOME}} {{FUNCAO}} {{TELEFONE}} {{CPF}} {{MATRICULA}} {{SETOR}} {{EMPRESA}} {{PAPEL}}`
    — somente os presentes no template são usados; validação de telefone/foto conforme o template
  - 4 templates preparados: ARCELORMITTAL (4/folha), ALTEC-PEQUENO (7/folha, com fotos 3x4 inseridas),
    CSN (4/folha 2x2), LOTOTO (1/folha ×2 slides)
  - `tools/prepare_pptx_templates.py`: regenera os templates a partir dos originais
  - Previews em `templates/cards/pptx/previews/`
- **Campo Matrícula** no cadastro de funcionários (migração automática do banco, formulário,
  tabela, import/export Excel coluna E); fallback: usa CPF quando vazia
- **Popup de contexto na emissão** (`GenerationOptionsDialog`): Setor do lote (global) e
  Líder/Liderado por funcionário (padrão Liderado, ações rápidas) — exibido só quando o
  template usa os campos
- Opção "1 cartão por página" na tela de cartões (templates PPTX)
- Testes: `test_pptx_cards.py` (unitários + E2E com PowerPoint)
- Docs: `docs/PPTX_TEMPLATES.md`; BUILD.md e ROADMAP.md atualizados

### Corrigido
- Linha duplicada na tabela de funcionários (nome renderizado 2x)

## [1.0.0] - 2026-08-25

### Adicionado
- Estrutura completa do projeto (src/, templates/, assets/, data/, build/)
- **Core**: Models Pydantic, Config, Template Loader, PDF Generator, Certificate Service
- **Banco de Dados**: SQLite com tabelas para empresa, funcionários, certificados, sequências, backup_meta
- **Repositórios**: EmployeeRepository (CRUD), HistoryRepository (histórico + numeração)
- **Backup Manager**: Backup automático semanal (silencioso), backup manual, restauração com senha Argon2
- **Interface CustomTkinter**:
  - Home: Seleção NR (grid), formulário dinâmico, autocomplete funcionários, preview, geração PDF
  - Funcionários: CRUD com busca, validação CPF, proteção contra exclusão com certificados
  - Histórico: Lista paginada, busca, abertura PDF/pasta
  - Configuração: Dados empresa + senha restauração
  - Backup: Lista backups, download, restauração com confirmação
- **Componentes**: NRSelector, EmployeeAutocomplete, DynamicForm, PDFPreview
- **Templates**: 10 NRs (01, 05, 06, 09, 10, 11, 12, 17, 18, 35) com campos específicos
- **Layout PDF**: A4 Landscape, logo centralizado, conteúdo 2 colunas, assinaturas duplas, numeração discreta
- **Assets**: Logo PNG → ICO (multi-resolução), fontes DejaVu (fallback Helvetica)
- **Build**: PyInstaller --onefile --windowed com ícone customizado
- **Documentação**: README.md completo, CHANGELOG.md

### Segurança
- Hash Argon2 para senha de restauração
- Validação CPF/CNPJ/Registro MTE
- Proteção contra exclusão de funcionários com certificados

### Preparado para Futuro
- SignatureProvider pattern (Local + ICP-Brasil placeholder)
- Campos de validade no modelo (para alertas futuros)
- Estrutura modular para novas funcionalidades