# Sugestões de Melhoria — NormaTech (priorizadas)

Levantamento de melhorias candidatas a próximas versões, ordenadas por
valor/esforço. Itens do ROADMAP concluídos não se repetem aqui.
Última revisão: v1.8.0.

---

## Alta prioridade

1. **Validar uso em rede (drive mapeado)** — executar o checklist do
   `docs/REDE.md` no ambiente real antes de qualquer decisão de arquitetura
   (2 máquinas simultâneas, lock do SQLite, latência). *(O backup em rede
   existe desde a v1.4.0 e o espelhamento de documentos desde a v1.8.0 —
   falta validar o BANCO em rede.)*
2. ~~Filtro "Assinado sim/não" no Histórico~~ — **feito na v1.7.0**
   (combinável com texto/NR/período; respeitado na exportação)
3. ~~Log de erros central~~ — **feito na v1.4.0** (`data/error.log`)
4. ~~Toast de vencimentos ao abrir~~ — **feito na v1.4.0** (7 dias)
5. ~~Ações nos cards de Vencimentos~~ — **feito na v1.4.0** (Emitir + Histórico)
6. **Build onefile opcional** — o BUILD.md já descreve o modo; gerar as duas
   variantes (onedir para testes, onefile para distribuição) em cada release.
7. **Re-emissão em massa pela tela Vencimentos** — renovar certificados
   vencidos em lote (seleção + revisão única, reaproveitando o padrão dos
   cartões).

## Média prioridade

8. **CI com GitHub Actions** — plano pronto em `docs/CI_GITHUB_ACTIONS.md`
   (workflow proposto; E2E fica manual por exigir PowerPoint). Falta
   commitar `.github/workflows/tests.yml`.
9. **Instalador (Inno Setup)** — planejado e documentado em
   `docs/INSTALADOR.md` (script pronto); falta gerar a primeira build.
10. ~~Dashboard de estatísticas~~ — **feito na v1.7.0** (painel de
    indicadores na tela inicial, ocultável e persistido)
11. ~~Visualizador de `error.log` no app~~ — **feito na v1.7.0** (seção
    Diagnóstico na tela de Configurações)
12. **Validador de templates PPTX** (`tools/`) — abre cada `.pptx` e confere
    tokens órfãos, shapes sem `CARD{slot}_` e fotos ausentes, evitando
    surpresas na impressão.

## Baixa prioridade / estudo

13. **QR code de autenticidade no certificado** — plano pronto em
    `docs/QR_CODE.md` (HMAC do número + verificação local-first; fases).
14. **Assinatura digital ICP-Brasil** — planejada em
    `docs/ASSINATURA_DIGITAL.md` (PAdES via pyHanko + token A3); falta o
    spike com o token real.
15. **Backup em nuvem** — Google Drive/OneDrive do usuário como destino
    adicional opcional (o destino em rede/drive mapeado existe desde a
    v1.4.0; nuvem ainda não).
16. **Multiusuário com servidor** — estudo em `docs/MULTIUSUARIO.md`;
    pré-requisito: validar o item 1 (rede). Avaliar PostgreSQL + trilha de
    auditoria se houver demanda real.
17. **Interface GPU** — ver `docs/UI_GPU.md` (medir primeiro; Flet ou
    PySide6+QML se um dia migrar).
18. ~~Tema claro/escuro + atalhos de teclado~~ — **feito na v1.7.0**
    (Ctrl+1..9/Ctrl+T/F5, tema persistido)

## Quick-wins de desempenho (CPU fraca)

- Busca por Enter/botão (feito na v1.3.2) — maior ganho isolado
- Manter fotos como miniaturas em cache nas linhas (já feito)
- Evitar animações/tema dinâmico (não usados)
- Reduzir `font_scale` nas máquinas mais lentas (config já permite)
