# Plano de Implementacao — Sistema de Licenca

## 1. Visao Geral

| Item | Decisao |
|---|---|
| **Tipo** | Offline, assinatura RSA-2048 |
| **Travamento** | Total desde o primeiro uso (sem trial) |
| **Limite de certificados** | Valor alto configuravel na licenca (ex: 999.999) |
| **Hardware** | Fingerprint vincula licenca a maquina |
| **Rede** | Licenca multi-machine (lista de hashes no mesmo arquivo) |
| **Banco de dados** | Compartilhado (mantido como esta) |
| **Revocacao** | Offline apenas (sem servidor) |

---

## 2. Estrutura de Arquivos

```
src/core/license/
  __init__.py
  hardware.py        # Coleta fingerprint do hardware
  models.py          # Modelo de dados Pydantic
  crypto.py          # RSA sign/verify
  manager.py         # Orquestra validacao
  ui.py              # Tela de bloqueio

tools/
  license_generator.py   # CLI para gerar licencas (só o admin usa)

data/
  license.json           # Arquivo de licenca (gerado pelo admin)
  .private_key.pem       # Private key (NAO entra no .exe, .gitignore)
  .public_key.pem        # Public key (pode estar no .exe ou no data/)
```

**`.gitignore`** — adicionar:
```
data/.private_key.pem
data/.public_key.pem
```

---

## 3. Hardware Fingerprint

**Arquivo**: `src/core/license/hardware.py`

Coleta identificadores da maquina e gera um fingerprint SHA-256.

### Fontes (Windows)

| Comando | Dado retornado |
|---|---|
| `wmic csproduct get uuid` | UUID da placa-mae |
| `wmic cpu get ProcessorId` | ID do processador |
| `Get-Volume ... SerialNumber` | Serial do disco C: (PowerShell) |

### Comportamento

- Se alguma fonte falhar, usa as disponiveis
- Hash final: `SHA-256("cpu_id|mobo_uuid|disk_serial")`
- Fallback: usa `socket.gethostname()` se tudo mais falhar

### Funcoes expostas

```python
def get_hardware_hash() -> str:
    """Retorna hash SHA-256 de 64 chars identificando a maquina."""
    ...

def get_hardware_hash_short() -> str:
    """Retorna versao curta para exibicao: primeiros 16 chars."""
    ...
```

**Exemplo de saida**: `a3f2b8c9d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1`

---

## 4. Modelo de Licenca

**Arquivo**: `src/core/license/models.py`

### LicenseStatus (enum)

| Valor | Significado |
|---|---|
| `VALID` | Tudo OK |
| `EXPIRING_SOON` | Valida mas expira em < 30 dias |
| `EXPIRED` | Prazo vencido |
| `HARDWARE_MISMATCH` | Licenca nao e para esta maquina |
| `INVALID` | Assinatura invalida / arquivo corrompido |
| `MISSING` | Sem arquivo de licenca |

### LicensePayload (Pydantic BaseModel)

```python
class LicensePayload(BaseModel):
    license_id: str                   # UUID unico
    licensee: str                     # "ALTEC INDUSTRIAL LTDA"
    hardware_hashes: list[str]        # Lista de hashes permitidos (multi-machine)
    license_type: str                 # "permanent" | "time_limited"
    issued_at: datetime
    expires_at: datetime | None       # None = permanente
    max_certificates: int             # Limite (ex: 999999)
    version: str                      # Versao minima do app compativel
```

### LicenseFile (Pydantic BaseModel)

```python
class LicenseFile(BaseModel):
    payload: LicensePayload
    signature: str                    # Base64 da assinatura RSA
```

### Exemplo de `license.json`

```json
{
  "payload": {
    "license_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "licensee": "ALTEC INDUSTRIAL LTDA",
    "hardware_hashes": [
      "a3f2b8c9d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1",
      "b7c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1"
    ],
    "license_type": "permanent",
    "issued_at": "2026-08-26T00:00:00",
    "expires_at": null,
    "max_certificates": 999999,
    "version": "1.0.0"
  },
  "signature": "MEUCIQD...base64...=="
}
```

