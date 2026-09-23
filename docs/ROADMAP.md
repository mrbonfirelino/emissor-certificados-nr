# Roadmap - NormaTech

## Status do Projeto
 - Versao atual: 1.45.0
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

### 2.10 Notificações Windows (Toast) (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Biblioteca Toast | Notificações nativas do Windows 10/11 via `windows-toasts` (WinRT) | Media | Concluído |
| Eventos Notificados | Emissão de certificados/cartões concluída, backup concluído, erros de importação/exportação | Media | Concluído |
| Fallback | Se toast indisponível, manter comportamento atual (messagebox/status) | Media | Concluído |
| Configuração | Opção de ativar/desativar notificações na página de configurações | Baixa | Concluído |

### 2.11 Experiência do Usuário (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Tema claro/escuro | Botão na sidebar + Ctrl+T, persistido (`data/appearance.json`), troca a quente | Media | Concluído (v1.7.0) |
| Atalhos de teclado | Ctrl+1..9 páginas, Ctrl+T tema, F5 atualizar | Media | Concluído (v1.7.0) |
| Painel de indicadores | Cards de vencimento/assinados + gráficos NR/mês na tela inicial, ocultável e persistido | Media | Concluído (v1.7.0) |
| Visualizador do log | Seção Diagnóstico na Config com `data/error.log` (Atualizar/Limpar/Abrir Pasta) | Media | Concluído (v1.7.0) |
| Filtro Assinado | Histórico: Todos/Sim/Não combinável com texto/NR/período + exportação | Media | Concluído (v1.7.0) |

### 2.12 Itens Planejados (docs dedicados)

| Item | Documento | Status |
|------|-----------|--------|
| CI GitHub Actions | docs/CI_GITHUB_ACTIONS.md | Concluído (v1.42.0) |
| Multiusuário/servidor | docs/MULTIUSUARIO.md | Superado pelo Portal Web (login, papéis e auditoria em produção) |
| Interface GPU | docs/UI_GPU.md | Superado pelo Portal Web (quick-wins aplicados; estudo arquivado) |

### 2.13 Documentos em Rede + Estrutura de Pastas (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Espelhamento em rede | Config: caminho de rede + Sincronizar Agora + sync no startup; toast/log em falha | Alta | Concluído (v1.8.0) |
| Estrutura por funcionário | `{Func}/Certificados/{NR}` com `00_Certificados_OLD` p/ vencidos, `Cartoes`, `Certificados Assinados`, `Outros`, `Cartoes_Gerais` | Alta | Concluído (v1.8.0) |
| Outros documentos | Botão Docs (BLOB no banco ≤10MB PDF/JPG/PNG) espelhado em `{Func}/Outros` | Alta | Concluído (v1.8.0) |
| Estrutura local nova | `data/certificados/{Func}/{NR}`, `data/cartoes/{Func}+LOTES`, `data/assinados/{Func}`; migração única idempotente de `CERTIFICADOS/` | Alta | Concluído (v1.8.0) |
| Contraste modo escuro | Paleta dark com textos/bordas mais claros | Media | Concluído (v1.8.0) |
| Tema na sidebar | Linha "Tema" acima de Config (fim da sobreposição com o hamburger) | Media | Concluído (v1.8.0) |

### 2.14 Expansão da Pasta Virtual do Funcionário (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Formatos Universais | Permitir envio de arquivos de **qualquer formato** (DOCX, XLSX, ZIP, MP4, etc.) para a pasta virtual do funcionário (além de PDF/JPG/PNG atuais) | Alta | Concluído (v1.9.0) |
| Limite de Tamanho | Definir novo limite máximo por arquivo (atual: 10MB para PDF/JPG/PNG) — sugerido: **50MB** para formatos universais | Alta | Concluído (v1.9.0, 50MB) |
| Tipos MIME | Validar tipos MIME no upload para prevenir arquivos maliciosos | Media | Concluído (v1.9.0, blocklist ext+MIME) |
| Armazenamento | Manter BLOB no banco + espelhamento em rede (`{Func}/Outros`) | Alta | Concluído (v1.8.0, inalterado) |

### 2.15 Data de Nascimento e Aniversariantes (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Campo Data Nascimento | Adicionar campo "Data de Nascimento" no card de cada funcionário (editável em caso de erro) | Alta | Concluído (v1.10.0) |
| Import com Data Nascimento | Permitir importar a data de nascimento no import de funcionários (Excel) | Alta | Concluído (v1.10.0) |
| Scrollbar Editar Funcionário | A janela "Editar Funcionário" não pode crescer mais — adicionar scrollbar | Media | Concluído (v1.10.0) |
| Data e Hora Atual (Home) | Na tela Home, exibir data e hora atual de forma bem visível | Media | Concluído (v1.10.0) |
| Aniversariantes do Mês | Na tela Home, adicionar campo "Aniversariantes deste mês" | Media | Concluído (v1.10.0) |
| Aniversariantes de Hoje | Na tela Home, adicionar campo "Aniversariantes de hoje" | Media | Concluído (v1.10.0) |
| Toast Aniversário | Exibir notificação (toast) quando alguém fizer aniversário no dia | Media | Concluído (v1.10.0) |

