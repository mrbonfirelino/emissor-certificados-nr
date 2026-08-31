# Changelog

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