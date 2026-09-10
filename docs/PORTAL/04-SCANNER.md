# NormaTech Portal — Estratégia de Digitalização

> Público: TI/responsável pelo sistema (decisões e configuração) + referência
> para a técnica de segurança (fluxos no `03-MANUAL_USO.md` §5).
> Cenário atual: **scanner USB plugado no PC da técnica de segurança**;
> hoje só ela digitaliza, mas o objetivo é abrir a digitalização para outras
> pessoas sem gerar chamados de suporte.

---

## 1. O problema, em uma frase

Um navegador **não consegue falar com um scanner USB** de outra máquina —
o scanner é um periférico local. Toda solução precisa de uma "ponte" entre o
navegador e o scanner. As opções abaixo são as pontes possíveis, ordenadas
pelo critério **plug-n-play / zero manutenção**.

## 2. Opções comparadas

| Opção | Como funciona | Instalação | Manutenção | Quando usar |
|-------|--------------|------------|------------|-------------|
| **C. Upload manual** | Digitaliza pelo software do fabricante → anexa o arquivo no portal | **Zero** | **Zero** | **Sempre disponível** — fallback universal |
| **D. NormaAgent** (alvo atual) | Mini-app no PC que tem o scanner; o portal chama `localhost:9999`, o agente digitaliza via WIA e envia ao servidor; preview aparece no navegador | Instalar 1x por máquina **com** scanner | Baixa (app simples, auto-start) | Cenário atual: scanner USB no PC da técnica |
| **B2. Digitalização no servidor** (futura) | Scanner USB movido para o **servidor**; o próprio portal digitaliza server-side via WIA; qualquer pessoa com permissão digitaliza do navegador, sem nada instalado | Zero nas máquinas clientes | Baixa | Se outras pessoas passarem a digitalizar com frequência |
| **A. Scan-to-folder** | Multifuncional de rede salva direto numa pasta do servidor; portal mostra "caixa de entrada" de digitalizações | Configuração 1x na multifuncional | Quase zero | Só se a empresa adquirir um multifuncional de rede |

> **Recomendação:** ativar **C + D** (Fase 4). Se a demanda de outros
> funcionários digitalizando crescer, fazer o spike da **B2**. A **A** entra
> automaticamente se um dia houver multifuncional de rede.

## 3. Opção C — Upload manual (disponível desde já)

Fluxo da técnica (idêntico ao que ela já conhece + 1 passo):

1. Digitaliza pelo software do scanner (como hoje), salvando PDF ou imagem
2. No portal: abre o certificado/funcionário → **Anexar documento** → escolhe o arquivo → envia

- Limite: 50 MB/arquivo; extensões livres (Decisão D5 do `01-VISAO_GERAL.md`)
- Vantagem: funciona em qualquer máquina, hoje, sem instalar nada
- Custo: o usuário alterna entre 2 programas (software do scanner + portal)

## 4. Opção D — NormaAgent (alvo plug-n-play do cenário atual)

### Como funciona

```
┌─────────────────────── PC da técnica ───────────────────────┐
│  Navegador (portal)          NormaAgent (mini-serviço local) │
│  botão "Digitalizar"  ────►  http://localhost:9999/scan      │
│        ▲                             │  reutiliza            │
│        │ preview/imagem              ▼                       │
│        └────────────────────  WIA (scanner_wia.py atual)     │
│                                        │                     │
│                                   SCANNER USB                 │
└──────────────────────────────────────────────────────────────┘
        imagem sobe para o servidor e é anexada ao registro
```

- O agente é um pequeno executável Python (PyInstaller) que roda **apenas na
  máquina que tem scanner**, escutando em `localhost:9999` (nunca exposto à rede)
- Reaproveita o módulo existente `src/utils/scanner_wia.py` (WIA via comtypes,
  com diálogo nativo de escolha de dispositivo)
- O portal só chama o agente quando o botão "Digitalizar" é usado; se o agente
  não estiver rodando, o portal mostra mensagem amigável + sugere o upload (C)

### Especificação mínima do agente (Fase 4)

