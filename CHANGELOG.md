## [1.48.0] - 2026-09-23

### Adicionado
- **Frota - Gráfico de custo e consumo (12 meses) na ficha do veículo**: SVG
  offline com barras empilhadas (azul = combustível, laranja = itens extras)
  e linha de litros; aparece no dialog Custo e consumo.
- **Frota - Exportação de custos para Excel**: individual por veículo (na
  ficha, com resumo + série mensal + abastecimentos) e geral (todos os
  veículos, com abas Resumo por veículo e Abastecimentos).
- **Abastecimentos - Itens extras por solicitação**: linhas de descrição/
  qtde/valor no formulário (ex.: óleo 2 tempos, aditivo, pedágio), somam no
  custo total com desglose (combustível x extras) em ficha/gráficos/resumos
  e ganham seção própria no PDF com TOTAL GERAL.
- **Abastecimentos - Bloquear/Excluir solicitação**: bloqueio com motivo
  (Não usada, Erro de lançamento, Cancelado, Outro + texto livre); somente a
  solicitação mais recente pode ser excluída (as antigas devem ser
  bloqueadas); bloqueadas ficam fora de todos os cálculos de custo
  (ficha, média, dashboard) e ganham badge BLOQUEADA + filtro por situação.
- **Abastecimentos - Ordenação da lista**: por Data (padrão, mais recentes
  primeiro) ou Serial; filtro por situação (Todas/Ativas/Bloqueadas).
- **Abastecimentos - Coluna Nota fiscal**: mostra o número da NF anexada ou
  badge "Sem NF".
- **Exportação de abastecimentos atualizada**: novas colunas Itens extras
  (R$), Total (R$), NF, Situação e Motivo.

## [1.47.0] - 2026-09-23

### Adicionado
- **Ficha de EPI — Fabricante e Lote por item** (opcionais): novos campos no
  formulário de abertura, exibidos na ficha e impressos como linha secundária
  no PDF ("Fabricante: X · Lote: Y").
- **Ficha de EPI — item descartável**: checkbox por linha; itens marcados
  ganham badge "Descartável" na ficha e indicação no PDF.
- **Ficha de EPI — badge "Devolução parcial"**: a lista e a ficha agora
  distinguem devolução parcial (amarelo) de "Itens devolvidos" (azul) e
  "Aberta" (verde), com filtro próprio na lista.
- **Ficha de EPI — TERMO DE COMPROMISSO na 1ª folha do PDF**: texto integral
  (Portaria 3.214/78, NR-01 item 1.8, NR-07, CLT Art. 462 §1º) com Local
  (reusa "Local de treinamento" das Configurações) e CNPJ da empresa, e linha
  de assinatura "li e estou ciente do termo acima".

### Corrigido
- **Usuários — badge de permissão**: o select de exceção por usuário voltava a
  mostrar "Padrão do papel" depois de salvar Permitir/Negar (a alteração era
  gravada, só a exibição errava). Agora o select reflete o estado salvo.
- **Backup — ordenação**: a lista agora mostra sempre os backups mais
  recentes primeiro (ordenada por data de modificação, independente do nome).
- **PDF da Ficha de EPI — sobreposição**: os títulos das colunas ("C.A.",
  "Descrição…", "Qtde"…) não são mais cobertos pelas faixas azuis
  "ENTREGA/DEVOLUÇÃO DE EQUIPAMENTO" — folga dedicada entre as faixas e
  cabeçalho de colunas com faixa própria também no bloco de devolução.

## [1.46.0] - 2026-09-18

### Adicionado
- **Permissões por módulo definidas pelo administrador** (Usuários →
  "Permissões por papel"): o admin marca o que cada papel (Emissor/Consulta)
  pode acessar, módulo por módulo, e também pode dar **exceções por usuário**
  (Permitir/Negar mesmo com o papel bloqueado). As mudanças valem na hora,
  sem re-login. Admin sempre mantém Usuários e Configurações.
- **PDF de certificados gerado na hora**: certificados importados (ou com o
  arquivo sumido) voltam a funcionar — o portal recria o PDF com o MESMO
  número (CERT-XXXXXX) ao abrir "Ver"/"PDF", e a lista de histórico mostra
  badge "Sem PDF" com botão **Gerar**. Impedimentos são explicados
  (funcionário sem CPF, modelo da NR ausente, empresa não configurada).
- **Ficha do veículo modernizada**: as 6 seções viraram janelas (dialogs)
  abertas por botões na barra da ficha — Documentos, Laudos, Movimentações,
  Abastecimentos, Custo, Checklist e Manutenções — e o cabeçalho agora mostra
  a **situação atual** (Disponível/Em Viagem/Em Manutenção/Indisponível),
  motorista e destino atual.