### 2.16 Campos SESMT e Ficha de EPI (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Campos do funcionário | Tipo Sanguíneo, Data de Admissão, Registro CTPS e CNH EAR no cadastro | Alta | Concluído (v1.11.0) |
| Import/Export novos campos | Colunas F-I no import Excel e novas colunas no export | Alta | Concluído (v1.11.0) |
| ASO — Página própria | Aba ASO na sidebar: emissão com número sequencial (ASO-XXXXXX), tipo (Admissional/Periódico/etc.), validade em meses, PDF com espaço reservado, anexo/digitalização do exame real | Alta | Concluído (v1.11.0) |
| ASO — Controle de vencimento | ASOs entram em Vencimentos (filtro ASO), dashboard e toast de vencimentos | Alta | Concluído (v1.11.0) |
| Ficha de EPI | Botão EPI por funcionário: fichas com código próprio (EPI-XXXXXX), itens de Entrega (CA/Descrição/Qtde/Data/Visto) e Devolução, PDF regenerável, status Em Aberto/Fechado | Alta | Concluído (v1.11.0) |
| EPI — Digitalizações múltiplas | Anexar fichas digitalizadas em várias versões (devoluções parciais) sem apagar anteriores | Media | Concluído (v1.11.0) |
| Rede | ASOs e EPIs espelhados na estrutura de rede ({Func}/ASOs e {Func}/EPIs) | Media | Concluído (v1.11.0) |
| ASO — Documento embutido | Documento do médico anexado/digitalizado entra nas páginas seguintes do próprio PDF do ASO | Alta | Concluído (v1.16.0) |
| EPI — Devolução separada | Botão Devolução por ficha: itens Pendente/Total/Parcial com data, Termo de Devolução em PDF próprio para assinar e ficha regenerada | Alta | Concluído (v1.16.0) |

### 2.17 Modelos de Importação e Atualização (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Modelos de importação | Pasta MODELOS DE IMPORTACAO/ com planilhas de exemplo (Funcionários, Certificados, Cartões, ASO) + LEIA-ME; geradas por tools/make_import_templates.py | Alta | Concluído (v1.12.0) |
| ASO em lote | Botão "Importar Excel" na aba ASO: casa CPF/nome, valida por linha e gera PDFs em lote | Alta | Concluído (v1.12.0) |
| Atualização no cliente | ATUALIZAR.bat copiado no dist: troca a versão a partir da pasta "Atualizacao" preservando data/ com backup automático | Alta | Concluído (v1.12.0) |

### 2.18 Crachá de Identificação (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Template CRACHA-ALTEC | Crachá 12x7,8cm (1/folha) na aba Cartões: foto 3x4, autorização, tabela de até 8 NRs com data/validade, emissão editável, ASO (vencimento + número) e assinatura obrigatória | Alta | Concluído (v1.13.0) |
| Template vertical CRACHA-VERTICAL | Mesmo crachá em retrato 7,8x12cm como novo template (paisagem inalterada); dimensões lidas do card.json | Alta | Concluído (v1.14.0) |
| Revisão da emissão | Diálogo com data de emissão e checkboxes de NRs por funcionário (pré-marcadas 8 mais recentes), com ASO exibido; emissão individual e em lote | Alta | Concluído (v1.13.0) |
| Gravação + rede | Emissões gravadas no banco (CRACHA-XXXXXX) em data/crachas/{Func} e LOTES; espelhadas na rede em {Func}/Crachas e Crachas_Gerais | Media | Concluído (v1.13.0) |
| Folha A4 + opção 86x54mm | Crachás (paisagem e vertical) em folha A4 com guia de corte (vários por folha; individual centrado) e opção de escala reduzida 86x54mm na revisão | Alta | Concluído (v1.15.0) |
| Bloqueio de emissão | Crachá só é gerado com foto, NR válida e ASO dentro da validade; NRs vencidas nunca entram (exibidas desabilitadas) | Alta | Concluído (v1.15.1) |

### 2.19 Backup via Tarefa Agendada do Windows (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Tarefa Agendada | Criar tarefa agendada no Windows Task Scheduler para executar backup automaticamente, mesmo com o programa fechado | Alta | Concluído (v1.15.0) |
| Configuração da Tarefa | Interface para configurar horário/frequência da tarefa agendada (diário, semanal, etc) | Alta | Concluído (v1.15.0) |
| Registro/Remoção | Registrar e remover a tarefa agendada diretamente pelo programa | Alta | Concluído (v1.15.0) |
| Verificação de Status | Indicar na UI se a tarefa agendada está ativa ou não | Media | Concluído (v1.15.0) |

### 2.20 Espelhamento de Todos os PDFs na Pasta de Documentos e Rede (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| PDFs na pasta documentos | Todos os PDFs gerados (fichas de EPI, ASO, cartões de bloqueio, crachás, certificados, etc.) devem ser salvos na pasta de documentos do funcionário | Alta | Concluído (v1.18.0) |
| Documentos assinados/digitalizados | Incluir PDFs assinados e digitalizados no espelhamento para a pasta de documentos | Alta | Concluído (v1.18.0) |
| Espelhamento em rede | Todos os documentos devem ser copiados para a pasta na rede também (estrutura {Func}/...) | Alta | Concluído (v1.18.0) |
| Consolidação de pastas | Unificar lógica de salvamento para que todos os tipos de documento sigam o mesmo padrão de espelhamento | Media | Concluído (v1.18.0) |

