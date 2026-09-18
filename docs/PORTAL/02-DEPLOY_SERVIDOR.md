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
| Rede | Acesso pelo **nome do servidor** (§3) dispensa IP fixo; se preferir hosts/DNS, aí sim fixe o IP ou reserve no DHCP |
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
#    (requirements-web.txt é AUTO-SUFICIENTE — não precisa do requirements.txt,
#     que é do app desktop e tem pins que podem não existir para Pythons novos)
cd C:\NormaTech
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements-web.txt   # fastapi, uvicorn, jinja2, python-multipart, itsdangerous, openpyxl, argon2, reportlab, pillow, pymupdf, python-pptx, apscheduler...

# 3. Primeiro teste manual (antes do serviço)
#    Dica: use --port 80 se quiser acessar por http://normatech (sem :8000).
.venv\Scripts\python run_web.py --host 0.0.0.0 --port 8000
# Deve subir em http://localhost:8000 — teste no próprio servidor.
# 1º acesso: usuário admin com senha provisória → troque imediatamente.
```

## 3. Nome na rede e porta

**Boa notícia: não precisa de IP fixo.** O Windows anuncia o **nome do PC** na
rede local (LLMNR/mDNS) — mesmo que o IP mude (DHCP), o nome continua
resolvendo de qualquer máquina da rede. Basta que a rede do servidor esteja
como perfil **Privado** (Configurações → Rede → propriedades da conexão).

Na prática, se o servidor se chama `ALTEC-ENG`, o portal abre em
`http://altecec-eng:8000` (ou `http://altecec-eng` com porta 80):

```powershell
# Ver o nome atual do servidor
hostname
# Testar de OUTRA máquina da rede
ping altec-eng
```

**Porta:** o jeito mais simples de acessar sem `:porta` na URL é o portal
escutando na **porta 80** — configure `set PORT=80` no `INSTALAR_PORTAL.bat`
(ou rode `INICIAR-PORTAL.bat 80` para teste manual). Se a porta 80 já estiver
ocupada no servidor (IIS, HTTP.sys, Skype), mantenha 8000 e acesse por
`http://nome-do-servidor:8000`.

**Quer um endereço mais bonito?** Renomear o servidor resolve
(opcional, uma vez só):

```powershell
# Executar como administrador no servidor e reiniciar
Rename-Computer -NewName NORMATECH -Restart
```

**Atalho "NormaTech"**: em cada máquina cliente, crie um atalho na Área de
Trabalho apontando para `http://altecec-eng:8000` (botão direito → Novo →
Atalho) — use o nome real do servidor e a porta escolhida.

**Celulares/tabletes**: costumam resolver por mDNS — tente
`http://altecec-eng.local:8000`.

**Se o nome não resolver** (redes corporativas bloqueiam anúncio de nomes),
escolha uma das alternativas, na ordem de preferência:

1. **Registro DNS no roteador** (se ele permitir): apontar o nome
   → IP do servidor; e **fixar o IP** no servidor (reserva de DHCP).
2. **Arquivo hosts em cada máquina** (exige IP fixo — senão quebra quando o
   IP mudar): abrir o Bloco de Notas **como administrador** e editar
   `C:\Windows\System32\drivers\etc\hosts`, adicionando a linha:

   ```
   192.168.0.50   normatech    # ← substitua pelo IP do servidor
   ```

## 4. Início automático com o Windows

### Opção A — atalho na Inicializar (simples, recomendada)

Rode **uma vez** na raiz do projeto:

```
INICIAR-COM-WINDOWS.bat
```

Ele cria o atalho "NormaTech Portal" na pasta *Inicializar* do Windows
(`shell:startup`) apontando para o `INICIAR-PORTAL.bat` (janela minimizada)
e libera a porta no firewall se executado como Administrador. O portal sobe
sozinho quando o servidor ligar. **Desfazer:** apague o atalho em
`shell:startup` (Windows+R → `shell:startup`).

### Opção B — serviço do Windows (NSSM, avançada)

