# NormaTech Portal — Manual de Uso

> Público: **todos os funcionários que usam o portal** (técnica de segurança,
> RH, gestão etc.).
> Versão deste manual: portal em implantação — os módulos vão sendo liberados
> conforme as fases avançam (ver `00-INDICE.md`).

---

## 1. Como acessar

1. Abra o navegador (Chrome ou Edge)
2. Digite na barra de endereço: **`normatech:8000`**
   (se não abrir, tente `http://normatech:8000` — com o `http://`)
3. Faça login com o usuário e a senha que você recebeu

> 💡 Dica: com o portal aberto, pressione **Ctrl+D** para adicionar aos
> favoritos e acessar com 1 clique depois.

O portal funciona em qualquer computador ligado na rede da empresa.
**Não precisa instalar nada** e não funciona de fora da empresa.

## 2. Login e senha

| Situação | O que fazer |
|----------|-------------|
| Primeiro acesso | Use a senha provisória recebida; o portal **obriga** a trocar no primeiro login |
| Trocar a senha | Menu do usuário (canto superior) → **Trocar senha** |
| Esqueci a senha | Fale com o administrador do sistema (ver §9) para redefinir |
| Sessão expira | Por segurança, o login expira após um tempo parado — basta entrar de novo |

**Boas práticas:**
- Não compartilhe sua senha — cada ação no portal fica registrada no seu nome
- Ao sair, use **Sair** no menu do usuário (importante em computadores compartilhados)
- Use uma senha com pelo menos 8 caracteres, misturando letras e números

## 3. Visão geral dos módulos

O menu lateral mostra **apenas os módulos que seu papel tem permissão**.
Papéis existentes:

| Papel | O que pode |
|-------|-----------|
| **Admin** | Tudo: módulos operacionais + configurações, backup e gestão de usuários |
| **Emissor** | Opera o dia a dia: cadastrar funcionários, emitir certificados/ASO/EPI/crachás, importar planilhas |
| **Consulta** | Só visualiza: dashboard, funcionários, histórico, vencimentos, frota e listas de presença (sem emitir nem editar) |

| Módulo | Para que serve |
|--------|---------------|
| **Dashboard** | Painel inicial: indicadores, aniversariantes e vencimentos próximos |
| **Funcionários** | Cadastro de colaboradores (nome, CPF, função, foto, documentos) |
| **Certificados** | Emissão de certificados de treinamento NR (NR-01, 05, 06, 09, 10, 11, 12, 17, 18, 35...) |
| **Histórico** | Todos os certificados já emitidos: busca, filtros, reabrir PDF/pasta, anexos assinados |
| **Vencimentos** | Certificados vencidos/próximos do vencimento, com ações rápidas de reemissão |
| **ASO** | Emissão de fichas/ASO em PDF |
| **EPI** | Fichas de EPI por funcionário |
| **Frota** | Veículos (com pasta de documentos e laudos com vencimento), solicitações de abastecimento em PDF e registro de saída/entrada com KM — laudos vencidos aparecem em Vencimentos |
| **Crachás** | Crachás de identificação por funcionário |
| **Cartões de Bloqueio** | Cartões de bloqueio de energia (modelos JSON e PPTX) e importação da lista de bloqueios. O formulário se adapta ao modelo: exibe **Setor**, **Matrícula** e **Papel** somente quando o modelo selecionado usa esses campos |
| **Importações** | Importar funcionários, certificados em lote, ASOs e lista de bloqueios por planilha (Excel) |
| **Integrações** | Vínculos funcionário × empresa cliente com validade (aparecem também em Vencimentos) |
| **Configurações** *(admin)* | Dados da empresa, instrutor, senha de restauração |
| **Backup** *(admin)* | Backup manual agora + histórico de backups automáticos |
| **Usuários** *(admin)* | Criar/desativar usuários e definir papéis |

## 4. Passo a passo: emitir um certificado

1. **Funcionários** → confira se o funcionário já está cadastrado
   (se não estiver: **Novo funcionário** → nome, CPF, função → **Salvar**;
   opcionalmente clique no campo de foto para anexar a foto)
2. Vá em **Certificados** (ou **Novo certificado**)
3. Selecione o **funcionário** (digita e o portal autocompleta)
4. Escolha a **NR** (ex: NR-35) — carga horária, validade e conteúdo
   programático já vêm preenchidos conforme a norma
