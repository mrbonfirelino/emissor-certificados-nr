# Sugestões de Melhoria — NormaTech (priorizadas)

Levantamento de melhorias candidatas a próximas versões, ordenadas por
valor/esforço. Itens do ROADMAP concluídos não se repetem aqui.

---

## Alta prioridade

1. **Validar uso em rede (drive mapeado)** — executar o checklist do
   `docs/REDE.md` no ambiente real antes de qualquer decisão de arquitetura
   (2 máquinas simultâneas, lock do SQLite, latência).
2. **Log de erros central** (`data/error.log`) — hoje exceções viram messagebox
   e somem; com log, diagnóstico remoto fica possível (junto do `backup.log`).
3. **Toast de vencimentos ao abrir o app** — "X certificados vencem em 7 dias"
   na inicialização (dados já existem em Vencimentos; só o toast na home).
4. **Ações nos cards de Vencimentos** — botão "Emitir novamente" /
   "Ver histórico" direto no card do funcionário (hoje precisa procurar na aba
   Certificados).
5. **Build onefile opcional** — o BUILD.md já descreve o modo; gerar as duas
   variantes (onedir para testes, onefile para distribuição) em cada release.

## Média prioridade

6. **CI com GitHub Actions** — rodar `test_pptx_cards --unit`, `test_signed_docs`,
   `test_backup` e `test_vencimentos` a cada push (o E2E precisa de PowerPoint,
   fica manual).
7. **Restauração de backup com auto-restart** — hoje restaura e sai (`self.quit()`);
   reiniciar sozinho (`os.execv`) evita "app fechou do nada" para o usuário.
8. **Instalador (Inno Setup)** — atalho, ícone, verificação de Office/PowerPoint
   e criação das pastas de backup externas na instalação.
9. **Histórico: filtros por NR/período + exportação Excel/CSV** da listagem.
10. **Exportar/importar fotos em massa** — hoje a foto só entra via cadastro
    individual ou edição; permitir pasta de fotos casando por nome/CPF.
11. **Validador de templates PPTX** (`tools/`) — abre cada `.pptx` e confere
    tokens órfãos, shapes sem `CARD{slot}_` e fotos ausentes, evitando surpresas
    na impressão.

## Baixa prioridade / estudo

12. **Interface GPU** — ver `docs/UI_GPU.md` (medir primeiro; Flet ou
    PySide6+QML se um dia migrar).
13. **Assinatura digital ICP-Brasil** — o `SignatureProvider` já tem placeholder
    para o fluxo.
14. **Backup em nuvem** — Google Drive/OneDrive do usuário como quarto destino
    opcional (cuidado com sincronização + SQLite; enviar só o `.gz` já fechado).
15. **Multiusuário com servidor** — se o item 1 indicar necessidade real de
    concorrência, avaliar PostgreSQL/Firebird (esforço alto).

## Quick-wins de desempenho (CPU fraca)

- Busca por Enter/botão (feito na v1.3.2) — maior ganho isolado
- Manter fotos como miniaturas em cache nas linhas (já feito)
- Evitar animações/tema dinâmico (não usados)
- Reduzir `font_scale` nas máquinas mais lentas (config já permite)
