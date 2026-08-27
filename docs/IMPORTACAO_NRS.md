# Guia de Importacao - Codigos NR

## Como Usar

1. Crie uma planilha Excel (`.xlsx`)
2. Preencha as colunas **A**, **B** e **C** (cabecalho opcional, sera ignorado)
3. No sistema, va em **Importar em Lote**
4. Selecione a planilha e clique em **Gerar Todos**

---

## Formato da Planilha

| Coluna A (Nome) | Coluna B (NR) | Coluna C (Data) |
|-----------------|---------------|------------------|
| Joao da Silva | NR-12 | 15/03/2026 |
| Maria Santos | FDS | 20/01/2026 |

---

## Codigos Validos

### Normas Regulamentadoras (NR)

| Codigo | Nome Completo |
|--------|---------------|
| NR-01 | NR-01 - Disposicoes Gerais |
| NR-06 | NR-06 - Equipamentos de Protecao Individual (EPI) |
| NR-10 | NR-10 - Seguranca em Instalacoes e Servicos em Eletricidade |
| NR-12 | NR-12 - Seguranca no Trabalho em Maquinas e Equipamentos |
| NR-18 | NR-18 - Controle das Condicoes de Trabalho na Industria da Construcao |
| NR-26 | NR-26 - Sinalizacao de Seguranca |
| NR-33 | NR-33 - Seguranca e Saude nos Trabalhos em Altura |
| NR-34 | NR-34 - Condicoes e Meio Ambiente do Trabalho na Industria da Construcao e Reparacao Naval |
| NR-35 | NR-35 - Trabalho em Altura |

### Cursos e Treinamentos

| Codigo | Nome Completo |
|--------|---------------|
| FDS | Formacao de Socorrista |
| BRIGADISTA-NR23 | Brigada de Incendio (NR-23) |
| CIPAA | Comissao Interna de Prevencao de Acidentes de Abrangencia |
| DIR-DEFENSIVA | Direcao Defensiva |
| MOTOSERRA | Operacao de Motoserra |
| MUNCK | Operacao de Munck |
| PONTE-ROLANTE | Operacao de Ponte Rolante |
| PTA | Prevencao de Tumores Ocupacionais |

---

## Erros Comuns

| Erro | Solucao |
|------|---------|
| `NR 'nr12' nao encontrado` | Use maiusculo e hifens: `NR-12` |
| `NR 'NR12' nao encontrado` | Adicione o hifem: `NR-12` |
| `NR 'NR 12' nao encontrado` | Sem espaco: `NR-12` |
| `NR vazio` | Preencha a coluna B com o codigo da NR |
| `data invalida` | Use o formato dd/mm/aaaa (ex: 15/03/2026) |
| `nome vazio` | Preencha a coluna A com o nome completo |

---

## Exemplo de Planilha Completa

| A | B | C |
|---|---|---|
| Joao da Silva | NR-12 | 15/03/2026 |
| Joao da Silva | FDS | 15/03/2026 |
| Maria Santos | NR-35 | 20/01/2026 |
| Pedro Oliveira | BRIGADISTA-NR23 | 10/02/2026 |
| Ana Costa | PTA | 05/12/2025 |