5. Confira **data de início/fim** e a carga horária
6. Clique em **Gerar certificado**
7. O portal abre o PDF: **imprima** (Ctrl+P) ou **baixe** o arquivo
8. Depois da assinatura física, volte no **Histórico**, abra o certificado e
   **anexe o documento assinado** (foto ou PDF escaneado) — fica registrado
   no sistema

> O número do certificado (CERT-000001...) é gerado automaticamente, em
> sequência, sem repetição — inclusive se duas pessoas emitirem ao mesmo tempo.

## 5. Passo a passo: digitalizar um documento

**Jeito 1 — Anexar arquivo (sempre disponível):**

1. Digitalize normalmente no scanner, como você já faz hoje (salve o PDF/imagem)
2. No portal, abra o registro (certificado/funcionário) → **Anexar documento**
3. Clique em **Escolher arquivo** → selecione o arquivo → **Enviar**

**Jeito 2 — Digitalizar direto do portal (com o NormaAgent instalado no PC
que tem o scanner — ver `04-SCANNER.md`):**

1. Abra o registro no portal → **Digitalizar**
2. Coloque o documento no scanner e confirme
3. Aparece a pré-visualização na tela → confira → **Anexar**

> Detalhe: limite de **50 MB por arquivo**. Documentos grandes: escaneie em
> PDF (não imagem) para ocupar menos espaço.

## 6. Passo a passo: importar planilha (Importações)

