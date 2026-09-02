# Assinatura Digital de Certificados (ICP-Brasil) — Planejamento

> **Status: documento/planejamento.** Nenhuma implementação foi feita.
> O projeto já possui o ponto de extensão `src/core/signature/`
> (`SignatureProvider`) preparado para receber um assinador digital.

---

## Cenário atual

- Certificados são gerados em PDF (ReportLab) com **assinatura manuscrita
  escaneada** anexada ao registro (v1.2.0) — não tem valor criptográfico.
- A assinatura digital **PAdES** (PDF Advanced Electronic Signature, padrão
  ICP-Brasil) dá integridade, autoria e não-repúdio com validade jurídica
  (MP 2.200-2/2001; para treinamentos NR não é exigida, é diferencial).

## Conceitos rápidos

| Termo | Significado |
|-------|-------------|
| **A1** | Certificado em arquivo (.pfx/.p12) — fácil, fica no computador |
| **A3** | Certificado em token/smartcard USB — a norma exige para CPF-A3; mais seguro |
| **PAdES-B/B-T** | Perfis de assinatura; B-T inclui carimbo do tempo (TSA) |
| **PKCS#11** | Driver padrão para falar com o token A3 no Windows |

## Opções técnicas comparadas

| Opção | Como funciona | Custo | Observações |
|-------|---------------|-------|-------------|
| **pyHanko + PKCS#11** (recomendada p/ começar) | Open source; assina PAdES localmente; A3 via driver do token (`p11crypt`) | R$ 0 (sw) + token | Controle total; exige testes com a marca do token do cliente |
| `pypades` / libs comerciais | Wrappers prontos PAdES/ICP-Brasil | Licença | Menos código, dependência de fornecedor |
| APIs em nuvem (Bry, Certisign, Serpro, D4Sign) | App envia o PDF, a nuvem assina com certificado deles ou do cliente | Assinatura mensal/por unidade | Sem token local; exige internet; cuidado com LGPD/dados |

## Arquitetura proposta (fase de implementação)

```
CertificatesPage (emitir)
  └─ certificate_service.generate_certificate(...)
        └─ [opcional] SignatureProvider.assinar_pdf(pdf_path)
              └─ SignerPAdES (novo, pyHanko)
                    ├─ certificado: A3 via PKCS#11 (DLL do token) ou A1 (.pfx)
                    ├─ carimbo do tempo: TSA configurável
                    └─ resultado: CERT-XXXXXX.pdf assinado + verificação
Configuração: pagina Config ganha seção "Assinatura Digital"
  (tipo A1/A3, caminho do .pfx ou DLL do token, PIN salvo? NUNCA — pedir por
   dialog na sessão; TSA URL; ativar/desativar por emissão)
```

Pontos de atenção:
- **Nunca persistir o PIN** — solicitar por diálogo a cada sessão de assinatura
- Assinar **após** gerar o PDF e **antes** de registrar no histórico
- Assinatura em lote (import em massa): sessão do token aberta 1x, assinar N
- Verificação: pyHanko também valida a assinatura gerada (self-check pós-sign)

## Pré-requisitos (lado do usuário)

1. Certificado digital A3 (e-CNPF/e-CPF da empresa/instrutor) + leitora
2. Driver PKCS#11 do token instalado (ex.: Safenet, GD, Bloomy)
3. Appconfig apontando a DLL do driver (ex.: `C:\Windows\System32\eToken.dll`)

## Fases sugeridas

| Fase | Entrega | Estimativa |
|------|---------|-----------|
| 1. Spike | Script standalone: pyHanko assina 1 PDF com o token real do cliente | 1-2 dias |
| 2. Integração | `SignerPAdES` + opção por emissão + config | 3-5 dias |
| 3. Robustez | Lote, erros de token ausente, validação pós-sign, docs | 2-3 dias |

## Riscos

- Diversidade de tokens/drivers (testar com o modelo usado pela ALTEC)
- pyHanko PKCS#11 no exe PyInstaller (empacotar DLLs do p11crypt — validar cedo)
- Sem token conectado no momento da emissão → fallback claro (gerar sem assinar?)
- TSA externo pode ter custo/latência
