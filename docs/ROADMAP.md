# Roadmap - NormaTech

## Status do Projeto
- Versao atual: 1.6.0
- NRs disponiveis: 17 (01, 05, 06, 09, 10, 11, 12, 17, 18, 26, 33, 34, 35 + FDS, BRIGADISTA-NR23, PTA, MOTOSERRA, MUNCK, PONTE-ROLANTE, DIR-DEFENSIVA, CIPAA)

---

## FASE 1: Novas NRs/Itens (CONCLUÍDA)

### Templates a Adicionar:

| NR | Nome | Prioridade | Status |
|----|------|------------|--------|
| FDS | Ficha de Dados de Seguranca | Alta | Concluído |
| NR-33 | Espacos Confinados | Alta | Concluído |
| NR-34 | Manutencao Industrial | Alta | Concluído |
| NR-23 | Brigadista (Brigada de Incendio) | Alta | Concluído |

### Itens Especiais:

| Item | Nome | Prioridade | Status |
|------|------|------------|--------|
| PTA | Programa de Treinamento e Aprendizagem | Media | Concluído |
| MOTOSERRA | Operacao de Motoserra | Media | Concluído |
| MUNCK | Operacao de Munck | Media | Concluído |
| PONTE ROLANTE | Operacao de Ponte Rolante | Media | Concluído |
| DIRECAO DEFENSIVA | Direcao Defensiva | Media | Concluído |
| CIPAA | CIPA | Media | Concluído |

---

## FASE 2: Funcionalidades Novas

### 2.1 Infraestrutura

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Drive Mapeado | Verificar viabilidade de rodar em rede | Alta | Pendente (checklist em docs/REDE.md — aguarda validacao no ambiente real) |
| Backup Duplo | Backup na pasta do programa + pasta Documents do PC | Media | Concluído |
| Backup Periódico | Backup automático a cada 15 minutos (intervalo configurável) enquanto o programa estiver em execução | Alta | Concluído |

### 2.2 Cadastro de Funcionarios (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Dropdown Funcao | Adicionar campo "Funcao" no cadastro de funcionarios | Alta | Concluído |
| Import com Funcao | Importacao Excel inclui funcao automaticamente (se nao existir, cadastra) | Alta | Concluído |
| Foto 3x4 | Incluir campo para upload de foto 3x4 no cadastro | Alta | Concluído |
| Armazenamento Foto | Salvar foto no banco de dados (BLOB) | Alta | Concluído |
| Remover campo Matrícula | Matrícula é exclusiva do cartão de bloqueio da ArcelorMittal; só deve ser preenchida na hora da emissão, pois o número tem validade | Alta | Concluído |

### 2.3 Tela de Funcionarios Cadastrados (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Mostrar Funcao | Exibir funcao ao lado do nome do funcionario | Alta | Concluído |
| Tabela Estilizada | Organizar lista como tabela Excel com linhas de separacao | Media | Concluído |
| Busca por Filtros | Filtros por funcao, nome, CPF, etc. | Media | Concluído |

### 2.4 Cartoes de Bloqueio (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Padrão ALTEC | Cartão de bloqueio no padrão ALTEC (JSON ReportLab) | Alta | Concluído |
| Padrão Cliente | Cartão no padrão cliente (templates PPTX: ARCELORMITTAL, CSN, LOTOTO + JSON configurável) | Alta | Concluído |
| Dados do Cartão | Campos: Nome, CPF, Funcao, Telefone, Foto 3x4 (+ Setor, Empresa, Papel, Matrícula via PPTX) | Alta | Concluído |
| Gerador de PDF | Gerar cartões em PDF (tamanho cartão, qualidade impressão) | Alta | Concluído |

### 2.5 Emissão em Massa de Cartões (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Seleção de Funcionários | Interface para selecionar funcionários cadastrados e gerar cartões | Alta | Concluído |
| Importação de Excel | Importar lista de bloqueios de planilha (.xlsx) para gerar em lote | Alta | Concluído |
| Preview em Massa | Visualizar cartões antes de gerar/ imprimir | Media | Concluído |
| Impressão Direta | Opção de enviar diretamente para impressora | Media | Concluído |

### 2.6 Diferenças entre Padrões

**Padrão ALTEC:**
- Layout com cores e identidade visual ALTEC
- SEMPRE incluir logo ALTEC no cartão
- Formato padrão da empresa

**Padrão Cliente:**
- Layout personalizável (cores, logo do cliente)
- SEMPRE incluir logo ALTEC + logo do cliente no cartão
- Configuração por empresa cliente
- Possibilidade de múltiplos layouts

