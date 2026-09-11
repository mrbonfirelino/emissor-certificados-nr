"""Matriz de permissoes do portal (3 papeis fixos — docs/PORTAL/01 §6).

Modulos = grupos de rotas. 'só ver' e tratado no proprio router (Fase 1 do
portal e read-only); aqui define quem ACESSA o modulo.
"""

ROLES = ("admin", "emissor", "consulta")

ROLE_LABELS = {"admin": "Administrador", "emissor": "Emissor", "consulta": "Consulta"}

# modulo -> papeis com acesso
PERMISSIONS = {
    "dashboard": {"admin", "emissor", "consulta"},
    "funcionarios": {"admin", "emissor", "consulta"},
    "certificados": {"admin", "emissor", "consulta"},
    "historico": {"admin", "emissor", "consulta"},
    "vencimentos": {"admin", "emissor", "consulta"},
    "aso": {"admin", "emissor", "consulta"},
    "epi": {"admin", "emissor", "consulta"},
    "crachas": {"admin", "emissor", "consulta"},
    "importacoes": {"admin", "emissor"},
    "integracoes": {"admin", "emissor"},
    "cartoes": {"admin", "emissor"},
    "config": {"admin"},
    "backup": {"admin"},
    "usuarios": {"admin"},
    "auditoria": {"admin"},
}


def pode(role: str, modulo: str) -> bool:
    return role in PERMISSIONS.get(modulo, set())


# Modulos onde consulta ve apenas ("só ver" na matriz) — escrita exige
# admin/emissor. Admin-only (config/backup/usuarios/auditoria) nunca entra aqui.
SO_LEITURA = {"funcionarios", "certificados", "historico", "vencimentos",
              "aso", "epi", "crachas"}


def pode_escrever(role: str, modulo: str) -> bool:
    """True se o papel pode executar acoes (POST) no modulo.

    Matriz docs/PORTAL/01 §6: modulos 'só ver' (consulta) exigem admin/emissor
    para operar; modulos admin-only ja sao bloqueados por pode().
    """
    if not pode(role, modulo):
        return False
    if modulo in SO_LEITURA:
        return role in ("admin", "emissor")
    return True


def modulos_do(role: str) -> list:
    """Modulos visiveis no menu para o papel, em ordem de exibicao."""
    ordem = ["dashboard", "certificados", "funcionarios", "historico", "vencimentos",
             "aso", "epi", "crachas", "cartoes", "importacoes", "integracoes",
             "backup", "usuarios"]
    return [m for m in ordem if pode(role, m)]