### 2.21 Guia de Introdução ao Sistema (PDF) (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Guia do Usuário | Montar um mini guia em PDF de introdução ao sistema e de como usar, voltado para o usuário final (nada muito técnico) | Media | Concluído (v1.18.0) |
| Conteúdo do Guia | Instruções de uso: cadastro de funcionários, emissão de certificados, cartões, ASO, fichas de EPI, importação Excel, backup, etc. | Media | Concluído (v1.18.0) |
| Acesso pelo Programa | Botão ou link no programa para abrir o guia (ex: menu Ajuda ou tela inicial) | Baixa | Concluído (v1.18.0) |

### 2.22 Melhorias na Ficha de EPIs (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Data padrão no preenchimento | Utilizar a data do dia como default para campos de retirada e devolução de EPIs, agilizando o preenchimento | Alta | Concluído (v1.17.0) |
| Correção do PDF — sobreposição de títulos | No PDF gerado, os títulos da tabela estão sobrepostos a outro texto/faixa — afastar para correção | Alta | Concluído (v1.17.0) |
| Itens devolvidos no PDF | Itens devolvidos não estão aparecendo na tabela geral do PDF — corrigir para exibir todos os itens | Alta | Concluído (v1.17.0) |
| Indicador de devolução | A Ficha de EPIs deve informar claramente se o item foi devolvido ou não (status visível para o usuário) | Alta | Concluído (v1.17.0) |
| Revisão geral da Ficha de EPIs | Rever o funcionamento atual da ficha de EPIs, que está confuso e pode gerar confusão ao usuário | Alta | Concluído (v1.17.0) |

### 2.23 Correções e Melhorias Gerais (v1.18.0) (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Ajuste CNH EAR | Corrigir informação de CNH EAR — EAR significa "Exerce Atividade Remunerada" | Alta | Concluído (v1.19.0) |
| Ajuda na sidebar | Colocar na barra lateral um pequeno texto "Ajuda - F1"; ao clicar, abrir o PDF de ajuda/guia | Media | Concluído (v1.19.0) |
| Data default ficha EPI | Corrigir campo data ao adicionar ficha de EPI — deve vir com a data atual ao invés de "-" | Alta | Concluído (v1.19.0) |
| Scroll horizontal tabela EPI | Adicionar barra de scroll horizontal na tabela da ficha de EPIs (itens estão saindo cortados) | Media | Concluído (v1.19.0) |
| Tabela de códigos ASO | Na tabela de importação de ASOs, utilizar códigos (A,B,C,D...) para os tipos de ASO (admissional, demissional, etc.) para evitar erros na importação | Alta | Concluído (v1.19.0) |
| Bug janela flutuante | Corrigir bug de janela flutuando indefinidamente em listas de pesquisa — aplicar correção já feita na lista de certificados às demais | Alta | Concluído (v1.19.0) |
| Data/Hora Home — layout | Na tela Home, deixar data e hora maiores, ao lado do logotipo/título, separados como duas colunas com uma linha preta fina no meio | Media | Concluído (v1.19.0) |
| Backup — hora e minuto | Na tela de backup, incluir hora e minuto no texto "Último Backup automático {data}" | Media | Concluído (v1.19.0) |
| Guia em DOCX | Alterar o guia de introdução para ser um PDF baseado em um arquivo Word (.docx), que poderá ser editado ao longo do tempo | Media | Concluído (v1.19.0) |

### 2.24 Ajustes Finais (v1.20.0) (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Conversão DOCX → PDF no build | A conversão do guia .DOCX para PDF deve ocorrer apenas no momento do build, para evitar travamentos ao usuário final | Alta | Concluído (v1.20.0) |
| ASOs vencidos — pasta específica | ASOs vencidos devem ser movidos para uma pasta específica (ex: {Func}/ASOs/Vencidos) | Alta | Concluído (v1.20.0) |
| Scrollbar na sidebar | Inserir scrollbar na barra lateral — alguns itens não ficam visíveis se a janela estiver muito pequena | Media | Concluído (v1.20.0) |
| Linha separadora Home | No menu Home, ajustar a linha preta: ela deve ficar entre o logotipo e a hora + data (não entre hora e data) | Media | Concluído (v1.20.0) |