### 2.7 Templates PPTX para Cartões (CONCLUÍDO)

Sistema alternativo de cartões usando arquivos PowerPoint como template,
integrado de forma transparente ao sistema JSON existente (mesmo dropdown).

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Serviço PPTX | `src/core/pptx_card_service.py` (python-pptx + comtypes + PyMuPDF) | Alta | Concluído |
| Integração | Dispatch automático JSON/PPTX em `blocking_card_service.py` | Alta | Concluído |
| Placeholders dinâmicos | Tokens {{NOME}}, {{FUNCAO}}, {{TELEFONE}}, {{CPF}}, {{MATRICULA}}, {{SETOR}}, {{EMPRESA}}, {{PAPEL}} — só usa os que existem no template | Alta | Concluído |
| Campo Matrícula | Novo campo no cadastro (banco + UI + import/export Excel), fallback CPF | Alta | Concluído |
| Líder/Liderado | Popup na geração com switch por funcionário (padrão Liderado, não persiste) | Alta | Concluído |
| Setor global | Informado no popup de geração, vale para o lote | Alta | Concluído |
| Templates preparados | ARCELORMITTAL, ALTEC-PEQUENO (com fotos 3x4), CSN, LOTOTO | Alta | Concluído |
| 1 cartão por página | Recorte via PyMuPDF (opção na tela de emissão) | Media | Concluído |
| Ferramenta de preparação | `tools/prepare_pptx_templates.py` (regenera templates dos originais) | Media | Concluído |
| Documentação | `docs/PPTX_TEMPLATES.md` | Media | Concluído |
| Testes | `test_pptx_cards.py` (unitários + E2E com PowerPoint) | Media | Concluído |
| Quebra de linha | word_wrap + auto-shrink vertical (todos PPTX); modo clip no LOTOTO (corta no limite) | Alta | Concluído |
| Edição por emissão | Revisão da Emissão: editar nome/função/telefone/foto só na hora (cópias, sem tocar o banco) + "Voltar e Editar" no Preview | Alta | Concluído |
| 8 cartões ALTEC-PEQUENO | Slot 8 validado (shapes CARD8_*, zonas e preparação atualizados) | Alta | Concluído |

Requisitos: Microsoft PowerPoint instalado na máquina (conversão via COM).

> **Nota:** o campo Matrícula no cadastro de funcionários **foi removido** (ver item 2.2).
> Ele é exclusivo do cartão de bloqueio da ArcelorMittal e o número tem validade —
> o preenchimento é feito **somente na hora da emissão** (popup de geração, obrigatório).

---

### 2.8 Certificados Assinados (Escaneados) (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Anexar Scan | Anexar imagem (JPG/PNG) ou PDF do certificado assinado (escaneado) a um certificado emitido, pela tela de histórico | Alta | Concluído |
| Armazenamento no DB | Salvar o documento assinado como BLOB no banco de dados (vinculado ao registro da tabela `certificates`), incluído nos backups | Alta | Concluído |
| Download do Assinado | Botão "Baixar assinado" no histórico para exportar o documento salvo no banco como imagem ou PDF | Alta | Concluído |
| Substituir/Remover | Permitir substituir ou remover o scan anexado | Media | Concluído |
| Indicador Visual | Marcar na lista de histórico quais certificados possuem documento assinado anexado | Media | Concluído |

### 2.9 Digitalização e Inserção Direta no Histórico (v1.5.0)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Upload de Scan | Digitalizar (escanear ou fotografar) um certificado assinado e anexar direto a partir de uma opção acessível | Alta | Concluído |
| Preview Antes de Inserir | Exibir preview da imagem/PDF digitalizado antes de confirmar a inserção no registro | Alta | Concluído |
| Inserção no Registro | Inserir o documento digitalizado vinculado ao registro correto no histórico (mesmo fluxo do item 2.8, mas com tela dedicada de digitalização) | Alta | Concluído |
| Crop/Ajuste | Opção de recortar, girar ou ajustar brilho/contraste antes de inserir | Media | Concluído |
| Multi-página | Frente/verso: páginas digitalizadas combinadas em um único PDF anexado | Alta | Concluído (v1.5.0) |
| Histórico de Digitalizações | Permitir visualizar digitalizações anteriores de um certificado (múltiplos scans) | Baixa | Pendente (exige mudança de esquema) |

