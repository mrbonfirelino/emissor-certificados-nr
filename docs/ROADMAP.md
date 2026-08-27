# Roadmap - Emissor de Certificados NR

## Status do Projeto
- Versao atual: 1.0.0
- NRs disponiveis: 10 (01, 05, 06, 09, 10, 11, 12, 17, 18, 35)

---

## FASE 1: Novas NRs/Itens (Prioridade Alta)

### Templates a Adicionar:

| NR | Nome | Prioridade | Status |
|----|------|------------|--------|
| FDS | Ficha de Dados de Seguranca | Alta | Pendente |
| NR-33 | Espacos Confinados | Alta | Pendente |
| NR-34 | Manutencao Industrial | Alta | Pendente |
| NR-23 | Brigadista (Brigada de Incendio) | Alta | Pendente |

### Itens Especiais:

| Item | Nome | Prioridade | Status |
|------|------|------------|--------|
| PTA | Programa de Treinamento e Aprendizagem | Media | Pendente |
| MOTOSERRA | Operacao de Motoserra | Media | Pendente |
| MUNCK | Operacao de Munck | Media | Pendente |
| PONTE ROLANTE | Operacao de Ponte Rolante | Media | Pendente |
| DIRECAO DEFENSIVA | Direcao Defensiva | Media | Pendente |
| CIPAA | CIPA | Media | Pendente |

---

## FASE 2: Funcionalidades Novas

### 2.1 Infraestrutura

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Drive Mapeado | Verificar viabilidade de rodar em rede | Alta | Pendente |
| Backup Duplo | Backup na pasta do programa + pasta Documents do PC do solicitante | Media | Pendente |

### 2.2 Cadastro de Funcionarios

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Dropdown Funcao | Adicionar campo "Funcao" no cadastro de funcionarios | Alta | Pendente |
| Import com Funcao | Importacao Excel inclui funcao automaticamente (se nao existir, cadastra) | Alta | Pendente |
| Foto 3x4 | Incluir campo para upload de foto 3x4 no cadastro | Alta | Pendente |
| Armazenamento Foto | Salvar foto no banco de dados (BLOB) ou pasta local com referencia no DB | Alta | Pendente |

### 2.3 Tela de Funcionarios Cadastrados

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Mostrar Funcao | Exibir funcao ao lado do nome do funcionario | Alta | Pendente |
| Tabela Estilizada | Organizar lista como tabela Excel com linhas de separacao | Media | Pendente |
| Busca por Filtros | Filtros por funcao, nome, CPF, etc. | Media | Pendente |

### 2.4 Cartoes de Bloqueio

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Padrão ALTEC | Criar cartão de bloqueio no padrão ALTEC (layout próprio, cores) | Alta | Pendente |
| Padrão Cliente | Criar cartão de bloqueio no padrão cliente (layout personalizável) | Alta | Pendente |
| Dados do Cartão | Campos: Nome, CPF, Funcao, Telefone, Foto 3x4 | Alta | Pendente |
| Gerador de PDF | Gerar cartões em PDF (tamanho cartão, qualidade impressão) | Alta | Pendente |

### 2.5 Emissão em Massa de Cartões

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Seleção de Funcionários | Interface para selecionar funcionários cadastrados e gerar cartões | Alta | Pendente |
| Importação de Excel | Importar lista de bloqueios de planilha (.xlsx) para gerar em lote | Alta | Pendente |
| Preview em Massa | Visualizar cartões antes de gerar/ imprimir | Media | Pendente |
| Impressão Direta | Opção de enviar diretamente para impressora | Media | Pendente |

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

---

## Cronograma Estimado

### Sprint 1 (1-2 semanas)
- [ ] Criar templates: FDS, NR-33, NR-34, NR-23
- [ ] Adicionar campo "Funcao" ao model Employee

### Sprint 2 (2-3 semanas)
- [ ] Ajustar import Excel para incluir funcao automaticamente
- [ ] Melhorar tela de funcionarios (tabela, filtros, funcao)
- [ ] Adicionar campo Foto 3x4 no cadastro de funcionarios
- [ ] Implementar upload e armazenamento de fotos no banco de dados

### Sprint 3 (3-4 semanas)
- [ ] Testar viabilidade de drive mapeado em rede
- [ ] Implementar backup duplo (programa + Documents)

### Sprint 4 (2-3 semanas)
- [ ] Criar modelo de cartão de bloqueio padrão ALTEC
- [ ] Criar modelo de cartão de bloqueio padrão Cliente
- [ ] Implementar campos: Nome, CPF, Funcao, Telefone, Foto 3x4
- [ ] Gerador de PDF para cartões

### Sprint 5 (2-3 semanas)
- [ ] Criar menu de emissão em massa
- [ ] Implementar seleção de funcionários para emissão em massa
- [ ] Implementar importação de Excel para bloqueios
- [ ] Preview e impressão de cartões em lote

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

### Para drive mapeado:
- Verificar caminhos relativos no config.py
- Testar acesso ao banco SQLite em rede
- Verificar performance do backup

### Para backup duplo:
- Configurar segundo destino no backup_manager.py
- Criar pasta automaticamente em C:\Users\{usuario}\Documents
- Sincronizar ambos os backups

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
