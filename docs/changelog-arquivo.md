# CHANGELOG - HISTORICO COMPLETO (NormaTech)

> **NAO leia este arquivo inteiro.** Use busca (Grep) por numero de versao ou palavra-chave.
> As versoes mais recentes estao em `CHANGELOG.md` (raiz).
> Nota: versoes 1.66.x a 1.70.2 foram reconstituidas a partir das mensagens de commit
> e podem ter menos detalhe que o original.

## [1.65.1] - 2026-10-07

### Adicionado
- Notificacao interna: sino no cabecalho com badge e dropdown dos vencimentos urgentes (atualiza junto com o painel).
- Escolher cards do painel: botao de engrenagem que abre um popup, no lugar do menu recolhivel (interface menos poluida).

### Alterado
- Card de vencimentos do painel em vermelho forte, com contraste garantido entre fundo e texto.
- Pagina /vencimentos mostra a faixa 'Vencem em 8 a 30 dias'.
- Grafico de custos por veiculo x combustivel ordenado do veiculo que mais gasta para o que menos gasta.

## [1.65.0] - 2026-10-06

### Adicionado
- Configura├º├Áes: campos de relat├│rios por e-mail (SMTP: host, porta, usu├írio, senha, seguran├ºa TLS/SSL, remetente, destinat├írios) + periodicidade (mensal/trimestral/semestral/anual). O envio autom├ítico ser├í implementado em vers├úo futura.
- Ficha do funcion├írio: card ASO com lista de ASOs do funcion├írio, link para o PDF, bot├úo Atualizar e atalho ÔÇ£+ Gerar ASOÔÇØ j├í com o funcion├írio pr├®-selecionado.

### Corrigido
- Lista de presen├ºa no servidor: cadeia de fallback na exporta├º├úo para PDF (ExportAsFixedFormat ÔåÆ SaveAs PDF ÔåÆ exporta├º├úo por planilha com mesclagem), registrando em data/error.log qual m├®todo funcionou (com-pdf-metodo).
- Formul├írio de certificados n├úo perde os dados preenchidos quando a valida├º├úo falha; campo Descri├º├úo agora ├® textarea maior.
- Formata├º├úo/encoding das p├íginas de Romaneios (texto quebrado por mojibake).

## [1.64.0] - 2026-10-05

### Adicionado
- Painel: novo card opcional 'Certificados vencem em 30 dias' (contagem apenas de certificados, sem misturar ASOs), com toggle em Meu perfil > Cards do painel.
- 'Ver por p├ígina' (10/20/25/50) nas listas de Hist├│rico, ASOs, Crach├ís (lista e novo), Cart├Áes (lista e novo), Romaneios e Listas de Presen├ºa.

### Alterado
- Checkbox 'Treinamento de v├írios dias' agora come├ºa DESMARCADO (emiss├úo individual e em lote).
- Emiss├úo em lote: 'Ver por p├ígina' da lista de funcion├írios agora inicia em 10.

## [1.63.3] - 2026-10-05

### Corrigido
- Pr├®-visualiza├º├úo e 'Gerar exemplo' de certificados agora usam o template PPTX da t├®cnica quando existir (templates/certificados_pptx/NR-XX.pptx), igual ├á emiss├úo real; fallback para o PDF padr├úo (ReportLab) registrado no log em caso de falha do PowerPoint.

## [1.63.2] - 2026-10-05

### Alterado
- Diagnostico de erros COM: o erro original (hresult + detalhes e os caminhos do
  arquivo de entrada/PDF) agora e registrado em data/error.log antes da mensagem
  amigavel - cobre listas de presenca, romaneios e cartoes PPTX.

## [1.63.1] - 2026-10-05

### Adicionado
- Certificados: bot├úo "Gerar exemplo" gera um PDF de demonstra├º├úo (dados inventados) sem gravar no hist├│rico.
- Dashboard: cards modulares ÔÇö o usu├írio escolhe quais cards ver ("Escolher cards do painel"), prefer├¬ncia salva por usu├írio.
- Portal: log no console do servidor mostrando qual usu├írio acessou cada p├ígina.

### Alterado
- Emiss├úo em lote: carga, validade, descri├º├úo e campos extras ficam em menu recolh├¡vel (dados do lote mais limpos).
- Login: bot├úo de mostrar senha com melhor contraste.
- Edi??o de funcion?rio: foto atual exibida no topo direito, com bot├úo de upload estilizado.

## [1.63.0] - 2026-10-05

### Corrigido
- Certificados/Emiss├úo em lote: checkbox "Treinamento de v├írios dias" estava invertido (campo de data de in├¡cio aparecia quando desmarcado).
- Romaneios: p├ígina renderizava em branco no portal (bloco Jinja `content` vs `conteudo`); agora com estado vazio explicativo.
- Listas de presenca/Romaneios/PPTX: remo├º├úo do Mark-of-the-Web antes de abrir arquivos via Office COM (falha no servidor por Modo Protegido), Workbooks.Open sem UpdateLinks e retry de erros transitorios; novos scripts deploy/web/ATUALIZAR_PORTAL.bat (Unblock-File) e deploy/web/DESATIVAR_MODO_PROTEGIDO.bat.
- Certificados PPTX: falha do PowerPoint agora ├® registrada em log (pptx-fallback) e cai no template ReportLab sem interromper a emiss├úo.
- Dashboard: card grande de Vencimentos removido; stat-card "Vencem em 30 dias (vencimentos)" vis├¡vel somente ao setor Seguran├ºa.
- Usu├írios: card "Permiss├Áes por setor" reorganizado em lista compacta (um bloco por setor, tabela de m├│dulos).

## [1.61.0] - 2026-10-05

## [1.62.4] - 2026-10-05

### Corrigido
- Notificacoes do navegador: /api/vencimentos/resumo falhava com AttributeError (sqlite3.Row nao tem .get); campos notif/setor_usuario agora lidos com fallback seguro.

### Adicionado
- Testes de Validacao/test_web_v162.py cobrindo o endpoint de resumo de vencimentos (45 testes na su?te).


## [1.62.3] - 2026-10-05

### Corrigido
- Frota: relatorio geral de custos nao mostrava as paginas por veiculo (e as notas de consumo Pesados/Leves): a serie mensal agrupava datas dd/mm/aaaa como se fossem ISO (substr) e o periodo de 30 dias so gerava o bucket do mes corrente; datas agora normalizadas no SQL e buckets de periodo ajustados (30->2 meses, 90->4, 180->7).
- Listas de presenca: area de impressao calculada so pelas colunas referenciadas no registry cortava a paginacao (Pag i de N) e a coluna ASSINATURA do PDF; agora usa o range real da planilha.
- Usuarios: pagina /usuarios quebrava com TypeError (_SETORES_FLAT chamada como funcao).


## [1.62.2] - 2026-10-05

### Corrigido
- ValueError 'too many values to unpack' ao abrir qualquer pagina logado: o grupo Administracao do menu foi inserido dentro da tupla do grupo Controle (v1.61.0); reestruturado como grupo proprio.


## [1.62.1] - 2026-10-05

### Corrigido
- Portal nao subia (TypeError: require_user() missing 1 required positional argument): as rotas /perfil agora usam a dependencia padrao `auth.require_permission("dashboard")`. Bug introduzido na v1.59.0, so se manifestava ao executar create_app().
- Rota /perfil/foto e /perfil/foto/remover usavam `flash` inexistente no escopo (correto: `_flash`).


## [1.62.0] - 2026-10-05

### Adicionado
- Perfil: foto do usuario (enviar/remover em /perfil, exibida no perfil; PNG/JPG ate 3 MB, migra├º├úo idempotente `foto`/`foto_tipo` em users).
- Romaneios: captura de assinaturas (Resp. ALTEC e transportadora) direto no navegador (canvas) na ficha, salvas no banco e embutidas no documento (xlsx/PDF regenerado), com auditoria `assinar-romaneio`.


### Adicionado
- Certificados: datas multi-dia ÔÇö checkbox 'Treinamento de varios dias' no formulario (individual e em lote); o PDF imprime 'realizado de X a Y' quando a data de inicio difere da data de emissao (fluxos JSON/ReportLab e PPTX).
- Admin: editor de templates NR em /admin/templates (nome, carga minima, validade, descricao, riscos, conteudo programatico e campos extras), com backup .bak automatico, validacao antes de gravar, restauracao de backup e auditoria.

## [1.60.0] - 2026-10-02

### Adicionado
- Dashboard: card de vencimentos com contagens por per├¡odo (vencidos, 7/15/30 dias) e lista dos 5 itens mais urgentes, com link para /vencimentos.
- Notifica├º├Áes do navegador: endpoint /api/vencimentos/resumo e aviso no navegador (Notification API, com polling a cada 10 minutos) informando 'voc├¬ tem X vencimentos', estruturado por setor do usu├írio e respeitando a prefer├¬ncia de notifica├º├Áes do /perfil.

## [1.59.0] - 2026-10-02

### Adicionado
- Permissoes por setor customizaveis pelo admin em /usuarios (seguranca, comercial, compras, engenharia, financeiro, RH) ? regras setor->modulo por checkbox.
- Campo de setor por usuario (criacao e edicao rapida na lista de usuarios).
- Pagina /perfil (Meu perfil): editar nome, trocar senha (exige senha atual) e preferencia de notificacoes; link no cabecalho.

## [1.58.0] - 2026-10-02

### Corrigido
- Listas de presenca: erro "(-2147352567, 'Excecao.')" ao gerar PDF via Excel COM agora e traduzido para mensagem amigavel (arquivo aberto/bloqueado, Office ausente etc.), com ate 3 tentativas automaticas e fechamento garantido do Excel a cada tentativa. Mesmo tratamento aplicado ao PDF de romaneios (Excel) e cartoes PPTX (PowerPoint).

## [1.57.0] - 2026-10-02

### Adicionado
- Romaneios: novo m├│dulo do portal com p├ígina dedicada (busca + pagina├º├úo), serial ├║nico ROM-000001 exibido no documento, bloqueio/desbloqueio sem exclus├úo (tarja BLOQUEADO + auditoria) e registro de quem emitiu.
- Romaneios: documento gerado a partir do modelo xlsx (aba Romaneio) com PDF via Excel COM; dados de OS, cliente, ordem de compra, respons├ível, datas, transportadora (CNPJ/CPF), ve├¡culo/placa, motorista e assinaturas.
- Romaneios: itens por blocos (Equipamentos, Parafusos, Componentes) + blocos 'Outros' din├ómicos; campos C├│digo, Unidade, Qtd, Dimens├Áes, Peso, Tipo e Observa├º├Áes.

## [1.56.0] - 2026-10-02
## [1.55.0] - 2026-10-02

### Adicionado
- Emissor de Crach├ís: barra de busca por nome/CPF na p├ígina de emiss├úo, com pagina├º├úo e scroll vertical na tabela (item 1 da fase de UX).
- Emissor de Crach├ís: campo listando os requisitos de emiss├úo (foto, NR v├ílida e ASO v├ílido) acima da tabela.
- Emissor de Crach├ís: novo campo "Orienta├º├úo" (Vertical padr├úo / Horizontal); o gerador troca largura├ùaltura do modelo quando necess├írio.
- Cart├Áes de Bloqueio: barra de busca por nome/CPF na p├ígina de emiss├úo, com pagina├º├úo (sele├º├úo preservada) e scroll vertical na tabela.
- Cart├Áes de Bloqueio: pr├®-visualiza├º├úo em miniatura da propor├º├úo do cart├úo selecionado (largura ├ù altura + tipo do modelo).

### Alterado
- Cart├Áes de Bloqueio: lista de modelos sem informa├º├Áes t├®cnicas (tipo/dimens├Áes removidas do nome; exibidas na pr├®-visualiza├º├úo).
- Cart├Áes de Bloqueio: importa├º├úo de lista (.xlsx) movida para um submenu hide/show (details).

## [1.54.1] - 2026-10-02

### Adicionado
- Login do Portal Web: bot├úo para mostrar/ocultar a senha (­ƒæü/­ƒÖê) no campo Senha (item 5 da fase de UX).
- Edi├º├úo de funcion├írio: a foto atual (3x4) agora ├® exibida no formul├írio de edi├º├úo, abaixo do campo de upload.

### Alterado
- Emiss├úo em Lote: layout dos "Dados do lote" mais horizontal, em 4 colunas (2 colunas em telas estreitas) (item 7 da fase de UX).

## [1.54.0] - 2026-09-25

### Adicionado
- Configura├º├úo persistente para gerar o PDF da Solicita├º├úo de Abastecimento em 2 vias por folha A4 (Configura├º├Áes > Abastecimentos (Frota)); gravada no app_settings.json, sobrevive a rein├¡cios do navegador/servidor.
- Gera├º├úo integrada do documento em 2 vias (layout paisagem do prot├│tipo aprovado), com marca d'├ígua CANCELADO compat├¡vel.

### Alterado
- Dashboard: card de custo de abastecimento agora tamb├®m tem anima├º├úo de contagem e todas as anima├º├Áes foram reduzidas para 500 ms.
- P├ígina da Frota: cores distintas nos bot├Áes (Gr├ífico de custos, Empresas/Fornecedores, Exportar Excel, Exportar custos, Importar Excel).

## [1.53.0] - 2026-09-25

### Corrigido
- Itens extras de abastecimentos antigos ficavam fora dos relat├│rios de custos: backfill recalcula o total a partir do JSON gravado (2.40.1).
- Abastecimentos com data em formato inv├ílido sumiam dos gr├íficos/relat├│rios: datas legadas s├úo normalizadas para ISO na inicializa├º├úo (2.40.1).

### Adicionado
- Marca d'├ígua "CANCELADO" no PDF de solicita├º├úo de abastecimento bloqueada ÔÇö regenerada na hora ao visualizar/baixar e removida ao desbloquear (2.40.2).
- Lista de abastecimentos com menu ├║nico "Op├º├Áes" (Ôï») reunindo NF, Editar, Ver, Baixar, Bloquear/Desbloquear e Excluir (2.40.3).
- Prot├│tipo standalone com 2 c├│pias da solicita├º├úo por folha A4 (script na raiz ÔÇö n├úo integrado ao sistema) (2.40.4).

## [1.52.0] - 2026-09-25

### Adicionado
- Custo e consumo da frota (2.39): colunas KM/L (real) e KM/L padr├úo na tabela Resumo por ve├¡culo, com tooltip de nota sobre consumo (pesados/leves) ao manter o mouse;
- Per├¡odo do relat├│rio de custos: seletor (├║ltimos 30 dias / 3 meses / 6 meses / 12 meses) que afeta a p├ígina, os PDFs (geral e individual) e as exporta├º├Áes Excel;
- Disclaimers de consumo impressos nos PDFs de custos (nota resumida na p├ígina geral e nota completa por tipo nos relat├│rios individuais);
- Ordena├º├úo do Resumo por maior gasto total no per├¡odo (R$) e do gr├ífico por ve├¡culo.

### Corrigido
- P├ígina de custos n├úo abre mais quando a frota n├úo tem nenhum abastecimento no per├¡odo;
- Tabela Resumo e gr├ífico por ve├¡culo com rolagem (tabela ~10 linhas, gr├ífico com altura limitada).

## [1.51.0] - 2026-09-24

### Corrigido
- Abastecimentos: ordena├º├úo da lista agora ignora datas gravadas fora do padr├úo ISO (datas quebradas v├úo para o fim, recentes primeiro).
- "Ver"/"Baixar" do PDF de abastecimento n├úo servem mais c├│pia em cache do navegador (Cache-Control no-store + ?v=revis├úo).
- Custos da frota: ve├¡culo sem abastecimento volta a aparecer com 0 (n├úo mais "1" fantasma).
- PDF de custos: foto do ve├¡culo agora ├® renderizada (ImageReader faltava no import); tabelas paginadas n├úo colidem mais com o rodap├®; relat├│rio pode passar de uma p├ígina.
- Gr├ífico "Custos por ve├¡culo ├ù tipo de combust├¡vel" redesenhado em barras horizontais (nomes dos ve├¡culos leg├¡veis) e com os itens extras destacados.

### Adicionado
- Separador de milhar em KM e valores (210884 -> 210.884; R$ 1.720,52) nas listas, custos e PDFs.
- Relat├│rio de custos individual com se├º├úo pr├│pria de "Itens extras" (descri├º├úo, quantidade, valor e solicita├º├úo de origem) e valor gasto por m├¬s abaixo do gr├ífico.
- Relat├│rio de custos da frota com tabela "Valores por m├¬s" (por ve├¡culo) e pagina├º├úo multi-p├ígina.
- Novas cores de bot├Áes na lista de abastecimentos: Bloquear (vermelho), Editar (verde), NF (amarelo claro), Baixar (azul claro).

