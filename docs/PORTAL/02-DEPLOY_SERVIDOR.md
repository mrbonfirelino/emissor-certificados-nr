# Portal Web NormaTech — Deploy no Servidor

> Status: **guia pronto — executar a partir da Fase 1** (ver
> [01-VISAO_GERAL.md](01-VISAO_GERAL.md) §8).
> Público: TI/responsável pelo sistema.
> Tempo estimado: 30–60 min na primeira vez.

---

## 1. Pré-requisitos do servidor

| Item | Requisito |
|------|-----------|
| Máquina | PC/servidor **sempre ligado** no horário de expediente, Windows 10/11 Pro ou Windows Server |
| Rede | IP fixo no servidor, **ou** reserva de IP no DHCP do roteador (recomendado) |
| Nome da máquina | `NORMATECH` (renomear — ver §3) |
| Disco | Projeto em pasta **local** (ex: `C:\NormaTech`) — **NUNCA** em pasta sincronizada (OneDrive, Google Drive, Dropbox) |
| Python | 3.10+ instalado no servidor |
| Acesso admin | Conta com privilégio de administrador para instalar o serviço |

> ⚠️ **Verificação de sincronização:** clique com o botão direito na pasta do
> projeto → se aparecer status de sincronização (nuvem, ✓ verde/azul do
> OneDrive etc.), mova para fora. Banco SQLite em pasta sincronizada corrompe
> (riscos em `docs/REDE.md`).

## 2. Instalação

```powershell
# 1. Copiar o projeto (limpo, sem .rar/lixo de teste) para C:\NormaTech
#    Dados atuais: copie também a pasta data\ do PC de origem (banco + certificados emitidos)

# 2. Ambiente virtual + dependências
cd C:\NormaTech
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install -r requirements-web.txt   # fastapi, waitress, jinja2, python-multipart, itsdangerous

# 3. Primeiro teste manual (antes do serviço)
.venv\Scripts\python run_web.py
# Deve subir em http://localhost:8000 — teste no próprio servidor.
# 1º acesso: usuário admin com senha provisória → troque imediatamente.
```

## 3. Nome da máquina (para acesso por `normatech:8000`)

```powershell
# Executar como administrador e reiniciar
Rename-Computer -NewName NORMATECH -Restart
```

Depois de reiniciar, de outra máquina da rede teste:

```powershell
ping normatech
```

**Se o ping funcionar**, o portal já abre em `http://normatech:8000`.

**Se não funcionar** (algumas redes não resolvem nomes por broadcast), escolha
uma das alternativas, na ordem de preferência:

1. **Registro DNS no roteador** (se ele permitir): apontar o nome
   `normatech` → IP fixo do servidor.
2. **Arquivo hosts em cada máquina** (fallback simples, sem depender de
   ninguém): abrir o Bloco de Notas **como administrador** e editar
   `C:\Windows\System32\drivers\etc\hosts`, adicionando a linha:

   ```
   192.168.0.50   normatech    # ← substitua pelo IP fixo do servidor
   ```

> Com IP fixo/reservado no servidor, essa configuração é feita **uma vez por
> máquina** e não precisa mais ser mexida.

## 4. Serviço do Windows (NSSM) — auto-start e auto-restart