1. Baixe o **modelo** de importação na tela (Excel/CSV)
2. Preencha o modelo (funcionários ou treinamentos em lote)
3. **Importações** → escolha o tipo → selecione o arquivo → **Importar**
4. O portal mostra o resumo: linhas importadas, avisos e erros linha a linha
5. Confira o resultado em **Funcionários**/**Histórico**

## 7. Vencimentos: não deixar certificado vencer

- O **Dashboard** mostra os vencimentos da semana assim que você entra
- Em **Vencimentos**, filtre por período/NR; cada item tem ação rápida
  **Emitir** (reemite o treinamento com os dados do funcionário)
- Recomendação: rode a tela de Vencimentos **1x por semana**

## 8. Frota: veículos, abastecimento, checklist e custos

1. **Cadastrar veículo**: Frota → **Novo veículo** → tipo (Caminhão mostra
   subtipo; Empilhadeira/Retroescavadeira não têm placa), próprio ou alugado
   (alugado pede contratante) e empresa → **Salvar**
2. **Documentos do veículo**: na ficha do veículo, anexe CRV, CRLV,
   contratos, inspeções (mesmo jeito da pasta do funcionário)
3. **Laudo com vencimento**: na ficha → **Adicionar laudo** → tipo (CRLV,
   Fumaça Preta etc.), arquivo e data de validade. Laudo vencendo/vencido
   aparece em **Vencimentos** e no painel do **Dashboard**
4. **Saída/entrada**: na ficha → **Registrar saída** (data, hora, KM,
   destino, motorista, autorizado por). Na volta, **Registrar entrada** com
   o KM final — o sistema calcula o KM rodado
5. **Abastecimento**: Frota → **Abastecimentos** → **Nova solicitação** →
   veículo, combustível, KM, **litros e valor**, condutor e aprovação →
   gera PDF com serial único (ex.: `AB-2026-00007`) pronto para imprimir
   e assinar. Use **Exportar Excel** para custos e o link **NF** para
   anexar a nota fiscal do abastecimento
6. **Checklist semanal (veículos leves)**: na ficha do veículo →
   **Novo checklist semanal** → marque S/N para cada item em cada dia
   (2ª a sábado), informe motorista, líder e se o veículo pode operar →
   **Salvar e gerar PDF** no formato do formulário da empresa
7. **Manutenção preventiva**: na ficha → cadastre o item (ex.: troca de
   óleo, intervalo 10.000 km) — o sistema avisa quanto falta em
   **Vencimentos** e na própria ficha; use **Concluir** quando fizer
8. **Custo e consumo**: no fim da ficha do veículo, o bloco "Custo e
   consumo" mostra o total abastecido e a média KM/L real comparada com a
   ficha técnica. No **Dashboard**, os cards de frota mostram veículos,
   saídas em aberto e custo do mês
9. **Status do veículo**: a lista de veículos mostra automaticamente se
   cada um está **Em Viagem** (com motorista e destino), **Em
   Manutenção**, **Indisponível** ou **Disponível**
10. **Checklist em branco**: na ficha, use **Gerar em branco (preenchimento
    manual)** para baixar o PDF do checklist semanal já com veículo, placa,
    KM e data — imprima, preencha, assine e anexe de volta em **Checklist →
    Anexar assinado**. O mesmo vale para o **abastecimento assinado**
    (tela de NFs do abastecimento)
11. **Menu**: o portal agora agrupa o menu em **Segurança** (Certificados,
    Emissão em Lote, Histórico, Listas de Presença, Ficha de EPIs, Crachás,
    Cartões, Vencimentos), **Cadastros** (Funcionários, ASO, Integrações) e
    o botão dedicado **Gestão de Frota** no topo

## 9. Listas de presença: gerar e anexar a assinada

1. **Gerar (fluxo do dia)**: Listas de Presença → **+ Nova lista** → informe
   só a **data** → o portal mostra, para cada NR emitida naquele dia, uma
   seção com os participantes para conferir (marcada por padrão) →
   **Emitir listas do dia** gera todas de uma vez.
2. **Compilado**: após emitir, aparece um aviso perguntando se você quer
   **baixar o compilado** — um PDF único com todas as listas do dia, pronto
   para imprimir. Também é possível baixá-lo depois pelo botão no topo da
   listagem (informando a data).
3. **Imprimir**: abra o PDF pelo detalhe da lista e distribua para os
   participantes assinarem.
4. **Registrar assinaturas**: no detalhe da lista, use **Enviar lista
   assinada** para anexar o escaneio (PDF, JPG ou PNG) — o status vira
   **Assinada** automaticamente.
5. **Status**: use **Alterar status** para marcar **Parcial** enquanto nem
   todos assinaram. Pendente/Parcial/Assinada aparecem com cores diferentes
   na listagem.
6. NRs com modelo pronto (NR-01, 06, 12, 18, 35) saem na planilha da
   empresa; as demais usam o layout padrão com a logo.

## 10. Backup e Auditoria (admin)

- **Backup**: menu **Backup** (só admin) → **Fazer backup agora** cria um
  ponto de segurança na hora; a lista abaixo mostra os backups existentes.
  Os automáticos continuam sendo configurados em **Configurações**
- **Auditoria**: menu **Auditoria** (só admin) → histórico de quem fez o
  quê (logins, emissões, importações, exclusões, frota, configurações, listas de presença),
  com busca

## 11. Perguntas frequentes (FAQ)

**O portal não abre (`normatech:8000` não carrega)**
1. Confira se escreveu certo; tente `http://normatech:8000`
2. Seu computador está na rede da empresa? (cabo/wifi da empresa, não visitante)
3. Teste no computador de um colega: se lá abrir, chame o responsável (pode ser
   o arquivo `hosts` da sua máquina — ver `02-DEPLOY_SERVIDOR.md` §3)

**"Não seguro" aparece na barra de endereço — é vírus?**
Não. É apenas um aviso padrão do navegador para sites internos sem cadeado
HTTPS. O portal é interno da empresa e não há bloqueio — pode usar normalmente.

**Esqueci minha senha**
Fale com o administrador (§9). Ele redefine e você troca no próximo login.

**Baixei o PDF mas ele não abre**
Baixe de novo; se persistir, abra o **Histórico** → reabra o certificado. Se
ainda falhar, anote o número do certificado (CERT-XXXXXX) e chame o responsável.

**Impressão saiu cortada**
Os PDFs são A4 paisagem. Na janela de impressão, marque **Paisagem** e
**Ajustar à página**; desative margens personalizadas.

**Emiti um certificado e o número saiu duplicado?**
Não acontece: a numeração é controlada pelo servidor. Se parecer estranho,
confira no **Histórico** filtrando pelo número.

**Posso usar o celular?**
Sim, pelo navegador, na rede wi-fi da empresa. Para digitalizar/imprimir, use
o computador.

**O app antigo (desktop) ainda funciona?**
Sim, enquanto a migração dura. Prefira o portal para o dia a dia — os dados
são os mesmos.

## 11. Com quem falar

| Assunto | Quem |
|---------|------|
| Senha, acesso, "não abre", erros | Responsável pelo sistema (admin do NormaTech) |
| Dúvidas de preenchimento de treinamento/NR | Técnica de Segurança |
| Trocar dados da empresa/instrutor | Admin, em **Configurações** |

> **Para o administrador:** procedimentos técnicos (deploy, serviço, backup,
> restauração) estão em `02-DEPLOY_SERVIDOR.md`.
