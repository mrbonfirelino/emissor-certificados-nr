# CHANGELOG (NormaTech)

> Historico completo de versoes antigas: `docs/changelog-arquivo.md` (NAO ler inteiro, usar busca).

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