### 2.10 Notificações Windows (Toast) (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Biblioteca Toast | Notificações nativas do Windows 10/11 via `windows-toasts` (WinRT) | Media | Concluído |
| Eventos Notificados | Emissão de certificados/cartões concluída, backup concluído, erros de importação/exportação | Media | Concluído |
| Fallback | Se toast indisponível, manter comportamento atual (messagebox/status) | Media | Concluído |
| Configuração | Opção de ativar/desativar notificações na página de configurações | Baixa | Concluído |

---

## Cronograma Estimado

### Sprint 1 (1-2 semanas)
- [x] Criar templates: FDS, NR-33, NR-34, NR-23

### Sprint 2 (2-3 semanas)
- [x] Ajustar import Excel para incluir funcao automaticamente
- [x] Melhorar tela de funcionarios (tabela, filtros, funcao)
- [x] Adicionar campo Foto 3x4 no cadastro de funcionarios
- [x] Implementar upload e armazenamento de fotos no banco de dados

### Sprint 3 (3-4 semanas)
- [ ] Testar viabilidade de drive mapeado em rede (ver docs/REDE.md)
- [x] Implementar backup duplo (programa + Documents)
- [x] Implementar backup periódico automático (padrão 15 min, configurável) durante a execução

### Sprint 4 (2-3 semanas)
- [x] Criar modelo de cartão de bloqueio padrão ALTEC
- [x] Criar modelo de cartão de bloqueio padrão Cliente
- [x] Implementar campos: Nome, CPF, Funcao, Telefone, Foto 3x4, Matricula
- [x] Gerador de PDF para cartões
- [x] Templates PPTX (ARCELORMITTAL, ALTEC-PEQUENO, CSN, LOTOTO) com placeholders dinâmicos
- [x] Popup de contexto (Setor + Líder/Liderado) na emissão

### Sprint 5 (2-3 semanas)
- [x] Criar menu de emissão em massa
- [x] Implementar seleção de funcionários para emissão em massa
- [x] Implementar importação de Excel para bloqueios
- [x] Preview e impressão de cartões em lote

### Sprint 6 (2-3 semanas)
- [x] Remover campo Matrícula do cadastro de funcionários (banco + UI + import/export)
- [x] Tornar matrícula obrigatória na emissão, preenchida somente no popup (sem fallback CPF)
- [x] Anexar certificado assinado (scan imagem/PDF) ao registro do certificado no banco
- [x] Botão para baixar o documento assinado do banco (foto ou PDF) na tela de histórico
- [x] Implementar notificações Windows (Toast) nos eventos principais
- [x] Página de configurações acessível na sidebar (seções Preferências e Backups)

---

## Notas Tecnicas

### Para adicionar nova NR:
1. Criar arquivo `templates/NR-XX.template.json`
2. Seguir estrutura dos templates existentes
3. Reiniciar programa (detecta automaticamente)

### Para campo "Funcao":
- Modificar `src/core/models.py` (Employee model)
- Modificar `src/core/employee_repo.py` (CRUD)
- Modificar `src/ui/pages/employees.py` (UI)
- Adicionar dropdown no formulario

### Para campo Foto 3x4:
- Modificar `src/core/models.py` (Employee model) - adicionar campo foto (BLOB ou caminho)
- Modificar `src/core/employee_repo.py` (CRUD) - incluir upload/salvamento de foto
- Modificar `src/ui/pages/employees.py` (UI) - adicionar botao de upload e preview da foto
- Opcao 1: Salvar foto como BLOB no SQLite (compacto, backup automatico)
- Opcao 2: Salvar foto em pasta `data/photos/` e guardar caminho no DB (melhor performance)
- Formatos aceitos: JPG, PNG (redimensionar automaticamente para 3x4)
- Validar tamanho maximo da imagem (ex: 2MB)

### Para certificados assinados (escaneados):
- Adicionar colunas BLOB na tabela `certificates` (`src/core/history_repo.py`): `signed_doc BLOB` + `signed_doc_tipo TEXT` (pdf/jpg/png)
- Migração automática do banco (ALTER TABLE), mesmo padrão usado para a coluna matricula
- UI no histórico (`src/ui/pages/history.py`): botão "Anexar assinado" (upload) e "Baixar assinado" (salvar como imagem ou PDF)
- Formatos aceitos: PDF, JPG, PNG — validar tamanho maximo (ex: 10MB)
- Indicador na lista de histórico para certificados com documento assinado anexado
- Documentos ficam dentro do DB, portanto já incluídos nos backups automáticos

### Para drive mapeado:
- Verificar caminhos relativos no config.py
- Testar acesso ao banco SQLite em rede
- Verificar performance do backup

