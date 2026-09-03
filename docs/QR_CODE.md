# QR Code de Autenticidade — Plano (documento)

> Status: **planejado** (não implementado). Este doc descreve a abordagem
> recomendada e as fases. Nenhuma dependência nova foi adicionada ainda.

## Objetivo

Imprimir um QR code no certificado (PDF) que permita a qualquer pessoa
(fiscal, cliente do serviço) confirmar que o documento foi emitido pelo
NormaTech e não foi alterado.

## Abordagem recomendada

QR code aponta para uma **verificação local-first**:

1. O QR codifica uma URL curta com o número do certificado:
   `https://normatech.local/verificar?cert=CERT-000123&sig=<hmac>`
   - `sig` = HMAC-SHA256 do número usando chave derivada do CNPJ +
     salt do banco (chave nunca impressa no PDF)
2. **Offline (hoje, sem servidor)**: a verificação pode ser feita pelo
   próprio app (tela "Verificar certificado" no Histórico) comparando
   número + HMAC + dados do banco local
3. **Online (futuro)**: a mesma URL passa a apontar para um serviço
   hospedado que consulta o banco sincronizado — sem mudar os PDFs
   já emitidos

## Implementação (fases)

### Fase 1 — Gerar e imprimir (esforço baixo)
- Dependência: `qrcode[pil]` (gera PNG) — leve, sem binários externos
- `src/core/pdf_generator.py`: desenhar QR (~18x18mm) no canto inferior
  esquerdo de **todas** as páginas (o número já vai em todas desde a
  v1.5.1); usar `reportlab` `drawImage`
- `CertificateRecord`: nada muda — o HMAC é derivado, não armazenado
  (se armazenar, qualquer restauração de backup quebra a verificação)

### Fase 2 — Verificação no app (esforço baixo)
- Botão "Verificar autenticidade" no Histórico: lê/scaneia o número
  (input manual já basta na v1) e recalcula o HMAC
- Deve responder: válido/inválido + dados do certificado (nome, NR, data)

### Fase 3 — Serviço online (esforço alto, opcional)
- Exige hospedagem + sincronização do banco (ver MULTIUSUARIO.md)
- Só fazer se houver demanda real de clientes/seguradoras

## Riscos e decisões

- **Chave HMAC**: derivar de `restore.key`? Não — gerar `data/hmac.key`
  dedicado no primeiro run, incluído no backup do `data/`
- **Privacidade**: o QR não pode conter nome/CPF (LGPD) — só número + sig
- **Impressão**: testar em 300dpi; QR mínimo ~15mm para leitura confiável
- **PDFs antigos**: não terão QR (normal; verificação manual pelo número)