## [1.50.0] ÔÇö 2026-09-24

### Adicionado
- Abastecimento: postos tempor├írios (nome + CNPJ na pr├│pria solicita├º├úo, sem cadastro) e CNPJ validado no formato.
- P├ígina "Custos e consumo ÔÇö Frota": gr├íficos interativos dos ├║ltimos 12 meses (por m├¬s empilhado por ve├¡culo e por ve├¡culo segmentado por tipo de combust├¡vel + extras), com tooltip, download em PNG e links de exporta├º├úo.
- Relat├│rio de custos em PDF para diretoria (estilo institucional): p├ígina resumo da frota + uma p├ígina por ve├¡culo com foto, totais, mini gr├ífico 12 meses e divis├úo por tipo de combust├¡vel ÔÇö individual ou geral, aberto direto no navegador.
- Formata├º├úo global com v├¡rgula decimal (litros, KM/L e valores em R$) na interface e colunas num├®ricas no Excel.

### Alterado
- Solicita├º├úo de abastecimento (PDF) n├úo exibe mais valores nem marcas de revis├úo (REV_x fica apenas no sistema).

## [1.49.0] ÔÇö 2026-09-24

### Adicionado
- **Frota**: dialog "Custo e consumo" da ficha do ve├¡culo ampliado (modal largo) para dar mais visibilidade ao gr├ífico.
- **Frota**: gr├ífico de 12 meses interativo ÔÇö tooltip flutuante com combust├¡vel, itens extras e litros separados por m├¬s + highlight da barra sob o mouse.
- **Frota**: linha "Itens extras" na tabela de resumo (abaixo de "Custo por km").
- **Frota**: bot├úo "Baixar gr├ífico (PNG)" ÔÇö exporta o gr├ífico como imagem direto do navegador (com fallback .svg), 100% offline.

## [1.48.0] - 2026-09-23

### Adicionado
- **Frota - Gr├ífico de custo e consumo (12 meses) na ficha do ve├¡culo**: SVG
  offline com barras empilhadas (azul = combust├¡vel, laranja = itens extras)
  e linha de litros; aparece no dialog Custo e consumo.
- **Frota - Exporta├º├úo de custos para Excel**: individual por ve├¡culo (na
  ficha, com resumo + s├®rie mensal + abastecimentos) e geral (todos os
  ve├¡culos, com abas Resumo por ve├¡culo e Abastecimentos).
- **Abastecimentos - Itens extras por solicita├º├úo**: linhas de descri├º├úo/
  qtde/valor no formul├írio (ex.: ├│leo 2 tempos, aditivo, ped├ígio), somam no
  custo total com desglose (combust├¡vel x extras) em ficha/gr├íficos/resumos
  e ganham se├º├úo pr├│pria no PDF com TOTAL GERAL.
- **Abastecimentos - Bloquear/Excluir solicita├º├úo**: bloqueio com motivo
  (N├úo usada, Erro de lan├ºamento, Cancelado, Outro + texto livre); somente a
  solicita├º├úo mais recente pode ser exclu├¡da (as antigas devem ser
  bloqueadas); bloqueadas ficam fora de todos os c├ílculos de custo
  (ficha, m├®dia, dashboard) e ganham badge BLOQUEADA + filtro por situa├º├úo.
- **Abastecimentos - Ordena├º├úo da lista**: por Data (padr├úo, mais recentes
  primeiro) ou Serial; filtro por situa├º├úo (Todas/Ativas/Bloqueadas).
- **Abastecimentos - Coluna Nota fiscal**: mostra o n├║mero da NF anexada ou
  badge "Sem NF".
- **Exporta├º├úo de abastecimentos atualizada**: novas colunas Itens extras
  (R$), Total (R$), NF, Situa├º├úo e Motivo.

## [1.47.0] - 2026-09-23

### Adicionado
- **Ficha de EPI ÔÇö Fabricante e Lote por item** (opcionais): novos campos no
  formul├írio de abertura, exibidos na ficha e impressos como linha secund├íria
  no PDF ("Fabricante: X ┬À Lote: Y").
- **Ficha de EPI ÔÇö item descart├ível**: checkbox por linha; itens marcados
  ganham badge "Descart├ível" na ficha e indica├º├úo no PDF.
- **Ficha de EPI ÔÇö badge "Devolu├º├úo parcial"**: a lista e a ficha agora
  distinguem devolu├º├úo parcial (amarelo) de "Itens devolvidos" (azul) e
  "Aberta" (verde), com filtro pr├│prio na lista.
- **Ficha de EPI ÔÇö TERMO DE COMPROMISSO na 1┬¬ folha do PDF**: texto integral
  (Portaria 3.214/78, NR-01 item 1.8, NR-07, CLT Art. 462 ┬º1┬║) com Local
  (reusa "Local de treinamento" das Configura├º├Áes) e CNPJ da empresa, e linha
  de assinatura "li e estou ciente do termo acima".

### Corrigido
- **Usu├írios ÔÇö badge de permiss├úo**: o select de exce├º├úo por usu├írio voltava a
  mostrar "Padr├úo do papel" depois de salvar Permitir/Negar (a altera├º├úo era
  gravada, s├│ a exibi├º├úo errava). Agora o select reflete o estado salvo.
- **Backup ÔÇö ordena├º├úo**: a lista agora mostra sempre os backups mais
  recentes primeiro (ordenada por data de modifica├º├úo, independente do nome).
- **PDF da Ficha de EPI ÔÇö sobreposi├º├úo**: os t├¡tulos das colunas ("C.A.",
  "Descri├º├úoÔÇª", "Qtde"ÔÇª) n├úo s├úo mais cobertos pelas faixas azuis
  "ENTREGA/DEVOLU├ç├âO DE EQUIPAMENTO" ÔÇö folga dedicada entre as faixas e
  cabe├ºalho de colunas com faixa pr├│pria tamb├®m no bloco de devolu├º├úo.

## [1.46.0] - 2026-09-18

### Adicionado
- **Permiss├Áes por m├│dulo definidas pelo administrador** (Usu├írios ÔåÆ
  "Permiss├Áes por papel"): o admin marca o que cada papel (Emissor/Consulta)
  pode acessar, m├│dulo por m├│dulo, e tamb├®m pode dar **exce├º├Áes por usu├írio**
  (Permitir/Negar mesmo com o papel bloqueado). As mudan├ºas valem na hora,
  sem re-login. Admin sempre mant├®m Usu├írios e Configura├º├Áes.
- **PDF de certificados gerado na hora**: certificados importados (ou com o
  arquivo sumido) voltam a funcionar ÔÇö o portal recria o PDF com o MESMO
  n├║mero (CERT-XXXXXX) ao abrir "Ver"/"PDF", e a lista de hist├│rico mostra
  badge "Sem PDF" com bot├úo **Gerar**. Impedimentos s├úo explicados
  (funcion├írio sem CPF, modelo da NR ausente, empresa n├úo configurada).
- **Ficha do ve├¡culo modernizada**: as 6 se├º├Áes viraram janelas (dialogs)
  abertas por bot├Áes na barra da ficha ÔÇö Documentos, Laudos, Movimenta├º├Áes,
  Abastecimentos, Custo, Checklist e Manuten├º├Áes ÔÇö e o cabe├ºalho agora mostra
  a **situa├º├úo atual** (Dispon├¡vel/Em Viagem/Em Manuten├º├úo/Indispon├¡vel),
  motorista e destino atual.