Reinicia sozinho se o processo cair e roda sem nenhum usuário logado.
Requer o NSSM (nssm.cc) em `tools\`:

1. Baixe o NSSM (nssm.cc), copie `nssm.exe` para `C:\NormaTech\tools\`

```powershell
# Executar PowerShell como administrador
C:\NormaTech\tools\nssm.exe install NormaTechPortal "C:\NormaTech\.venv\Scripts\python.exe" "C:\NormaTech\run_web.py" --host 0.0.0.0 --port 80
C:\NormaTech\tools\nssm.exe set NormaTechPortal AppDirectory C:\NormaTech
C:\NormaTech\tools\nssm.exe set NormaTechPortal AppStdout C:\NormaTech\logs\service-out.log
C:\NormaTech\tools\nssm.exe set NormaTechPortal AppStderr C:\NormaTech\logs\service-err.log
C:\NormaTech\tools\nssm.exe set NormaTechPortal AppRotateFiles 1
C:\NormaTech\tools\nssm.exe start NormaTechPortal
```

(O script `deploy\web\INSTALAR_PORTAL.bat` faz tudo isso sozinho — inclusive
venv, dependências e firewall — usando a porta da variável `PORT` no topo.)
Comportamento obtido: inicia sozinho ao ligar o servidor e reinicia sozinho se
o processo cair. Logs ficam em `C:\NormaTech\logs\`.

## 5. Firewall (permitir o acesso das outras máquinas)

```powershell
# Executar como administrador no SERVIDOR (porta 80 ou a que você escolheu)
netsh advfirewall firewall add rule name="NormaTech Web" dir=in action=allow protocol=TCP localport=80
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
C:\NormaTech\tools\nssm.exe stop NormaTechPortal
# copiar/substituir os arquivos atualizados (src\, templates\, run_web.py, requirements-web.txt)
.venv\Scripts\pip install -r requirements-web.txt   # se mudou
C:\NormaTech\tools\nssm.exe start NormaTechPortal
```

Downtime esperado: ~1 minuto.

## 8. Troubleshooting

| Sintoma | Causa provável / solução |
|---------|--------------------------|
| `http://normatech` não abre de outra máquina | 1) `ping normatech` falhou? → ver §3 (DNS/hosts). 2) Regra de firewall aplicada no servidor? → ver §5. 3) Serviço está rodando? → `nssm status NormaTechPortal` |
| Porta 80 ocupada no servidor | IIS/HTTP.sys/Skype usando a porta → desative ou volte para 8000 (`http://normatech:8000`); teste com `netstat -ano \| findstr :80` |
| Página carrega mas dá erro 500 | Ver `logs\service-err.log`; `data\error.log` também registra erros da aplicação |
| Porta 8000 ocupada no servidor | Outro app usa a porta → mudar `PORT` no `INSTALAR_PORTAL.bat` (ou o `--port` do comando) e atualizar a regra de firewall |
| Serviço não inicia | Conferir caminhos no NSSM; rodar `run_web.py` manualmente para ver o erro real |
| `database is locked` recorrente | Verificar se não há outro processo fora do servidor acessando o `.db` (ex: desktop em pasta compartilhada); no servidor isso não deve ocorrer |
| Esqueceu a senha do admin | Recriar usuário via linha de comando utilitária (a definir na Fase 1: `run_web.py --reset-admin`) |
| Pendrive/scanner não funciona no portal | Scanner USB é acessado pelo NormaAgent na máquina onde está plugado (ver `04-SCANNER.md`) — o servidor não enxerga periféricos das máquinas cliente |

## 9. Checklist final de deploy

- [ ] Servidor renomeado para `NORMATECH` com IP fixo/reservado
- [ ] Projeto em `C:\NormaTech`, fora de pasta sincronizada
- [ ] `data\` migrado e conferido (funcionários + histórico + backups)
- [ ] Serviço `NormaTechPortal` instalado e rodando (NSSM, porta escolhida em `PORT`) **ou** atalho na Inicializar (`INICIAR-COM-WINDOWS.bat`)
- [ ] Firewall liberado na porta escolhida (80 para `http://normatech` sem `:porta`)
- [ ] Acesso testado de **outra máquina** via `http://normatech` (ou `http://normatech:8000`)
- [ ] Senha do admin trocada no primeiro login
- [ ] Usuários criados com papéis (Emissor/Consulta) e senhas entregues
- [ ] Backup manual executado e conferido

## 10. Desenvolvimento local do portal (Fase 1)

Para testar o portal na maquina local antes do servidor:

```
pip install -r requirements-web.txt
python run_web.py
```

- Atalho: `INICIAR-PORTAL.bat` na raiz (cria o .venv se faltar e sobe em
  `0.0.0.0`; opcionalmente passe a porta: `INICIAR-PORTAL.bat 80`).
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
