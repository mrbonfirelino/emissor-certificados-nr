# Changelog

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