- **Edi├º├úo de abastecimento com revis├úo**: bot├úo "Editar" corrige dados e
  gera novo PDF carimbado **REV_A, REV_BÔÇª** ("documento revisado; substitui
  a vers├úo anterior").
- Op├º├úo **"Outros / Ferramentas"** no abastecimento (motosserras, ro├ºadeiras
  etc.) ÔÇö o t├¡tulo do campo virou "Combust├¡vel / Despesa".

### Corrigido
- **Lista de ve├¡culos: coluna "Posse" estava sempre vazia** (erro de digita├º├úo
  no template).
- Interface geral com realce ao passar o mouse (linhas das tabelas, bot├Áes,
  links, summary) e contorno azul nos campos com foco.
- Bot├Áes/r├│tulos do Frota padronizados: H1 "Gest├úo de Frota", "Empresas
  (Posse)", "Fornecedores (Postos)"; importar Excel agora abre ao clicar no
  bot├úo "Importar Excel"; bot├úo **NF** dispon├¡vel em todas as linhas dos
  abastecimentos.

## [1.45.3] - 2026-09-18

### Adicionado
- **Vers├úo do sistema no cabe├ºalho do portal** (ex.: `v1.45.3`) ao lado da
  marca NormaTech ÔÇö aparece em todas as p├íginas, inclusive no login.
- **Calend├írio para escolher datas**: todo campo de data do portal ganhou o
  bot├úo ­ƒôà que abre o calend├írio do navegador e preenche a data sozinho
  (dd/mm/aaaa). O campo tamb├®m s├│ aceita n├║meros e insere as barras
  automaticamente. Aplicado em: certificados (individual e lote),
  funcion├írios (nascimento/admiss├úo), ASO, EPI (entrega, itens, devolu├º├úo),
  crach├ís, frota (abastecimento, checklist, laudos, sa├¡da/entrada,
  manuten├º├Áes, NFs), hist├│rico (filtros De/At├®).
- **M├íscara de telefone** no cadastro de funcion├írio (s├│ n├║meros, m├íx. 11).
- **M├íscara de CNPJ** nas empresas/fornecedores (frota, integra├º├Áes) e
  valida├º├úo ao salvar: se preenchido, exige os 14 d├¡gitos (vazio continua
  permitido).

### Corrigido
- **Emiss├úo individual: funcion├írio n├úo perde mais a sele├º├úo ao trocar a
  NR** ÔÇö a p├ígina n├úo recarrega mais; carga, validade, descri├º├úo e campos
  extras se ajustam na hora (o funcion├írio escolhido continua selecionado).
- **Emiss├úo em lote: marca├º├úo dos funcion├írios sobrevive ├á troca da NR**.
- **Aviso ÔÇ£Gerando documentoÔÇØ n├úo aparece mais quando h├í erro de
  preenchimento** (ex.: enviar sem selecionar funcion├írio) ÔÇö o carregamento
  s├│ ├® exibido quando o formul├írio realmente ├® enviado.
- Campos num├®ricos que aceitavam texto viraram num├®ricos de verdade (carga
  e validade na emiss├úo em lote, quantidades de EPI); litros/valores/KM-L
  s├│ aceitam n├║meros e v├¡rgula.
- M├íscaras de data/hora da ficha de frota, que existiam no c├│digo mas nunca
  eram executadas, foram substitu├¡das pelas m├íscaras globais do portal.

## [1.45.2] - 2026-09-18

### Corrigido
- **Portal fora do ar por CPF inv├ílido**: um funcion├írio com CPF digitado
  errado (d├¡gito verificador inv├ílido, ex.: `211.323.497-22`) derrubava a
  listagem de funcion├írios inteira com erro de valida├º├úo. Duas corre├º├Áes:
  - O sistema agora aceita qualquer CPF com 11 n├║meros (a verifica├º├úo do
    d├¡gito verificador foi removida ÔÇö CPF s├│ ├® validado pelo formato:
    11 d├¡gitos, sem repeti├º├Áes tipo 111.111.111-11);
  - Blindagem extra: se qualquer registro antigo com dado inv├ílido existir
    no banco, ele n├úo derruba mais listagens/fichas/emiss├Áes ÔÇö o
    funcion├írio aparece normalmente e o erro ├® registrado em
    `data/error.log`.
- Vale para cadastro manual (portal e desktop) e importa├º├Áes por planilha.

## [1.45.1] - 2026-09-18

### Adicionado
- **Portal ÔÇö bot├úo ÔÇ£Exibir senhaÔÇØ**: nos formul├írios de senha (p├ígina
  Usu├írios ÔåÆ ÔÇ£Definir senhaÔÇØ e Trocar senha) cada campo ganhou o bot├úo
  Exibir/Ocultar para conferir o que foi digitado.
- **Portal ÔÇö m├íscara de CPF no cadastro de funcion├írio**: o campo CPF s├│
  aceita n├║meros e formata sozinho (000.000.000-00) enquanto se digita.

### Corrigido
- **Importa├º├úo de funcion├írios ÔÇö CPF robusto**: c├®lulas num├®ricas do Excel
  (CPF digitado como n├║mero chega como `11144477735.0`) n├úo s├úo mais
  corrompidas; o importador aceita CPF com ponto/h├¡fen ou n├║meros puros e
  rejeita com mensagem clara qualquer coisa que n├úo tenha exatamente 11
  n├║meros (ex.: ÔÇ£CPF tem mais de 11 numerosÔÇØ, ÔÇ£menos de 11 numeros ÔÇö zeros
  ├á esquerda podem ter sido perdidosÔÇØ).
- **Importa├º├Áes ÔÇö erro em uma linha n├úo derruba o resto**: falha de banco
  ao cadastrar uma linha (ex.: CPF duplicado, banco ocupado) vira erro
  daquela linha no resumo; as demais linhas continuam sendo importadas
  (funcion├írios, ve├¡culos, bloqueios de cart├úo).
- **Modelos de importa├º├úo**: coluna CPF dos modelos FUNCIONARIOS, ASO e
  CARTOES BLOQUEIO agora ├® Texto (preserva zeros ├á esquerda), exemplos em
  n├║meros puros, coment├írio de instru├º├úo no cabe├ºalho e aba ÔÇ£LEIA-MEÔÇØ no
  modelo de funcion├írios. LEIA-ME.txt atualizado.

## [1.45.0] - 2026-09-17

### Adicionado
- **Portal ÔÇö barra de progresso real (ROADMAP 2.32.1)**: emiss├úo em lote e
  importa├º├Áes (funcion├írios, certificados, ASOs, cart├Áes) rodam em job de
  fundo com barra de percentual, contador i/total e item atual; o navegador
  consulta o status a cada 500 ms (/jobs/{id}). Chamadas sem JavaScript
  continuam funcionando no modo s├¡ncrono anterior.
- **Portal ÔÇö importar fotos dos funcion├írios (ROADMAP 2.32.1)**: bot├úo
  ÔÇ£Importar FotosÔÇØ na p├ígina de Funcion├írios. Aceita v├írios arquivos
  (JPG/PNG/BMP/WEBP at├® 50 MB), casa pelo CPF (11 d├¡gitos no nome do
  arquivo) ou nome exato, mostra pr├®via com foto nova x atual, marca
  ÔÇ£SUBSTITUIR/adicionarÔÇØ e s├│ grava o que for confirmado.
- **Portal ÔÇö menu renomeado (ROADMAP 2.31.4)**: grupo ÔÇ£CadastrosÔÇØ passou a
  se chamar ÔÇ£Funcion├íriosÔÇØ e o item interno ÔÇ£Funcion├íriosÔÇØ passou a se
  chamar ÔÇ£CadastrosÔÇØ (troca literal de interface).

### Alterado
- **Dashboard ÔÇö anima├º├úo de contagem em ~2 segundos** (antes 0,8 s).
- **Solicita├º├úo de Abastecimento ÔÇö aprova├º├úo sem nome (ROADMAP 2.32.2)**:
  o PDF n├úo imprime mais o nome do aprovador ÔÇö fica apenas a linha de
  assinatura com ÔÇ£AprovadoÔÇØ embaixo. O campo ÔÇ£Aprova├º├úo (superior)ÔÇØ saiu
  do formul├írio e da valida├º├úo; a coluna ÔÇ£SuperiorÔÇØ saiu da exporta├º├úo
  Excel (coluna segue no banco, ignorada).
- Corrigida a codifica├º├úo (mojibake) do formul├írio de checklist semanal.

## [1.44.0] - 2026-09-17

### Adicionado
- **Frota ÔÇö status do ve├¡culo derivado automaticamente** (ROADMAP 2.31):
  lista com badge Em Viagem (sa├¡da aberta), Em Manuten├º├úo (manuten├º├úo
  urgente), Indispon├¡vel (manuten├º├úo vencida ou alugado com contrato
  vencido) e Dispon├¡vel; colunas Motorista e Destino da viagem atual.
- **Frota ÔÇö lista simplificada**: coluna Ve├¡culo mostra "PLACA - Marca
  Modelo" (colunas Placa e Ano/Cor removidas) e a tabela ganhou barra de
  rolagem pr├│pria (n├úo estica a p├ígina).
- **Frota ÔÇö m├íscara de data/hora** (dd/mm/aaaa e HH:MM) nos campos de
  sa├¡da/entrada de movimenta├º├Áes.
- **Frota ÔÇö checklist em branco pr├®-preenchido**: bot├úo na ficha gera o PDF
  do checklist semanal com ve├¡culo, placa, KM atual e data j├í preenchidos
  para imprimir, preencher ├á m├úo, assinar e anexar de volta (registro criado
  com serial CKL).
- **Frota ÔÇö abastecimento assinado**: anexar foto/PDF do abastecimento
  assinado na tela de NFs (upload, download e exclus├úo).
- **Menu reorganizado**: grupo "Seguran├ºa" (Certificados, Emiss├úo em Lote,
  Hist├│rico, Listas de Presen├ºa, Ficha de EPIs, Crach├ís, Cart├Áes,
  Vencimentos), grupo "Cadastros" (Funcion├írios, ASO, Integra├º├Áes) e bot├úo
  dedicado "Gest├úo de Frota" no topo do menu.
- **Dashboard**: atalho Vencimentos, contagem animada nos cards e barra de
  rolagem no card de aniversariantes do m├¬s.

## [1.43.0] - 2026-09-17

### Corrigido
- **Portal ÔÇö importa├º├úo de certificados em lote voltou a funcionar com planilhas grandes**:
  a pr├®via era guardada na sess├úo (cookie) e, com ~40 linhas ou mais, o cookie
  estourava o limite de 4 KB dos navegadores e era descartado ÔÇö ao clicar em
  "Emitir", o servidor n├úo encontrava a pr├®via e mostrava "Nenhuma pr├®via
  pendente ÔÇö envie a planilha novamente.". Agora a pr├®via ├® gravada em
  `data/tmp_importacoes/{token}.json` (a sess├úo guarda s├│ o token) e o arquivo
  ├® apagado ap├│s a emiss├úo; ├│rf├úos com mais de 24h s├úo limpos automaticamente.
- **Listas de presen├ºa NR-01 com carga quebrada**: a carga hor├íria chega do
  banco como n├║mero decimal (8.0) e o formato `{n:02d}HS` do modelo n├úo aceita
  decimal ("Unknown format code 'd'"). Agora o valor ├® convertido para inteiro
  quando n├úo tem parte fracion├íria antes de formatar (E4 = "08HS").

### Adicionado
- **Usu├írios ÔÇö "Definir senha"**: o admin pode definir uma senha espec├¡fica
  para um usu├írio (m├¡nimo 6 caracteres), sem depender da senha provis├│ria
  aleat├│ria (A├º├Áes ÔåÆ Definir senha).
- **Certificados ÔÇö data e hora da emiss├úo no PDF (opcional)**: nova op├º├úo em
  Configura├º├Áes ÔåÆ Certificados ("Incluir data e hora da emiss├úo no PDF").
  Quando ativa, imprime `dd/mm/aaaa HH:MM` pequeno junto ao n├║mero do
  certificado (CERT-XXXXXX ÔÇó dd/mm/aaaa HH:MM). Vale para os PDFs JSON/ReportLab
  e para os modelos PPTX da t├®cnica.
- **Abastecimento ÔÇö propriedade do ve├¡culo na solicita├º├úo**: o PDF agora indica
  "ÔÇö Pr├│prio" ou "ÔÇö Alugado (contratante: X)" ao lado do ve├¡culo.

## [1.42.0] - 2026-09-17

### Adicionado (ROADMAP 2.29.7 ÔÇö Frota)
- **Importar/Exportar ve├¡culos** (Excel): bot├Áes na lista de Frota; modelo
  `MODELO VEICULOS.xlsx` dispon├¡vel para download; empresa inexistente ├®
  criada automaticamente; erros s├úo por linha.
- **Motorista/Condutor por lista de funcion├írios ou "Outro"** nos formul├írios
  de movimenta├º├úo e abastecimento.
- **Checklist assinado de volta**: anexar ao checklist o PDF/foto assinado
  (download e remo├º├úo pelo mesmo ponto).
- **Conflito de movimenta├º├Áes**: com uma sa├¡da aberta, novas sa├¡das s├úo
  bloqueadas at├® registrar a entrada.
- **Tags nos documentos do ve├¡culo**: Manuten├º├úo (Nota Fiscal), Documento,
  Abastecimento, Outros.
- **Valor e Litros opcionais**: podem ficar em branco na emiss├úo e ser
  completados depois na tela de NFs (custo/KM-L continuam funcionando).
- **Combust├¡vel por tipo**: Arla/Diesel/Arla+Diesel bloqueados para carros
  (no servidor e no formul├írio).
- **Abastecimento a partir da ficha**: bot├úo leva ao formul├írio com o
  ve├¡culo pr├®-preenchido (bot├úo em tom amarelo).
- **"Ver por p├ígina"** na lista de ve├¡culos e de abastecimentos
  (10/20/25/50).

### Adicionado (ROADMAP 2.30)
- **Notifica├º├Áes pop** (lateral direita, auto-fecha) substituindo os banners
  de mensagem.
- **Menu em grupos** no header (Certificados, Cadastros, Controle, Sistema).
- **Pop-up de progresso** durante emiss├Áes/gera├º├Áes (overlay com spinner em
  todo POST do portal).
- **Auditoria**: busca por data (de/at├®), linhas por p├ígina (10/20/30/50) e
  coluna "A├º├úo" truncada com tooltip.
- **Download do log de erros** e **download de backups** pelo admin
  (com prote├º├úo anti-traversal).
- **Card "Vencem em 8 a 15 dias"** em Vencimentos (com filtro dedicado).

### Alterado
- Datas/horas de movimenta├º├úo no formato `17/09/2026, 07:00`; KM com ponto
  de milhar (ex.: 100.000) na ficha do ve├¡culo.
- Se├º├Áes da ficha do ve├¡culo viraram **abas retr├íteis** (Documentos, Laudos,
  Movimenta├º├Áes, Abastecimentos, Custo, Checklist, Manuten├º├Áes).
- Popover da foto do ve├¡culo abre para dentro da tela.
- CI: workflow `.github/workflows/tests.yml` (unit├írio + portal); ROADMAP
  2.12 fechado (CI conclu├¡do; Multiusu├írio/GPU superados pelo Portal Web).

## [1.41.0] - 2026-09-16

### Alterado
- **Listas de Presen├ºa** (ajustes de layout pedidos ap├│s testes):
  - Campo **empresa** (ao lado do nome) sempre preenchido com
    `ALTEC INDUSTRIAL` ÔÇö modelos e layout padr├úo.
  - PDFs sempre em **folha vertical** (paisagem n├úo ficou bom).
  - **Serial da lista** gravado na c├®lula `{SERIAL}` do modelo e
    **pagina├º├úo** (`Pag X de Y`) na c├®lula `{PAGINACAO}`.
  - **Muitos participantes**: o mesmo modelo ├® preenchido em folhas
    separadas (vagas do registry; 20 no padr├úo) com `Pag 1 de N`,
    `Pag 2 de N`ÔÇª e os PDFs s├úo mesclados em um ├║nico arquivo.
  - Logo do modelo n├úo ├® mais reinserida (vinha duplicada: o openpyxl
    preserva a imagem embutida do XLSX; o layout padr├úo continua com logo).

## [1.40.0] - 2026-09-16

### Corrigido
- **Conte├║do program├ítico das listas de presen├ºa n├úo ├® mais alterado**: o
  gerador reescrevia o n├║mero de horas dentro do texto do template
  (ex.: "CONTE├ÜDO PROGRAM├üTICO ÔÇö 03 HORAS") com a carga da emiss├úo. O texto
  do modelo fica intacto agora (mesma regra dos certificados PPTX). A c├®lula
  dedicada de carga da NR-01 continua sendo preenchida normalmente.
- **Compilado de listas usa s├│ as listas da emiss├úo**: o dialog p├│s-emiss├úo
  agora baixa um PDF com exatamente as listas geradas naquele momento
  (link com `?ids=...`), e n├úo mais tudo do dia ÔÇö emiss├Áes anteriores no
  mesmo dia n├úo vazam para dentro. O mini-form "Baixar compilado de um dia"
  da listagem continua gerando o dia completo.
- Regress├úo coberta por testes: PDFs sem rastro de `comtypes` (texto de
  vers├Áes antigas), sem abas de outras NRs e com a carga original
  preservada.

## [1.39.0] - 2026-09-16## [1.39.0] - 2026-09-16

### Corrigido
- **Portal ÔÇö Listas de Presen├ºa: preenchimento deixou de usar o Excel COM**.
  Na m├íquina do servidor, a escrita via COM n├úo persistia (mesma classe do
  bug de binding j├í corrigido) e as listas sa├¡am com campos vazios ou com os
  dados de exemplo do template. Agora o preenchimento ├® 100% openpyxl
  (determin├¡stico): edita data, carga e participantes, **limpa as vagas n├úo
  utilizadas** (exemplos do template somem) e o Excel ├® usado apenas para a
  convers├úo final em PDF.
- **Folhas em branco no PDF**: ├írea de impress├úo expl├¡cita (`print_area`) +
  ajuste de largura + paisagem + grade nos modelos preenchidos e no layout
  padr├úo ÔÇö sem p├íginas vazias.
- **Popup do compilado n├úo fechava**: "Baixar compilado" agora fecha o
  di├ílogo e volta para a listagem (download continua em paralelo).
- A logo do modelo XLSX ├® extra├¡da do arquivo original e reancorada na
  posi├º├úo lida do XML do template (openpyxl perde imagens ao re-salvar).

## [1.38.1] - 2026-09-16

### Corrigido
- **Portal ÔÇö Listas de Presen├ºa: dados do sistema n├úo apareciam nas listas
  (NRs com modelo)**: o preenchimento via Excel alterava o arquivo na
  mem├│ria, mas o fechamento descartava as altera├º├Áes (`Close` sem salvar) ÔÇö
  o PDF sa├¡a com o modelo em branco, sem data nem colaboradores. Agora o
  workbook ├® salvo antes de fechar. A data impressa ├® a data referente
  escolhida na emiss├úo (o dia em que os certificados foram emitidos).

## [1.38.0] - 2026-09-15

### Corrigido
- **Portal ÔÇö Listas de Presen├ºa: gera├º├úo dos modelos NR-01/06/12/18/35 voltou a
  funcionar**: dois problemas de COM no servidor, s├│ no preenchimento do
  modelo Excel (o layout padr├úo, como Brigadista, n├úo passa por ele):
  1. `CreateObject` sem `CoInitialize` nas threads do servidor ("CoInitialize
     n├úo foi chamado") ÔÇö agora Excel COM ├® iniciado por um helper ├║nico
     (`_excel_app`), usado no preenchimento e na convers├úo para PDF.
  2. Grava├º├úo de c├®lulas (`Range.Value`) passou a falhar com
     `AttributeError: Value` ÔÇö a interoperabilidade din├ómica do comtypes
     deixou de resolver a grava├º├úo da propriedade nesta combina├º├úo de
     Office/Windows. Corrigido com fallback que obt├®m o identificador da
     propriedade (via Bind GET) e grava direto em `IDispatch::Invoke`
     (PROPERTYPUT); NumberFormat, PageSetup e demais escritas usam o mesmo
     caminho quando necess├írio.

### Alterado
- **Portal ÔÇö Listas de Presen├ºa em folha horizontal e organizadas**: todas as
  listas (modelo ou layout padr├úo) saem em orienta├º├úo paisagem, com ajuste
  para caber em 1 p├ígina de largura, linhas de divis├úo vis├¡veis (grade como
  no Excel) e conte├║do centralizado horizontalmente.

## [1.37.0] - 2026-09-15

### Alterado
- **Portal ÔÇö Listas de Presen├ºa: emiss├úo do dia inteiro de uma vez**:
  em "+ Nova lista" agora basta informar a **data** ÔÇö o portal mostra uma
  se├º├úo por NR com os participantes daquele dia (marcadas por padr├úo) e o
  bot├úo **Emitir listas do dia** gera todas de uma vez (uma NR com problema
  n├úo bloqueia as demais; o resumo mostra geradas e falhas).

### Adicionado
- **Compilado das listas do dia (PDF ├║nico)**: ap├│s emitir, um di├ílogo
  pergunta se quer baixar o compilado (todas as listas do dia em um ├║nico
  PDF, pronto para imprimir); tamb├®m d├í para baixar depois pela listagem
  informando a data.

### Corrigido
- **Portal ÔÇö uso de Excel/PowerPoint (COM) nas rotas web**: as chamadas COM
  falhavam dentro das threads do servidor ("CoInitialize n├úo foi chamado").
  Corrigido em `presenca_generator` (Excel) e `pptx_card_service`
  (PowerPoint ÔÇö afetava tamb├®m cart├Áes e certificados PPTX no portal).

## [1.36.0] - 2026-09-15

### Adicionado
- **Portal ÔÇö aba "Listas de Presen├ºa"**: gera├º├úo e controle das listas de
  presen├ºa de treinamento, uma lista por NR:
  - **Gera├º├úo autom├ítica**: escolha a NR e a data; o portal puxa sozinho os
    funcion├írios que tiveram certificado daquela NR emitido no dia (com nome,
    fun├º├úo e carga hor├íria detectada). Pr├®via antes de gerar; datas antigas
    funcionam (hist├│rico por data final do certificado).
  - **Modelos reais**: NR-01, NR-06, NR-12, NR-18 e NR-35 usam as planilhas
    da empresa (`LISTA DE PRESEN├çA\` copiadas para
    `templates/listas_presenca/` + mapeamento em `registry.json`) ÔÇö o
    preenchimento ├® feito via **Excel COM** na c├│pia (preserva logo e
    formata├º├úo) e convertido para PDF. NRs sem modelo recebem um **layout
    padr├úo** com logo da empresa, dados da configura├º├úo e grade de
    assinaturas.
  - **Controle por lista**: serial ├║nico `LP-{ano}-{seq}`, status
    (Pendente/Parcial/Assinada com badges e contadores), PDF salvo em
    `data/listas_presenca/`, upload da **lista assinada** escaneada
    (PDF/JPG/PNG at├® 50 MB) que muda o status para Assinada, download e
    remo├º├úo do anexo.
  - Permiss├Áes: admin e emissor editam; consulta apenas consulta.
  - Auditoria: gerar, assinar e excluir listas.
- `src/core/presenca_repo.py` + `src/core/presenca_generator.py` +
  `src/web/routers/presencas.py` + templates (lista, nova com pr├®via,
  detalhe).
- `test_web_presencas.py` (31 checks): rotas mockadas (28 P01ÔÇôP28) + E2E
  real com Excel gerando exemplos de modelo (NR-01, NR-06) e layout padr├úo
  (NR-33) em `comparacao_listas/` para confer├¬ncia manual.

## [1.35.0] - 2026-09-15

### Adicionado
- **Certificados PPTX da t├®cnica de seguran├ºa (NR-06, NR-12, NR-18, NR-35)**:
  os modelos PowerPoint usados pela t├®cnica agora s├úo suportados de ponta a
  ponta, sem alterar texto, design ou o conte├║do program├ítico:
  - `tools/prepare_nr_pptx.py`: converte os originais de `MODELOS NR pptx\`
    em modelos com tokens (`{{NOME}}`, `{{CPF}}`, `{{DIA}}/{{MES}}/{{ANO}}`)
    preservando toda a formata├º├úo, salvando em
    `templates/certificados_pptx/NR-XX.pptx` (originais intocados; pode ser
    reexecutado a qualquer momento).
  - `src/core/pptx_certificate_service.py`: preenche os tokens (nome em
    caixa alta, CPF do cadastro, data por extenso no corpo **e** na
    assinatura) e adiciona o n├║mero do certificado (ex.: `CERT-000491`) em
    cinza, pequeno, no canto inferior direito de todos os slides; converte
    para PDF via PowerPoint.
  - Gancho em `CertificateService`: se existir
    `templates/certificados_pptx/NR-XX.pptx`, a emiss├úo usa o modelo PPTX;
    sen├úo, o fluxo JSON/ReportLab atual. Portal, desktop, emiss├úo em lote e
    importa├º├úo de planilha ganham automaticamente (todos usam o mesmo
    servi├ºo), com hist├│rico, pastas por funcion├írio e espelhamento em rede
    funcionando como antes.
  - A carga hor├íria impressa nos modelos permanece a do texto original
    (fixa); a carga digitada continua registrada no hist├│rico.
- `test_pptx_certificados.py` (33 checks): parte unit├íria (tokens,
  formata├º├úo por run, datas) + E2E gerando os 4 PDFs reais e copiando para
  `comparacao_pptx/` para confer├¬ncia manual.

## [1.34.0] - 2026-09-15

### Adicionado
- **Portal ÔÇö Fase 4 conclu├¡da (v1.34.0)**:
  - **Backup** (admin): bot├úo "Fazer backup agora" + lista dos backups
    existentes (nome, tamanho, data). Sem restore pela web (decis├úo de
    projeto ÔÇö restaurar pelo desktop ou com o portal desligado).
  - **Auditoria** (admin): nova tela com busca e pagina├º├úo lendo o
    `audit_log`; agora tamb├®m registramos emiss├Áes (certificado, lote,
    crach├ís, cart├Áes, ASO), abertura de ficha EPI, importa├º├Áes (4 tipos),
    criar funcion├írio, salvar configura├º├Áes, backup manual e todas as
    opera├º├Áes de Frota.
- **Frota ÔÇö Checklist semanal de ve├¡culos leves (2.29.5)**: formul├írio no
  portal replica o papel da empresa (itens 1.1ÔÇô1.19, 2.1ÔÇô2.9 e 3.1ÔÇô3.6 ├ù
  dias 2┬¬ a s├íbado, S/N), "Pode-se operar com seguran├ºa?", observa├º├Áes por
  dia, motorista e l├¡der. Gera PDF preenchido no formato do formul├írio
  (`data/frota/checklists/`, serial CKL-{ano}-{seq}) com hist├│rico no
  ve├¡culo e download.
- **Frota ÔÇö Notas fiscais e custo (2.29.6)**: abastecimentos aceitam
  **Litros** e **Valor**; anexo de NFs (PDF/imagem) por abastecimento com
  download; ficha do ve├¡culo com total abastecido, **m├®dia KM/L real**
  (cruzando movimenta├º├Áes) e custo por km; exporta├º├úo da lista de
  abastecimentos para Excel.
- **Frota ÔÇö Manuten├º├úo preventiva por KM**: itens com intervalo (ex.: troca
  de ├│leo a cada 10.000 km), progresso calculado pelas movimenta├º├Áes,
  conclus├úo com KM do servi├ºo e aviso no menu Vencimentos (itens pr├│ximos/
  vencidos por KM).
- **Frota ÔÇö Campos novos do ve├¡culo**: cor, ano, carroceria (hatch/sedan,
  apenas carros), fim do contrato de aluguel (apenas alugados), KM/L da
  ficha t├®cnica e **foto do ve├¡culo** (miniatura na lista e na ficha).
- **Dashboard**: cards de frota (ve├¡culos cadastrados, sa├¡das em aberto e
  custo de abastecimento do m├¬s) para quem tem acesso ao m├│dulo.

### Removido
- ROADMAP: item 2.1 "Drive Mapeado" (obsoleto ÔÇö o portal web na rede j├í
  atende o caso de uso).

## [1.33.0] - 2026-09-14

### Adicionado
- **Portal Web ÔÇö m├│dulo Frota (ROADMAP 2.29, blocos 2.29.1 a 2.29.4)**:
  gest├úo completa de ve├¡culos com banco pr├│prio (7 tabelas) e permiss├Áes
  (admin/emissor escrevem, consulta l├¬).
  - **Cadastro de ve├¡culos**: tipo (Caminh├úo com subtipos Ca├ºamba/Munck/
    Plataforma, Pickup, Carro, Van, Empilhadeira, Retroescavadeira, Outros),
    placa obrigat├│ria exceto Empilhadeira/Retroescavadeira, pr├│prio ou
    alugado (com contratante), empresa do ve├¡culo (cadastro pr├│prio) e
    pasta virtual de documentos (CRV, CRLV, contratos, inspe├º├Áes).
  - **Solicita├º├úo de Abastecimento**: PDF com logo e dados da empresa,
    serial ├║nico `AB-{ano}-{sequ├¬ncia}` (sequ├¬ncia global que nunca
    reinicia), fornecedor posto (Nome/CNPJ/Endere├ºo com cadastro pr├│prio),
    combust├¡vel (Gasolina/├ülcool/Diesel/Arla/GNV/ARLA+Diesel), data,
    viagem/servi├ºo, KM, observa├º├Áes, ve├¡culo da lista, condutor digitado e
    campos de assinatura (condutor + aprova├º├úo do superior).
  - **Sa├¡da/Entrada de ve├¡culos**: registro de sa├¡da (data, hora, KM
    inicial, destino, motivo, obs, motorista, autorizado por) e entrada
    posterior (data, hora, KM final ÔÇö n├úo pode ser menor que o inicial),
    com KM rodado calculado.
  - **Laudos e documentos com vencimento**: upload do arquivo + tipo
    (Certificado Final, CRLV, Fuma├ºa Preta, Laudo de Avalia├º├úo, Laudo
    Eletromec├ónico, Plano de Manuten├º├úo, Seguro, Outro) + data de validade,
    com badges de status e download; **integrado ├á aba Vencimentos e aos
    contadores do dashboard** (vencidos/7 dias/30 dias).
  - Listas com busca e pagina├º├úo; ficha do ve├¡culo re├║ne documentos,
    laudos, movimenta├º├Áes e abastecimentos.

## [1.32.0] - 2026-09-14

### Adicionado
- **Portal Web ÔÇö dashboard estilo tela inicial do desktop**: logo da empresa
  (nova rota `/logo.png`), data completa + rel├│gio, boas-vindas, 3 cart├Áes de
  resumo (certificados / funcion├írios / NRs), atalhos r├ípidos e aniversariantes
  do dia e do m├¬s. Chips de vencimento e tabelas por NR/m├¬s continuam
  dispon├¡veis no painel recolh├¡vel "Ver indicadores".
- **Portal Web ÔÇö tela de Configura├º├Áes (somente admin)**: espelho da tela do
  desktop ÔÇö Dados da Empresa (CNPJ e Registro MTE com formata├º├úo e valida├º├úo),
  Seguran├ºa (senha de restaura├º├úo de backup), Backups (intervalo, c├│pia
  externa, rede e Tarefa Agendada do Windows), Documentos em Rede (com bot├úo
  "Sincronizar Agora") e Diagn├│stico com visualiza├º├úo/limpeza do log de erros.
  Aparece no menu apenas para administrador.
- **Confirma├º├úo com lista de nomes antes de emiss├Áes em massa**: ao emitir
  certificados em lote, crach├ís ou cart├Áes, um popup mostra os selecionados
  (nome + CPF) para conferir antes de confirmar.

### Alterado
- **Portal Web ÔÇö Crach├ís e Cart├Áes ganharam busca e pagina├º├úo** (20 por
  p├ígina, p├íginas numeradas), acompanhando o padr├úo das demais listagens.

## [1.31.1] - 2026-09-11

### Corrigido
- **Portal Web n├úo depende mais do desktop para importar funcion├írios**:
  `excel_importer` importava `src.ui.pages.funcoes`, que arrastava
  customtkinter (interface gr├ífica). No servidor sem desktop, o POST de
  importa├º├úo de funcion├írios falharia. A l├│gica de `funcoes.json` foi
  extra├¡da para `src/utils/funcoes_store.py` (a p├ígina desktop importa
  da├¡ tamb├®m ÔÇö sem mudan├ºa de comportamento).

### Alterado
- **`requirements-web.txt` virou auto-suficiente para o servidor**: al├®m das
  depend├¬ncias web, inclui as bibliotecas core usadas pelo portal (pydantic,
  reportlab, pillow, pymupdf, python-pptx, apscheduler, comtypes etc.) com
  pisos de vers├úo compat├¡veis com Pythons novos. O `requirements.txt`
  (desktop, com pins exatos) continua intocado ÔÇö instalar os dois juntos no
  servidor podia abortar o pip inteiro por causa de pins sem build para o
  Python do servidor (ex.: `pyinstaller==6.8.0`).
- `INICIAR-PORTAL.bat` e `INSTALAR_PORTAL.bat` instalam apenas
  `requirements-web.txt` e o teste de depend├¬ncias agora importa tamb├®m os
  4 importadores de planilha (pega acoplamentos como o de cima).

## [1.31.0] - 2026-09-11

### Corrigido
- **Portal Web ÔÇö tela "Novo funcion├írio" voltou a abrir**: a rota
  `/funcionarios/novo` estava declarada depois de `/funcionarios/{emp_id}` e o
  FastAPI capturava "novo" como se fosse um ID (erro `int_parsing` ao tentar
  cadastrar).

### Alterado
- **Portal Web ÔÇö Cart├Áes de bloqueio: formul├írio adapta-se ao modelo**:
  campo **Setor**, colunas **Matr├¡cula** e **Papel** e a linha "Este modelo
  usaÔÇª" aparecem somente quando o modelo selecionado realmente usa o campo
  (lido dos placeholders do PPTX); modelos JSON continuam pedindo apenas
  telefone/foto. A emiss├úo tamb├®m s├│ envia as op├º├Áes que o modelo usa.

### Adicionado
- **Deploy**: `INICIAR-PORTAL.bat` na raiz (sobe o portal na rede; aceita a
  porta como argumento, ex.: `INICIAR-PORTAL.bat 80` para `http://normatech`
  sem `:porta`). `deploy\web\INSTALAR_PORTAL.bat` com porta configur├ível
  (`set PORT=80`), corre├º├úo do teste de depend├¬ncias (uvicorn) e auto-start do
  servi├ºo NSSM. `docs/PORTAL/02-DEPLOY_SERVIDOR.md` atualizado (porta 80,
  nome `normatech` na rede, troubleshooting de porta ocupada).

## [1.30.1] - 2026-09-11

### Alterado
- **Portal Web ÔÇö polimento de UI/UX em todos os m├│dulos**:
  - Layout fluido (fim da largura fixa 1080px) e contorno preto de 1px em todas
    as tabelas.
  - **Certificados**: campo de funcion├írio virou **busca com dropdown** (digita
    nome/CPF e clica no resultado); trocar a NR recarrega a p├ígina e os campos
    extras agora correspondem sempre ├á NR selecionada (ex.: Tipo de brigada);
    campos opcionais ficam em menu "Campos adicionais (opcional)" abre/fecha.
  - **Emiss├úo em lote**: busca e seletor **ver por p├ígina (10/20/25/50) junto ├á
    tabela**, com pagina├º├úo no navegador que preserva os ajustes individuais
    digitados nas linhas fora da p├ígina.
  - **Funcion├írios**: seletor de itens por p├ígina (10/20/25/50); no perfil,
    bot├úo **Voltar largo no topo** do cart├úo e atalho para as fichas de EPI.
  - **Pagina├º├úo numerada** ("P├ígina X de Y" + links 1 2 3 ÔÇª): Funcion├írios,
    Hist├│rico, Vencimentos, ASOs e EPI.
  - **Hist├│rico**: anexo de documento assinado em menu sanfona com ├írea de
    upload estilizada (mostra o nome do arquivo escolhido).
  - **Vencimentos**: pain├®is de resumo por severidade (vencidos/7/30 dias)
    clic├íveis, aplicando o filtro correspondente.
  - **EPI**: filtro por situa├º├úo (Abertas/Fechadas/**Itens devolvidos** ÔÇö ficha
    aberta com todos os itens devolvidos), seletor 10/20/25/50, pagina├º├úo,
    p├ígina **/epi/funcionario/{id}** com todas as fichas do funcion├írio (link na
    lista e no perfil), badge azul "Itens devolvidos" e campo "QTD devolvida"
    **desabilitado automaticamente** quando a devolu├º├úo do item ├® marcada Total.

## [1.30.0] - 2026-09-11

### Adicionado
- **Portal Web ÔÇö Fase 3 conclu├¡da (Cart├Áes, Importa├º├Áes e Integra├º├Áes no navegador)**:
  - Aba **Cart├Áes de Bloqueio**: emiss├úo de lotes com todos os modelos (JSON/ReportLab
    e PPTX com setor, l├¡der/liderado e matr├¡cula obrigat├│ria preenchida s├│ na emiss├úo ÔÇö
    PPTX exige PowerPoint no servidor), sa├¡da em folha ├║nica ou um cart├úo por p├ígina,
    importa├º├úo da lista de bloqueios (.xlsx) pr├®-selecionando funcion├írios e listagem
    dos PDFs gerados em `data/cartoes` (LOTES + pasta por funcion├írio) com ver/baixar.
  - Aba **Importa├º├Áes**: os 4 importadores do desktop no navegador ÔÇö funcion├írios
    (colunas AÔÇôI), certificados em lote com **pr├®via antes de emitir** (cria
    funcion├írios inexistentes; sem CPF registra sem PDF), ASOs em lote (A/P/M/R/D) e
    lista de bloqueios de cart├Áes ÔÇö com modelos oficiais de `MODELOS DE IMPORTACAO/`
    para download.
  - Aba **Integra├º├Áes**: integra├º├Áes funcion├írio/empresa com tipo livre, datas e
    observa├º├Áes (status Em dia/Vencida pela mesma regra do desktop), CRUD de
    **empresas clientes** (nome ├║nica, CNPJ, exclus├úo protegida com integra├º├Áes
    vinculadas) ÔÇö alimenta a aba Vencimentos.
- Menu do portal completo (Cart├Áes, Integra├º├Áes e Importa├º├Áes s├│ para
  admin/emissor; consulta segue s├│ leitura).

### Alterado
- `requirements-web.txt`: adicionado `openpyxl` (importa├º├Áes .xlsx no portal).

## [1.29.0] - 2026-09-11

### Adicionado
- **Portal Web ÔÇö Fase 3 parte 2 (EPI e Crach├ís no navegador)**:
  - Aba **EPI**: lista de fichas, nova ficha com itens (C.A./descri├º├úo/qtde/data),
    ficha com situa├º├úo por item (Total/Parcial/Pendente), **devolu├º├úo pelo
    navegador** (regenera a ficha e emite o Termo de Devolu├º├úo), ver/baixar PDF,
    anexos m├║ltiplos (upload/baixar/excluir) e fechar/reabrir ficha.
  - Aba **Crach├ís**: emiss├úo em lote pelo navegador com os mesmos bloqueios do
    desktop (foto, NR v├ílida e ASO dentro da validade; bloqueados aparecem com
    o motivo), templates Altec paisagem/vertical, tamanho real ou reduzido,
    PDF A4 com guia de corte, ver/baixar inline e por crach├í gravado.
- Menu do portal com Vencimentos, ASO, EPI e Crach├ís (consulta s├│ leitura).

## [1.28.0] - 2026-09-11

### Adicionado
- Portal Web (Fase 3, parte 1): aba **Vencimentos** no navegador ÔÇö todos os certificados, ASOs e integra├º├Áes com vencimento, cards de totais (vencidos / pr├│ximos 7 / pr├│ximos 30 dias) e filtros por NR, per├¡odo e busca.
- Portal Web: aba **ASO** ÔÇö lista com busca e status, cadastro de novo ASO (gera PDF numerado com moldura), documento do m├®dico anexado (embutido no PDF em capa + moldura), ver/baixar PDF e do documento, remover documento (volta ao placeholder).

### Alterado
- Menu do portal reorganizado: Dashboard, Certificados, Emiss├úo em Lote, Funcion├írios, Hist├│rico, Vencimentos, ASO e Usu├írios (cada papel v├¬ apenas o que pode).

## [1.27.0] - 2026-09-11

### Adicionado
- Portal: Emiss├úo em Lote ÔÇö escolha a NR, marque v├írios funcion├írios (sem CPF fica bloqueado), defina data/carga/validade/descri├º├úo do lote com ajuste individual por funcion├írio, e emita tudo de uma vez com p├ígina de resultado (n├║meros gerados + Ver/PDF + erros).
- Menu "Emiss├úo em Lote" vis├¡vel apenas para Admin/Emissor; Consulta continua somente leitura.

## [1.26.0] - 2026-09-11

### Adicionado
- Portal: bot├úo "+ Novo funcion├írio" na lista (admin/emissor).
- Portal: PDF vis├¡vel no navegador ÔÇö "Ver no navegador" no detalhe do certificado e "Ver" no Hist├│rico (abre inline, sem baixar).
- Portal: "Visualizar pr├®via" no formul├írio de emiss├úo ÔÇö abre o PDF de pr├®via em nova aba sem gravar registro nem consumir numera├º├úo.

### Alterado
- Nenhuma mudan├ºa no app desktop nesta vers├úo.

## [1.25.0] - 2026-09-11

### Adicionado (Portal Web ÔÇö Fase 2)
- **Funcion├írios no portal**: lista com busca e pagina├º├úo, ficha completa (dados SESMT), novo/editar com valida├º├úo, upload de foto 3x4 e documentos (qualquer formato at├® 50MB, baixar/excluir).
- **Certificados no portal**: emiss├úo pelo navegador (funcion├írio, NR com carga/validade/descri├º├úo e campos extras do modelo), p├ígina de detalhe e download do PDF. PDF salvo na pasta do funcion├írio com espelhamento em rede.
- **Hist├│rico no portal**: filtros (busca, NR, per├¡odo, assinado) e pagina├º├úo; anexar documento assinado (PDF/JPG/PNG), baixar e remover.
- **Permiss├Áes**: pap├®is Consulta navegam em modo somente leitura (Admin/Emissor operam).

## [1.24.1] - 2026-09-11

### Corrigido
- Portal n├úo abre mais com "Internal Server Error": o servidor passou a ser o uvicorn (ASGI, padr├úo do FastAPI). O waitress ├® WSGI e era incompat├¡vel com o FastAPI.
- Validado com servidor HTTP real (uvicorn + httpx): login, troca de senha obrigat├│ria, dashboard e logout funcionando ponta a ponta.

## [1.24.0] - 2026-09-10

### Adicionado
- **Portal Web ÔÇö Fase 1**: login com 3 papeis (Admin/Emissor/Consulta), dashboard de indicadores, gestao de usuarios e auditoria ÔÇö acesso pelo navegador ao MESMO banco do desktop.
- Usuario `admin` criado no 1o boot com senha provisoria (console + `data/web_admin_provisorio.txt`); troca de senha obrigatoria no 1o acesso.
- Rate-limit de login (5 tentativas / 5 min) e auditoria de acoes (tabela `audit_log`).
- `run_web.py` (FastAPI + waitress; `--host 0.0.0.0` para o servidor, `--reset-admin`, `--sem-backup`).
- `requirements-web.txt` (dependencias do portal, separadas do desktop).
- Scripts de servidor em `deploy/web/`: INSTALAR_PORTAL, ATUALIZAR_PORTAL, ZERAR_DADOS e REMOVER_PORTAL.
- `python run_web.py` nao afeta o app desktop; backup automatico compartilhado quando ativo.

## [1.23.0] - 2026-09-10

### Adicionado
- Emiss├úo em Lote de Certificados NR (item 2.26): nova p├ígina "Emiss├úo em Lote" com sele├º├úo de NR, sele├º├úo de funcion├írios com busca/pagina├º├úo, valida├º├úo autom├ítica (sem CPF = bloqueado), edi├º├úo em lote (data, carga hor├íria, validade, descri├º├úo e campos extras do template), edi├º├úo individual por funcion├írio, preview antes de emitir e gera├º├úo com salvamento na pasta do funcion├írio + espelhamento em rede.

### Adicionado (validade)
- Validade por certificado: o lote (ou a edi├º├úo individual) pode definir uma validade em meses pr├│pria, respeitada em Vencimentos, painel de indicadores, toast, crach├ís e na pasta 00_Certificados_OLD da rede (vazio = usa a validade do template).

### Alterado
- Nenhuma janela do sistema pode ter mais de 720px de altura (limite global); janelas menores: Novo/Editar Funcion├írio, Ficha de EPI (itens/gerenciar/devolu├º├úo/anexos), Adicionar Fun├º├úo, Empresas e Nova Integra├º├úo.

## [1.22.7] - 2026-09-10

### Corrigido
- Digitacao de datas (nascimento, admissao), CPF e telefone nao embaralha mais: a formatacao agora acontece ao sair do campo (ou Enter), nao a cada tecla.
- Menu Configuracoes abre imediatamente (verificacao da tarefa agendada passou para segundo plano).
- Dialogos de cartoes de bloqueio/crachas (revisao da emissao, preview e resultado) nao travam mais o programa - mesmo ajuste da v1.22.6 aplicado a todos os dialogos, com reexibicao forcada caso a janela nasca oculta.

## [1.22.6] - 2026-09-10

### Corrigido
- Janela de Nova Integra├º├úo/Empresas abria e sumia e o programa parava de receber cliques: o grab modal agora s├│ ├® aplicado depois que a janela est├í est├ível (dan├ºa interna de t├¡tulo do CustomTkinter), com lift/focus e libera├º├úo segura ao fechar.
- Erro "unknown option 0.0" ao rolar o preview de cart├Áes em PDF.

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
- Placeholders dos campos agora ficam vis├¡veis: a cor padr├úo do CustomTkinter (cinza claro) tinha contraste baixo demais e sumia sobre o fundo dos campos ÔÇö cor sobrescrita globalmente para um tom mais escuro/leg├¡vel (acompanha o tema claro/escuro).

### Alterado
- Di├ílogo "Empresas" (Integra├º├Áes): r├│tulos "Nome da empresa" e "CNPJ (opcional)" acima dos campos de cadastro r├ípido.


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
- **Gap entre a lista e a pagina├º├úo (todas as abas)**: o frame de bot├Áes de
  p├ígina do `PaginationBar` era criado sem altura definida e, com
  `pack_propagate(False)`, travava nos 200px default do CTkFrame ÔÇö com o
  scaling da tela, a barra ficava ~400px de altura e empurrava a pagina├º├úo
  para longe da lista. Agora a barra nasce com a altura correta (34px) e a
  lista preenche todo o espa├ºo at├® ela
- Removidos tamb├®m os c├ílculos-manuais de altura das listas
  (`_fit_scroll_height`) das p├íginas ÔÇö o layout por grid passa a mandar

## [1.21.0] - 2026-09-08

### Adicionado
- **ASO com moldura Altec no PDF**: o documento do m├®dico (PDF ou imagem)
  agora entra em p├íginas A4 com cabe├ºalho/rodap├® Altec ÔÇö logo, empresa,
  "ASO n┬║ ÔÇö Tipo ÔÇö Documento do m├®dico" e "P├ígina X de Y" ÔÇö com o conte├║do
  encaixado na ├írea central (antes ia solto, sem identidade)
- **Lista de backups mais limpa**: mostra apenas os **├║ltimos 30** backups
  (com aviso quando existem mais) e nova coluna **Data e Hora** leg├¡vel
  (dd/mm/aaaa HH:MM:SS) para cada backup
- **Seta de rolagem na sidebar**: "Ôû╝ role" discreto no rodap├® indica quando
  h├í mais itens abaixo e some ao chegar no fim

### Corrigido
- **Lista flutuante do autocomplete resolvida**: a lista de nomes agora
  esconde quando o foco sai dela (Alt-Tab, clique fora), quando a p├ígina ├®
  trocada (inclusive via atalhos Ctrl+N) e quando o campo ├® limpo ÔÇö n├úo
  fica mais ├│rf├ú sobre a tela

## [1.20.1] - 2026-09-08

### Corrigido
- **Tabelas/listas quebradas (regress├úo v1.19.0)**: aninhar um
  `CTkScrollableFrame` horizontal dentro de outro vertical colapsava o
  conte├║do (tabela virava um quadro pequeno e cortado). O `ScrollListFrame`
  agora usa **um ├║nico canvas** com scroll vertical + barra horizontal
  manual: sem overflow a tabela estica at├® a largura dispon├¡vel (como
  antes da v1.19.0); com conte├║do mais largo que a janela, a barra
  horizontal ativa de verdade (Shift + roda do mouse tamb├®m rola).
  Componente ├║nico ÔÇö hist├│rico, funcion├írios, fun├º├Áes, backups, cart├Áes,
  ASO e di├ílogos de EPI sem nenhuma mudan├ºa de c├│digo.

## [1.20.0] - 2026-09-08

### Adicionado
- **Guia convertido s├│ no build (2.24)**: o `build_exe.py` agora converte
  `templates/GUIA_NORMATECH.docx` ÔåÆ `GUIA_NORMATECH.pdf` durante o build
  (Word da m├íquina de desenvolvimento); o cliente s├│ recebe o PDF pronto ÔÇö
  sem Word COM no cliente, sem travamentos. Sem PDF pronto, o app usa o
  gerador ReportLab embutido (fallback silencioso)
- **ASOs vencidos em pasta pr├│pria (2.24)**: na rede, ASO vencido vai para
  `{Func}/ASOs/Vencidos/` e a c├│pia antiga em `ASOs/` ├® movida (mesmo padr├úo
  dos certificados `00_Certificados_OLD`); arquivos locais ficam intactos

### Corrigido
- Linha divis├│ria da tela inicial agora fica **entre o logotipo e o bloco
  data+hora** (data em cima, hora embaixo) ÔÇö n├úo mais entre data e hora (2.24)

### Alterado
- Barra lateral com **scroll** ÔÇö todos os itens ficam acess├¡veis mesmo com a
  janela pequena (vers├úo permanece fixa no rodap├®) (2.24)

## [1.19.0] - 2026-09-08

### Adicionado
- **Ajuda na sidebar (2.23)**: nova linha "Ajuda (F1)" na barra lateral ÔÇö abre
  o Guia de Introdu├º├úo (mesma a├º├úo do F1 e do bot├úo da tela inicial)
- **Guia em DOCX edit├ível (2.23)**: o guia agora nasce de
  `templates/GUIA_NORMATECH.docx` ÔÇö quando o arquivo existe e ├® mais novo que
  o PDF, o app converte via Word (COM) automaticamente; sem Word ou sem docx,
  cai no gerador ReportLab embutido (fallback silencioso). Para editar o guia:
  altere o .docx no Word (ou regenere com `python tools/make_guia_docx.py`)
- **C├│digos de tipo na importa├º├úo de ASOs (2.23)**: coluna Tipo aceita
  `A` Admissional, `P` Peri├│dico, `M` Mudan├ºa de Fun├º├úo, `R` Retorno ao
  Trabalho e `D` Demissional (nomes completos continuam aceitos); modelo
  Excel atualizado com legenda
- **Scroll horizontal em todas as tabelas/listas** (hist├│rico, funcion├írios,
  fun├º├Áes, backups, cart├Áes, ASO, fichas e di├ílogos de EPI): nada mais sai
  cortado em janelas estreitas

### Corrigido
- Data de entrega na ficha de EPI voltava com "ÔÇö" ao adicionar item ÔÇö agora
  vem com a data atual (2.23)
- Dropdown do autocomplete podia ficar flutuando na tela ao fechar o di├ílogo
  pai (Novo ASO etc.) ÔÇö agora ├® destru├¡do junto (2.23)
- CNH E.A.R. no cadastro: legenda corrigida para "Exerce Atividade Remunerada"
  (2.23)

### Alterado
- Tela inicial: data e hora em destaque ao lado do logotipo, separados por
  linha divis├│ria fina (2.23)
- Tela de backups: "├Ültimo Backup autom├ítico" agora mostra data **e hora**
  (2.23)

## [1.18.0] - 2026-09-08

### Adicionado
- **Guia de Introdu├º├úo (2.21)**: novo PDF amig├ível para o usu├írio final gerado
  pelo pr├│prio sistema (`data/GUIA_NORMATECH.pdf`) cobrindo funcion├írios,
  certificados, vencimentos, cart├Áes, crach├ís, ASO, EPI, backups, rede,
  configura├º├Áes e atalhos; aberto pelo novo bot├úo "Guia de Introdu├º├úo" na tela
  inicial ou pela tecla **F1** em qualquer tela
- **Espelhamento completo validado (2.20)**: teste de integra├º├úo garante que o
  `Sincronizar Agora`/sync de inicializa├º├úo copia 100% dos tipos de documento
  para a rede (certificados, assinados, outros, cart├Áes e lotes, ASOs, fichas
  e termos de EPI, crach├ís e lotes) na estrutura `{Funcion├írio}/...`

## [1.17.0] - 2026-09-08

### Corrigido
- **Ficha de EPI ÔÇö PDF refeito (2.22)**: t├¡tulos das tabelas n├úo sobrep├Áem mais
  o cabe├ºalho; linha de devolu├º├úo agora tem espa├ºo pr├│prio e fica leg├¡vel
  ("Devolvido: 2/5 (Parcial) em dd/mm/aaaa" ÔÇö verde quando Total, laranja
  quando Parcial); fichas com muitos itens quebram para uma nova p├ígina
  repetindo o cabe├ºalho da tabela
- **Devolu├º├Áes preservadas ao editar itens**: ao editar a ficha, as devolu├º├Áes
  s├úo reagrupadas por conte├║do do item (C.A. + descri├º├úo) em vez de posi├º├úo,
  evitando que remover/reordenar itens desloque devolu├º├Áes para o item errado
  (quantidade reduzida abaixo do devolvido descarta a devolu├º├úo)

### Alterado
- Lista de fichas de EPI indica "tudo devolvido"/"devolu├º├úo parcial"/"sem
  devolu├º├úo" e exibe badges "TUDO DEVOLVIDO"/"PARCIAL" por ficha

## [1.16.0] - 2026-09-08

### Adicionado
- **Documento do ASO embutido no PDF**: ao anexar ou digitalizar o ASO, o
  documento do m├®dico passa a ser inclu├¡do nas p├íginas seguintes do pr├│prio PDF
  do ASO (capa do sistema + documento); ao remover o documento, o PDF volta ├á
  capa com espa├ºo reservado
- **Configura├º├Áes organizadas em se├º├Áes recolh├¡veis**: 6 se├º├Áes (Dados da
  Empresa, Seguran├ºa, Apar├¬ncia e Notifica├º├Áes, Backups, Documentos em Rede,
  Diagn├│stico) com esconder/mostrar ÔÇö apenas a primeira abre por padr├úo
- **Devolu├º├úo de EPI separada** (refinamento 2.16): novo bot├úo "Devolu├º├úo" por
  ficha registra itens como Pendente/Total/Parcial com data pr├│pria; gera
  **Termo de Devolu├º├úo em PDF** para o funcion├írio assinar
  (`Devolucao - dd-mm-aaaa (EPI-XXXXXX).pdf`) e regenera a ficha com as
  devolu├º├Áes registradas; se todos os itens forem devolvidos por completo,
  oferece fechar a ficha

### Corrigido
- **Salvar ficha de EPI**: di├ílogo de itens agora expande a rolagem
  corretamente; datas com ano de 2 d├¡gitos s├úo rejeitadas (antes viravam ano
  26); salvar com o PDF aberto em um leitor mostra mensagem amig├ível pedindo
  para fechar o arquivo; remover todos os itens pede confirma├º├úo
- **Formul├írio de itens da ficha**: colunas de devolu├º├úo sa├¡ram do formul├írio
  de retirada (devolu├º├úo ├® registrada depois, pelo bot├úo pr├│prio)

## [1.15.1] - 2026-09-08

### Adicionado
- **Bloqueio de emiss├úo de crach├ís**: o crach├í (paisagem e vertical) s├│ ├®
  gerado para funcion├írio com foto cadastrada, pelo menos uma NR dentro da
  validade e ASO dentro da validade; na revis├úo da emiss├úo o funcion├írio
  bloqueado aparece destacado em vermelho com os motivos e ├® pulado na gera├º├úo
  (listado em "Pulados" no resultado)

### Alterado
- **NRs vencidas nunca entram no crach├í**: checkboxes s├│ oferecem treinamentos
  v├ílidos (vencidas aparecem desabilitadas) e a gera├º├úo filtra vencidas em
  qualquer caminho

## [1.15.0] - 2026-09-08

### Adicionado
- **Crach├ís em folha A4**: crach├ís (paisagem e vertical) agora saem em folha
  A4 com guia de corte tracejada ÔÇö v├írios por folha (paisagem real 3/folha,
  vertical real 4/folha); PDF individual tamb├®m em A4 com o crach├í centrado
- **Tamanho reduzido 86x54mm**: op├º├úo na revis├úo da emiss├úo para escalar o
  crach├í ao tamanho de cart├úo de cr├®dito sem alterar o layout (mais por folha)
- **Backup via Tarefa Agendada do Windows** (item 2.19): switch na aba
  Configura├º├Áes para ligar/desligar backup di├írio com o programa fechado,
  hor├írio configur├ível (padr├úo 12:00) e indicador de status da tarefa;
  registra via schtasks (NormaTechBackup) executando `--backup` headless

### Alterado
- `main.py` aceita `--backup` (backup sem interface, usado pela tarefa
  agendada); BackupManager n├úo inicia agendador interno no modo headless

## [1.14.0] - 2026-09-05

### Adicionado
- **Crach├í de Identifica├º├úo vertical 7,8x12cm**: novo modelo
  `CRACHA-VERTICAL` na aba Cart├Áes de Bloqueio ÔÇö mesmo conte├║do do modelo
  paisagem (NRs com validade, ASO, emiss├úo, assinatura) em layout retrato;
  dimens├Áes lidas do template (qualquer card.json cracha pode definir
  largura/altura)

### Inalterado
- Modelo paisagem `CRACHA-ALTEC` (12x7,8cm) mantido intacto

## [1.13.0] - 2026-09-04

### Adicionado
- **Crach├í de Identifica├º├úo 12x7,8cm**: novo modelo `CRACHA-ALTEC` na aba
  Cart├Áes de Bloqueio ÔÇö r├®plica do modelo XLSX da ALTEC (t├¡tulo, foto 3x4,
  texto de autoriza├º├úo, tabela Capacita├º├úo/Data/Validade at├® 8 NRs, emiss├úo
  edit├ível, vencimento + n├║mero do ASO, campo de assinatura destacado e
  rodap├® de proibi├º├úo)
- **Revis├úo da emiss├úo do crach├í**: di├ílogo pr├│prio com data de emiss├úo
  (padr├úo hoje) e sele├º├úo de NRs por funcion├írio (pr├®-marcadas com as 8 mais
  recentes, limite m├íximo de 8), exibindo o ASO vigente
- **Grava├º├úo das emiss├Áes**: tabela `crachas` com numera├º├úo sequencial
  CRACHA-XXXXXX por funcion├írio; preview n├úo consome numera├º├úo
- **Lote**: PDF ├║nico multip├ígina (data/crachas/LOTES) ou um PDF por
  funcion├írio (data/crachas/{Funcionario})
- **Rede**: crach├ís espelhados em {Funcionario}/Crachas e lotes em
  Crachas_Gerais

### Corrigido
- Dashboard: contagem de ASOs vencidos respeita apenas o ASO mais recente
  de cada funcion├írio (teste atualizado para a sem├óntica correta)

## [1.12.0] - 2026-09-04

### Adicionado
- **Modelos de importa├º├úo**: pasta `MODELOS DE IMPORTACAO/` com planilhas de
  exemplo (Funcion├írios A-I, Certificados A-C, Cart├Áes de Bloqueio A-B e ASO
  A-E) + LEIA-ME com colunas e valores v├ílidos; geradas por
  `tools/make_import_templates.py` (regener├ível)
- **Importa├º├úo de ASOs em lote**: bot├úo "Importar Excel" na aba ASO ÔÇö casa por
  CPF ou nome, valida tipo/data/validade por linha e gera os PDFs
  automaticamente com espelhamento na rede; linhas com erro n├úo param a
  importa├º├úo (resumo ao final)
- **ATUALIZAR.bat** (`deploy/`, copiado para `dist/` no build): atualiza o
  programa na m├íquina do cliente a partir da pasta "Atualizacao" ÔÇö fecha o app,
  faz backup autom├ítico de `data/`, substitui os arquivos com `robocopy /MIR`
  **excluindo `data/`** e esvazia a pasta de atualiza├º├úo ao terminar

## [1.11.0] - 2026-09-04

### Adicionado
- **Novos campos do funcion├írio (2.16)**: Tipo Sangu├¡neo (lista), Data de
  Admiss├úo (m├íscara dd/mm/aaaa), Registro CTPS e checkbox "Possui CNH com
  E.A.R." no cadastro
- **Import Excel colunas F-I**: Tipo Sangu├¡neo, Data de Admiss├úo, Registro
  CTPS e CNH EAR (Sim/N├úo) com valida├º├úo por linha; export ganha as mesmas
  colunas
- **Aba ASO (2.16)**: Atestado de Sa├║de Ocupacional com numera├º├úo sequencial
  (ASO-XXXXXX), tipo (Admissional, Peri├│dico, Mudan├ºa de Fun├º├úo, Retorno ao
  Trabalho, Demissional), validade em meses (padr├úo 12) e PDF com espa├ºo
  reservado para colar/digitalizar o exame real; anexar arquivo ou digitalizar
  direto pelo scanner; busca, pagina├º├úo e download do documento
- **ASO em Vencimentos**: ASOs aparecem na aba Vencimentos (filtro NR "ASO"),
  no painel de indicadores da Home e no toast de vencimentos (certificados +
  ASOs que vencem em 7 dias); bot├úo "ASO" no card emite direto para o
  funcion├írio
- **Ficha de EPI (2.16)**: bot├úo "EPI" na linha do funcion├írio abre o gerente
  de fichas ÔÇö cada ficha tem c├│digo pr├│prio (EPI-XXXXXX), itens de Entrega
  (CA / Descri├º├úo / Qtde / Data / Visto) e Devolu├º├úo (Qtde / Data / Visto),
  PDF A4 regener├ível a cada edi├º├úo com linhas em branco para assinatura ├á m├úo
- **EPI ÔÇö anexos m├║ltiplos**: fichas digitalizadas podem ser anexadas em
  v├írias vers├Áes (devolu├º├Áes parciais) sem apagar as anteriores; status
  Em Aberto/Fechado altern├ível a qualquer momento
- **Rede**: ASOs e fichas de EPI espelhados na estrutura de documentos em rede
  (`{Funcion├írio}/ASOs` e `{Funcion├írio}/EPIs`)
- Atalho Ctrl+7 abre a aba ASO (Ctrl+8 Cart├Áes, Ctrl+9 Importa├º├úo em Lote,
  Ctrl+0 Backups)

### Corrigido
- SQL amb├¡guo (`created_at`) na listagem de ASOs com JOIN de funcion├írios

## [1.10.0] - 2026-09-04

### Corrigido
- **Digitaliza├º├úo em 2 m├íquinas (bug cr├¡tico)**: `ShowSelectItem` n├úo existe na
  API WIA ÔÇö agora lista scanners via DeviceManager; sem scanner ÔåÆ erro amig├ível,
  1 scanner conecta direto, 2+ abre o seletor nativo (`ShowSelectDevice`)

### Adicionado
- **Data de Nascimento (2.15)**: campo edit├ível no cadastro de funcion├írios
  (m├íscara dd/mm/aaaa, valida├º├úo de data real), coluna E no import Excel e
  coluna "Data Nascimento" no export
- **Aniversariantes na Home**: blocos "Aniversariantes de hoje" e
  "Aniversariantes do m├¬s" com nome e dia
- **Data e hora atuais na Home**: rel├│gio (HH:MM:SS) e data por extenso,
  atualizados a cada segundo
- **Toast de anivers├írio**: notifica├º├úo no in├¡cio do app quando algu├®m faz
  anivers├írio no dia

### Alterado
- Janela Cadastrar/Editar Funcion├írio com campos rol├íveis e bot├Áes fixos no
  rodap├® (cabe em telas menores mesmo com o novo campo)

## [1.9.0] - 2026-09-04

### Adicionado
- **Pasta virtual universal (2.14)**: os "Outros documentos" do funcion├írio
  (bot├úo Docs) agora aceitam **qualquer formato** (DOCX, XLSX, ZIP, MP4 etc.),
  com limite de **50MB** por arquivo (antes: 10MB e apenas PDF/JPG/PNG)
- **Valida├º├úo de seguran├ºa no upload**: extens├Áes execut├íveis/scripts
  (EXE, BAT, CMD, JS, VBS, PS1, MSI etc.) e tipos MIME correlatos s├úo
  bloqueados; arquivos sem extens├úo tamb├®m s├úo rejeitados

### Alterado
- Tamanho exibido na lista de documentos em KB/MB conforme o arquivo
- Di├ílogo "Adicionar" abre para todos os arquivos (`*.*`)

## [1.8.2] - 2026-09-04

### Adicionado
- **Roadmap**: nova se├º├úo 2.14 "Expans├úo da Pasta Virtual do Funcion├írio" ÔÇö envio de arquivos de qualquer formato (DOCX, XLSX, ZIP, etc.) com limite de 50MB por arquivo

## [1.8.1] - 2026-09-03

### Corrigido
- **Card duplicado em Vencimentos**: certificados antigos (emitidos antes do
  CPF ser cadastrado) geravam um segundo card do mesmo funcion├írio, pois o
  agrupamento usava o CPF/nome registrados no momento da emiss├úo ÔÇö agora
  agrupa apenas por funcion├írio, exibindo o snapshot mais completo
- **Vencimentos/Dashboard/toast contam apenas a ├║ltima emiss├úo de cada NR**:
  emiss├úo renovada deixa de constar como vencida (renova├º├úo substitui a
  antiga no controle de vencimentos, indicadores da tela inicial e notifica├º├úo
  de startup); card TOTAL renomeado para "TOTAL de certificados ativos"

## [1.8.0] - 2026-09-03

### Adicionado
- **Documentos em rede**: nova se├º├úo em Configura├º├Áes ÔÇö espelha certificados,
  cart├Áes, certificados assinados e outros documentos em pasta/caminho de rede
  organizados por funcion├írio (`{Func}/Certificados/{NR}`, vencidos em
  `00_Certificados_OLD`, `{Func}/Cartoes`, `{Func}/Certificados Assinados`,
  `{Func}/Outros`, lotes em `Cartoes_Gerais`); sincroniza├º├úo no startup +
  bot├úo "Sincronizar Agora"; toast e log de erro se a rede falhar
- **Documentos do funcion├írio ("Outros")**: bot├úo **Docs** na aba Funcion├írios
  ÔÇö identidade, CNH etc. salvos no banco (BLOB at├® 10MB, PDF/JPG/PNG) e
  espelhados na rede em `{Func}/Outros`
- **Nova estrutura de pastas local**: `data/certificados/{Func}/{NR}`,
  `data/cartoes/{Func}` + `data/cartoes/LOTES`, `data/assinados/{Func}`;
  migra├º├úo autom├ítica ├║nica dos PDFs antigos de `CERTIFICADOS/` com
  atualiza├º├úo dos caminhos no banco (idempotente; n├úo casados v├úo para
  `_ORFAOS`)
- **Contraste do modo escuro aumentado**: textos secund├írios, textos muted,
  bordas e verde de sucesso mais claros/leg├¡veis

### Alterado
- **Bot├úo do tema**: agora ├® uma linha "Tema" na barra lateral, acima de
  Configura├º├Áes (antes sobreponha o bot├úo hamburger no header)

## [1.7.1] - 2026-09-03

### Corrigido
- **Bot├úo de tema vis├¡vel com a sidebar aberta**: hamburger e tema dividiam
  a mesma c├®lula do grid e se sobrepunham em alguns escalamentos; agora
  vivem em um header pr├│prio (hamburger ├á esquerda, tema ├á direita)
- **Duplica├º├úo do content_frame**: `_build_sidebar` recriava a ├írea de
  conte├║do e a Home a cada boot/troca de tema (frames empilhados)
- **Tela inicial rol├ível**: com o painel de indicadores aberto em telas
  pequenas o conte├║do era cortado ÔÇö agora a p├ígina tem scrollbar
- **Bot├úo "Mostrar/Ocultar indicadores" em destaque**: altura 36, fundo
  `surface` com borda e texto centralizado bold (antes era transparente e
  discreto demais)

### Alterado
- **Scrollbar vis├¡vel nas listas**: novo `ScrollListFrame`
  (`src/ui/components/scroll_frame.py`) com trilho e thumb nas cores
  corporativas ÔÇö aplicado nas listas do Hist├│rico e dos Cart├Áes de
  Bloqueio (a scrollbar do CTK ├® cinza flat e se confundia com a superf├¡cie)

## [1.7.0] - 2026-09-03

### Adicionado
- **Painel de indicadores na tela inicial**: vencidos, vencem em 7/30 dias,
  percentual de assinados, emiss├Áes por NR (top 5) e por m├¬s (├║ltimos 6) ÔÇö
  com bot├úo para ocultar/mostrar persistido entre sess├Áes
- **Tema claro/escuro**: bot├úo na sidebar (persistido em `data/appearance.json`,
  atalho Ctrl+T); paleta escura completa sem reiniciar o app
- **Atalhos de teclado**: Ctrl+1..9 navega entre as p├íginas, Ctrl+T alterna
  o tema, F5 atualiza a p├ígina atual
- **Visualizador do log de erros**: nova se├º├úo "Diagn├│stico" na tela de
  Configura├º├Áes com as ├║ltimas linhas de `data/error.log` e bot├Áes
  Atualizar/Limpar/Abrir Pasta
- **Filtro "Assinado" no Hist├│rico**: Todos/Sim/N├úo combin├ível com os
  filtros existentes (texto, NR, per├¡odo) e respeitado na exporta├º├úo
- `HistoryRepository.get_dashboard_stats()` (indicadores do painel)
- Docs de planejamento: `docs/QR_CODE.md`, `docs/CI_GITHUB_ACTIONS.md`,
  `docs/MULTIUSUARIO.md`

## [1.6.0] - 2026-09-03

### Adicionado
- **Filtros no Hist├│rico de Emiss├Áes**: al├®m da busca por texto, a listagem
  agora filtra por **NR** (menu suspenso com as NRs existentes no banco) e por
  **per├¡odo do treinamento** (De/At├® em dd/mm/aaaa, campos opcionais);
  filtros combin├íveis entre si
- **Exporta├º├úo da listagem**: bot├úo "Exportar" exporta **todos os resultados
  dos filtros atuais** (n├úo s├│ a p├ígina vis├¡vel) para **Excel (.xlsx)** ou
  **CSV (.csv)** ÔÇö formato escolhido no di├ílogo de salvar; CSV com `;` e
  UTF-8 BOM para abrir corretamente no Excel brasileiro; colunas: Numero,
  NR, Funcionario, CPF, Data Inicio, Data Fim, Carga (h), Descricao, Assinado
- Novo `HistoryRepository.query()/count_query()/distinct_nrs()` (busca
  combinada texto + NR + per├¡odo); `search/count_search` passam a delegar
- Teste `test_history_filters.py`: filtros (texto/NR/per├¡odo/combinados),
  contagens, `distinct_nrs` e exporta├º├úo xlsx/csv

## [1.5.1] - 2026-09-03

### Corrigido
- **Autocomplete de funcion├írios n├úo fecha mais sozinho**: removidos os
  timers de fechamento autom├ítico (FocusOut 250ms e watchdog 300ms) que
  faziam a lista sumir durante a emiss├úo; agora a lista fecha apenas por
  a├º├úo expl├¡cita ÔÇö clique fora, Esc, sele├º├úo de funcion├írio ou minimizar ÔÇö
  com um fallback de seguran├ºa de 60 segundos
- **N├║mero do certificado em todas as folhas**: "CERT-XXXX" agora ├®
  impresso no canto inferior direito de todas as p├íginas do PDF (antes
  s├│ na primeira); assinaturas continuam apenas na p├ígina 1

### Adicionado
- Teste `test_cert_number.py`: valida presen├ºa do n├║mero em todas as
  p├íginas de um certificado multi-p├ígina

## [1.5.0] - 2026-09-01

### Adicionado
- **Digitaliza├º├úo direta no app** (roadmap 2.9): bot├úo "Digitalizar" por
  certificado no hist├│rico abre tela dedicada com:
  - **Escanear no scanner** via WIA (comtypes ÔÇö sem depend├¬ncias novas;
    cancelamento e aus├¬ncia de scanner tratados com mensagem clara + error.log)
  - **Escolher arquivo / foto** do celular (JPG/PNG/PDF)
  - **Multi-p├ígina**: loop de p├íginas combinadas em **um ├║nico PDF** anexado
  - **Ajustes de imagem**: girar ┬▒90┬░, brilho, contraste e **recorte por
    arraste** no preview (com desfazer)
  - Preview antes de confirmar; inser├º├úo pelo mesmo fluxo do item 2.8
    (substitui scan anterior)
- **Novo ├¡cone do programa** ("ICONE RECORTADO"): `assets/logo.ico` convertido
  para ICO verdadeiro multi-resolu├º├úo (16ÔÇô256px) ÔÇö o anterior era um JPEG
  renomeado e n├úo funcionava; `setup_assets.py` regenera a partir da imagem

### Pendente (roadmap 2.9)
- Hist├│rico de digitaliza├º├Áes (m├║ltiplos scans por certificado) ÔÇö exige
  mudan├ºa de esquema do banco

## [1.4.0] - 2026-09-01

### Corrigido
- **Erro ao abrir Certificados** ("bind_all is not allowed"): o clique-global do
  autocomplete usava `bind_all` dos widgets CTk (proibido pelo CustomTkinter) ÔÇö
  trocado por binding direto no Tcl com `%W`, sem o guard e sem colis├Áes

### Adicionado
- **Log de erros central** (`data/error.log`): captura exce├º├Áes de callbacks do
  tkinter e de threads de trabalho (antes invis├¡veis no exe), com contexto,
  traceback e truncamento autom├ítico (1MB ÔåÆ ├║ltimos 256KB)
- **Toast de vencimentos ao abrir**: certificados que vencem nos pr├│ximos 7
  dias (contagem na notifica├º├úo; respeita o toggle de notifica├º├Áes)
- **A├º├Áes nos cards de Vencimentos**: "Emitir" abre Certificados com o
  funcion├írio pr├®-selecionado; "Hist├│rico" abre o Hist├│rico com a busca
  preenchida (clique nos bot├Áes n├úo expande/colapsa o card)
- **Importar fotos em massa** (aba Funcion├írios): escolhe uma pasta, casa por
  CPF (11 d├¡gitos no nome do arquivo) ou nome exato (ignora acentos/caixa) e
  mostra janela de confer├¬ncia com miniatura, status adicionar/substituir e
  checkboxes antes de aplicar (corte 3x4 autom├ítico)
- **Backup em rede (drive mapeado)**: destino configur├ível (padr├úo
  `Z:\SEGURAN├çA\NORMATECH-BACKUP`), ativo por padr├úo e tolerante ÔÇö drive fora
  do ar pula com aviso no `backup.log` sem interromper o backup local
- **Documentos de planejamento**: `docs/INSTALADOR.md` (script Inno Setup
  completo pronto para uso) e `docs/ASSINATURA_DIGITAL.md` (PAdES/ICP-Brasil,
  op├º├Áes, arquitetura e fases)

### Alterado
- **Restaura├º├úo de backup reinicia o app automaticamente** (`os.execv`) em vez
  de apenas fechar
- Configura├º├Áes ganham "Backup em rede" (toggle + caminho edit├ível)

## [1.3.3] - 2026-09-01

### Corrigido
- **Autocomplete de funcion├írios**: a lista agora permanece aberta at├® o
  usu├írio tirar o foco ou clicar fora (antes o watchdog fechava cedo demais);
  removida a checagem de janela ativa que causava fechamento precoce; novo
  gatilho global de clique-fora
- **Filtro de vencimentos (7/15/30/90 dias)**: certificados j├í vencidos
  apareciam nos filtros de per├¡odo futuro ÔÇö agora cada filtro exige
  `0 Ôëñ dias Ôëñ limite` (vencidos s├│ em "Vencidos"/"Todos"); l├│gica extra├¡da
  para `filter_certs` test├ível

### Alterado
- **Backup externo em dois destinos**: al├®m do hist├│rico local, cada backup ├®
  copiado para `Documentos\NormaTech-Backup` e `C:\NormaTech-Backup` (pastas
  criadas automaticamente; falha num destino n├úo interrompe os outros e fica
  registrada no `data/backup.log`); reten├º├úo igual ├á local aplicada nos
  destinos; antiga `Documents\BackupsNormaTech` descontinuada

### Adicionado
- `docs/SUGESTOES.md`: lista priorizada de melhorias (rede, log de erros,
  toast de vencimentos, CI, instalador, validador de templates etc.)
- `test_vencimentos.py`: testes do filtro por per├¡odo/NR/busca

## [1.3.2] - 2026-09-01

### Corrigido
- **Autocomplete de funcion├írios flutuante**: dropdown ganhava watchdog (250ms)
  que o fecha se o app minimizar, outro programa ficar em foco, ou mouse/foco
  sa├¡rem do campo; fecha imediato ao minimizar (`<Unmap>`) e acompanha a janela
  ao mover (`<Configure>`); sele├º├úo usa o cache da lista exibida (sem re-buscar)
- **Erro "bad stickiness value 'center'" ao anexar assinado**: badge "ASSINADO"
  usava `sticky="center"` (inv├ílido no tkinter) ÔÇö o anexo era salvo, mas o
  refresh da lista quebrava. Corrigido para centrar via grid padr├úo

### Alterado
- **Busca mais fluida (CPU fraca)**: as abas Funcion├írios, Hist├│rico, Cart├Áes e
  Vencimentos agora pesquisam somente no **Enter** ou no novo bot├úo **Buscar**
  ÔÇö fim do re-render por tecla digitada (autocomplete do certificado segue ao
  vivo, m├íximo 10 resultados)

### Adicionado
- **Busca na aba Fun├º├Áes**: barra com o mesmo padr├úo (Enter + Buscar + X),
  filtro client-side com edi├º├úo/exclus├úo mapeadas para o ├¡ndice original
- `docs/UI_GPU.md`: estudo de interface com acelera├º├úo GPU (Flet/Flutter,
  PySide6+QML, Dear PyGui, Tauri/Electron) para o cen├írio CPU fraca + GPU
  integrada, com recomenda├º├úo e quick-wins

## [1.3.1] - 2026-09-01

### Corrigido
- **Matr├¡cula pedida s├│ onde precisa**: nova flag `matricula_obrigatoria` por
  template ÔÇö LOTOTO n├úo pede mais (campo some da revis├úo; espa├ºo fica em branco);
  ArcelorMittal continua obrigat├│ria
- **CSN dentro do quadrado**: ajuste por caixa com fonte uniforme reduzida
  (~9pt) e limite de linhas por campo (`wrap_max_lines`): nome em at├® 2 linhas,
  Dpto/Empresa em 1 ÔÇö o excedente ├® apagado (ex.: "JUNIOR" do nome de teste)
- **Impress├úo (WinError 1155)**: cascata ÔÇö verbo "print" do Windows ÔåÆ leitor
  padr├úo com flag de impress├úo (Acrobat `/p /h`, Foxit `/p`, SumatraPDF
  `-print-dialog`, abrindo j├í na janela de imprimir) ÔåÆ ├║ltimo recurso abre o PDF
- **Preview de certificado sem CPF**: mensagem amig├ível em vez do erro
  `CertificateData.funcionario_cpf` (a emiss├úo j├í bloqueava; o preview n├úo validava)
- **Backup autom├ítico em sess├Áes curtas**: jobs com avalia├º├úo imediata no
  startup via metadados (`last_periodic_backup`) ÔÇö intervalo de 15 min passa a
  valer tamb├®m para quem abre o app por poucos minutos; semanal idem
- **Log de backups** (`data/backup.log`): falhas deixam de ser invis├¡veis no exe
- **Rodap├® da tela de cart├Áes**: a├º├Áes divididas em 2 linhas ÔÇö todos os bot├Áes
  vis├¡veis sem esticar a janela
- **Tela de backups**: refresh ao abrir + auto-refresh a cada 30s; tipo
  "Peri├│dico" reconhecido na lista

## [1.3.0] - 2026-09-01

### Adicionado
- **Revis├úo da Emiss├úo** (substitui o popup simples): abre sempre antes de Gerar e
  Preview, com edi├º├úo de **nome, fun├º├úo, telefone e foto** por funcion├írio
  (c├│pias transit├│rias ÔÇö nada grava no cadastro), setor do lote, papel
  L├¡der/Liderado e matr├¡cula obrigat├│ria
- **"Voltar e Editar" no Preview**: reabre a revis├úo com as edi├º├Áes preservadas e
  regenera o preview at├® o resultado ficar bom
- **Quebra de linha** (word_wrap) para nome/fun├º├úo nos templates PPTX com
  auto-shrink vertical: reduz a fonte em passos de 0,5pt at├® as linhas caberem
- **Modo clip** (`text_fit: "clip"`, usado no LOTOTO): sem quebra e sem redu├º├úo ÔÇö
  o texto que passar do limite do campo ├® cortado

### Corrigido
- **ALTEC-PEQUENO com 8 cart├Áes por folha**: shapes do 8┬║ cart├úo (adicionados
  manualmente) renomeados para `CARD8_*` ÔÇö antes os dois ├║ltimos cart├Áes sa├¡am
  com os dados do 7┬║ funcion├írio
- Shape de fun├º├úo do cart├úo 3 do ALTEC-PEQUENO estava nomeado como NOME
  (funcionava por token, corrigido por clareza); toler├óncia da tabela de
  posi├º├Áes da prepara├º├úo reduzida (0,45 ÔåÆ 0,35) para evitar esse tipo de troca
- Script de prepara├º├úo agora reproduz o 8┬║ cart├úo e a posi├º├úo das fotos da
  linha 2 ajustada pelo usu├írio (regenera├º├Áes futuras n├úo desfazem a edi├º├úo)

## [1.2.0] - 2026-08-31

### Adicionado
- **Certificados assinados (escaneados)**: anexar PDF/JPG/PNG (ate 10MB) ao certificado
  pelo historico (BLOB no banco, incluido nos backups), com indicador "ASSINADO",
  download, substituicao e remocao ÔÇö migracao automatica do banco
- **Backup periodico**: a cada 15 min (configuravel em 1-720) enquanto o app esta aberto,
  com retencao propria (ultimos 32) separada dos 12 manuais/semanais
- **Backup duplo**: copia adicional automatica em `Documentos\BackupsCertificados` (toggle)
- **Notificacoes Windows (toast)**: emissao de cartoes, importacao em lote e backups
  concluidos ÔÇö com fallback silencioso e toggle nas configuracoes
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
  da emissao (ArcelorMittal/LOTOTO) ÔÇö agora obrigatoria no popup de geracao, sem fallback
  de CPF e sem persistencia; coluna SQLite antiga e ignorada sem risco
- Backup (todos os tipos) usa **snapshot consistente via SQLite backup API** ÔÇö corrige
  perda potencial de dados em WAL ao copiar o `.db` direto
- Restauracao de backup remove `-wal`/`-shm` residuais ao substituir o banco

### Documentacao
- `docs/REDE.md`: riscos e checklist de validacao do uso em drive mapeado
- ROADMAP atualizado (FASE 1 e se├º├Áes concluidas identificadas na auditoria)

## [1.1.0] - 2026-08-31

### Adicionado
- **Cart├Áes de bloqueio via template PPTX** (alternativo ao JSON, transparente no dropdown):
  - `src/core/pptx_card_service.py`: preenchimento por tokens, troca de foto (blob swap + crop 3x4),
    convers├úo PDF via PowerPoint COM (uma sess├úo por lote), merge e recorte "1 cart├úo por p├ígina" (PyMuPDF)
  - Tokens din├ómicos: `{{NOME}} {{FUNCAO}} {{TELEFONE}} {{CPF}} {{MATRICULA}} {{SETOR}} {{EMPRESA}} {{PAPEL}}`
    ÔÇö somente os presentes no template s├úo usados; valida├º├úo de telefone/foto conforme o template
  - 4 templates preparados: ARCELORMITTAL (4/folha), ALTEC-PEQUENO (7/folha, com fotos 3x4 inseridas),
    CSN (4/folha 2x2), LOTOTO (1/folha ├ù2 slides)
  - `tools/prepare_pptx_templates.py`: regenera os templates a partir dos originais
  - Previews em `templates/cards/pptx/previews/`
- **Campo Matr├¡cula** no cadastro de funcion├írios (migra├º├úo autom├ítica do banco, formul├írio,
  tabela, import/export Excel coluna E); fallback: usa CPF quando vazia
- **Popup de contexto na emiss├úo** (`GenerationOptionsDialog`): Setor do lote (global) e
  L├¡der/Liderado por funcion├írio (padr├úo Liderado, a├º├Áes r├ípidas) ÔÇö exibido s├│ quando o
  template usa os campos
- Op├º├úo "1 cart├úo por p├ígina" na tela de cart├Áes (templates PPTX)
- Testes: `test_pptx_cards.py` (unit├írios + E2E com PowerPoint)
- Docs: `docs/PPTX_TEMPLATES.md`; BUILD.md e ROADMAP.md atualizados

### Corrigido
- Linha duplicada na tabela de funcion├írios (nome renderizado 2x)

## [1.0.0] - 2026-08-25

### Adicionado
- Estrutura completa do projeto (src/, templates/, assets/, data/, build/)
- **Core**: Models Pydantic, Config, Template Loader, PDF Generator, Certificate Service
- **Banco de Dados**: SQLite com tabelas para empresa, funcion├írios, certificados, sequ├¬ncias, backup_meta
- **Reposit├│rios**: EmployeeRepository (CRUD), HistoryRepository (hist├│rico + numera├º├úo)
- **Backup Manager**: Backup autom├ítico semanal (silencioso), backup manual, restaura├º├úo com senha Argon2
- **Interface CustomTkinter**:
  - Home: Sele├º├úo NR (grid), formul├írio din├ómico, autocomplete funcion├írios, preview, gera├º├úo PDF
  - Funcion├írios: CRUD com busca, valida├º├úo CPF, prote├º├úo contra exclus├úo com certificados
  - Hist├│rico: Lista paginada, busca, abertura PDF/pasta
  - Configura├º├úo: Dados empresa + senha restaura├º├úo
  - Backup: Lista backups, download, restaura├º├úo com confirma├º├úo
- **Componentes**: NRSelector, EmployeeAutocomplete, DynamicForm, PDFPreview
- **Templates**: 10 NRs (01, 05, 06, 09, 10, 11, 12, 17, 18, 35) com campos espec├¡ficos
- **Layout PDF**: A4 Landscape, logo centralizado, conte├║do 2 colunas, assinaturas duplas, numera├º├úo discreta
- **Assets**: Logo PNG ÔåÆ ICO (multi-resolu├º├úo), fontes DejaVu (fallback Helvetica)
- **Build**: PyInstaller --onefile --windowed com ├¡cone customizado
- **Documenta├º├úo**: README.md completo, CHANGELOG.md

### Seguran├ºa
- Hash Argon2 para senha de restaura├º├úo
- Valida├º├úo CPF/CNPJ/Registro MTE
- Prote├º├úo contra exclus├úo de funcion├írios com certificados

### Preparado para Futuro
- SignatureProvider pattern (Local + ICP-Brasil placeholder)
- Campos de validade no modelo (para alertas futuros)
- Estrutura modular para novas funcionalidades


---

# Versoes reconstituidas (LEIA-MEs de atualizacao e commits)

## [1.87.1]
- CORRECAO: o arquivamento de feedbacks NAO funcionava (o popup enviava os campos errados e o formulario nao tinha destino). Agora funciona com os motivos padrao (Realizado, Corrigido, Cancelado) e com motivo personalizado digitado.
- O statcard de feedbacks no dashboard agora se chama "Feedbacks em aberto" e pisca com FUNDO azul claro (texto em azul escuro, alto contraste).
- Na pagina de feedbacks, a lista mostra so uma previa da mensagem, com um botao "Ler" que abre o texto completo e os anexos para ver/baixar.

## [1.87.0]
- NOVO modulo de Feedback: botao roxo "FeedBack" no topo de todas as paginas. Qualquer usuario logado pode escrever erros/feedback e anexar arquivos (fotos/prints/PDF, ate 8 arquivos de 50 MB). O horario e a pagina onde o usuario estava sao gravados automaticamente. Os feedbacks ficam salvos em arquivos na pasta do programa no servidor (data\feedbacks\).
- Pagina /feedbacks (acesso SOMENTE do administrador): lista completa com data/hora, usuario, pagina, texto, anexos para download e status. O admin arquiva cada feedback com motivo: Realizado, Corrigido, Cancelado ou um motivo personalizado.
- Dashboard: novo statcard "Feedbacks abertos" — mostra quantos feedbacks ainda nao foram atendidos e pisca em azul claro quando houver algum. Clique nele para abrir a lista (visivel apenas para o administrador).
- Link "Feedbacks" na guia Sistema do menu e atalho personalizavel na area de Atalhos do dashboard.

## [1.86.2]
- Listas de presenca: nomes e funcoes longos NAO sao mais cortados na lateral da celula (quebra de linha ativada nos participantes e altura das linhas ajustada para o texto completo). Cada folha sai sempre em 1 pagina. Testado com NR-01, NR-06, NR-12, NR-18, NR-35, FDS e layout padrao.

## [1.86.1]
- Listas de presenca NR-01 e FDS: o PDF agora sai DEITADO (horizontal), ocupando a folha inteira.
- Listas de presenca: correcao garantida contra corte de texto — o conteudo programatico (NR-06 e demais NRs) nunca mais sai cortado; o gerador amplia a altura da linha automaticamente quando o texto precisa de mais espaco.

## [1.86.0]
- Backup: novo campo "Locais extras de backup" em Configuracoes - cadastre varios destinos adicionais (um caminho por linha, inclusive pastas de rede); cada backup passa a ser copiado para todos os locais.
- Listas de presenca: nova pagina "Lista avulsa" - escolha a NR, qualquer data (futura ou passada) e selecione livremente os colaboradores do cadastro (com busca e marcar/desmarcar todos) ou digite nomes avulsos; nao depende de emissao de certificados no dia.
- Listas de presenca: a lista de FDS (FISPQ) agora usa o modelo proprio "Lista de presenca de treinamento - FISPQ.xlsx" (8 vagas por folha).
- Certificados: emissao com data futura liberada; ao usar data diferente de hoje (individual ou lote), aparece um popup de confirmacao antes de emitir.
- Frota (custos): o campo "Mes especifico" atualiza a pagina automaticamente ao selecionar o mes (sem precisar apertar Enter).
- Frota (custos): o grafico "Custos por mes" ganhou uma linha vermelha com o total mensal sobre as barras; o tooltip mostra apenas o veiculo sob o mouse (gasto total, combustivel e extras).
- Funcionarios: o setor Seguranca agora pode ARQUIVAR funcionarios desligados (sai das listas, historico preservado); excluir e desarquivar continuam exclusivos do administrador.
- Verificado: lista de presenca NR-12 nao corta conteudo no PDF (testes com 1 a 33 participantes, todas as folhas completas).

## [1.85.1]
- Frota (custos): novo botao "Baixar Pacote" — baixa de uma vez um ZIP com o relatorio PDF completo e a planilha Excel do periodo ou do mes selecionado.
- Frota (custos): o campo "Mes especifico" agora usa o seletor de calendario do proprio navegador (sem digitacao) e ganhou um botao "Limpar" para voltar ao modo por periodo.
- Corrigido: o PDF do mes especifico mostrava os meses ate o mes atual (com meses vazios) em vez de mostrar apenas o mes escolhido — tanto no grafico geral quanto nas paginas por veiculo.

## [1.85.0]
- Cintos e Talabartes: ao descartar um item agora e possivel anexar fotos ou documentos (PDF/JPG/PNG, ate 30 MB cada); os anexos ficam salvos na ficha do item descartado e podem ser baixados a qualquer momento.
- Dashboard: dois novos cards de inspecoes de cintos/talabartes — "Inspeções de cintos próximas (30 dias)" (destaque pulsando) e "Inspeções de cintos atrasadas" (destaque vermelho); podem ser ligados ou desligados em "Escolher cards" e levam a pagina de cintos ao clicar.
- Frota: relatorio de custos e consumo por MES ESPECIFICO — na pagina de custos digite o mes (mm/aaaa) para ver graficos e resumo daquele mes; os PDFs (geral e por veiculo) e o Excel respeitam o mes escolhido, e o nome dos arquivos passa a incluir o mes (ex. custos_frota_09-2026.xlsx).

## [1.84.1]
- Cintos e Talabartes: formulario de item repõe os dados digitados quando ha erro de validacao (inclusive o tipo escolhido); data de fabricacao aceita m/aaaa ou mm/aaaa e nao pode ser no futuro.
- Cintos e Talabartes: foto da inspecao "no sistema" voltou a ser selecionavel (o campo ficava oculto).
- Cintos e Talabartes: inspecao so pode ser registrada com o item no estoque; datas de saida/entrada nao podem ser no futuro e a entrada nao pode ser anterior a saida.
- Cintos e Talabartes: atalhos de Saida/Retorno na tabela abrem popups grandes no meio da tela (mesmo padrao da ficha).
- Cintos e Talabartes: registro de entrada pergunta "Item inspecionado" e a escolha entre "Item apto para uso" ou "Item danificado" (com aviso para avaliar o descarte); filtros da lista em uma unica linha.

## [1.84.0]
- Cintos e Talabartes: escolha do tipo (Cinto ou Talabarte) ao criar, com filtro por tipo na lista; campo "Nome" como titulo do item; numero identificador automatico (CINTO-0001 / TALAB-0001).
- Cintos e Talabartes: inspecao inicial automatica ao criar o item (proxima inspecao em 3 meses).
- Cintos e Talabartes: atalhos de Saida e Retorno direto na tabela; busca logo acima da tabela com filtros acima; tabela com rolagem vertical e paginacao.
- Cintos e Talabartes: ficha com popups grandes no centro da tela para Registrar saida, Registrar inspecao e Descartar; popup de inspecao pergunta primeiro se anexa relatorio ou faz no site; proxima inspecao visivel na ficha e sempre com data na badge da lista.
- Cintos e Talabartes: antichama agora e uma barra SIM/Nao; CA obrigatorio apenas para cintos; fabricacao em mes/ano (mm/aaaa); so descarta quem esta no estoque; saida/entrada exigem confirmacao de inspecao/apto.
- Cartoes de bloqueio: nomes e cargos longos reduzem a fonte para caber (antes saiam cortados).

## [1.83.0]
- Novo modulo "Cintos e Talabartes" (menu Seguranca): estoque proprio com marca, modelo, CA, lote, numero de serie e data de fabricacao (dd/mm/aaaa ou mm/aaaa); validade padrao de 5 anos, configuravel por item; badge para itens antichama; descarte antecipado com motivo (desgaste, retencao de queda etc.) e opcao de reativar.
- Inspecoes periodicas a cada 3 meses por item: anexe um relatorio (PDF/JPG/PNG, ate 30 MB) ou crie um relatorio interno com texto e foto; o relatorio fica salvo e pode ser baixado a qualquer momento; a ficha alerta quando a inspecao esta vencida ou proxima (badge piscando a 7 dias).
- Controle de entrada/saida com localizacao (ex. "Ternium - Rio Negro"): ao registrar saida/entrada o usuario confirma "Eu, <usuario>, confirmo que o equipamento foi inspecionado pela equipe de seguranca e que esta apto para uso" e pode incluir observacoes; apenas uma saida aberta por item.
- Permissao "Cintos e Talabartes" (admin/emissor editam; consulta ve).

## [1.82.0]
- Dashboard ainda mais rapido: pilha de vencimentos e frota agora usam cache automatico (15 segundos, com invalidacao imediata quando o banco muda).
- Cards de ASO e certificados vencidos nao fazem mais varreduras duplicadas do banco.
- Contagem de cadastros incompletos deixou de carregar as fotos dos funcionarios.
- Logo do portal cacheada no navegador por 24 horas.
- Modal "Escolher atalhos" so oferece modulos que o usuario tem permissao.
- Emissao em lote corrigida: aviso de erro agora aparece corretamente e itens invalidos (funcionario inexistente, sem CPF, data invalida) sao rejeitados antes da confirmacao de substituicao.

## [1.81.2]
- DASHBOARD MUITO MAIS RAPIDO: o painel estava recalculando os vencimentos 3 vezes a cada abertura (chegava a ~7,5 segundos no servidor). Agora os dados sao calculados uma unica vez, os templates de NR ficam em cache e o calculo de validade foi otimizado — o painel abre quase instantaneo. Os numeros dos cards continuam exatamente os mesmos.
- ASOs e integracoes de funcionarios ARQUIVADOS nao contam mais nos vencimentos (mesma regra que ja valia para os certificados).

## [1.81.1]
- Aviso ao gerar o PDF de uma solicitacao de abastecimento com data mais de 60 dias no passado: o portal pergunta "Deseja gerar o PDF mesmo assim?". Ao confirmar, o PDF e gerado normalmente. Vale para "Ver PDF" e "Baixar PDF" na lista de abastecimentos e na ficha do veiculo — evita erros de digitacao na data (como o caso do AB-2026-00033 com 21/09/2025).

## [1.81.0]
- AVISO MENSAL DE ASOs POR E-MAIL: no dia 1 de cada mes o portal envia a lista de ASOs que vencem no mes seguinte. Para ativar: va em Configuracoes, na secao de E-mail (SMTP) preencha o servidor (se ainda nao estiver), cadastre o e-mail de cada usuario e/ou outros destinatarios e marque "Aviso mensal de ASOs".
- NOVO BOTAO "Incompletos (Excel)" em Funcionarios: exporta planilha formatada com os funcionarios de cadastro incompleto e uma coluna mostrando o que falta (Foto, CPF, Funcao, Telefone, ASO valido).
- VERIFICADO (sem mudanca): os relatorios de gastos da frota (pagina, Excel e PDF) JA incluem os itens extras dos abastecimentos nos totais — na coluna "Itens extras" e no total geral. Manutencao nao tem valor monetario cadastrado (e so preventivo).

## [1.80.2]
- Documento assinado do certificado: o anexo agora aceita arquivos de ate 30MB (antes o limite era 10MB).

## [1.80.1]
- Duplicidades de funcionarios: apos mesclar, o grupo sai da lista automaticamente (o agrupamento considera somente cadastros ativos; o arquivado fica em Funcionarios > Arquivados).
- Painel: card renomeado para "Vencimentos em 30 dias" e com a MESMA fonte de dados da pagina /vencimentos (certificados + ASOs + integracoes) — os numeros do painel e da pagina agora sao sempre iguais.
- /Funcionarios: filtros reorganizados em linha horizontal (quebrando de linha quando nao couber na tela); o botao "Limpar" aparece sempre que algum filtro estiver ativo (busca, arquivados, nivel, ASO, telefone, foto, CPF, funcao).
- /presencas: botao "Arquivar" agora e vermelho e fica alinhado a direita da lista.

## [1.80.0]
- Duplicidades de funcionarios: nova pagina (botao "Duplicidades" em /funcionarios, apenas admin) que agrupa cadastros com o mesmo nome (ignorando acentos) ou o mesmo CPF.
- Mescla de duplicados: transfere certificados, ASOs, EPIs, crachas e documentos para o registro principal e arquiva o duplicado (historico preservado). Pede motivo e registra no log de auditoria.
- (v1.79.0 incluso) card "Certificados vencidos", "ASOs vencidos" piscando, filtros Sim/Nao em /funcionarios, atalho "Cartao de bloqueio" na ficha, foco mantido na busca ao limpar, "Saidas (veiculos) em aberto".
- (v1.78.0 incluso) correcao do 404 na paginacao de /aso, filtros de situacao/tipo em /aso, busca em /aso/novo, contagens do painel igualadas as de /vencimentos.

## [1.79.0]
- Dashboard: novo card "Certificados vencidos" e destaque vermelho piscante no card "ASOs vencidos" quando houver vencidos.
- Dashboard: "Saidas em aberto" agora se chama "Saidas (veiculos) em aberto".
- /funcionarios: filtros Sim/Nao por ASO, Telefone, Foto, CPF e Funcao.
- Ficha do funcionario: novo atalho "Cartao de bloqueio".
- Barras de busca: o foco permanece na caixa apos limpar o texto.
- Observacao: o card "Cadastro incompleto" ja contava apenas funcionarios com nivel "Incompleto" (Basico nao entra).

## [1.78.0]
- /aso: corrigido o erro 404 ao abrir a segunda pagina da lista.
- /aso: novos filtros de situacao (Vencidos / Vencem em 30 dias) e de tipo.
- /aso/novo: busca de funcionario ao digitar + tipo "Periodico" pre-selecionado.
- Vencimentos: painel e pagina /vencimentos agora mostram as MESMAS contagens (mesma fonte e regra — apenas a emissao mais recente de cada NR/ASO; frota continua contada a parte, nos seus proprios cards).

## [1.77.1]
- Correcao do erro intermitente "duplicate column name: arquivado" no terminal durante a inicializacao (o backup agendado e o portal criavam a coluna ao mesmo tempo). As migracoes agora toleram execucao concorrente; nenhum dado foi afetado. CONTEUDO DA 1.77.0 (incluido nesta pasta)
- Painel do Dashboard por setor: admin define em Configuracoes > "Painel do Dashboard por setor" quais statcards e atalhos cada setor ve.
- Arquivar listas de presenca, certificados e fichas de EPI: Arquivar/ Desarquivar com popup de motivo; filtro Ativos/Arquivados/Todos; itens arquivados saem de /vencimentos, do XLSX e dos contadores do dashboard.
- /funcionarios: coluna "Nivel de cadastro" (Completo/Basico/Incompleto) com filtro por nivel.

## [1.77.0]
- Painel do Dashboard por setor: o admin define em Configuracoes > "Painel do Dashboard por setor" quais statcards e atalhos cada setor ve. Usuario do setor sem preferencia propria recebe o padrao do setor.
- Arquivar listas de presenca, certificados e fichas de EPI: novo botao Arquivar/Desarquivar com popup de motivo; filtro Ativos/Arquivados/Todos nas listas; itens arquivados saem de /vencimentos, do export XLSX e dos contadores do dashboard.
- /funcionarios: nova coluna "Nivel de cadastro" com badge Completo (verde), Basico (amarelo) e Incompleto (vermelho), com filtro por nivel na lista.

## [1.76.2]
- Cards do painel com contagem zero agora aparecem sempre (mostrando 0) quando o modulo e permitido e o card esta habilitado na personalizacao — antes eles sumiam quando nao havia ocorrencias.
- Animacoes de alerta (piscar) continuam apenas quando a contagem e maior que zero.

## [1.76.1]
- Ficha do veiculo: todas as acoes (Editar, Nova solicitacao, Arquivar, Bloquear, Excluir) em linha unica abaixo do quadro de informacoes.
- Cards do painel piscam em vermelho quando ha listas de presenca nao assinadas ou documentos da frota proximos de vencer.
- Paginacao na pagina de vencimentos da frota (25 itens por pagina; o Excel exportado continua completo).
- Vencimentos de NRs e da frota agora ignoram funcionarios e veiculos arquivados (nao aparecem em /vencimentos, /frota/vencimentos nem nos contadores do painel).

## [1.76.0]
- layout da ficha de veiculo, bloqueio de exclusao com historico, popup de motivo, novos cards no painel. [resumo compacto de HISTORICO RECENTE]

## [1.75.0]
- templates NR persistentes, NR-06/NR-18 ajustados, XLSX formatado, filtros de certificados na ficha. [resumo compacto de HISTORICO RECENTE]

## [1.74.0]
- novos atalhos, envio de lista assinada, cracha rapido. [resumo compacto de HISTORICO RECENTE]

## [1.73.2]
- Corrigido: a busca em tempo real agora pesquisa o cadastro completo. Ao digitar na barra de busca, apos uma breve pausa a pesquisa e enviada automaticamente ao servidor, trazendo resultados de todo o banco — nao apenas da pagina atual. Corrige o caso de funcionarios nao encontrados (ex.: nomes que estao em outra pagina da listagem, com ou sem acento).
- O texto digitado e o foco da barra de busca sao preservados apos a busca automatica, permitindo continuar digitando.

## [1.73.1]
- Busca em tempo real: as tabelas filtram enquanto voce digita nas barras de pesquisa (contagem de resultados, ignora acentos) em todas as telas com busca.
- Dashboard: nova area de Atalhos em painel proprio com borda, acima dos cards; botao "Personalizar" permite escolher quais atalhos mostrar; os atalhos respeitam as permissoes do usuario.

## [1.73.0]
- Regra de 1 certificado por NR dentro da validade: ao emitir um certificado de NR que o funcionario ja possui dentro da validade (individual ou em lote), o portal avisa e pede confirmacao antes de emitir. O novo certificado substitui o vigente anterior; o antigo permanece no historico.
- Certificados antigos/vencidos da mesma NR nao sao mais contados como "vencidos" quando o funcionario ja tem uma NR igual dentro da validade.

## [1.72.0]
- Painel (dashboard): novo card "Certificados sem documento assinado" com link direto para o historico filtrado.
- Painel: os cards agora respeitam as permissoes do usuario (quem nao tem acesso a um modulo nao ve mais os cards dele).
- Painel: administrador pode gravar a escolha de cards como padrao do seu setor — novos usuarios do setor ja comecam com esses cards.
- Painel: cards personalizaveis agora ficam em um painel proprio com borda e botao "Personalizar".
- Painel: cards de aniversariantes (hoje e do mes) podem ser recolhidos e expandidos.

## [1.71.0]
- Busca sem acentos em todas as telas: digitar "joao" encontra "Joao" e "Joao" (frota, abastecimentos, EPI, crachas, cartoes, vencimentos, emissao em lote e pagina de emissao de certificados).
- Barras de busca maiores em todas as paginas.
- Corrigido: "?" sobrando no botao "Gestao de Frota" do menu.

## [1.70.6]
- correcao de erro interno ao abrir ficha do veiculo (migracao da coluna "ano"). [resumo compacto de HISTORICO RECENTE]

## [1.70.5]
- cartao LOTOTO com matricula opcional. [resumo compacto de HISTORICO RECENTE]

## [1.70.4]
- melhorias no formulario de cartoes de bloqueio (busca e popup de setor). [resumo compacto de HISTORICO RECENTE]
