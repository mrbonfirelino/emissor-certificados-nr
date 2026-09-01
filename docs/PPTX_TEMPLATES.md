# Templates PPTX de Cartao de Bloqueio

O sistema de cartoes suporta DOIS tipos de template, de forma transparente ao usuario:

- **JSON** (`templates/cards/*.card.json`): layout desenhado pelo ReportLab (ex.: `ALTEC`)
- **PPTX** (`templates/cards/pptx/*.card.json` + `.pptx`): layout desenhado no PowerPoint

Os dois aparecem juntos no dropdown "Modelo" da tela de Emissao de Cartoes de Bloqueio.

---

## Requisitos

- **Microsoft PowerPoint instalado** (conversao PPTX -> PDF via COM/`comtypes`).
  Sem PowerPoint, templates PPTX nao funcionam (mensagem de erro clara e exibida).
- Bibliotecas: `python-pptx`, `comtypes`, `pymupdf` (ja no `requirements.txt`).

---

## Como funciona

1. Cada template PPTX e uma "folha" com 1 ou N cartoes por slide.
2. Os shapes de dados sao nomeados no PowerPoint como `CARD{slot}_{CAMPO}`:
   - Textos: qualquer nome `CARD{k}_...` (ex.: `CARD1_NOME`, `CARD2_DADOS`)
   - Foto: obrigatoriamente `CARD{k}_FOTO` (shape Picture)
3. Os textos contem tokens que sao substituidos na geracao:

   | Token | Origem do dado |
   |-------|----------------|
   | `{{NOME}}` | Funcionario (maiusculas) — editavel na revisao |
   | `{{FUNCAO}}` | Funcionario (maiusculas) — editavel na revisao |
   | `{{TELEFONE}}` | Funcionario (formatado) — editavel na revisao |
   | `{{CPF}}` | Funcionario |
   | `{{MATRICULA}}` | **Obrigatória no popup** de geração (número tem validade — não fica no cadastro, sem fallback CPF) |
   | `{{SETOR}}` | Perguntado na revisão (valor unico para o lote) |
   | `{{EMPRESA}}` | Fixo no `card.json` (`empresa_default`) |
   | `{{PAPEL}}` | Revisão: LIDER ou LIDERADO (por funcionario) |

4. **Somente os tokens presentes no template sao usados** (deteccao automatica).
   A validacao tambem e dinamica: um template sem `{{TELEFONE}}` nao exige telefone.
5. **Ajuste de texto** (campo `text_fit` do `card.json`):
   - `"wrap"` (padrao): liga quebra de linha (word_wrap) e reduz a fonte em
     passos de 0,5pt (min. 5,5pt) ate as linhas caberem na largura e altura da caixa
   - `"clip"` (ex.: LOTOTO): sem quebra e sem reducao — o que passar do limite
     do campo e **cortado**
6. Na geracao:
   - Lotes maiores que a capacidade geram varios clones do template
     (capacidade = nº slides x cartoes por slide)
   - Cartoes nao preenchidos na ultima folha ficam em branco (texto vazio + foto cinza)
   - Conversao em PDF com UMA unica sessao do PowerPoint (rapida)
   - Opcao "1 cartao por pagina": recorta cada cartao da folha via PyMuPDF
   - Sem "PDF unico": gera 1 PDF por funcionario (cartao recortado)

## Revisao da Emissao (edicao temporaria)

Antes de **Gerar** e de **Preview** abre sempre a tela de Revisao da Emissao,
onde o usuario pode alterar **nome, funcao, telefone e foto** de cada funcionario,
alem do setor do lote, papel (Lider/Liderado) e matricula.

- As alteracoes valem **somente para aquela emissao** — nada e gravado no
  cadastro/banco (o dialog trabalha sobre copias transitorias do funcionario)
- No Preview ha o botao **"Voltar e Editar"**, que reabre a revisao com as
  edicoes anteriores preservadas para regenerar o preview

---

## Arquivos de cada template (em `templates/cards/pptx/`)