### 2.25 Menu de Integrações (Fábricas de Clientes) (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Menu de Integrações | Criar menu dedicado para gerenciar integrações com fábricas de clientes (marcador de validade, sem geração de certificado) | Alta | Concluído (v1.22.0) |
| Controle de validade | Cada integração possui data de validade — verificar se está ativa/válida no menu "Vencimentos" | Alta | Concluído (v1.22.0) |
| Integração por empresa | Suportar múltiplas empresas clientes com integrações diferentes por funcionário | Alta | Concluído (v1.22.0) |
| Cadastro de empresas | Menu para criar/gerenciar empresas em que é possível fazer integração (nome, CNPJ, etc.) | Alta | Concluído (v1.22.0) |
| Vinculação ao funcionário | Vincular integrações ao cadastro do funcionário (empresa, tipo, data início, data validade) | Alta | Concluído (v1.22.0) |
| Indicador de status | Exibir na interface se a integração está "Em dia" ou "Vencida" (similar ao fluxo de NRs/ASOs) | Media | Concluído (v1.22.0) |
| Notificação de vencimento | Toast e painel de vencimentos para integrações próximas do vencimento | Media | Concluído (v1.22.0) |

### 2.26 Emissão em Massa de Certificados NR (CONCLUÍDA)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Seleção de NR | Interface para o usuário escolher qual NR deseja emitir em lote | Alta | Concluído (v1.23.0) |
| Seleção de funcionários | Selecionar funcionários do banco de dados para emissão (mesmos requisitos: nome completo, CPF, etc.) | Alta | Concluído (v1.23.0) |
| Validação de requisitos | Verificar automaticamente se cada funcionário selecionado atende aos requisitos de emissão antes de prosseguir | Alta | Concluído (v1.23.0) |
| Edição em lote | Editar dados do certificado de forma geral para todos os selecionados (Duração em Horas, Período de Validade, Data) | Alta | Concluído (v1.23.0) |
| Edição individual | Possibilidade de editar manualmente os dados do certificado de funcionários específicos dentro do lote | Alta | Concluído (v1.23.0) |
| Preview antes de emitir | Visualizar os certificados que serão gerados antes de confirmar a emissão | Media | Concluído (v1.23.0) |
| Geração e salvar na pasta | Gerar PDFs e salvar automaticamente na pasta de documentos do funcionário (com espelhamento em rede) | Alta | Concluído (v1.23.0) |
| Ajustar dimensões das telas/diálogos | Ajustar dimensões das telas e diálogos para ficar menor — algumas estão ficando maiores que a tela do aplicativo | Alta | Concluído (v1.23.0) |

### 2.27 Portal Web (docs/PORTAL)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Fase 1 — Esqueleto + login + papeis + dashboard + usuarios/auditoria | FastAPI + waitress + NSSM; acesso em 2 maquinas com login | Alta | Concluído (v1.24.0) |
| Fase 2 — Funcionarios, Certificados e Historico no portal | CRUD/consulta pelo navegador com a matriz de permissoes | Alta | Concluído (v1.25.0) |
| Fase 3 — ASO, EPI, Crachas, Cartoes, Vencimentos, Importacoes | Demais modulos de leitura/operacao | Media | Concluído (v1.28.0: Vencimentos e ASO; v1.29.0: EPI e Crachás; v1.30.0: Cartões, Importações e Integrações) |
| Fase 4 — Admin completo (backup, auditoria avancada) | Painel administrativo final | Media | Concluído (v1.32.0: Configurações; v1.34.0: Backup, Auditoria e audit_log nas ações) |

### 2.29 Gestão de Frota (Veículos) (CONCLUÍDA — 2.29.1 a 2.29.4 e 2.29.6 no Portal Web em v1.33.0/v1.34.0; 2.29.5 concluído em v1.34.0 com checklist de veículos leves)

#### 2.29.1 Cadastro Completo de Veículos

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Cadastro de veículos | Modelo, marca e tipo: Caminhão (subtipos: Caçamba, Munck, Plataforma), Pickup, Carro, Van, Empilhadeira, Retroescavadeira e Outros | Alta | Concluído (v1.33.0) |
| Placa condicional | Placa obrigatória para todos os tipos, exceto Empilhadeira e Retroescavadeira (não possuem placa) | Alta | Concluído (v1.33.0) |
| Propriedade do veículo | Indicar se é veículo próprio (sem nome) ou alugado (informar nome da pessoa que contratou) | Alta | Concluído (v1.33.0) |
| Empresa do veículo | Indicar a qual empresa o veículo pertence (ex: Altec Industrial, Ferro Fácil...) com cadastro/lista de empresas | Alta | Concluído (v1.33.0) |
| Pasta virtual do veículo | Pasta virtual própria por veículo para documentos relevantes (CRV, CRLV, Contratos, Inspeções etc.), mesmo padrão da pasta virtual do funcionário | Alta | Concluído (v1.33.0) |

#### 2.29.2 Solicitação de Abastecimento

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Documento PDF | Documento "Solicitação de Abastecimento" com logotipo da empresa | Alta | Concluído (v1.33.0) |
| Código serial | Código Identificador Serial único (não pode repetir) | Alta | Concluído (v1.33.0) |
| Fornecedor | Nome do posto de gasolina; permitir cadastrar empresas fornecedoras (Nome, CNPJ, Endereço) | Alta | Concluído (v1.33.0) |
| Tipo de combustível | Gasolina, Álcool, Diesel, Arla, GNV + opção específica "ARLA + DIESEL" | Alta | Concluído (v1.33.0) |
| Dados da solicitação | Data da solicitação, Viagem/Serviço (descrição rápida), KM do veículo no momento, campo de Descrição/Observações | Alta | Concluído (v1.33.0) |
| Veículo | Seleção a partir da lista de veículos cadastrados | Alta | Concluído (v1.33.0) |
| Condutor | Nome digitado na hora (o motorista pode ser de fora da empresa) | Alta | Concluído (v1.33.0) |
| Assinaturas | Campo de assinatura/rubrica do condutor + campo de aprovação do superior (nome para digitar + rubrica) | Alta | Concluído (v1.33.0) |