| Endpoint | Função |
|----------|--------|
| `GET /health` | O portal usa para saber se o agente está ativo |
| `GET /scanners` | Lista dispositivos WIA disponíveis |
| `POST /scan` | Digitaliza (PNG) e devolve a imagem; parâmetros: resolução, cor, frente/verso se o scanner suportar |

### Instalação (por máquina com scanner — 1 vez)

1. Copiar `NormaAgent.exe` para a máquina
2. Executar 1x → cria atalho no **Iniciar do Windows** (pasta Startup do
   usuário) → sobe sozinho no login
3. Ícone na bandeja (bandeau/tray) confirma que está ativo

### Por que não instalar o agente no servidor?

Porque o navegador da técnica fala com `localhost` — o agente precisa estar na
**mesma máquina do navegador** (ou seja, onde o scanner está plugado). Falar
com o PC da outra pessoa exigiria liberar porta e achar IP de cliente — frágil
(firewall, DHCP), exatamente o que queremos evitar. Para centralizar no
servidor, existe a opção B2.

## 5. Opção B2 — Scanner no servidor (futuro, quando outros precisarem digitalizar)

**Ideia:** mover o scanner USB para o servidor; o FastAPI ganha um endpoint
`POST /digitalizar` que aciona o WIA **no próprio servidor**. Aí qualquer
pessoa com permissão digitaliza do navegador — sem instalar nada em lugar
nenhum (UX igual à do NormaAgent, sem agente).

**Risco técnico a validar em spike (1–2h):** o portal roda como **serviço do
Windows (sessão 0)**, sem área de trabalho:

- O diálogo gráfico do WIA (`CommonDialog.ShowTransfer`, usado hoje) **não
  aparece** na sessão 0
- É preciso digitalizar **sem diálogo**: `DeviceManager → Connect → Item →
  Transfer(formato PNG)` (a WIA Automation Library permite transferência sem UI)
- Se o spike funcionar: implementar endpoint server-side (com fila simples:
  1 digitalização por vez, já que há 1 scanner)
- Se falhar: alternativa documentada — rodar o portal como app de usuário com
  login automático do Windows no servidor (menos elegante, mas comum em
  pequenas empresas), ou permanecer no NormaAgent

**Critério de disparo:** 2+ pessoas diferentes precisando digitalizar na
mesma semana, ou reclamação recorrente de "preciso ir até o PC da técnica".

## 6. Opção A — Multifuncional de rede com scan-to-folder (se um dia houver)

Fluxo: funcionário aperta **Digitalizar** no painel da multifuncional →
o aparelho salva o PDF em `\\NORMATECH\digitalizacoes` → o portal mostra a
**caixa de entrada** com os arquivos novos → a pessoa clica em **Anexar** no
registro desejado.

Configuração única (IT):

1. Criar pasta compartilhada no servidor com permissão de escrita para o
   usuário da multifuncional
2. No painel web do aparelho: Catálogo de endereços → adicionar destino SMB
   com `NORMATECH`/compartilhamento/credenciais
3. Reservar o IP da multifuncional no DHCP (o destino SMB usa hostname, não IP)
4. No portal (Fase futura): página "Digitalizações" listando arquivos novos da pasta

> Passos concretos variam por marca (Kyocera, HP, Xerox, Brother...): procurar
> "digitalizar para pasta SMB <marca>" no manual do modelo.

## 7. Resumo executivo

| Etapa | O que a técnica faz | O que você (TI) mantém |
|-------|--------------------|------------------------|
| Hoje → Fase 3 | Digitaliza no software do scanner + anexa no portal (C) | Nada |
| Fase 4 | Botão **Digitalizar** no portal (D — NormaAgent no PC dela) | Instalar o agente 1x; pronto |
| Se demanda crescer | Botão Digitalizar para todos (B2 — scanner no servidor) | Mover scanner; validar spike WIA |
| Se comprarem multifuncional de rede | Botão Digitalizar no painel do aparelho + caixa de entrada (A) | Configurar destino SMB 1x |