1. Baixe o NSSM (nssm.cc), copie `nssm.exe` para `C:\NormaTech\tools\`

```powershell
# Executar PowerShell como administrador
C:\NormaTech\tools\nssm.exe install NormaTechWeb "C:\NormaTech\.venv\Scripts\python.exe" "C:\NormaTech\run_web.py"
C:\NormaTech\tools\nssm.exe set NormaTechWeb AppDirectory C:\NormaTech
C:\NormaTech\tools\nssm.exe set NormaTechWeb AppStdout C:\NormaTech\logs\service-out.log
C:\NormaTech\tools\nssm.exe set NormaTechWeb AppStderr C:\NormaTech\logs\service-err.log
C:\NormaTech\tools\nssm.exe set NormaTechWeb AppRotateFiles 1
C:\NormaTech\tools\nssm.exe start NormaTechWeb
```

Comportamento obtido: inicia sozinho ao ligar o servidor e reinicia sozinho se
o processo cair. Logs ficam em `C:\NormaTech\logs\`.

## 5. Firewall (permitir o acesso das outras máquinas)

```powershell
# Executar como administrador no SERVIDOR
netsh advfirewall firewall add rule name="NormaTech Web" dir=in action=allow protocol=TCP localport=8000
```

## 6. Migração dos dados atuais

1. Feche o app desktop no PC de origem (garante o backup do WAL)
2. Copie a pasta `data\` completa para `C:\NormaTech\data\` no servidor:
   - `certificados.db` (+ `-shm`/`-wal` se existirem — fechar antes evita)
   - `certificados\`, `asos\`, `epis\`, `crachas\`, `cartoes\` (documentos gerados)
   - `app_settings.json`, `company_config.json`, `funcoes.json`, `restore.key`
3. Suba o serviço e valide: funcionários, histórico e backups aparecem no portal
4. **Backup primeiro:** na primeira semana, rode um backup manual no fim do dia

## 7. Rotina de atualização do portal

```powershell
C:\NormaTech\tools\nssm.exe stop NormaTechWeb
# copiar/substituir os arquivos atualizados (src\, templates\, run_web.py, requirements*.txt)
.venv\Scripts\pip install -r requirements.txt -r requirements-web.txt   # se mudou
C:\NormaTech\tools\nssm.exe start NormaTechWeb
```

Downtime esperado: ~1 minuto.

## 8. Troubleshooting

| Sintoma | Causa provável / solução |
|---------|--------------------------|
| `http://normatech:8000` não abre de outra máquina | 1) `ping normatech` falhou? → ver §3 (DNS/hosts). 2) Regra de firewall aplicada no servidor? → ver §5. 3) Serviço está rodando? → `nssm status NormaTechWeb` |
| Página carrega mas dá erro 500 | Ver `logs\service-err.log`; `data\error.log` também registra erros da aplicação |
| Porta 8000 ocupada no servidor | Outro app usa a porta → mudar `PORT` no `run_web.py` (ex: 8080) e atualizar a regra de firewall |
| Serviço não inicia | Conferir caminhos no NSSM; rodar `run_web.py` manualmente para ver o erro real |
| `database is locked` recorrente | Verificar se não há outro processo fora do servidor acessando o `.db` (ex: desktop em pasta compartilhada); no servidor isso não deve ocorrer |
| Esqueceu a senha do admin | Recriar usuário via linha de comando utilitária (a definir na Fase 1: `run_web.py --reset-admin`) |
| Pendrive/scanner não funciona no portal | Scanner USB é acessado pelo NormaAgent na máquina onde está plugado (ver `04-SCANNER.md`) — o servidor não enxerga periféricos das máquinas cliente |

## 9. Checklist final de deploy

- [ ] Servidor renomeado para `NORMATECH` com IP fixo/reservado
- [ ] Projeto em `C:\NormaTech`, fora de pasta sincronizada
- [ ] `data\` migrado e conferido (funcionários + histórico + backups)
- [ ] Serviço `NormaTechWeb` instalado e rodando (NSSM)
- [ ] Firewall liberado na porta 8000
- [ ] Acesso testado de **outra máquina** via `http://normatech:8000`
- [ ] Senha do admin trocada no primeiro login
- [ ] Usuários criados com papéis (Emissor/Consulta) e senhas entregues
- [ ] Backup manual executado e conferido

## 10. Desenvolvimento local do portal (Fase 1)

Para testar o portal na maquina local antes do servidor:

```
pip install -r requirements-web.txt
python run_web.py
```

- Abre em `http://127.0.0.1:8000` usando o MESMO `data\` do desktop (mesmo banco).
- No 1o boot o usuario `admin` e criado com senha provisoria exibida no console
  (e gravada em `data\web_admin_provisorio.txt` — apague o arquivo depois de anotar).
- A troca de senha no 1o acesso e obrigatoria.
- Resetar a senha do admin: `python run_web.py --reset-admin`
- Modo servidor: `python run_web.py --host 0.0.0.0 --port 8000`
- Testes do portal: `python test_web_auth.py` (29 verificacoes, banco temporario).
- Scripts de servidor em `deploy/web/`: INSTALAR_PORTAL.bat, ATUALIZAR_PORTAL.bat,
  ZERAR_DADOS.bat, REMOVER_PORTAL.bat (copie-os para a raiz do portal no servidor).
- O portal NAO entra no exe do desktop; sao sistemas separados no mesmo banco.
