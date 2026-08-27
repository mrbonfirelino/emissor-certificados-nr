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

### 2.3 Tela de Funcionarios Cadastrados

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Mostrar Funcao | Exibir funcao ao lado do nome do funcionario | Alta | Pendente |
| Tabela Estilizada | Organizar lista como tabela Excel com linhas de separacao | Media | Pendente |
| Busca por Filtros | Filtros por funcao, nome, CPF, etc. | Media | Pendente |

---

## Cronograma Estimado

### Sprint 1 (1-2 semanas)
- [ ] Criar templates: FDS, NR-33, NR-34, NR-23
- [ ] Adicionar campo "Funcao" ao model Employee

### Sprint 2 (2-3 semanas)
- [ ] Ajustar import Excel para incluir funcao automaticamente
- [ ] Melhorar tela de funcionarios (tabela, filtros, funcao)

### Sprint 3 (3-4 semanas)
- [ ] Testar viabilidade de drive mapeado em rede
- [ ] Implementar backup duplo (programa + Documents)

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

### Para drive mapeado:
- Verificar caminhos relativos no config.py
- Testar acesso ao banco SQLite em rede
- Verificar performance do backup

### Para backup duplo:
- Configurar segundo destino no backup_manager.py
- Criar pasta automaticamente em C:\Users\{usuario}\Documents
- Sincronizar ambos os backups

---

## Referencias
- README.md: Visao geral do projeto
- CHANGELOG.md: Historico de versoes
- templates/: Templates de NRs existentes