#### 2.29.3 Controle Individual de Veículos (Saída/Entrada)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Registro de Saída/Retirada | Data, hora, KM inicial, destino, motivo, descrições/observações | Alta | Concluído (v1.33.0) |
| Registro de Entrada/Devolução | Data, hora, KM final | Alta | Concluído (v1.33.0) |
| Motorista e Autorização | Nome do motorista + campo "Autorizado Por" (usuário digita o nome de quem autorizou) | Alta | Concluído (v1.33.0) |

#### 2.29.4 Laudos e Documentos com Vencimento

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Laudos manuais | Usuário insere laudos/documentos gerados manualmente, com data de vencimento | Alta | Concluído (v1.33.0) |
| Download do laudo | Opção de baixar o laudo/documento pelo usuário | Alta | Concluído (v1.33.0) |
| Aviso de vencimento | Sistema avisa quando estiver perto do vencimento (integrado ao menu Vencimentos, toast e dashboard) | Alta | Concluído (v1.33.0) |
| Documentos veículos pesados | Certificado Final, CRLV, Fumaça Preta, Laudo de Avaliação, Laudo Eletromecânico, Plano de Manutenção | Alta | Concluído (v1.33.0) |
| Documentos veículos leves | CRLV e Seguro | Alta | Concluído (v1.33.0) |
| Validade padrão | 1 ano por padrão (configurável) | Media | Concluído (v1.33.0 — validade informada por laudo) |

#### 2.29.5 Relatório de Verificação Semanal (Checklist)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Checklist semanal | Checklist de verificação para veículos leves e pesados | Baixa | Concluído (v1.34.0 — veículos leves, replicando o formulário em papel; pesados sem modelo definido) |
| Informações do relatório | Data Inicial, Data Final, KM Rodado, Veículo (com placa) | Baixa | Concluído (v1.34.0) |

#### 2.29.6 Notas Fiscais e Custo de Abastecimento (Longo Prazo)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Cadastro de notas fiscais | Notas fiscais vinculadas às solicitações de abastecimento (e também NFs realizadas durante viagens) | Baixa | Concluído (v1.34.0 — NF com arquivo anexado ao abastecimento) |
| Custo por veículo | Noção do custo de abastecimento acumulado por veículo | Baixa | Concluído (v1.34.0) |
| Média KM/L | Calcular média de KM/L por veículo e comparar com a ficha técnica | Baixa | Concluído (v1.34.0) |
| Autonomia no cadastro | Campos de autonomia/dados da ficha técnica nos detalhes do veículo | Baixa | Concluído (v1.34.0 — campo KM/L esperado) |

#### 2.29.7 Ajustes e Melhorias da Frota (CONCLUÍDA — v1.42.0)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Importar/Exportar veículos | Opção de importar e exportar veículos da frota (Excel, mesmo padrão das demais importações) | Alta | Concluído (v1.42.0) |
| Janela de foto do veículo | Janela de seleção de foto deve abrir para o outro lado — atualmente sai da tela (indo para a esquerda) | Media | Concluído (v1.42.0) |
| Formatação de data/hora | Na ficha do veículo (adicionar movimentação), a data de saída/entrada e hora devem sair formatadas (ex: 17/09/2026, 07:00) | Alta | Concluído (v1.42.0) |
| Formatação de KM | Incluir ponto de milhar na KM para facilitar a leitura (ex: 100.000 KM) | Media | Concluído (v1.42.0) |
| Motorista — funcionário ou "Outro" | Permitir escolher um funcionário da lista ou marcar checkbox "Outro" e escrever o nome do motorista | Alta | Concluído (v1.42.0) |
| Campos Motivo e Obs | Aumentar um pouco o tamanho dos campos "Motivo" e "Obs" e ativar scroll para esses campos | Media | Concluído (v1.42.0) |
| Abas retráteis na ficha | Deixar as abas da ficha do veículo retráteis (Documentos, Laudos e Documentos com Vencimento, Movimentações, Abastecimentos, Custo e Consumo, Checklist Semanal, Manutenções Preventivas por KM) | Media | Concluído (v1.42.0) |
| Cor do botão de abastecimento | Alterar a cor do botão "Nova Solicitação de Abastecimento" — um tom amarelo deve ficar bom | Baixa | Concluído (v1.42.0) |
| Abastecimento a partir da ficha | Se o usuário estiver na ficha do veículo e pedir abastecimento, levar para a tela de abastecimento com o veículo já preenchido | Alta | Concluído (v1.42.0) |
| Combustível por tipo de veículo | Não permitir Arla, Diesel e Arla + Diesel em carros | Alta | Concluído (v1.42.0) |
| Remover Valor e Litros | Remover os campos Valor e Litros da solicitação de abastecimento (sempre enchemos o tanque) | Media | Concluído (v1.42.0) |
| Funcionário ou "Outro" no abastecimento | Na ficha de abastecimento, permitir incluir funcionário da lista ou "Outro" | Alta | Concluído (v1.42.0) |
| Checklist semanal em PDF | Checklist semanal do veículo deve ser um documento gerado em PDF, impresso, preenchido, assinado e enviado de volta ao sistema (anexado ao veículo) | Alta | Concluído (v1.42.0) |
| Validação de conflito de movimentações | Se o veículo tem uma saída aberta, não pode ter outra saída; verificar conflito de horários e datas | Alta | Concluído (v1.42.0) |
| Tags nos documentos do veículo | Ao adicionar documentos na ficha do veículo, permitir selecionar "tags" para o arquivo (ex: Manutenções (Nota Fiscal), Documentos, Abastecimentos, Outros) | Media | Concluído (v1.42.0) |
| Ver por página | Em Frota, adicionar opção "Ver por página" (paginação da lista) | Media | Concluído (v1.42.0) |