---

## 5. Criptografia

**Arquivo**: `src/core/license/crypto.py`

### Algoritmo

| Parametro | Valor |
|---|---|
| Algoritmo | RSA-2048 |
| Padding | PSS (Probabilistic Signature Scheme) |
| Hash | SHA-256 |
| Formato da chave | PEM |

### Chaves

- **Public key**: Hardcoded em `crypto.py` como constante. **Entra** no `.exe`.
- **Private key**: Armazenada em `data/.private_key.pem`. **Nunca** entra no `.exe`.

### Funcoes expostas

```python
class LicenseCrypto:
    PUBLIC_KEY_PEM = b"-----BEGIN PUBLIC KEY-----\nMIIBIjAN..."
    
    @staticmethod
    def verify_license(payload_json: bytes, signature_b64: str) -> bool:
        """Verifica assinatura RSA-PSS SHA-256."""
        ...
    
    @staticmethod
    def generate_keypair():
        """Gera par de chaves RSA-2048. Retorna (private_pem, public_pem)."""
        ...
```

---

## 6. Manager de Licenca

**Arquivo**: `src/core/license/manager.py`

### Localizacao do arquivo

```python
LICENSE_FILE = get_data_dir() / "license.json"
```

### Fluxo de validacao (`validate()`)

```
1. license.json existe?          → Nao: MISSING
2. JSON valido (parse)?          → Nao: INVALID
3. Assinatura RSA valida?        → Nao: INVALID
4. hardware_hash do PC na lista? → Nao: HARDWARE_MISMATCH
5. expires_at > agora?           → Nao: EXPIRED
6. expires_at - agora < 30 dias? → Sim: EXPIRING_SOON
7. Senao:                        → VALID
```

### Funcoes expostas

```python
class LicenseManager:
    def __init__(self):
        self.current_license: LicensePayload | None = None
        self._hardware_hash = get_hardware_hash()
    
    def validate(self) -> LicenseStatus:
        ...
    
    def get_license_info(self) -> dict:
        """Retorna dados para exibicao na UI."""
        return {
            "licensee": self.current_license.licensee,
            "expires_at": self.current_license.expires_at,
            "max_certificates": self.current_license.max_certificates,
            "certificates_used": self._get_certificate_count(),
            "hardware_hash": self._hardware_hash,
        }
    
    def is_certificate_limit_reached(self) -> bool:
        """Verifica se atingiu o limite de certificados."""
        ...
```

---

## 7. Tela de Bloqueio

**Arquivo**: `src/core/license/ui.py`

### Layout

```
+-------------------------------------------------------+
|                                                       |
|            Bloqueio de Licenca                         |
|                                                       |
|  Este software requer uma licenca valida para         |
|  funcionar.                                           |
|                                                       |
|  +-----------------------------------------------+    |
|  | Codigo desta maquina:                         |    |
|  | a3f2b8c9d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1    |    |
|  |                         [Copiar Codigo]       |    |
|  +-----------------------------------------------+    |
|                                                       |
|  Envie este codigo ao administrador para obter        |
|  seu arquivo de licenca (license.json).               |
|                                                       |
|  +-----------------------------------------------+    |
|  |  Carregar arquivo de licenca...               |    |
|  +-----------------------------------------------+    |
|                                                       |
|  Status: Sem licenca valida                           |
|                                                       |
+-------------------------------------------------------+
```

### Comportamento

- Janela **modal** (sem botao fechar, exceto minimize)
- **Zero acesso** a qualquer funcionalidade do app
- Botao "Copiar Codigo" -> copia o hardware hash para clipboard
- Botao "Carregar arquivo" -> file picker, copia `license.json` para `data/`, revalida
- Se licenca invalida ao carregar -> mostra erro e mantem bloqueio

