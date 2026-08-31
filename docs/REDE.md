# Uso em Rede (Drive Mapeado) — Guia de Validação

Item 2.1 do roadmap: verificar a viabilidade de rodar o sistema em rede.
Este documento descreve os riscos conhecidos e o checklist de testes para
validar o cenário real antes de qualquer mudança no código.

---

## Riscos conhecidos (antes de testar)

| Risco | Detalhe |
|-------|---------|
| **SQLite + WAL em rede** | O modo WAL do SQLite depende de memory-mapped I/O e locks de arquivo que **não são confiáveis em compartilhamentos SMB/OneDrive**. Dois computadores escrevendo ao mesmo tempo podem corromper o banco. |
| Arquivo de banco travado | Antivírus/sincronização (OneDrive!) podem bloquear o `.db` durante escrita, gerando `database is locked`. |
| Backups periódicos | O backup de 15 min em rede adiciona tráfego constante; latência alta amplia janelas de lock. |
| Caminhos | O app resolve pastas relativas ao `.exe`/raiz — em rede, `data/` e `CERTIFICADOS/` cairiam no compartilhamento. |

## Recomendação inicial

- **Cenário seguro atual:** 1 máquina por vez usa o sistema; backups duplos
  (locais + `Documents`) já protegem os dados.
- **Se o objetivo é compartilhar dados entre máquinas**, o caminho correto é
  manter o banco na máquina principal e compartilhar apenas a pasta
  `CERTIFICADOS\` (leitura) — não o banco.

## Checklist de validação (executar no ambiente real)

1. Preparar
   - [ ] Copiar a pasta `dist\CertificadosNR\` para o drive mapeado (ex: `Z:\CertificadosNR\`)
   - [ ] Conferir permissões de leitura/escrita para todos os usuários (icacls)
2. Banco em rede — 1 máquina
   - [ ] Abrir o app, cadastrar um funcionário, emitir um certificado
   - [ ] Fechar e reabrir: dados persistiram?
   - [ ] Rodar backup manual: funcionou? quanto tempo levou?
3. Banco em rede — 2 máquinas simultâneas
   - [ ] Abrir o app nas duas máquinas
   - [ ] Cadastrar funcionários diferentes ao mesmo tempo
   - [ ] Emitir certificados ao mesmo tempo
   - [ ] Observar: erros `database is locked`? corrompimento? (rodar `PRAGMA integrity_check`)
4. Latência
   - [ ] Medir tempo de: abrir tela de funcionários / emitir certificado / backup manual
   - [ ] Comparar com uso local
5. OneDrive/sincronização
   - [ ] Se o drive for pasta sincronizada, pausar a sincronização e repetir o teste 3

## Resultados e próximos passos

- Se o teste 3 falhar (esperado): registrar e avaliar migração para cliente-servidor
  (ex: PostgreSQL) — esforço alto, fora do escopo atual.
- Se o teste 3 passar com 2 máquinas ocasionais: documentar limitação
  ("uso simultâneo restrito a baixa concorrência") e monitorar.

> Preencha os resultados dos testes nesta seção antes de mudar o código.