### 2.30 Melhorias Gerais de Usabilidade e Sistema (CONCLUÍDA — v1.42.0)

#### 2.30.1 Notificações e Navegação

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Notificações "pop" | Notificações na lateral direita da tela para avisos rápidos (ex: Salvo com sucesso, Documento emitido etc.) | Alta | Concluído (v1.42.0) |
| Grupos no header | Melhorar a organização das abas no header, separando por grupos (ex: Certificados → Emitir, Emissão em Lote; Vencimentos etc.) | Media | Concluído (v1.42.0) |
| Pop-up de progresso | Adicionar pop-up para mostrar progresso da emissão, geração de documentos etc. | Alta | Concluído (v1.42.0) |

#### 2.30.2 Auditoria e Sistema

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Tabela de auditoria | Ajustar a lista: itens da coluna "Ação" estão ficando muito grandes comparados ao restante | Alta | Concluído (v1.42.0) |
| Linhas por página (auditoria) | Adicionar botão para ajustar quantas linhas vão aparecer na lista (10/20/30/50) | Media | Concluído (v1.42.0) |
| Busca por data (auditoria) | Permitir ao usuário buscar registros da auditoria pela data | Alta | Concluído (v1.42.0) |
| Salvar log de erros | Adicionar botão para salvar o log de erros | Media | Concluído (v1.42.0) |
| Download de backups | Permitir ao administrador baixar backups | Alta | Concluído (v1.42.0) |

#### 2.30.3 Vencimentos

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Card de 15 dias | Em Vencimentos, adicionar um card para itens que vão vencer em 15 dias | Alta | Concluído (v1.42.0) |

### 2.31 Frota, Menu e Dashboard (CONCLUÍDA — v1.44.0/v1.45.0)

#### 2.31.1 Lista da Aba "Frota" — Detalhes de Status

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Badges de status | Incluir badges indicando o status do veículo: Disponível, Indisponível, Em Manutenção, Em Viagem, Outros etc. | Alta | Concluído (v1.44.0 — status derivado: Em Viagem/Em Manutenção/Indisponível/Disponível) |
| Coluna "Veículo" simplificada | Ajustar o campo "Veículo" para mostrar apenas placa e modelo (ex: KWK-6C02 - New Fiesta); remover as colunas "Placa" e "Ano/Cor" | Alta | Concluído (v1.44.0) |
| Motorista atual | Adicionar campo com o nome do motorista atual do veículo | Media | Concluído (v1.44.0) |
| Local/destino da viagem | Adicionar coluna para informar o local/destino da viagem | Media | Concluído (v1.44.0) |
| Scrollbars na lista | Colocar scrollbar lateral (horizontal) se for o caso, e scrollbar vertical também | Media | Concluído (v1.44.0) |

#### 2.31.2 Ficha do Veículo — Movimentações e Abastecimentos

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Data/hora com máscara | Ao registrar saída/entrada, a formatação dos campos Data da saída e hora deve ser aplicada conforme o usuário digita (mostrar corretamente na hora e indicar caso tenha algum erro) | Alta | Concluído (v1.44.0) |
| Abastecimento assinado + NF | Permitir ao usuário enviar o abastecimento assinado e inserir foto ou PDF da nota fiscal também | Alta | Concluído (v1.44.0 — NF já existia) |

#### 2.31.3 Checklist Semanal — Template Pré-preenchido

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Template do checklist | Transformar o Checklist semanal em um template: o usuário baixa o template com os dados do veículo, KM atual, placa e data já preenchidos pelo sistema; depois imprime, preenche, assina e anexa de volta no sistema | Alta | Concluído (v1.44.0 — "Gerar em branco" com cabeçalho pré-preenchido) |