---

## 8. Integracao no App

### Arquivos a modificar

Apenas **1 arquivo**: `src/ui/app.py` (funcao `main()`)

### Codigo da integracao

```python
def main():
    from src.core.license.manager import LicenseManager, LicenseStatus
    from src.core.license.ui import show_license_screen
    
    license_mgr = LicenseManager()
    status = license_mgr.validate()
    
    if status in (LicenseStatus.MISSING, LicenseStatus.INVALID,
                  LicenseStatus.HARDWARE_MISMATCH, LicenseStatus.EXPIRED):
        show_license_screen(license_mgr)
        return  # Nao abre o app
    
    app = NormaTechApp()
    
    if status == LicenseStatus.EXPIRING_SOON:
        # Aviso apos 2 segundos de uso
        app.after(2000, lambda: show_expiring_warning(app, license_mgr))
    
    app.mainloop()
```

### Fluxo resultante

```
App inicia
  -> LicenseManager.validate()
  -> Sem licenca ou invalida? -> Tela de bloqueio (app nao abre)
  -> Licenca OK? -> App abre normal
  -> Expirando? -> App abre + warning apos 2s
```

---

## 9. Gerador de Licencas (CLI)

**Arquivo**: `tools/license_generator.py`

Só o admin executa. Carrega a private key de `.private_key.pem`.

### Comandos

```bash
# Gerar par de chaves (uma unica vez)
python tools/license_generator.py --generate-keys

# Licenca permanente para multiplas maquinas
python tools/license_generator.py \
  --type permanent \
  --licensee "ALTEC INDUSTRIAL LTDA" \
  --hardware-hashes "hash_pc1,hash_pc2,hash_pc3" \
  --max-certificates 999999 \
  --output data/license.json

# Licenca temporaria
python tools/license_generator.py \
  --type time_limited \
  --months 12 \
  --licensee "Cliente X" \
  --hardware-hashes "hash_pc1" \
  --max-certificates 50000 \
  --output data/license.json
```

### Saida esperada

```
Licenca gerada com sucesso!
  ID:        f47ac10b-58cc-4372-a567-0e02b2c3d479
  Tipo:      Permanente
  Maquinas:  3
  Limite:    999.999 certificados
  Arquivo:   data/license.json
```

---

## 10. Seguranca — Matriz de Protecoes

| Vetor de ataque | Defesa |
|---|---|
| Copiar `license.json` para outro PC | `hardware_hashes` lista os PCs autorizados |
| Editar `license.json` (mudar expiry, etc.) | Assinatura RSA quebra — validacao rejeita |
| Decompilar .exe para pegar private key | Private key **nunca** entra no .exe |
| Desabilitar checagem no codigo | Public key hardcoded em `crypto.py` + `manager.py` valida em multiplos pontos |
| Usar versao antiga do .exe sem licenca | Campo `version` no payload; app rejeita versoes inferiores |
| Reverter relogio do sistema | Se `now < issued_at` -> rejeita (anti-rollback) |
| Compartilhar .exe sem a licenca | Licenca fica em `data/` ao lado do .exe — precisa copiar junto |
| Engenheiro reverso o gerador | Private key em arquivo .pem separado, nunca no repositorio |

---

## 11. Dependencias Novas

```
# requirements.txt (adicionar)
cryptography>=42.0.0
```

Apenas 1 dependencia. Leve, amplamente mantida, sem dependencias nativas complexas.

---

## 12. Fluxograma Completo

