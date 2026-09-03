# Sugestões de Melhoria — NormaTech (priorizadas)

Levantamento de melhorias candidatas a próximas versões, ordenadas por
valor/esforço. Itens do ROADMAP concluídos não se repetem aqui.

---

## Alta prioridade

1. **Validar uso em rede (drive mapeado)** — executar o checklist do
   `docs/REDE.md` no ambiente real antes de qualquer decisão de arquitetura
   (2 máquinas simultâneas, lock do SQLite, latência). *(O backup em rede já
   existe desde a v1.4.0 — falta validar o BANCO em rede.)*
2. ~~Log de erros central~~ — **feito na v1.4.0** (`data/error.log`)
3. ~~Toast de vencimentos ao abrir~~ — **feito na v1.4.0** (7 dias)
4. ~~Ações nos cards de Vencimentos~~ — **feito na v1.4.0** (Emitir + Histórico)
5. **Build onefile opcional** — o BUILD.md já descreve o modo; gerar as duas
   variantes (onedir para testes, onefile para distribuição) em cada release.

## Média prioridade

6. **CI com GitHub Actions** — rodar `test_pptx_cards --unit`, `test_signed_docs`,
   `test_backup`, `test_vencimentos` e `test_photo_importer` a cada push
   (o E2E precisa de PowerPoint, fica manual).
7. ~~Restauração de backup com auto-restart~~ — **feito na v1.4.0**
8. **Instalador (Inno Setup)** — planejado e documentado em
   `docs/INSTALADOR.md` (script pronto); falta gerar a primeira build.
9. ~~Histórico: filtros por NR/período + exportação Excel/CSV~~ — **feito na
   v1.6.0** (menu NR + período De/Até + botão Exportar xlsx/csv)
10. ~~Exportar/importar fotos em massa~~ — **feito na v1.4.0** (aba Funcionários,
    casamento por CPF/nome com janela de conferência)
11. **Validador de templates PPTX** (`tools/`) — abre cada `.pptx` e confere
    tokens órfãos, shapes sem `CARD{slot}_` e fotos ausentes, evitando surpresas
    na impressão.

## Baixa prioridade / estudo

12. **Interface GPU** — ver `docs/UI_GPU.md` (medir primeiro; Flet ou
    PySide6+QML se um dia migrar).
13. **Assinatura digital ICP-Brasil** — planejada em `docs/ASSINATURA_DIGITAL.md`
    (PAdES via pyHanko + token A3); falta o spike com o token real.
14. **Backup em nuvem** — Google Drive/OneDrive do usuário como destino
    adicional opcional (o destino em rede/drive mapeado existe desde a v1.4.0;
    nuvem ainda não).
15. **Multiusuário com servidor** — se o item 1 indicar necessidade real de
    concorrência, avaliar PostgreSQL/Firebird (esforço alto).

## Quick-wins de desempenho (CPU fraca)

- Busca por Enter/botão (feito na v1.3.2) — maior ganho isolado
- Manter fotos como miniaturas em cache nas linhas (já feito)
- Evitar animações/tema dinâmico (não usados)
- Reduzir `font_scale` nas máquinas mais lentas (config já permite)