#### 2.31.4 Reorganização do Menu/Header (apenas interface)

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Botão dedicado "Gestão de Frota" | No menu/Header, tirar a Frota do submenu e colocar como botão dedicado, renomeando para "Gestão de Frota" | Alta | Concluído (v1.44.0) |
| Menu "Certificados" → "Segurança" | Alterar o nome do menu "Certificados" para "Segurança" | Alta | Concluído (v1.44.0) |
| Aba "EPI" → "Ficha de EPIs" | Renomear a aba "EPI" para "Ficha de EPIs" e colocá-la dentro do menu "Segurança" | Alta | Concluído (v1.44.0) |
| "Crachás" e "Cartões" em "Segurança" | Colocar as abas "Crachás" e "Cartões" dentro do menu "Segurança" | Alta | Concluído (v1.44.0) |
| Aba "Vencimentos" em "Segurança" | Colocar a aba "Vencimentos" dentro de "Segurança" | Alta | Concluído (v1.44.0) |
| Menu "Cadastros" → "Funcionários" | Renomear o menu "Cadastros" para "Funcionários" e o botão "Funcionários" para "Cadastros" (apenas interface) | Alta | Concluído (v1.45.0 — troca literal: grupo "Funcionários" contém "Cadastros", ASO e Integrações) |

#### 2.31.5 Dashboard

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Atalho para Vencimentos | Adicionar um botão/atalho para Vencimentos no Dashboard | Alta | Concluído (v1.44.0) |
| Animação de contagem nos cards | Adicionar animação de números crescendo nos cards do dashboard (cerca de 2 segundos até chegar ao valor final) | Baixa | Concluído (v1.44.0; duração ajustada para ~2s em v1.45.0) |

### 2.32 Portal, Importações e Abastecimento (CONCLUÍDA — v1.45.0)

#### 2.32.1 Portal — Progresso e Importação de Fotos

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Barra de progresso | Adicionar barra de progresso (se possível com percentual) ao emitir certificados em lote e durante importações | Alta | Concluído (v1.45.0 — jobs em background com barra %, contador i/total e item atual; polling `/jobs/{id}`) |
| Importar fotos dos funcionários | O botão de importar as fotos dos funcionários não está disponível no site — adicionar/restaurar no portal | Alta | Concluído (v1.45.0 — "Importar Fotos" em Funcionários: upload múltiplo, casa por CPF/nome, prévia com conferência antes de aplicar) |

#### 2.32.2 Solicitação de Abastecimento — Template de Aprovação

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Aprovação sem nome | Alterar o template da Solicitação de Abastecimento: não especificar o nome do aprovador, deixando apenas um campo para assinatura e, embaixo, escrito "Aprovado" | Alta | Concluído (v1.45.0 — nome do aprovador removido do PDF, formulário e validação) |

### 2.33 Permissões, Frota, Certificados e Interface (CONCLUÍDA — v1.46.0, implementado em 18/09/2026)

#### 2.33.1 Acessos e Permissões

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Permissões por módulo | Mudar a forma de acesso com base em permissões de acesso para cada módulo, definidas pelo administrador (papel + exceção por usuário; aplicam sem re-login) | Alta | Concluído (v1.46.0) |

#### 2.33.2 Gestão de Frota — Interface e Ajustes

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| H1 do card | Na aba "Gestão de Frota", alterar o H1 no card para mostrar "Gestão de Frota" ao invés de só "Frota" | Media | Concluído (v1.46.0) |
| Importar veículos | Ajustar para que o "Escolher arquivos" só apareça se o usuário clicar no botão "Importar" | Media | Concluído (v1.46.0) |
| Botão "Fornecedores (Postos)" | Renomear o botão "Fornecedores" para "Fornecedores (Postos)" | Media | Concluído (v1.46.0) |
| Botão "Empresas (Posse)" | Renomear "Empresas de veículos" para "Empresas (Posse)" | Media | Concluído (v1.46.0) |
| Campo "Posse" na lista | O campo "Posse" na lista de veículos não mostra nada — ajustar para aparecer "Próprio" ou "Alugado" | Alta | Concluído (v1.46.0 — bug de digitação `possse`→`posse`) |
| Ver NF nos abastecimentos | Faltou um botão para ver a NF no menu "Frota/Abastecimentos" | Alta | Concluído (v1.46.0 — botão NF em todas as linhas) |
| Edição de abastecimento | Permitir que o usuário altere os dados do abastecimento caso precise ajustar ou corrigir erro; adicionar histórico de revisão do documento no sistema e texto no cantinho do PDF com o código da revisão (ex: REV_A) | Alta | Concluído (v1.46.0 — botão Editar + revisão incremental REV_A/REV_B…; PDF regenerado e carimbado) |
| Outros/Ferramentas (abastecimento) | Adicionar opção "Outros/Ferramentas" nos abastecimentos (ex: motosserras, roçadeiras etc.); deixar essa parte mais genérica, com o usuário informando observações na hora | Alta | Concluído (v1.46.0 — título "Combustível / Despesa") |
| Reformular menu do veículo | Deixar o menu do veículo mais moderno e reduzir o número de dropdownlists; substituir algumas por botões que abrem um popup/dialog (ex: clicar em "Laudos e Documentos com Vencimento" abre um dialog e o usuário faz tudo por lá) | Media | Concluído (v1.46.0 — 7 dialogs: Documentos, Laudos, Movimentações, Abastecimentos, Custo, Checklist, Manutenções) |
| Situação atual do veículo | Na ficha do veículo, incluir onde o veículo está, quem está dirigindo atualmente e se está disponível — puxando os dados com base nas movimentações (saída/entrada) | Alta | Concluído (v1.46.0 — badge de situação + motorista/destino no cabeçalho) |