| Arquivo | Funcao |
|---------|--------|
| `{CODE}.pptx` | Template preparado (tokens + shapes nomeados) |
| `{CODE}.card.json` | Metadados: codigo, cliente, `cards_per_slide`, `empresa_default`, zonas |
| `previews/*.pdf` | Exemplos gerados para validacao visual |

### Formato do `.card.json`

```json
{
  "card_code": "CSN",
  "cliente_nome": "CSN",
  "descricao": "Cartao de bloqueio CSN (4 por folha, Lider/Liderado)",
  "template_type": "pptx",
  "pptx_file": "CSN.pptx",
  "cards_per_slide": 4,
  "slides": 1,
  "empresa_default": "ALTEC",
  "card_zones_fraction": [[0.0, 0.0, 0.5, 0.5], [0.5, 0.0, 1.0, 0.5], ...]
}
```

- `card_zones_fraction`: bbox de cada cartao em fracao da pagina
  (usado no recorte "1 cartao por pagina"). Ordem: linha por linha, esquerda->direita.

---

## Templates disponiveis

| Codigo | Campos | Capacidade | Ajuste de texto |
|--------|--------|-----------|-----------------|
| `ARCELORMITTAL` | NOME, MATRICULA, FOTO | 4 por folha (1 slide) | wrap |
| `ALTEC-PEQUENO` | NOME, FUNCAO, TELEFONE, FOTO* | 8 por folha (4x2, 1 slide) | wrap |
| `CSN` | NOME, SETOR, EMPRESA, PAPEL, FOTO | 4 por folha (2x2) | wrap |
| `LOTOTO` | NOME, FUNCAO, MATRICULA, SETOR, PAPEL (2x), FOTO | 1 por folha (2 slides) | **clip** (corta no limite) |

*Fotos do ALTEC-PEQUENO: o modelo original nao tinha foto; os placeholders 3x4
foram inseridos na preparacao (centralizados, entre os logos e a faixa de perigo).
O 8o cartao foi acrescentado pelo usuario e reproduzido no script de preparacao.

---

## Criar um novo template PPTX

### Jeito manual (no PowerPoint)

1. Duplique um `.pptx` existente em `templates/cards/pptx/`.
2. Substitua os dados de exemplo pelos tokens (ex.: `Nome: {{NOME}}`).
3. No Painel de Selecao (Inicio > Organizar > Painel de Selecao), renomeie:
   - Shape de foto -> `CARD{n}_FOTO` (n = posicao do cartao na folha, 1..K)
   - Shapes de texto -> `CARD{n}_{QUALQUER}` (sufixo livre)
4. Meça as zonas de cada cartao (fracao da pagina) e crie o `{CODE}.card.json`.
5. Reinicie o programa (o dropdown detecta automaticamente).

### Jeito automatico

Os 4 templates atuais foram gerados por `tools/prepare_pptx_templates.py`,
que le os originais de `MODELOS CARTAO BLOQUEIO/`, aplica tokens/nomes/zonas e
escreve as copias preparadas. Use como base para novos modelos (o script e
idempotente: pode ser re-executado sem corromper os originais).

---

## Solução de problemas

| Problema | Causa / Solucao |
|----------|-----------------|
| "Microsoft PowerPoint nao encontrado" | Instale o Office ou use templates JSON |
| Token `{{X}}` apareceu no PDF impresso | Shape de texto nao esta nomeado `CARD{n}_...` |
| Foto nao trocou | Shape precisa ser Picture e chamar `CARD{n}_FOTO` exatamente |
| Cartao em branco na folha | Normal: slot nao preenchido do ultimo lote |
| Texto do nome cortado | Diminua a fonte no template ou use nome menor |
| Erro COM ao converter | Feche dialogs do PowerPoint abertos e tente de novo |

---

## Notas tecnicas

- Substituicao de texto e por **paragrafo** (herda estilo do 1o run), o que
  resolve tokens quebrados em varios runs ("FABIO" + "RCIO").
- Foto e trocada por **blob swap** (troca a imagem mantendo posicao/tamanho/z-order)
  com center-crop para o aspecto do box (nao distorce).
- Shapes dentro de grupos sao processados recursivamente.
- Conversao: `PowerPoint.Application` (COM dinamico) -> `SaveAs(..., 32)` = PDF.
