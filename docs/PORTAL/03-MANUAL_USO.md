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
| **Consulta** | Só visualiza: dashboard, funcionários, histórico e vencimentos (sem emitir nem editar) |

| Módulo | Para que serve |
|--------|---------------|
| **Dashboard** | Painel inicial: indicadores, aniversariantes e vencimentos próximos |
| **Funcionários** | Cadastro de colaboradores (nome, CPF, função, foto, documentos) |
| **Certificados** | Emissão de certificados de treinamento NR (NR-01, 05, 06, 09, 10, 11, 12, 17, 18, 35...) |
| **Histórico** | Todos os certificados já emitidos: busca, filtros, reabrir PDF/pasta, anexos assinados |
| **Vencimentos** | Certificados vencidos/próximos do vencimento, com ações rápidas de reemissão |
| **ASO** | Emissão de fichas/ASO em PDF |
| **EPI** | Fichas de EPI por funcionário |
| **Crachás** | Crachás de identificação por funcionário |
| **Cartões de Bloqueio** | Cartões de bloqueio de energia (modelos PPTX) |
| **Importações** | Importar funcionários e treinamentos por planilha (Excel/CSV) |
| **Integrações** | Configurações de integração entre telas/dados |
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

## 8. Perguntas frequentes (FAQ)

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

## 9. Com quem falar

| Assunto | Quem |
|---------|------|
| Senha, acesso, "não abre", erros | Responsável pelo sistema (admin do NormaTech) |
| Dúvidas de preenchimento de treinamento/NR | Técnica de Segurança |
| Trocar dados da empresa/instrutor | Admin, em **Configurações** |

> **Para o administrador:** procedimentos técnicos (deploy, serviço, backup,
> restauração) estão em `02-DEPLOY_SERVIDOR.md`.