```
         +------------------+
         |  Usuario abre    |
         |    NormaTech     |
         +--------+---------+
                  |
         +--------v---------+
         |  license.json    |
         |  existe?         |
         +--------+---------+
            NAO   |   SIM
         +--------+------------------+
         |                            |
  +------v------+           +--------v--------+
  |   MISSING   |           |  JSON valido?   |
  |             |           +--------+--------+
  +------+------+           NAO      |   SIM
         |               +-----------+--------+
         |               |                    |
  +------v------+  +-----v------+   +--------v----------+
  |   INVALID   |  | INVALID    |   | Assinatura OK?    |
  |  (parse)    |  | (assina)   |   +--------+---------+
  +------+------+  +-----+------+      NAO   |   SIM
         |               |           +--------+--------+
         |               |           |                 |
         |         +-----v------+ +--v-----------+ +---v--------------+
         |         |   INVALID  | |   INVALID    | | HW na lista?     |
         |         +-----+------+ +-----+--------+ +--------+---------+
         |               |               |          NAO    |   SIM
         |         +-----v------+ +------+--------+  +-----v----------+
         |         |   INVALID  | |  HARDWARE    |  | Expirou?        |
         |         +-----+------+ |  _MISMATCH   |  +--------+--------+
         |               |        +------+--------+     SIM |   NAO
         |               |               |            +------v------+
         |               |               |            |   EXPIRED   |
         |               |               |            +------+------+
         |               |               |                   |
         +---------------+---------------+-------------------+
         |
         |          QUALQUER STATUS INVALIDO
         |
         +---------------------------------------------------+
         |                                                   |
  +------v---------------------------------------------------v--+
  |                   TELA DE BLOQUEIO                           |
  |  +-------------------------------------------------------+  |
  |  | Hardware Hash: [a3f2b8c9...]  [Copiar Codigo]         |  |
  |  +-------------------------------------------------------+  |
  |  [Carregar license.json...]                                 |
  |  Status: Licenca invalida                                   |
  +-------------------------------------------------------------+
         |
         |   Usuario carrega license.json valido
         |   -> Revalida -> Se OK -> fecha bloqueio -> abre app
         |
         +---------------------------------------------------+
         |                                                   |
         |              STATUS = VALID                       |
         |                                                   |
  +------v---------------------------------------------------v--+
  |                   APP ABRE NORMALMENTE                       |
  |                                                              |
  |  Se EXPIRING_SOON -> warning apos 2s de uso                 |
  |  Se atingir max_certificates -> aviso ao gerar certificado   |
  +--------------------------------------------------------------+
```

---

## 13. Roadmap de Implementacao

| # | Fase | Arquivos | Dependencias |
|---|---|---|---|
| 1 | Hardware fingerprint | `hardware.py` | Nenhuma |
| 2 | Modelo de dados | `models.py` | pydantic (ja usa) |
| 3 | Criptografia RSA | `crypto.py` | cryptography |
| 4 | Manager de licenca | `manager.py` | 1, 2, 3 |
| 5 | Tela de bloqueio | `ui.py` | 4, customtkinter |
| 6 | Gerador CLI | `tools/license_generator.py` | 2, 3 |
| 7 | Integracao no app | `app.py` (2 linhas) | 4, 5 |
| 8 | Testes unitarios | `tests/test_license_*.py` | 1, 2, 3, 4 |
| 9 | Warning de expiracao | `ui.py` + `app.py` | 5 |
| 10 | Validacao de limite | `manager.py` + home page | 4 |

**Esforco estimado**: ~4-6 horas para fases 1-7 (core funcional).

---

## 14. Checklist de Seguranca (antes de distribuir)

- [ ] Private key gerada e armazenada em local seguro (fora do repo)
- [ ] `.gitignore` atualizado para ignorar `.pem` files
- [ ] Public key hardcoded em `crypto.py` (nao le de arquivo)
- [ ] `license_generator.py` nao e distribuido com o .exe
- [ ] Testado: app trava sem `license.json`
- [ ] Testado: app trava com `license.json` de outra maquina
- [ ] Testado: app trava com `license.json` forjado (assinatura invalida)
- [ ] Testado: app trava com `license.json` expirado
- [ ] Testado: app abre com `license.json` valido
- [ ] Testado: warning aparece quando expira em < 30 dias
- [ ] Testado: limite de certificados e respeitado
