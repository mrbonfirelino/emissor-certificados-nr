"""Matriz de permissoes do portal (3 papeis fixos — docs/PORTAL/01 §6).

Modulos = grupos de rotas. 'só ver' e tratado no proprio router (Fase 1 do
portal e read-only); aqui define quem ACESSA o modulo.

v1.46.0 (2.33.4): a matriz virou DINAMICA — o admin ajusta o acesso de cada
papel por modulo na tela Usuários (tabela permissoes_papel) e pode conceder/
negar acessos por USUARIO (excecao individual, tabela permissoes_usuario,
avalia antes do papel). Sem linha gravada vale a matriz base abaixo.
"""

import time

ROLES = ("admin", "emissor", "consulta")

ROLE_LABELS = {"admin": "Administrador", "emissor": "Emissor", "consulta": "Consulta"}

# modulo -> papeis com acesso (BASE — usada quando nao ha ajuste gravado)
PERMISSIONS = {
    "dashboard": {"admin", "emissor", "consulta"},
    "funcionarios": {"admin", "emissor", "consulta"},
    "certificados": {"admin", "emissor", "consulta"},
    "historico": {"admin", "emissor", "consulta"},
    "vencimentos": {"admin", "emissor", "consulta"},
    "aso": {"admin", "emissor", "consulta"},
    "epi": {"admin", "emissor", "consulta"},
    "frota": {"admin", "emissor", "consulta"},
    "presencas": {"admin", "emissor", "consulta"},
    "crachas": {"admin", "emissor", "consulta"},
    "importacoes": {"admin", "emissor"},
    "integracoes": {"admin", "emissor"},
    "cartoes": {"admin", "emissor"},
    "config": {"admin"},
    "backup": {"admin"},
    "usuarios": {"admin"},
    "auditoria": {"admin"},
}

# Modulos ajustaveis na tela Usuários (dashboard e fixo: negar = loop de
# redirect na home, entao sai da matriz).
MODULOS_UI = [
    ("certificados", "Certificados"),
    ("historico", "Histórico"),
    ("vencimentos", "Vencimentos"),
    ("presencas", "Listas de Presença"),
    ("epi", "Ficha de EPIs"),
    ("crachas", "Crachás"),
    ("cartoes", "Cartões"),
    ("funcionarios", "Funcionários (Cadastros)"),
    ("aso", "ASO"),
    ("frota", "Gestão de Frota"),
    ("importacoes", "Importações"),
    ("integracoes", "Integrações"),
    ("backup", "Backup"),
    ("usuarios", "Usuários"),
    ("auditoria", "Auditoria"),
    ("config", "Configurações"),
]

# Modulos que o admin nao pode perder (evita se trancar fora do portal).
_MODULOS_ADMIN_FIXOS = {"usuarios", "config"}

# -- cache curto dos ajustes gravados (evita 1 query SQL por item de menu) ---
_TTL = 3.0
_cache = {"t": 0.0, "papel": {}, "usuario": {}}


def invalidar_cache_permissoes():
    _cache["t"] = 0.0


def _overrides():
    """Retorna ({papel: {modulo: bool}}, {user_id: {modulo: bool}})."""
    agora = time.time()
    if agora - _cache["t"] > _TTL:
        papel_ov, usuario_ov = {}, {}
        try:
            from src.web.users_repo import UsersRepository
            papel_ov, usuario_ov = UsersRepository().permissoes_overrides()
        except Exception:
            papel_ov, usuario_ov = {}, {}
        _cache["papel"], _cache["usuario"] = papel_ov, usuario_ov
        _cache["t"] = agora
    return _cache["papel"], _cache["usuario"]


def pode(role: str, modulo: str) -> bool:
    """Acesso final do PAPEL ao modulo (ajuste do admin > matriz base)."""
    if role not in ROLES:
        return False
    papel_ov, _ = _overrides()
    ov = papel_ov.get(role) or {}
    if modulo in ov:
        return bool(ov[modulo])
    if role == "admin" and modulo in _MODULOS_ADMIN_FIXOS:
        return True
    return role in PERMISSIONS.get(modulo, set())


def pode_usuario(user, modulo: str) -> bool:
    """Acesso final do USUARIO: excecao individual > papel (base/ajuste)."""
    if not user:
        return False
    _, usuario_ov = _overrides()
    ex = usuario_ov.get(user.get("id")) or {}
    if modulo in ex:
        return bool(ex[modulo])
    return pode(user.get("papel"), modulo)


# Modulos onde consulta ve apenas ("só ver" na matriz) — escrita exige
# admin/emissor. Admin-only (config/backup/usuarios/auditoria) nunca entra aqui.
SO_LEITURA = {"funcionarios", "certificados", "historico", "vencimentos",
              "aso", "epi", "frota", "presencas", "crachas"}


def pode_escrever(role: str, modulo: str) -> bool:
    """True se o papel pode executar acoes (POST) no modulo.

    Escrita continua atrelada ao PAPEL (excecao de acesso nao concede escrita):
    modulos 'só ver' (consulta) exigem admin/emissor para operar; modulos
    admin-only ja sao bloqueados por pode().
    """
    if not pode(role, modulo):
        return False
    if modulo in SO_LEITURA:
        return role in ("admin", "emissor")
    return True


def modulos_do(role: str) -> list:
    """Modulos visiveis no menu para o papel, em ordem de exibicao."""
    ordem = ["dashboard", "certificados", "funcionarios", "historico", "vencimentos",
             "aso", "epi", "frota", "presencas", "crachas", "cartoes", "importacoes", "integracoes",
             "backup", "usuarios"]
    return [m for m in ordem if pode(role, m)]
