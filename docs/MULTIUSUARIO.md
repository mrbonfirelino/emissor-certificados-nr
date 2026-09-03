# Multiusuário / Servidor — Estudo (documento)

> Status: **estudo** (não implementado). **Pré-requisito absoluto: validar o
> item 1 do SUGESTOES.md (banco em drive mapeado, checklist REDE.md)** — a
> decisão de arquitetura depende desse resultado.

## Cenários possíveis

### Cenário A — Rede com SQLite (hoje, custo zero)
- App instalado em cada máquina, banco no drive mapeado (`Z:\`)
- SQLite/WAL suporta acesso concorrente pela rede, **mas** locking em SMB
  é frágil (corrupção já documentada com WAL em compartilhamentos)
- Veredicto do REDE.md decide: se 2 máquinas simultâneas funcionarem sem
  erros de lock por semanas, **este cenário basta** para o caso de uso
- Mitigações: `PRAGMA busy_timeout` (já 30s), backups frequentes (já ok),
  e uma única máquina emitindo por vez (processo, não tecnologia)

### Cenário B — Servidor de banco real (custo alto)
- PostgreSQL (recomendado; licença livre) ou Firebird/SQL Server
- Migração via SQLAlchemy? **Não** — o código usa SQL direto e enxuto;
  trocar para SQLAlchemy reescreve ~4 repos + perde o SQLite backup API
- Abordagem recomendada se B for necessário:
  1. Manter SQLite como cache/local e sincronizar (complexo — evitar)
  2. **ou** extrair camada de persistência com 2 implementações
     (SQLite local / PostgreSQL servidor) — esforço estimado: 2-3 rounds
- Requer infra: servidor sempre ligado, rede estável, IT do cliente

### Cenário C — Servidor de aplicação (fora de escopo)
- API REST + frontend web; equivale a reescrever o produto. Só se houver
  demanda comercial clara.

## Recursos que acompanham multiusuário (qualquer cenário B+)

| Recurso | Descrição | Esforço |
|---------|-----------|---------|
| Tabela `users` | login + papel (admin/operador) | médio |
| Trilha de auditoria | quem emitiu/anexou o quê (tabela `audit_log`) | médio |
| Tela de login | substitui acesso direto | médio |
| Sessões/lock otimista | conflito de edição de funcionário | alto |

## Recomendação

1. Rodar o checklist REDE.md no ambiente real (2ª máquina)
2. Se A funcionar: documentar limitação e ficar no A — o app é single-site
   por natureza (fotos/scanner locais, PowerPoint local)
3. Se A falhar e houver N clientes pedindo: avaliar B com PostgreSQL +
   camada de persistência dupla, começando pela trilha de auditoria
   (útil mesmo em single-user)