### Para backup duplo:
- Configurar segundo destino no backup_manager.py
- Criar pasta automaticamente em C:\Users\{usuario}\Documents
- Sincronizar ambos os backups

### Para backup periódico (15 min):
- Estender `src/core/backup_manager.py`: hoje o agendador é apenas semanal (`_start_auto_backup`)
- Timer configurável nas configurações (padrão: 15 minutos enquanto o app estiver aberto)
- Executar backup em thread separada para não travar a UI
- Atenção ao WAL: copiar o DB com `sqlite3` backup API ou checkpoint antes de compactar
- Criar retenção rotativa própria (ex: manter últimos N backups periódicos do dia) — a limpeza atual de 12 backups apagaria tudo em ~3 horas no ritmo de 15 min
- Considerar backup periódico incremental/leve vs. backup semanal completo

### Para notificações Windows (Toast):
- Biblioteca: `windows-toasts` (WinRT, nativo Win10/11); alternativa: `plyer`
- Criar helper central (ex: `src/utils/notifications.py`) com fallback silencioso/messagebox
- Eventos: emissão concluída (especialmente em massa), backup concluído, erros de importação/exportação
- Opção de ativar/desativar na página de configurações (`src/ui/pages/config.py`)

### Para remoção do campo Matrícula:
- Motivo: matrícula é exclusiva do cartão de bloqueio da ArcelorMittal e o número tem validade — não deve ficar no cadastro
- Remover de: `src/core/models.py` (Employee), `src/core/employee_repo.py` (create/update/busca/`update_matricula`), `src/ui/pages/employees.py` (formulário, coluna da tabela e texto de ajuda do import)
- Import/Export Excel: remover coluna E (Matrícula) do `excel_importer.py` e coluna do `excel_exporter.py`
- Popup de emissão (`src/ui/components/generation_options_dialog.py`):
  - Campo inicia **vazio** (sem pré-preenchimento do cadastro)
  - **Sem fallback de CPF** — remover fallback em `src/core/pptx_card_service.py`
  - Matrícula **obrigatória**: bloquear emissão se ficar vazia
  - Remover checkbox "Salvar matrículas no cadastro" e o salvamento em `blocking_cards.py`
- Banco: manter coluna `matricula` no SQLite (apenas ignorada — zero risco de migração)
- Atualizar `test_pptx_cards.py` (testes de fallback CPF saem; novo teste de matrícula obrigatória)
- Docs: atualizar `docs/PPTX_TEMPLATES.md` (fallback do token `{{MATRICULA}}`) e `CHANGELOG.md`

### Para cartoes de bloqueio:
- Criar pasta `templates/` com layouts de cartão (padrão ALTEC e padrão cliente)
- Adicionar campo "Foto 3x4" no model Employee (armazenar caminho da foto)
- Criar `src/core/blocking_card_service.py` para geracao de PDF
- Criar `src/ui/pages/blocking_cards.py` para tela de emissao
- Formato do cartao: tamanho cartao (8.5cm x 5.5cm ou similar)
- Suporte a impressao em lote (varias paginas A4 com multiplos cartoes)
- **SEMPRE** incluir logo ALTEC em todos os cartoes (padrao ALTEC e cliente)
- No padrao cliente: incluir logo ALTEC + logo do cliente (lado a lado ou posicao definida)
- Configurar posicao e tamanho das logos no layout do cartao

### Para templates PPTX (ver docs/PPTX_TEMPLATES.md):
- Templates em `templates/cards/pptx/` (`.pptx` + `.card.json` companheiro)
- Shapes nomeados `CARD{slot}_{CAMPO}`; foto = `CARD{slot}_FOTO`
- Tokens `{{NOME}} {{FUNCAO}} {{TELEFONE}} {{CPF}} {{MATRICULA}} {{SETOR}} {{EMPRESA}} {{PAPEL}}`
- Conversao PDF exige Microsoft PowerPoint instalado (COM/comtypes)
- Regenerar templates dos originais: `python tools/prepare_pptx_templates.py`
- Testes: `python test_pptx_cards.py` (unit + E2E)

### Para emissao em massa:
- Criar `src/ui/pages/bulk_blocking.py` para tela de emissao em massa
- Implementar selecao multipla de funcionarios (checkboxes)
- Implementar importador de Excel para bloqueios (similar ao batch_importer.py)
- Gerar PDF com multiplos cartoes por pagina (otimizar impressao)
- Adicionar preview antes de gerar/imprimir

---

## Referencias
- README.md: Visao geral do projeto
- CHANGELOG.md: Historico de versoes
- templates/: Templates de NRs existentes