#### 2.33.3 Certificados — Visualização de PDFs Importados

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| PDF de certificados importados | Na aba Certificados, há erros ao visualizar PDFs de certificados importados (tenta abrir um link mas falha porque o PDF não foi gerado) | Alta | Concluído (v1.46.0 — rota tenta regenerar antes de responder) |
| Gerar PDF na hora | Verificar se o PDF existe; se não existir, gerar na hora — informando o usuário e com tela de carregamento | Alta | Concluído (v1.46.0 — mesmo número CERT-, sem duplicar registro; botão Gerar na listagem e no detalhe) |
| Aviso de impedimento | Avisar o usuário quando não for possível visualizar devido a algum impeditivo (ex: usuário sem CPF cadastrado) | Alta | Concluído (v1.46.0 — motivo claro: sem CPF, modelo ausente, empresa não configurada) |

#### 2.33.4 Melhorias Gerais de Interface

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Realce no hover | Melhorias gerais na interface para ficar mais bonita — ex: realce nos botões e itens das listas ao passar com o mouse em cima | Media | Concluído (v1.46.0 — hover em linhas, botões, links, summaries; foco visível em inputs) |

### 2.34 Portal, Backup e Ficha de EPI (CONCLUÍDA — v1.47.0)

#### 2.34.1 Portal — Usuários e Backup

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Badge de permissão (Usuários) | No menu Usuários, após alterar a permissão de um usuário e salvar ainda aparece como "padrão do papel", apesar da alteração funcionar | Alta | Concluído (v1.47.0 — select reflete Permitir/Negar salvo) |
| Ordenação dos backups | Na aba Backup, sempre organizar com base nos backups mais recentes | Media | Concluído (v1.47.0 — por data, mais recente primeiro) |

#### 2.34.2 Ficha de EPI — Campos e Situação

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Fabricante e Lote | Adicionar campos "Fabricante" e "Lote" como opcionais na ficha | Alta | Concluído (v1.47.0 — por item, no form/ficha/PDF) |
| Item descartável | Adicionar "Check" (checkbox) se o item for descartável | Media | Concluído (v1.47.0 — checkbox por item + badge/PDF) |
| Badge "Devolução parcial" | O badge de situação no menu de fichas de EPI deveria mostrar "Devolução parcial" para quando houver devolução de parte dos itens | Alta | Concluído (v1.47.0 — badge amarelo + filtro) |

#### 2.34.3 Ficha de EPI — PDF

| Item | Descricao | Prioridade | Status |
|------|-----------|------------|--------|
| Correção do PDF | A geração do PDF da ficha de EPI ainda não ficou legal: sobreposição de textos na tabela etc. (faixas "ENTREGA/DEVOLUÇÃO DE EQUIPAMENTO" cobrindo os títulos das colunas) | Alta | Concluído (v1.47.0 — folga entre faixas e colunas + zebra na devolução) |
| Termo de Compromisso | Adicionar o texto do "TERMO DE COMPROMISSO" na primeira folha de todas as fichas de EPIs, com um campo abaixo desse texto para o funcionário assinar atestando que leu todo o termo; incluir o local de treinamento (endereço da empresa) e o CNPJ da empresa nessa ficha | Alta | Concluído (v1.47.0 — termo integral + Local/CNPJ + assinatura) |

Texto integral do Termo de Compromisso (typo "anterios" corrigido para "anterior"):

```
TERMO DE COMPROMISSO:
Declaro que recebi orientação sobre o uso do EPI – Equipamento de Proteção Individual fornecida pela Empresa e que estou ciente da legislação discriminada, comprometendo-me a cumpri-la.
Portaria Nº 3.214, 08/06/78 – Norma Regulamentadora Nº 01 – Disposições Gerais, Item 1.8 – CABE AO EMPREGADO:
a) Cumprir as disposições legais e regulamentares sobre segurança e medicina do trabalho, inclusive as ordens de serviço expedidas pelo empregador;
b) Usar o EPI fornecida pelo empregador;
c) Submeter-se aos exames médicos previstos nas Normas Regulamentadoras – NR 07
1.8.1 – Constitui ato faltoso a recusa injustificada do empregado (a) ao cumprimento do disposto no item anterior.
CLT – Artigo 462, § 1º - Em caso de dano causado pelo empregado, o desconto será licito, desde que esta possibilidade tenha sido acordada, ou na ocorrência de dolo do empregado.
```


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
 - [x] Testar viabilidade de drive mapeado em rede (obsoleto — substituído pelo Portal Web em rede, v1.24.0+)
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

### Para drive mapeado (OBSOLETO):
- Substituído pelo Portal Web (Fase 1, v1.24.0): o acesso em rede é feito
  pelo navegador, sem mapear drive nem expor o SQLite na rede.

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