- **Edição de abastecimento com revisão**: botão "Editar" corrige dados e
  gera novo PDF carimbado **REV_A, REV_B…** ("documento revisado; substitui
  a versão anterior").
- Opção **"Outros / Ferramentas"** no abastecimento (motosserras, roçadeiras
  etc.) — o título do campo virou "Combustível / Despesa".

### Corrigido
- **Lista de veículos: coluna "Posse" estava sempre vazia** (erro de digitação
  no template).
- Interface geral com realce ao passar o mouse (linhas das tabelas, botões,
  links, summary) e contorno azul nos campos com foco.
- Botões/rótulos do Frota padronizados: H1 "Gestão de Frota", "Empresas
  (Posse)", "Fornecedores (Postos)"; importar Excel agora abre ao clicar no
  botão "Importar Excel"; botão **NF** disponível em todas as linhas dos
  abastecimentos.

## [1.45.3] - 2026-09-18

### Adicionado
- **Versão do sistema no cabeçalho do portal** (ex.: `v1.45.3`) ao lado da
  marca NormaTech — aparece em todas as páginas, inclusive no login.
- **Calendário para escolher datas**: todo campo de data do portal ganhou o
  botão 📅 que abre o calendário do navegador e preenche a data sozinho
  (dd/mm/aaaa). O campo também só aceita números e insere as barras
  automaticamente. Aplicado em: certificados (individual e lote),
  funcionários (nascimento/admissão), ASO, EPI (entrega, itens, devolução),
  crachás, frota (abastecimento, checklist, laudos, saída/entrada,
  manutenções, NFs), histórico (filtros De/Até).
- **Máscara de telefone** no cadastro de funcionário (só números, máx. 11).
- **Máscara de CNPJ** nas empresas/fornecedores (frota, integrações) e
  validação ao salvar: se preenchido, exige os 14 dígitos (vazio continua
  permitido).

### Corrigido
- **Emissão individual: funcionário não perde mais a seleção ao trocar a
  NR** — a página não recarrega mais; carga, validade, descrição e campos
  extras se ajustam na hora (o funcionário escolhido continua selecionado).
- **Emissão em lote: marcação dos funcionários sobrevive à troca da NR**.
- **Aviso “Gerando documento” não aparece mais quando há erro de
  preenchimento** (ex.: enviar sem selecionar funcionário) — o carregamento
  só é exibido quando o formulário realmente é enviado.
- Campos numéricos que aceitavam texto viraram numéricos de verdade (carga
  e validade na emissão em lote, quantidades de EPI); litros/valores/KM-L
  só aceitam números e vírgula.
- Máscaras de data/hora da ficha de frota, que existiam no código mas nunca
  eram executadas, foram substituídas pelas máscaras globais do portal.

## [1.45.2] - 2026-09-18

### Corrigido
- **Portal fora do ar por CPF inválido**: um funcionário com CPF digitado
  errado (dígito verificador inválido, ex.: `211.323.497-22`) derrubava a
  listagem de funcionários inteira com erro de validação. Duas correções:
  - O sistema agora aceita qualquer CPF com 11 números (a verificação do
    dígito verificador foi removida — CPF só é validado pelo formato:
    11 dígitos, sem repetições tipo 111.111.111-11);
  - Blindagem extra: se qualquer registro antigo com dado inválido existir
    no banco, ele não derruba mais listagens/fichas/emissões — o
    funcionário aparece normalmente e o erro é registrado em
    `data/error.log`.
- Vale para cadastro manual (portal e desktop) e importações por planilha.

## [1.45.1] - 2026-09-18

### Adicionado
- **Portal — botão “Exibir senha”**: nos formulários de senha (página
  Usuários → “Definir senha” e Trocar senha) cada campo ganhou o botão
  Exibir/Ocultar para conferir o que foi digitado.
- **Portal — máscara de CPF no cadastro de funcionário**: o campo CPF só
  aceita números e formata sozinho (000.000.000-00) enquanto se digita.

### Corrigido
- **Importação de funcionários — CPF robusto**: células numéricas do Excel
  (CPF digitado como número chega como `11144477735.0`) não são mais
  corrompidas; o importador aceita CPF com ponto/hífen ou números puros e
  rejeita com mensagem clara qualquer coisa que não tenha exatamente 11
  números (ex.: “CPF tem mais de 11 numeros”, “menos de 11 numeros — zeros
  à esquerda podem ter sido perdidos”).
- **Importações — erro em uma linha não derruba o resto**: falha de banco
  ao cadastrar uma linha (ex.: CPF duplicado, banco ocupado) vira erro
  daquela linha no resumo; as demais linhas continuam sendo importadas
  (funcionários, veículos, bloqueios de cartão).
- **Modelos de importação**: coluna CPF dos modelos FUNCIONARIOS, ASO e
  CARTOES BLOQUEIO agora é Texto (preserva zeros à esquerda), exemplos em
  números puros, comentário de instrução no cabeçalho e aba “LEIA-ME” no
  modelo de funcionários. LEIA-ME.txt atualizado.

## [1.45.0] - 2026-09-17

### Adicionado
- **Portal — barra de progresso real (ROADMAP 2.32.1)**: emissão em lote e
  importações (funcionários, certificados, ASOs, cartões) rodam em job de
  fundo com barra de percentual, contador i/total e item atual; o navegador
  consulta o status a cada 500 ms (/jobs/{id}). Chamadas sem JavaScript
  continuam funcionando no modo síncrono anterior.
- **Portal — importar fotos dos funcionários (ROADMAP 2.32.1)**: botão
  “Importar Fotos” na página de Funcionários. Aceita vários arquivos
  (JPG/PNG/BMP/WEBP até 50 MB), casa pelo CPF (11 dígitos no nome do
  arquivo) ou nome exato, mostra prévia com foto nova x atual, marca
  “SUBSTITUIR/adicionar” e só grava o que for confirmado.
- **Portal — menu renomeado (ROADMAP 2.31.4)**: grupo “Cadastros” passou a
  se chamar “Funcionários” e o item interno “Funcionários” passou a se
  chamar “Cadastros” (troca literal de interface).

### Alterado
- **Dashboard — animação de contagem em ~2 segundos** (antes 0,8 s).
- **Solicitação de Abastecimento — aprovação sem nome (ROADMAP 2.32.2)**:
  o PDF não imprime mais o nome do aprovador — fica apenas a linha de
  assinatura com “Aprovado” embaixo. O campo “Aprovação (superior)” saiu
  do formulário e da validação; a coluna “Superior” saiu da exportação
  Excel (coluna segue no banco, ignorada).
- Corrigida a codificação (mojibake) do formulário de checklist semanal.

## [1.44.0] - 2026-09-17

### Adicionado
- **Frota — status do veículo derivado automaticamente** (ROADMAP 2.31):
  lista com badge Em Viagem (saída aberta), Em Manutenção (manutenção
  urgente), Indisponível (manutenção vencida ou alugado com contrato
  vencido) e Disponível; colunas Motorista e Destino da viagem atual.
- **Frota — lista simplificada**: coluna Veículo mostra "PLACA - Marca
  Modelo" (colunas Placa e Ano/Cor removidas) e a tabela ganhou barra de
  rolagem própria (não estica a página).
- **Frota — máscara de data/hora** (dd/mm/aaaa e HH:MM) nos campos de
  saída/entrada de movimentações.
- **Frota — checklist em branco pré-preenchido**: botão na ficha gera o PDF
  do checklist semanal com veículo, placa, KM atual e data já preenchidos
  para imprimir, preencher à mão, assinar e anexar de volta (registro criado
  com serial CKL).
- **Frota — abastecimento assinado**: anexar foto/PDF do abastecimento
  assinado na tela de NFs (upload, download e exclusão).
- **Menu reorganizado**: grupo "Segurança" (Certificados, Emissão em Lote,
  Histórico, Listas de Presença, Ficha de EPIs, Crachás, Cartões,
  Vencimentos), grupo "Cadastros" (Funcionários, ASO, Integrações) e botão
  dedicado "Gestão de Frota" no topo do menu.
- **Dashboard**: atalho Vencimentos, contagem animada nos cards e barra de
  rolagem no card de aniversariantes do mês.

## [1.43.0] - 2026-09-17

### Corrigido
- **Portal — importação de certificados em lote voltou a funcionar com planilhas grandes**:
  a prévia era guardada na sessão (cookie) e, com ~40 linhas ou mais, o cookie
  estourava o limite de 4 KB dos navegadores e era descartado — ao clicar em
  "Emitir", o servidor não encontrava a prévia e mostrava "Nenhuma prévia
  pendente — envie a planilha novamente.". Agora a prévia é gravada em
  `data/tmp_importacoes/{token}.json` (a sessão guarda só o token) e o arquivo
  é apagado após a emissão; órfãos com mais de 24h são limpos automaticamente.
- **Listas de presença NR-01 com carga quebrada**: a carga horária chega do
  banco como número decimal (8.0) e o formato `{n:02d}HS` do modelo não aceita
  decimal ("Unknown format code 'd'"). Agora o valor é convertido para inteiro
  quando não tem parte fracionária antes de formatar (E4 = "08HS").

### Adicionado
- **Usuários — "Definir senha"**: o admin pode definir uma senha específica
  para um usuário (mínimo 6 caracteres), sem depender da senha provisória
  aleatória (Ações → Definir senha).
- **Certificados — data e hora da emissão no PDF (opcional)**: nova opção em
  Configurações → Certificados ("Incluir data e hora da emissão no PDF").
  Quando ativa, imprime `dd/mm/aaaa HH:MM` pequeno junto ao número do
  certificado (CERT-XXXXXX • dd/mm/aaaa HH:MM). Vale para os PDFs JSON/ReportLab
  e para os modelos PPTX da técnica.
- **Abastecimento — propriedade do veículo na solicitação**: o PDF agora indica
  "— Próprio" ou "— Alugado (contratante: X)" ao lado do veículo.

## [1.42.0] - 2026-09-17

### Adicionado (ROADMAP 2.29.7 — Frota)
- **Importar/Exportar veículos** (Excel): botões na lista de Frota; modelo
  `MODELO VEICULOS.xlsx` disponível para download; empresa inexistente é
  criada automaticamente; erros são por linha.
- **Motorista/Condutor por lista de funcionários ou "Outro"** nos formulários
  de movimentação e abastecimento.
- **Checklist assinado de volta**: anexar ao checklist o PDF/foto assinado
  (download e remoção pelo mesmo ponto).
- **Conflito de movimentações**: com uma saída aberta, novas saídas são
  bloqueadas até registrar a entrada.
- **Tags nos documentos do veículo**: Manutenção (Nota Fiscal), Documento,
  Abastecimento, Outros.
- **Valor e Litros opcionais**: podem ficar em branco na emissão e ser
  completados depois na tela de NFs (custo/KM-L continuam funcionando).
- **Combustível por tipo**: Arla/Diesel/Arla+Diesel bloqueados para carros
  (no servidor e no formulário).
- **Abastecimento a partir da ficha**: botão leva ao formulário com o
  veículo pré-preenchido (botão em tom amarelo).
- **"Ver por página"** na lista de veículos e de abastecimentos
  (10/20/25/50).

### Adicionado (ROADMAP 2.30)
- **Notificações pop** (lateral direita, auto-fecha) substituindo os banners
  de mensagem.
- **Menu em grupos** no header (Certificados, Cadastros, Controle, Sistema).
- **Pop-up de progresso** durante emissões/gerações (overlay com spinner em
  todo POST do portal).
- **Auditoria**: busca por data (de/até), linhas por página (10/20/30/50) e
  coluna "Ação" truncada com tooltip.
- **Download do log de erros** e **download de backups** pelo admin
  (com proteção anti-traversal).
- **Card "Vencem em 8 a 15 dias"** em Vencimentos (com filtro dedicado).

### Alterado
- Datas/horas de movimentação no formato `17/09/2026, 07:00`; KM com ponto
  de milhar (ex.: 100.000) na ficha do veículo.
- Seções da ficha do veículo viraram **abas retráteis** (Documentos, Laudos,
  Movimentações, Abastecimentos, Custo, Checklist, Manutenções).
- Popover da foto do veículo abre para dentro da tela.
- CI: workflow `.github/workflows/tests.yml` (unitário + portal); ROADMAP
  2.12 fechado (CI concluído; Multiusuário/GPU superados pelo Portal Web).

## [1.41.0] - 2026-09-16

### Alterado
- **Listas de Presença** (ajustes de layout pedidos após testes):
  - Campo **empresa** (ao lado do nome) sempre preenchido com
    `ALTEC INDUSTRIAL` — modelos e layout padrão.
  - PDFs sempre em **folha vertical** (paisagem não ficou bom).
  - **Serial da lista** gravado na célula `{SERIAL}` do modelo e
    **paginação** (`Pag X de Y`) na célula `{PAGINACAO}`.
  - **Muitos participantes**: o mesmo modelo é preenchido em folhas
    separadas (vagas do registry; 20 no padrão) com `Pag 1 de N`,
    `Pag 2 de N`… e os PDFs são mesclados em um único arquivo.
  - Logo do modelo não é mais reinserida (vinha duplicada: o openpyxl
    preserva a imagem embutida do XLSX; o layout padrão continua com logo).

## [1.40.0] - 2026-09-16

### Corrigido
- **Conteúdo programático das listas de presença não é mais alterado**: o
  gerador reescrevia o número de horas dentro do texto do template
  (ex.: "CONTEÚDO PROGRAMÁTICO — 03 HORAS") com a carga da emissão. O texto
  do modelo fica intacto agora (mesma regra dos certificados PPTX). A célula
  dedicada de carga da NR-01 continua sendo preenchida normalmente.
- **Compilado de listas usa só as listas da emissão**: o dialog pós-emissão
  agora baixa um PDF com exatamente as listas geradas naquele momento
  (link com `?ids=...`), e não mais tudo do dia — emissões anteriores no
  mesmo dia não vazam para dentro. O mini-form "Baixar compilado de um dia"
  da listagem continua gerando o dia completo.
- Regressão coberta por testes: PDFs sem rastro de `comtypes` (texto de
  versões antigas), sem abas de outras NRs e com a carga original
  preservada.

## [1.39.0] - 2026-09-16## [1.39.0] - 2026-09-16

### Corrigido
- **Portal — Listas de Presença: preenchimento deixou de usar o Excel COM**.
  Na máquina do servidor, a escrita via COM não persistia (mesma classe do
  bug de binding já corrigido) e as listas saíam com campos vazios ou com os
  dados de exemplo do template. Agora o preenchimento é 100% openpyxl
  (determinístico): edita data, carga e participantes, **limpa as vagas não
  utilizadas** (exemplos do template somem) e o Excel é usado apenas para a
  conversão final em PDF.
- **Folhas em branco no PDF**: área de impressão explícita (`print_area`) +
  ajuste de largura + paisagem + grade nos modelos preenchidos e no layout
  padrão — sem páginas vazias.
- **Popup do compilado não fechava**: "Baixar compilado" agora fecha o
  diálogo e volta para a listagem (download continua em paralelo).
- A logo do modelo XLSX é extraída do arquivo original e reancorada na
  posição lida do XML do template (openpyxl perde imagens ao re-salvar).

## [1.38.1] - 2026-09-16

### Corrigido
- **Portal — Listas de Presença: dados do sistema não apareciam nas listas
  (NRs com modelo)**: o preenchimento via Excel alterava o arquivo na
  memória, mas o fechamento descartava as alterações (`Close` sem salvar) —
  o PDF saía com o modelo em branco, sem data nem colaboradores. Agora o
  workbook é salvo antes de fechar. A data impressa é a data referente
  escolhida na emissão (o dia em que os certificados foram emitidos).

## [1.38.0] - 2026-09-15

### Corrigido
- **Portal — Listas de Presença: geração dos modelos NR-01/06/12/18/35 voltou a
  funcionar**: dois problemas de COM no servidor, só no preenchimento do
  modelo Excel (o layout padrão, como Brigadista, não passa por ele):
  1. `CreateObject` sem `CoInitialize` nas threads do servidor ("CoInitialize
     não foi chamado") — agora Excel COM é iniciado por um helper único
     (`_excel_app`), usado no preenchimento e na conversão para PDF.
  2. Gravação de células (`Range.Value`) passou a falhar com
     `AttributeError: Value` — a interoperabilidade dinâmica do comtypes
     deixou de resolver a gravação da propriedade nesta combinação de
     Office/Windows. Corrigido com fallback que obtém o identificador da
     propriedade (via Bind GET) e grava direto em `IDispatch::Invoke`
     (PROPERTYPUT); NumberFormat, PageSetup e demais escritas usam o mesmo
     caminho quando necessário.

### Alterado
- **Portal — Listas de Presença em folha horizontal e organizadas**: todas as
  listas (modelo ou layout padrão) saem em orientação paisagem, com ajuste
  para caber em 1 página de largura, linhas de divisão visíveis (grade como
  no Excel) e conteúdo centralizado horizontalmente.

## [1.37.0] - 2026-09-15

### Alterado
- **Portal — Listas de Presença: emissão do dia inteiro de uma vez**:
  em "+ Nova lista" agora basta informar a **data** — o portal mostra uma
  seção por NR com os participantes daquele dia (marcadas por padrão) e o
  botão **Emitir listas do dia** gera todas de uma vez (uma NR com problema
  não bloqueia as demais; o resumo mostra geradas e falhas).

### Adicionado
- **Compilado das listas do dia (PDF único)**: após emitir, um diálogo
  pergunta se quer baixar o compilado (todas as listas do dia em um único
  PDF, pronto para imprimir); também dá para baixar depois pela listagem
  informando a data.

### Corrigido
- **Portal — uso de Excel/PowerPoint (COM) nas rotas web**: as chamadas COM
  falhavam dentro das threads do servidor ("CoInitialize não foi chamado").
  Corrigido em `presenca_generator` (Excel) e `pptx_card_service`
  (PowerPoint — afetava também cartões e certificados PPTX no portal).

## [1.36.0] - 2026-09-15

### Adicionado
- **Portal — aba "Listas de Presença"**: geração e controle das listas de
  presença de treinamento, uma lista por NR:
  - **Geração automática**: escolha a NR e a data; o portal puxa sozinho os
    funcionários que tiveram certificado daquela NR emitido no dia (com nome,
    função e carga horária detectada). Prévia antes de gerar; datas antigas
    funcionam (histórico por data final do certificado).
  - **Modelos reais**: NR-01, NR-06, NR-12, NR-18 e NR-35 usam as planilhas
    da empresa (`LISTA DE PRESENÇA\` copiadas para
    `templates/listas_presenca/` + mapeamento em `registry.json`) — o
    preenchimento é feito via **Excel COM** na cópia (preserva logo e
    formatação) e convertido para PDF. NRs sem modelo recebem um **layout
    padrão** com logo da empresa, dados da configuração e grade de
    assinaturas.
  - **Controle por lista**: serial único `LP-{ano}-{seq}`, status
    (Pendente/Parcial/Assinada com badges e contadores), PDF salvo em
    `data/listas_presenca/`, upload da **lista assinada** escaneada
    (PDF/JPG/PNG até 50 MB) que muda o status para Assinada, download e
    remoção do anexo.
  - Permissões: admin e emissor editam; consulta apenas consulta.
  - Auditoria: gerar, assinar e excluir listas.
- `src/core/presenca_repo.py` + `src/core/presenca_generator.py` +
  `src/web/routers/presencas.py` + templates (lista, nova com prévia,
  detalhe).
- `test_web_presencas.py` (31 checks): rotas mockadas (28 P01–P28) + E2E
  real com Excel gerando exemplos de modelo (NR-01, NR-06) e layout padrão
  (NR-33) em `comparacao_listas/` para conferência manual.

## [1.35.0] - 2026-09-15

### Adicionado
- **Certificados PPTX da técnica de segurança (NR-06, NR-12, NR-18, NR-35)**:
  os modelos PowerPoint usados pela técnica agora são suportados de ponta a
  ponta, sem alterar texto, design ou o conteúdo programático:
  - `tools/prepare_nr_pptx.py`: converte os originais de `MODELOS NR pptx\`
    em modelos com tokens (`{{NOME}}`, `{{CPF}}`, `{{DIA}}/{{MES}}/{{ANO}}`)
    preservando toda a formatação, salvando em
    `templates/certificados_pptx/NR-XX.pptx` (originais intocados; pode ser
    reexecutado a qualquer momento).
  - `src/core/pptx_certificate_service.py`: preenche os tokens (nome em
    caixa alta, CPF do cadastro, data por extenso no corpo **e** na
    assinatura) e adiciona o número do certificado (ex.: `CERT-000491`) em
    cinza, pequeno, no canto inferior direito de todos os slides; converte
    para PDF via PowerPoint.
  - Gancho em `CertificateService`: se existir
    `templates/certificados_pptx/NR-XX.pptx`, a emissão usa o modelo PPTX;
    senão, o fluxo JSON/ReportLab atual. Portal, desktop, emissão em lote e
    importação de planilha ganham automaticamente (todos usam o mesmo
    serviço), com histórico, pastas por funcionário e espelhamento em rede
    funcionando como antes.
  - A carga horária impressa nos modelos permanece a do texto original
    (fixa); a carga digitada continua registrada no histórico.
- `test_pptx_certificados.py` (33 checks): parte unitária (tokens,
  formatação por run, datas) + E2E gerando os 4 PDFs reais e copiando para
  `comparacao_pptx/` para conferência manual.

## [1.34.0] - 2026-09-15

### Adicionado
- **Portal — Fase 4 concluída (v1.34.0)**:
  - **Backup** (admin): botão "Fazer backup agora" + lista dos backups
    existentes (nome, tamanho, data). Sem restore pela web (decisão de
    projeto — restaurar pelo desktop ou com o portal desligado).
  - **Auditoria** (admin): nova tela com busca e paginação lendo o
    `audit_log`; agora também registramos emissões (certificado, lote,
    crachás, cartões, ASO), abertura de ficha EPI, importações (4 tipos),
    criar funcionário, salvar configurações, backup manual e todas as
    operações de Frota.
- **Frota — Checklist semanal de veículos leves (2.29.5)**: formulário no
  portal replica o papel da empresa (itens 1.1–1.19, 2.1–2.9 e 3.1–3.6 ×
  dias 2ª a sábado, S/N), "Pode-se operar com segurança?", observações por
  dia, motorista e líder. Gera PDF preenchido no formato do formulário
  (`data/frota/checklists/`, serial CKL-{ano}-{seq}) com histórico no
  veículo e download.
- **Frota — Notas fiscais e custo (2.29.6)**: abastecimentos aceitam
  **Litros** e **Valor**; anexo de NFs (PDF/imagem) por abastecimento com
  download; ficha do veículo com total abastecido, **média KM/L real**
  (cruzando movimentações) e custo por km; exportação da lista de
  abastecimentos para Excel.
- **Frota — Manutenção preventiva por KM**: itens com intervalo (ex.: troca
  de óleo a cada 10.000 km), progresso calculado pelas movimentações,
  conclusão com KM do serviço e aviso no menu Vencimentos (itens próximos/
  vencidos por KM).
- **Frota — Campos novos do veículo**: cor, ano, carroceria (hatch/sedan,
  apenas carros), fim do contrato de aluguel (apenas alugados), KM/L da
  ficha técnica e **foto do veículo** (miniatura na lista e na ficha).
- **Dashboard**: cards de frota (veículos cadastrados, saídas em aberto e
  custo de abastecimento do mês) para quem tem acesso ao módulo.

### Removido
- ROADMAP: item 2.1 "Drive Mapeado" (obsoleto — o portal web na rede já
  atende o caso de uso).

## [1.33.0] - 2026-09-14

### Adicionado
- **Portal Web — módulo Frota (ROADMAP 2.29, blocos 2.29.1 a 2.29.4)**:
  gestão completa de veículos com banco próprio (7 tabelas) e permissões
  (admin/emissor escrevem, consulta lê).
  - **Cadastro de veículos**: tipo (Caminhão com subtipos Caçamba/Munck/
    Plataforma, Pickup, Carro, Van, Empilhadeira, Retroescavadeira, Outros),
    placa obrigatória exceto Empilhadeira/Retroescavadeira, próprio ou
    alugado (com contratante), empresa do veículo (cadastro próprio) e
    pasta virtual de documentos (CRV, CRLV, contratos, inspeções).
  - **Solicitação de Abastecimento**: PDF com logo e dados da empresa,
    serial único `AB-{ano}-{sequência}` (sequência global que nunca
    reinicia), fornecedor posto (Nome/CNPJ/Endereço com cadastro próprio),
    combustível (Gasolina/Álcool/Diesel/Arla/GNV/ARLA+Diesel), data,
    viagem/serviço, KM, observações, veículo da lista, condutor digitado e
    campos de assinatura (condutor + aprovação do superior).
  - **Saída/Entrada de veículos**: registro de saída (data, hora, KM
    inicial, destino, motivo, obs, motorista, autorizado por) e entrada
    posterior (data, hora, KM final — não pode ser menor que o inicial),
    com KM rodado calculado.
  - **Laudos e documentos com vencimento**: upload do arquivo + tipo
    (Certificado Final, CRLV, Fumaça Preta, Laudo de Avaliação, Laudo
    Eletromecânico, Plano de Manutenção, Seguro, Outro) + data de validade,
    com badges de status e download; **integrado à aba Vencimentos e aos
    contadores do dashboard** (vencidos/7 dias/30 dias).
  - Listas com busca e paginação; ficha do veículo reúne documentos,
    laudos, movimentações e abastecimentos.

## [1.32.0] - 2026-09-14

### Adicionado
- **Portal Web — dashboard estilo tela inicial do desktop**: logo da empresa
  (nova rota `/logo.png`), data completa + relógio, boas-vindas, 3 cartões de
  resumo (certificados / funcionários / NRs), atalhos rápidos e aniversariantes
  do dia e do mês. Chips de vencimento e tabelas por NR/mês continuam
  disponíveis no painel recolhível "Ver indicadores".
- **Portal Web — tela de Configurações (somente admin)**: espelho da tela do
  desktop — Dados da Empresa (CNPJ e Registro MTE com formatação e validação),
  Segurança (senha de restauração de backup), Backups (intervalo, cópia
  externa, rede e Tarefa Agendada do Windows), Documentos em Rede (com botão
  "Sincronizar Agora") e Diagnóstico com visualização/limpeza do log de erros.
  Aparece no menu apenas para administrador.
- **Confirmação com lista de nomes antes de emissões em massa**: ao emitir
  certificados em lote, crachás ou cartões, um popup mostra os selecionados
  (nome + CPF) para conferir antes de confirmar.

### Alterado
- **Portal Web — Crachás e Cartões ganharam busca e paginação** (20 por
  página, páginas numeradas), acompanhando o padrão das demais listagens.

## [1.31.1] - 2026-09-11

### Corrigido
- **Portal Web não depende mais do desktop para importar funcionários**:
  `excel_importer` importava `src.ui.pages.funcoes`, que arrastava
  customtkinter (interface gráfica). No servidor sem desktop, o POST de
  importação de funcionários falharia. A lógica de `funcoes.json` foi
  extraída para `src/utils/funcoes_store.py` (a página desktop importa
  daí também — sem mudança de comportamento).

### Alterado
- **`requirements-web.txt` virou auto-suficiente para o servidor**: além das
  dependências web, inclui as bibliotecas core usadas pelo portal (pydantic,
  reportlab, pillow, pymupdf, python-pptx, apscheduler, comtypes etc.) com
  pisos de versão compatíveis com Pythons novos. O `requirements.txt`
  (desktop, com pins exatos) continua intocado — instalar os dois juntos no
  servidor podia abortar o pip inteiro por causa de pins sem build para o
  Python do servidor (ex.: `pyinstaller==6.8.0`).
- `INICIAR-PORTAL.bat` e `INSTALAR_PORTAL.bat` instalam apenas
  `requirements-web.txt` e o teste de dependências agora importa também os
  4 importadores de planilha (pega acoplamentos como o de cima).

## [1.31.0] - 2026-09-11

### Corrigido
- **Portal Web — tela "Novo funcionário" voltou a abrir**: a rota
  `/funcionarios/novo` estava declarada depois de `/funcionarios/{emp_id}` e o
  FastAPI capturava "novo" como se fosse um ID (erro `int_parsing` ao tentar
  cadastrar).

### Alterado
- **Portal Web — Cartões de bloqueio: formulário adapta-se ao modelo**:
  campo **Setor**, colunas **Matrícula** e **Papel** e a linha "Este modelo
  usa…" aparecem somente quando o modelo selecionado realmente usa o campo
  (lido dos placeholders do PPTX); modelos JSON continuam pedindo apenas
  telefone/foto. A emissão também só envia as opções que o modelo usa.

### Adicionado
- **Deploy**: `INICIAR-PORTAL.bat` na raiz (sobe o portal na rede; aceita a
  porta como argumento, ex.: `INICIAR-PORTAL.bat 80` para `http://normatech`
  sem `:porta`). `deploy\web\INSTALAR_PORTAL.bat` com porta configurável
  (`set PORT=80`), correção do teste de dependências (uvicorn) e auto-start do
  serviço NSSM. `docs/PORTAL/02-DEPLOY_SERVIDOR.md` atualizado (porta 80,
  nome `normatech` na rede, troubleshooting de porta ocupada).

## [1.30.1] - 2026-09-11

### Alterado
- **Portal Web — polimento de UI/UX em todos os módulos**:
  - Layout fluido (fim da largura fixa 1080px) e contorno preto de 1px em todas
    as tabelas.
  - **Certificados**: campo de funcionário virou **busca com dropdown** (digita
    nome/CPF e clica no resultado); trocar a NR recarrega a página e os campos
    extras agora correspondem sempre à NR selecionada (ex.: Tipo de brigada);
    campos opcionais ficam em menu "Campos adicionais (opcional)" abre/fecha.
  - **Emissão em lote**: busca e seletor **ver por página (10/20/25/50) junto à
    tabela**, com paginação no navegador que preserva os ajustes individuais
    digitados nas linhas fora da página.
  - **Funcionários**: seletor de itens por página (10/20/25/50); no perfil,
    botão **Voltar largo no topo** do cartão e atalho para as fichas de EPI.
  - **Paginação numerada** ("Página X de Y" + links 1 2 3 …): Funcionários,
    Histórico, Vencimentos, ASOs e EPI.
  - **Histórico**: anexo de documento assinado em menu sanfona com área de
    upload estilizada (mostra o nome do arquivo escolhido).
  - **Vencimentos**: painéis de resumo por severidade (vencidos/7/30 dias)
    clicáveis, aplicando o filtro correspondente.
  - **EPI**: filtro por situação (Abertas/Fechadas/**Itens devolvidos** — ficha
    aberta com todos os itens devolvidos), seletor 10/20/25/50, paginação,
    página **/epi/funcionario/{id}** com todas as fichas do funcionário (link na
    lista e no perfil), badge azul "Itens devolvidos" e campo "QTD devolvida"
    **desabilitado automaticamente** quando a devolução do item é marcada Total.

## [1.30.0] - 2026-09-11

### Adicionado
- **Portal Web — Fase 3 concluída (Cartões, Importações e Integrações no navegador)**:
  - Aba **Cartões de Bloqueio**: emissão de lotes com todos os modelos (JSON/ReportLab
    e PPTX com setor, líder/liderado e matrícula obrigatória preenchida só na emissão —
    PPTX exige PowerPoint no servidor), saída em folha única ou um cartão por página,
    importação da lista de bloqueios (.xlsx) pré-selecionando funcionários e listagem
    dos PDFs gerados em `data/cartoes` (LOTES + pasta por funcionário) com ver/baixar.
  - Aba **Importações**: os 4 importadores do desktop no navegador — funcionários
    (colunas A–I), certificados em lote com **prévia antes de emitir** (cria
    funcionários inexistentes; sem CPF registra sem PDF), ASOs em lote (A/P/M/R/D) e
    lista de bloqueios de cartões — com modelos oficiais de `MODELOS DE IMPORTACAO/`
    para download.
  - Aba **Integrações**: integrações funcionário/empresa com tipo livre, datas e
    observações (status Em dia/Vencida pela mesma regra do desktop), CRUD de
    **empresas clientes** (nome única, CNPJ, exclusão protegida com integrações
    vinculadas) — alimenta a aba Vencimentos.
- Menu do portal completo (Cartões, Integrações e Importações só para
  admin/emissor; consulta segue só leitura).

### Alterado
- `requirements-web.txt`: adicionado `openpyxl` (importações .xlsx no portal).

## [1.29.0] - 2026-09-11

### Adicionado
- **Portal Web — Fase 3 parte 2 (EPI e Crachás no navegador)**:
  - Aba **EPI**: lista de fichas, nova ficha com itens (C.A./descrição/qtde/data),
    ficha com situação por item (Total/Parcial/Pendente), **devolução pelo
    navegador** (regenera a ficha e emite o Termo de Devolução), ver/baixar PDF,
    anexos múltiplos (upload/baixar/excluir) e fechar/reabrir ficha.
  - Aba **Crachás**: emissão em lote pelo navegador com os mesmos bloqueios do
    desktop (foto, NR válida e ASO dentro da validade; bloqueados aparecem com
    o motivo), templates Altec paisagem/vertical, tamanho real ou reduzido,
    PDF A4 com guia de corte, ver/baixar inline e por crachá gravado.
- Menu do portal com Vencimentos, ASO, EPI e Crachás (consulta só leitura).

## [1.28.0] - 2026-09-11

### Adicionado
- Portal Web (Fase 3, parte 1): aba **Vencimentos** no navegador — todos os certificados, ASOs e integrações com vencimento, cards de totais (vencidos / próximos 7 / próximos 30 dias) e filtros por NR, período e busca.
- Portal Web: aba **ASO** — lista com busca e status, cadastro de novo ASO (gera PDF numerado com moldura), documento do médico anexado (embutido no PDF em capa + moldura), ver/baixar PDF e do documento, remover documento (volta ao placeholder).

### Alterado
- Menu do portal reorganizado: Dashboard, Certificados, Emissão em Lote, Funcionários, Histórico, Vencimentos, ASO e Usuários (cada papel vê apenas o que pode).

## [1.27.0] - 2026-09-11

### Adicionado
- Portal: Emissão em Lote — escolha a NR, marque vários funcionários (sem CPF fica bloqueado), defina data/carga/validade/descrição do lote com ajuste individual por funcionário, e emita tudo de uma vez com página de resultado (números gerados + Ver/PDF + erros).
- Menu "Emissão em Lote" visível apenas para Admin/Emissor; Consulta continua somente leitura.

## [1.26.0] - 2026-09-11

### Adicionado
- Portal: botão "+ Novo funcionário" na lista (admin/emissor).
- Portal: PDF visível no navegador — "Ver no navegador" no detalhe do certificado e "Ver" no Histórico (abre inline, sem baixar).
- Portal: "Visualizar prévia" no formulário de emissão — abre o PDF de prévia em nova aba sem gravar registro nem consumir numeração.

### Alterado
- Nenhuma mudança no app desktop nesta versão.

## [1.25.0] - 2026-09-11

### Adicionado (Portal Web — Fase 2)
- **Funcionários no portal**: lista com busca e paginação, ficha completa (dados SESMT), novo/editar com validação, upload de foto 3x4 e documentos (qualquer formato até 50MB, baixar/excluir).
- **Certificados no portal**: emissão pelo navegador (funcionário, NR com carga/validade/descrição e campos extras do modelo), página de detalhe e download do PDF. PDF salvo na pasta do funcionário com espelhamento em rede.
- **Histórico no portal**: filtros (busca, NR, período, assinado) e paginação; anexar documento assinado (PDF/JPG/PNG), baixar e remover.
- **Permissões**: papéis Consulta navegam em modo somente leitura (Admin/Emissor operam).

## [1.24.1] - 2026-09-11

### Corrigido
- Portal não abre mais com "Internal Server Error": o servidor passou a ser o uvicorn (ASGI, padrão do FastAPI). O waitress é WSGI e era incompatível com o FastAPI.
- Validado com servidor HTTP real (uvicorn + httpx): login, troca de senha obrigatória, dashboard e logout funcionando ponta a ponta.

## [1.24.0] - 2026-09-10

### Adicionado
- **Portal Web — Fase 1**: login com 3 papeis (Admin/Emissor/Consulta), dashboard de indicadores, gestao de usuarios e auditoria — acesso pelo navegador ao MESMO banco do desktop.
- Usuario `admin` criado no 1o boot com senha provisoria (console + `data/web_admin_provisorio.txt`); troca de senha obrigatoria no 1o acesso.
- Rate-limit de login (5 tentativas / 5 min) e auditoria de acoes (tabela `audit_log`).
- `run_web.py` (FastAPI + waitress; `--host 0.0.0.0` para o servidor, `--reset-admin`, `--sem-backup`).
- `requirements-web.txt` (dependencias do portal, separadas do desktop).
- Scripts de servidor em `deploy/web/`: INSTALAR_PORTAL, ATUALIZAR_PORTAL, ZERAR_DADOS e REMOVER_PORTAL.
- `python run_web.py` nao afeta o app desktop; backup automatico compartilhado quando ativo.

## [1.23.0] - 2026-09-10

### Adicionado
- Emissão em Lote de Certificados NR (item 2.26): nova página "Emissão em Lote" com seleção de NR, seleção de funcionários com busca/paginação, validação automática (sem CPF = bloqueado), edição em lote (data, carga horária, validade, descrição e campos extras do template), edição individual por funcionário, preview antes de emitir e geração com salvamento na pasta do funcionário + espelhamento em rede.

### Adicionado (validade)
- Validade por certificado: o lote (ou a edição individual) pode definir uma validade em meses própria, respeitada em Vencimentos, painel de indicadores, toast, crachás e na pasta 00_Certificados_OLD da rede (vazio = usa a validade do template).

### Alterado
- Nenhuma janela do sistema pode ter mais de 720px de altura (limite global); janelas menores: Novo/Editar Funcionário, Ficha de EPI (itens/gerenciar/devolução/anexos), Adicionar Função, Empresas e Nova Integração.

## [1.22.7] - 2026-09-10

### Corrigido
- Digitacao de datas (nascimento, admissao), CPF e telefone nao embaralha mais: a formatacao agora acontece ao sair do campo (ou Enter), nao a cada tecla.
- Menu Configuracoes abre imediatamente (verificacao da tarefa agendada passou para segundo plano).
- Dialogos de cartoes de bloqueio/crachas (revisao da emissao, preview e resultado) nao travam mais o programa - mesmo ajuste da v1.22.6 aplicado a todos os dialogos, com reexibicao forcada caso a janela nasca oculta.

## [1.22.6] - 2026-09-10

### Corrigido
- Janela de Nova Integração/Empresas abria e sumia e o programa parava de receber cliques: o grab modal agora só é aplicado depois que a janela está estável (dança interna de título do CustomTkinter), com lift/focus e liberação segura ao fechar.
- Erro "unknown option 0.0" ao rolar o preview de cartões em PDF.

## [1.22.5] - 2026-09-10

### Corrigido
- Erro ao salvar NOVA integracao: o autocomplete passava um objeto e o dialogo esperava dicionario (TypeError silencioso)

### Alterado
- Dialogo Nova Integracao menor (440x300) e Cadastro de Empresas menor (370x240)
- Tela de funcionario menor (460x600) e TODAS as janelas do sistema agora podem ser redimensionadas
- Data de validade da integracao vem preenchida com 1 ano a partir de hoje (editavel)

## [1.22.2] - 2026-09-10

### Corrigido
- Placeholders das barras de busca agora aparecem de verdade (bug do CustomTkinter: placeholder nunca era ativado em campos com variavel de texto). Ativo nas buscas de Historico, Funcionarios, Funcoes, Vencimentos, ASO, Cartoes, Integracoes e no autocomplete ? a dica some ao digitar e volta quando o campo esvazia; o texto de dica nunca e pesquisado nem salvo.
- Dialogo de Nova/Editar Integracao ficava com o conteudo cortado (Tipo, Datas e botao Salvar fora da janela) em telas com scaling alto ? formulario agora rolavel com rodape fixo e a busca nunca perde o botao Salvar.

### Alterado
- Todos os dialogos do sistema agora ajustam o tamanho pelo scaling da tela (23 dialogos), limitado ao tamanho do monitor.

# Changelog

## [1.22.4] - 2026-09-10

### Corrigido
- **"Empresa nao encontrada" ao salvar integracao**: o dialogo procurava a empresa pelo nome numa funcao que so aceita id ? nenhuma integracao chegava a ser salva. Agora a busca por nome (tolerante a maiusculas/acentos) encontra a empresa correta.

### Alterado
- Dialogos de Nova Integracao e Empresas abrem com tamanho menor (continuam redimensionaveis e com conteudo rolavel).

## [1.22.3] - 2026-09-10

### Corrigido
- **Pesquisa com placeholder**: ao digitar no campo de busca, o texto da dica era gravado junto (bug do patch de placeholder do CustomTkinter com `textvariable`), fazendo a busca nao filtrar / nao encontrar nada. Agora a dica nunca interfere enquanto o campo esta com foco.
- **Nova Integracao abria vazia**: o dialogo de nova integracao travava ao criar (variaveis de Tipo/Observacoes lidas de registro inexistente), deixando a janela sem campos e sem botoes.
- **Botoes Salvar/Cancelar/Fechar fora de vista**: dialogos com conteudo expansivel empurravam o rodape para fora da janela (Nova Integracao, Empresas, Imprimir/Preview de cartoes). Rodapes agora ficam sempre visiveis.

## [1.22.1] - 2026-09-10

### Corrigido
- Placeholders dos campos agora ficam visíveis: a cor padrão do CustomTkinter (cinza claro) tinha contraste baixo demais e sumia sobre o fundo dos campos — cor sobrescrita globalmente para um tom mais escuro/legível (acompanha o tema claro/escuro).

### Alterado
- Diálogo "Empresas" (Integrações): rótulos "Nome da empresa" e "CNPJ (opcional)" acima dos campos de cadastro rápido.


## [1.22.0] - 2026-09-09

### Adicionado
- Menu **Integra??es (F?bricas de Clientes)** (roadmap 2.25): cadastro de integra??es por empresa vinculadas ao funcion?rio (empresa, tipo, data de in?cio e data de validade), com cadastro/gest?o de empresas (nome, CNPJ) e status "Em dia"/"Vencida" na lista.
- Integra??es vencendo aparecem no menu **Vencimentos** (filtro INTEGRA??O, contagem nos cards, sem bot?es Emitir/ASO), no painel de indicadores e no toast de inicializa??o.
- Seletor **"Por p?gina"** (10/20/50/100) nas listas de Hist?rico, Funcion?rios, Fun??es e Vencimentos (j? existia em Cart?es).

### Alterado
- Execut?vel renomeado para **NormaTech.exe** (pasta dist\NormaTech); ATUALIZAR.bat atualizado e aceita instala??es antigas em CertificadosNR.
- Placeholders intuitivos nas barras de busca (mantidos e adicionados nos novos di?logos).

## [1.21.1] - 2026-09-09

### Corrigido
- **Gap entre a lista e a paginação (todas as abas)**: o frame de botões de
  página do `PaginationBar` era criado sem altura definida e, com
  `pack_propagate(False)`, travava nos 200px default do CTkFrame — com o
  scaling da tela, a barra ficava ~400px de altura e empurrava a paginação
  para longe da lista. Agora a barra nasce com a altura correta (34px) e a
  lista preenche todo o espaço até ela
- Removidos também os cálculos-manuais de altura das listas
  (`_fit_scroll_height`) das páginas — o layout por grid passa a mandar

## [1.21.0] - 2026-09-08

### Adicionado
- **ASO com moldura Altec no PDF**: o documento do médico (PDF ou imagem)
  agora entra em páginas A4 com cabeçalho/rodapé Altec — logo, empresa,
  "ASO nº — Tipo — Documento do médico" e "Página X de Y" — com o conteúdo
  encaixado na área central (antes ia solto, sem identidade)
- **Lista de backups mais limpa**: mostra apenas os **últimos 30** backups
  (com aviso quando existem mais) e nova coluna **Data e Hora** legível
  (dd/mm/aaaa HH:MM:SS) para cada backup
- **Seta de rolagem na sidebar**: "▼ role" discreto no rodapé indica quando
  há mais itens abaixo e some ao chegar no fim

### Corrigido
- **Lista flutuante do autocomplete resolvida**: a lista de nomes agora
  esconde quando o foco sai dela (Alt-Tab, clique fora), quando a página é
  trocada (inclusive via atalhos Ctrl+N) e quando o campo é limpo — não
  fica mais órfã sobre a tela

## [1.20.1] - 2026-09-08

### Corrigido
- **Tabelas/listas quebradas (regressão v1.19.0)**: aninhar um
  `CTkScrollableFrame` horizontal dentro de outro vertical colapsava o
  conteúdo (tabela virava um quadro pequeno e cortado). O `ScrollListFrame`
  agora usa **um único canvas** com scroll vertical + barra horizontal
  manual: sem overflow a tabela estica até a largura disponível (como
  antes da v1.19.0); com conteúdo mais largo que a janela, a barra
  horizontal ativa de verdade (Shift + roda do mouse também rola).
  Componente único — histórico, funcionários, funções, backups, cartões,
  ASO e diálogos de EPI sem nenhuma mudança de código.

## [1.20.0] - 2026-09-08

### Adicionado
- **Guia convertido só no build (2.24)**: o `build_exe.py` agora converte
  `templates/GUIA_NORMATECH.docx` → `GUIA_NORMATECH.pdf` durante o build
  (Word da máquina de desenvolvimento); o cliente só recebe o PDF pronto —
  sem Word COM no cliente, sem travamentos. Sem PDF pronto, o app usa o
  gerador ReportLab embutido (fallback silencioso)
- **ASOs vencidos em pasta própria (2.24)**: na rede, ASO vencido vai para
  `{Func}/ASOs/Vencidos/` e a cópia antiga em `ASOs/` é movida (mesmo padrão
  dos certificados `00_Certificados_OLD`); arquivos locais ficam intactos

### Corrigido
- Linha divisória da tela inicial agora fica **entre o logotipo e o bloco
  data+hora** (data em cima, hora embaixo) — não mais entre data e hora (2.24)

### Alterado
- Barra lateral com **scroll** — todos os itens ficam acessíveis mesmo com a
  janela pequena (versão permanece fixa no rodapé) (2.24)

## [1.19.0] - 2026-09-08

### Adicionado
- **Ajuda na sidebar (2.23)**: nova linha "Ajuda (F1)" na barra lateral — abre
  o Guia de Introdução (mesma ação do F1 e do botão da tela inicial)
- **Guia em DOCX editável (2.23)**: o guia agora nasce de
  `templates/GUIA_NORMATECH.docx` — quando o arquivo existe e é mais novo que
  o PDF, o app converte via Word (COM) automaticamente; sem Word ou sem docx,
  cai no gerador ReportLab embutido (fallback silencioso). Para editar o guia:
  altere o .docx no Word (ou regenere com `python tools/make_guia_docx.py`)
- **Códigos de tipo na importação de ASOs (2.23)**: coluna Tipo aceita
  `A` Admissional, `P` Periódico, `M` Mudança de Função, `R` Retorno ao
  Trabalho e `D` Demissional (nomes completos continuam aceitos); modelo
  Excel atualizado com legenda
- **Scroll horizontal em todas as tabelas/listas** (histórico, funcionários,
  funções, backups, cartões, ASO, fichas e diálogos de EPI): nada mais sai
  cortado em janelas estreitas

### Corrigido
- Data de entrega na ficha de EPI voltava com "—" ao adicionar item — agora
  vem com a data atual (2.23)
- Dropdown do autocomplete podia ficar flutuando na tela ao fechar o diálogo
  pai (Novo ASO etc.) — agora é destruído junto (2.23)
- CNH E.A.R. no cadastro: legenda corrigida para "Exerce Atividade Remunerada"
  (2.23)

### Alterado
- Tela inicial: data e hora em destaque ao lado do logotipo, separados por
  linha divisória fina (2.23)
- Tela de backups: "Último Backup automático" agora mostra data **e hora**
  (2.23)

## [1.18.0] - 2026-09-08

### Adicionado
- **Guia de Introdução (2.21)**: novo PDF amigável para o usuário final gerado
  pelo próprio sistema (`data/GUIA_NORMATECH.pdf`) cobrindo funcionários,
  certificados, vencimentos, cartões, crachás, ASO, EPI, backups, rede,
  configurações e atalhos; aberto pelo novo botão "Guia de Introdução" na tela
  inicial ou pela tecla **F1** em qualquer tela
- **Espelhamento completo validado (2.20)**: teste de integração garante que o
  `Sincronizar Agora`/sync de inicialização copia 100% dos tipos de documento
  para a rede (certificados, assinados, outros, cartões e lotes, ASOs, fichas
  e termos de EPI, crachás e lotes) na estrutura `{Funcionário}/...`

## [1.17.0] - 2026-09-08

### Corrigido
- **Ficha de EPI — PDF refeito (2.22)**: títulos das tabelas não sobrepõem mais
  o cabeçalho; linha de devolução agora tem espaço próprio e fica legível
  ("Devolvido: 2/5 (Parcial) em dd/mm/aaaa" — verde quando Total, laranja
  quando Parcial); fichas com muitos itens quebram para uma nova página
  repetindo o cabeçalho da tabela
- **Devoluções preservadas ao editar itens**: ao editar a ficha, as devoluções
  são reagrupadas por conteúdo do item (C.A. + descrição) em vez de posição,
  evitando que remover/reordenar itens desloque devoluções para o item errado
  (quantidade reduzida abaixo do devolvido descarta a devolução)

### Alterado
- Lista de fichas de EPI indica "tudo devolvido"/"devolução parcial"/"sem
  devolução" e exibe badges "TUDO DEVOLVIDO"/"PARCIAL" por ficha

## [1.16.0] - 2026-09-08

### Adicionado
- **Documento do ASO embutido no PDF**: ao anexar ou digitalizar o ASO, o
  documento do médico passa a ser incluído nas páginas seguintes do próprio PDF
  do ASO (capa do sistema + documento); ao remover o documento, o PDF volta à
  capa com espaço reservado
- **Configurações organizadas em seções recolhíveis**: 6 seções (Dados da
  Empresa, Segurança, Aparência e Notificações, Backups, Documentos em Rede,
  Diagnóstico) com esconder/mostrar — apenas a primeira abre por padrão
- **Devolução de EPI separada** (refinamento 2.16): novo botão "Devolução" por
  ficha registra itens como Pendente/Total/Parcial com data própria; gera
  **Termo de Devolução em PDF** para o funcionário assinar
  (`Devolucao - dd-mm-aaaa (EPI-XXXXXX).pdf`) e regenera a ficha com as
  devoluções registradas; se todos os itens forem devolvidos por completo,
  oferece fechar a ficha

### Corrigido
- **Salvar ficha de EPI**: diálogo de itens agora expande a rolagem
  corretamente; datas com ano de 2 dígitos são rejeitadas (antes viravam ano
  26); salvar com o PDF aberto em um leitor mostra mensagem amigável pedindo
  para fechar o arquivo; remover todos os itens pede confirmação
- **Formulário de itens da ficha**: colunas de devolução saíram do formulário
  de retirada (devolução é registrada depois, pelo botão próprio)

## [1.15.1] - 2026-09-08

### Adicionado
- **Bloqueio de emissão de crachás**: o crachá (paisagem e vertical) só é
  gerado para funcionário com foto cadastrada, pelo menos uma NR dentro da
  validade e ASO dentro da validade; na revisão da emissão o funcionário
  bloqueado aparece destacado em vermelho com os motivos e é pulado na geração
  (listado em "Pulados" no resultado)

### Alterado
- **NRs vencidas nunca entram no crachá**: checkboxes só oferecem treinamentos
  válidos (vencidas aparecem desabilitadas) e a geração filtra vencidas em
  qualquer caminho

## [1.15.0] - 2026-09-08

### Adicionado
- **Crachás em folha A4**: crachás (paisagem e vertical) agora saem em folha
  A4 com guia de corte tracejada — vários por folha (paisagem real 3/folha,
  vertical real 4/folha); PDF individual também em A4 com o crachá centrado
- **Tamanho reduzido 86x54mm**: opção na revisão da emissão para escalar o
  crachá ao tamanho de cartão de crédito sem alterar o layout (mais por folha)
- **Backup via Tarefa Agendada do Windows** (item 2.19): switch na aba
  Configurações para ligar/desligar backup diário com o programa fechado,
  horário configurável (padrão 12:00) e indicador de status da tarefa;
  registra via schtasks (NormaTechBackup) executando `--backup` headless

### Alterado
- `main.py` aceita `--backup` (backup sem interface, usado pela tarefa
  agendada); BackupManager não inicia agendador interno no modo headless

## [1.14.0] - 2026-09-05

### Adicionado
- **Crachá de Identificação vertical 7,8x12cm**: novo modelo
  `CRACHA-VERTICAL` na aba Cartões de Bloqueio — mesmo conteúdo do modelo
  paisagem (NRs com validade, ASO, emissão, assinatura) em layout retrato;
  dimensões lidas do template (qualquer card.json cracha pode definir
  largura/altura)

### Inalterado
- Modelo paisagem `CRACHA-ALTEC` (12x7,8cm) mantido intacto

## [1.13.0] - 2026-09-04

### Adicionado
- **Crachá de Identificação 12x7,8cm**: novo modelo `CRACHA-ALTEC` na aba
  Cartões de Bloqueio — réplica do modelo XLSX da ALTEC (título, foto 3x4,
  texto de autorização, tabela Capacitação/Data/Validade até 8 NRs, emissão
  editável, vencimento + número do ASO, campo de assinatura destacado e
  rodapé de proibição)
- **Revisão da emissão do crachá**: diálogo próprio com data de emissão
  (padrão hoje) e seleção de NRs por funcionário (pré-marcadas com as 8 mais
  recentes, limite máximo de 8), exibindo o ASO vigente
- **Gravação das emissões**: tabela `crachas` com numeração sequencial
  CRACHA-XXXXXX por funcionário; preview não consome numeração
- **Lote**: PDF único multipágina (data/crachas/LOTES) ou um PDF por
  funcionário (data/crachas/{Funcionario})
- **Rede**: crachás espelhados em {Funcionario}/Crachas e lotes em
  Crachas_Gerais

### Corrigido
- Dashboard: contagem de ASOs vencidos respeita apenas o ASO mais recente
  de cada funcionário (teste atualizado para a semântica correta)

## [1.12.0] - 2026-09-04

### Adicionado
- **Modelos de importação**: pasta `MODELOS DE IMPORTACAO/` com planilhas de
  exemplo (Funcionários A-I, Certificados A-C, Cartões de Bloqueio A-B e ASO
  A-E) + LEIA-ME com colunas e valores válidos; geradas por
  `tools/make_import_templates.py` (regenerável)
- **Importação de ASOs em lote**: botão "Importar Excel" na aba ASO — casa por
  CPF ou nome, valida tipo/data/validade por linha e gera os PDFs
  automaticamente com espelhamento na rede; linhas com erro não param a
  importação (resumo ao final)
- **ATUALIZAR.bat** (`deploy/`, copiado para `dist/` no build): atualiza o
  programa na máquina do cliente a partir da pasta "Atualizacao" — fecha o app,
  faz backup automático de `data/`, substitui os arquivos com `robocopy /MIR`
  **excluindo `data/`** e esvazia a pasta de atualização ao terminar

## [1.11.0] - 2026-09-04

### Adicionado
- **Novos campos do funcionário (2.16)**: Tipo Sanguíneo (lista), Data de
  Admissão (máscara dd/mm/aaaa), Registro CTPS e checkbox "Possui CNH com
  E.A.R." no cadastro
- **Import Excel colunas F-I**: Tipo Sanguíneo, Data de Admissão, Registro
  CTPS e CNH EAR (Sim/Não) com validação por linha; export ganha as mesmas
  colunas
- **Aba ASO (2.16)**: Atestado de Saúde Ocupacional com numeração sequencial
  (ASO-XXXXXX), tipo (Admissional, Periódico, Mudança de Função, Retorno ao
  Trabalho, Demissional), validade em meses (padrão 12) e PDF com espaço
  reservado para colar/digitalizar o exame real; anexar arquivo ou digitalizar
  direto pelo scanner; busca, paginação e download do documento
- **ASO em Vencimentos**: ASOs aparecem na aba Vencimentos (filtro NR "ASO"),
  no painel de indicadores da Home e no toast de vencimentos (certificados +
  ASOs que vencem em 7 dias); botão "ASO" no card emite direto para o
  funcionário
- **Ficha de EPI (2.16)**: botão "EPI" na linha do funcionário abre o gerente
  de fichas — cada ficha tem código próprio (EPI-XXXXXX), itens de Entrega
  (CA / Descrição / Qtde / Data / Visto) e Devolução (Qtde / Data / Visto),
  PDF A4 regenerável a cada edição com linhas em branco para assinatura à mão
- **EPI — anexos múltiplos**: fichas digitalizadas podem ser anexadas em
  várias versões (devoluções parciais) sem apagar as anteriores; status
  Em Aberto/Fechado alternável a qualquer momento
- **Rede**: ASOs e fichas de EPI espelhados na estrutura de documentos em rede
  (`{Funcionário}/ASOs` e `{Funcionário}/EPIs`)
- Atalho Ctrl+7 abre a aba ASO (Ctrl+8 Cartões, Ctrl+9 Importação em Lote,
  Ctrl+0 Backups)

### Corrigido
- SQL ambíguo (`created_at`) na listagem de ASOs com JOIN de funcionários

## [1.10.0] - 2026-09-04

### Corrigido
- **Digitalização em 2 máquinas (bug crítico)**: `ShowSelectItem` não existe na
  API WIA — agora lista scanners via DeviceManager; sem scanner → erro amigável,
  1 scanner conecta direto, 2+ abre o seletor nativo (`ShowSelectDevice`)

### Adicionado
- **Data de Nascimento (2.15)**: campo editável no cadastro de funcionários
  (máscara dd/mm/aaaa, validação de data real), coluna E no import Excel e
  coluna "Data Nascimento" no export
- **Aniversariantes na Home**: blocos "Aniversariantes de hoje" e
  "Aniversariantes do mês" com nome e dia
- **Data e hora atuais na Home**: relógio (HH:MM:SS) e data por extenso,
  atualizados a cada segundo
- **Toast de aniversário**: notificação no início do app quando alguém faz
  aniversário no dia

### Alterado
- Janela Cadastrar/Editar Funcionário com campos roláveis e botões fixos no
  rodapé (cabe em telas menores mesmo com o novo campo)

## [1.9.0] - 2026-09-04

### Adicionado
- **Pasta virtual universal (2.14)**: os "Outros documentos" do funcionário
  (botão Docs) agora aceitam **qualquer formato** (DOCX, XLSX, ZIP, MP4 etc.),
  com limite de **50MB** por arquivo (antes: 10MB e apenas PDF/JPG/PNG)
- **Validação de segurança no upload**: extensões executáveis/scripts
  (EXE, BAT, CMD, JS, VBS, PS1, MSI etc.) e tipos MIME correlatos são
  bloqueados; arquivos sem extensão também são rejeitados

### Alterado
- Tamanho exibido na lista de documentos em KB/MB conforme o arquivo
- Diálogo "Adicionar" abre para todos os arquivos (`*.*`)

## [1.8.2] - 2026-09-04

### Adicionado
- **Roadmap**: nova seção 2.14 "Expansão da Pasta Virtual do Funcionário" — envio de arquivos de qualquer formato (DOCX, XLSX, ZIP, etc.) com limite de 50MB por arquivo

## [1.8.1] - 2026-09-03

### Corrigido
- **Card duplicado em Vencimentos**: certificados antigos (emitidos antes do
  CPF ser cadastrado) geravam um segundo card do mesmo funcionário, pois o
  agrupamento usava o CPF/nome registrados no momento da emissão — agora
  agrupa apenas por funcionário, exibindo o snapshot mais completo
- **Vencimentos/Dashboard/toast contam apenas a última emissão de cada NR**:
  emissão renovada deixa de constar como vencida (renovação substitui a
  antiga no controle de vencimentos, indicadores da tela inicial e notificação
  de startup); card TOTAL renomeado para "TOTAL de certificados ativos"

## [1.8.0] - 2026-09-03

### Adicionado
- **Documentos em rede**: nova seção em Configurações — espelha certificados,
  cartões, certificados assinados e outros documentos em pasta/caminho de rede
  organizados por funcionário (`{Func}/Certificados/{NR}`, vencidos em
  `00_Certificados_OLD`, `{Func}/Cartoes`, `{Func}/Certificados Assinados`,
  `{Func}/Outros`, lotes em `Cartoes_Gerais`); sincronização no startup +
  botão "Sincronizar Agora"; toast e log de erro se a rede falhar
- **Documentos do funcionário ("Outros")**: botão **Docs** na aba Funcionários
  — identidade, CNH etc. salvos no banco (BLOB até 10MB, PDF/JPG/PNG) e
  espelhados na rede em `{Func}/Outros`
- **Nova estrutura de pastas local**: `data/certificados/{Func}/{NR}`,
  `data/cartoes/{Func}` + `data/cartoes/LOTES`, `data/assinados/{Func}`;
  migração automática única dos PDFs antigos de `CERTIFICADOS/` com
  atualização dos caminhos no banco (idempotente; não casados vão para
  `_ORFAOS`)
- **Contraste do modo escuro aumentado**: textos secundários, textos muted,
  bordas e verde de sucesso mais claros/legíveis

### Alterado
- **Botão do tema**: agora é uma linha "Tema" na barra lateral, acima de
  Configurações (antes sobreponha o botão hamburger no header)

## [1.7.1] - 2026-09-03

### Corrigido
- **Botão de tema visível com a sidebar aberta**: hamburger e tema dividiam
  a mesma célula do grid e se sobrepunham em alguns escalamentos; agora
  vivem em um header próprio (hamburger à esquerda, tema à direita)
- **Duplicação do content_frame**: `_build_sidebar` recriava a área de
  conteúdo e a Home a cada boot/troca de tema (frames empilhados)
- **Tela inicial rolável**: com o painel de indicadores aberto em telas
  pequenas o conteúdo era cortado — agora a página tem scrollbar
- **Botão "Mostrar/Ocultar indicadores" em destaque**: altura 36, fundo
  `surface` com borda e texto centralizado bold (antes era transparente e
  discreto demais)

### Alterado
- **Scrollbar visível nas listas**: novo `ScrollListFrame`
  (`src/ui/components/scroll_frame.py`) com trilho e thumb nas cores
  corporativas — aplicado nas listas do Histórico e dos Cartões de
  Bloqueio (a scrollbar do CTK é cinza flat e se confundia com a superfície)

## [1.7.0] - 2026-09-03

### Adicionado
- **Painel de indicadores na tela inicial**: vencidos, vencem em 7/30 dias,
  percentual de assinados, emissões por NR (top 5) e por mês (últimos 6) —
  com botão para ocultar/mostrar persistido entre sessões
- **Tema claro/escuro**: botão na sidebar (persistido em `data/appearance.json`,
  atalho Ctrl+T); paleta escura completa sem reiniciar o app
- **Atalhos de teclado**: Ctrl+1..9 navega entre as páginas, Ctrl+T alterna
  o tema, F5 atualiza a página atual
- **Visualizador do log de erros**: nova seção "Diagnóstico" na tela de
  Configurações com as últimas linhas de `data/error.log` e botões
  Atualizar/Limpar/Abrir Pasta
- **Filtro "Assinado" no Histórico**: Todos/Sim/Não combinável com os
  filtros existentes (texto, NR, período) e respeitado na exportação
- `HistoryRepository.get_dashboard_stats()` (indicadores do painel)
- Docs de planejamento: `docs/QR_CODE.md`, `docs/CI_GITHUB_ACTIONS.md`,
  `docs/MULTIUSUARIO.md`

## [1.6.0] - 2026-09-03

### Adicionado
- **Filtros no Histórico de Emissões**: além da busca por texto, a listagem
  agora filtra por **NR** (menu suspenso com as NRs existentes no banco) e por
  **período do treinamento** (De/Até em dd/mm/aaaa, campos opcionais);
  filtros combináveis entre si
- **Exportação da listagem**: botão "Exportar" exporta **todos os resultados
  dos filtros atuais** (não só a página visível) para **Excel (.xlsx)** ou
  **CSV (.csv)** — formato escolhido no diálogo de salvar; CSV com `;` e
  UTF-8 BOM para abrir corretamente no Excel brasileiro; colunas: Numero,
  NR, Funcionario, CPF, Data Inicio, Data Fim, Carga (h), Descricao, Assinado
- Novo `HistoryRepository.query()/count_query()/distinct_nrs()` (busca
  combinada texto + NR + período); `search/count_search` passam a delegar
- Teste `test_history_filters.py`: filtros (texto/NR/período/combinados),
  contagens, `distinct_nrs` e exportação xlsx/csv

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