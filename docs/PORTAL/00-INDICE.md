# Portal Web NormaTech — Índice da Documentação

> Tudo sobre a evolução do NormaTech de aplicativo desktop para portal web
> na rede da empresa. Criado em Set/2026 — versão de referência: NormaTech v1.12+

## Por onde começar?

| Você é... | Leia nesta ordem |
|-----------|------------------|
| **Funcionário / Técnica de Segurança** (usuário do portal) | `03-MANUAL_USO.md` |
| **TI / responsável pelo sistema** | `01-VISAO_GERAL.md` → `02-DEPLOY_SERVIDOR.md` → `04-SCANNER.md` |
| **Quer entender uma decisão** (HTTPS, banco de dados, scanner...) | Seção "Decisões Registradas" do `01-VISAO_GERAL.md` |

## Arquivos

| Arquivo | Conteúdo |
|---------|----------|
| `01-VISAO_GERAL.md` | Documento mestre: arquitetura, stack, decisões registradas (HTTP/hostname, SQLite vs PostgreSQL, scanner, uploads), matriz de permissões, fases do projeto, riscos |
| `02-DEPLOY_SERVIDOR.md` | Passo a passo técnico: preparar o servidor, instalar, configurar como serviço do Windows (NSSM), firewall, acesso por `http://normatech` (porta 80) ou `http://normatech:8000`, atualizações e troubleshooting |
| `03-MANUAL_USO.md` | Manual do usuário final: como acessar, login, cada módulo explicado, passo a passo de emissão de certificado, anexos, digitalização, FAQ |
| `04-SCANNER.md` | Estratégia de digitalização: cenário atual (scanner USB no PC da técnica), opções comparadas, NormaAgent, caminhos futuros |

## Status do projeto

| Fase | Entrega | Status |
|------|---------|--------|
| 0 | Documentação (esta pasta) | ✅ Concluída |
| 1 | Esqueleto web + login + permissões + dashboard | ✅ Concluída (v1.24.0) |
| 2 | Funcionários + Certificados + Histórico no portal | ✅ Concluída (v1.25.0–v1.27.0) |
| 3 | Demais módulos (ASO, EPI, crachás, cartões, vencimentos, importações) | ✅ Concluída (v1.28.0–v1.30.0) |
| 3c | Listas de Presença (geração por emissão do dia; pendente/parcial/assinada) | ✅ Concluída (v1.36.0) |
| 3b | Frota (ROADMAP 2.29 — veículos, abastecimento, movimentações, laudos) | ✅ Concluída (v1.33.0; checklist 2.29.5 aguarda modelo WORD, NFs 2.29.6 longo prazo) |
| 4 | Admin (usuários, config, backup) + auditoria + scanner plug-n-play | ⬜ Pendente (config já entregue na v1.32.0) |

> **Importante:** durante todas as fases, o app desktop continua funcionando
> normalmente — os dois usam o mesmo banco de dados no servidor.
