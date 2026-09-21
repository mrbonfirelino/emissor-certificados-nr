"""Repositorio de usuarios e auditoria do portal web (mesmo certificados.db).

Tabelas novas (nao tocam nas existentes):
- users: username UNIQUE, password_hash (Argon2), nome, papel, ativo, must_change
- audit_log: usuario, acao, alvo, detalhe, created_at

1o boot: bootstrap_admin() cria o usuario admin com senha provisoria.
"""

import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import argon2

from src.utils.paths import get_db_path
from src.web.permissions import ROLES, ROLE_LABELS, invalidar_cache_permissoes  # noqa: F401 (ROLE_LABELS re-export)

_ph = argon2.PasswordHasher()


def _hash_senha(senha: str) -> str:
    return _ph.hash(senha)


def _verificar_senha(hash_str: str, senha: str) -> bool:
    try:
        return _ph.verify(hash_str, senha)
    except Exception:
        return False


def _senha_provisoria() -> str:
    # 3 blocos de 4 caracteres: facil de ler no console/parede
    alfabeto = "abcdefghjkmnpqrstuvwxyz23456789"
    partes = []
    for _ in range(3):
        partes.append("".join(secrets.choice(alfabeto) for _ in range(4)))
    return "-".join(partes)


class UsersRepository:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else Path(get_db_path())
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    nome TEXT NOT NULL DEFAULT '',
                    papel TEXT NOT NULL DEFAULT 'consulta',
                    ativo INTEGER NOT NULL DEFAULT 1,
                    must_change INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL DEFAULT '',
                    acao TEXT NOT NULL,
                    alvo TEXT NOT NULL DEFAULT '',
                    detalhe TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)
            # v1.46.0 (2.33.4): permissoes dinamicas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS permissoes_papel (
                    papel TEXT NOT NULL,
                    modulo TEXT NOT NULL,
                    permitido INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (papel, modulo)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS permissoes_usuario (
                    user_id INTEGER NOT NULL,
                    modulo TEXT NOT NULL,
                    permitido INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (user_id, modulo)
                )
            """)

    # -- auditoria -------------------------------------------------------
    def audit(self, acao: str, username: str = "", alvo: str = "", detalhe: str = ""):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO audit_log (username, acao, alvo, detalhe, created_at) VALUES (?, ?, ?, ?, ?)",
                (username or "", acao, alvo or "", detalhe or "", datetime.now().isoformat(timespec="seconds")),
            )

    def audit_list(self, limit: int = 100):
        with self._get_conn() as conn:
            return conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    def audit_page(self, q: str = "", limit: int = 20, offset: int = 0,
                   data_de: str = None, data_ate: str = None) -> tuple:
        """Busca paginada no audit_log. Retorna (rows, total)."""
        conds, args = [], []
        if (q or "").strip():
            filtro = f"%{(q or '').strip().lower()}%"
            conds.append("(lower(username) LIKE ? OR lower(acao) LIKE ?"
                         " OR lower(alvo) LIKE ? OR lower(detalhe) LIKE ?)")
            args += [filtro, filtro, filtro, filtro]
        if data_de:
            conds.append("substr(created_at,1,10) >= ?")
            args.append(data_de)
        if data_ate:
            conds.append("substr(created_at,1,10) <= ?")
            args.append(data_ate)
        where = (" WHERE " + " AND ".join(conds)) if conds else ""
        with self._get_conn() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM audit_log{where}", args).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM audit_log{where} ORDER BY id DESC LIMIT ? OFFSET ?",
                args + [limit, offset]).fetchall()
        return rows, total

    # -- login / senha ---------------------------------------------------
    def get_by_username(self, username: str) -> Optional[sqlite3.Row]:
        username = (username or "").strip().lower()
        with self._get_conn() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()

    def get_by_id(self, user_id: int) -> Optional[sqlite3.Row]:
        with self._get_conn() as conn:
            return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def verify_login(self, username: str, senha: str) -> Optional[sqlite3.Row]:
        """Retorna o usuario se credenciais validas e conta ativa; None senao."""
        user = self.get_by_username(username)
        if user is None or not user["ativo"]:
            return None
        if not _verificar_senha(user["password_hash"], senha or ""):
            return None
        return user

    def change_password(self, user_id: int, nova_senha: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE users SET password_hash = ?, must_change = 0 WHERE id = ?",
                (_hash_senha(nova_senha), user_id),
            )
            return cur.rowcount > 0

    # -- administracao de usuarios ----------------------------------------
    def list_users(self):
        with self._get_conn() as conn:
            return conn.execute(
                "SELECT id, username, nome, papel, ativo, must_change, created_at"
                " FROM users ORDER BY username"
            ).fetchall()

    def create_user(self, username: str, nome: str, papel: str,
                    senha: Optional[str] = None) -> tuple:
        """Cria usuario com senha provisoria. Retorna (user_id, senha_provisoria)."""
        username = (username or "").strip().lower()
        if not username:
            raise ValueError("Informe o login do usuario.")
        if papel not in ROLES:
            raise ValueError("Papel invalido.")
        if self.get_by_username(username):
            raise ValueError(f"Ja existe usuario com o login '{username}'.")
        provisoria = senha or _senha_provisoria()
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, nome, papel, ativo,"
                " must_change, created_at) VALUES (?, ?, ?, ?, 1, 1, ?)",
                (username, _hash_senha(provisoria), (nome or "").strip(),
                 papel, datetime.now().isoformat(timespec="seconds")),
            )
            return cur.lastrowid, provisoria

    def set_active(self, user_id: int, ativo: bool) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE users SET ativo = ? WHERE id = ?", (1 if ativo else 0, user_id)
            )
            return cur.rowcount > 0

    def reset_password(self, user_id: int) -> Optional[str]:
        """Gera nova senha provisoria e marca troca obrigatoria."""
        user = self.get_by_id(user_id)
        if user is None:
            return None
        provisoria = _senha_provisoria()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, must_change = 1 WHERE id = ?",
                (_hash_senha(provisoria), user_id),
            )
        return provisoria

    def count_admins_ativos(self) -> int:
        with self._get_conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM users WHERE papel = 'admin' AND ativo = 1"
            ).fetchone()[0]

    # -- permissoes dinamicas (2.33.4) -------------------------------------
    def permissoes_overrides(self) -> tuple:
        """Retorna ({papel: {modulo: bool}}, {user_id: {modulo: bool}})."""
        papel_ov, usuario_ov = {}, {}
        with self._get_conn() as conn:
            for r in conn.execute("SELECT papel, modulo, permitido FROM permissoes_papel"):
                papel_ov.setdefault(r["papel"], {})[r["modulo"]] = bool(r["permitido"])
            for r in conn.execute("SELECT user_id, modulo, permitido FROM permissoes_usuario"):
                usuario_ov.setdefault(r["user_id"], {})[r["modulo"]] = bool(r["permitido"])
        return papel_ov, usuario_ov

    def set_permissao_papel(self, papel: str, modulo: str, permitido) -> None:
        """permitido=True/False grava o ajuste; None remove (volta a matriz base)."""
        if papel not in ROLES:
            raise ValueError("Papel invalido.")
        with self._get_conn() as conn:
            if permitido is None:
                conn.execute(
                    "DELETE FROM permissoes_papel WHERE papel = ? AND modulo = ?",
                    (papel, modulo))
            else:
                conn.execute("""
                    INSERT INTO permissoes_papel (papel, modulo, permitido)
                    VALUES (?, ?, ?)
                    ON CONFLICT(papel, modulo) DO UPDATE SET permitido = excluded.permitido
                """, (papel, modulo, 1 if permitido else 0))
        invalidar_cache_permissoes()

    def limpar_permissoes_papel(self) -> int:
        """Restaura a matriz base (apaga todos os ajustes de papel)."""
        with self._get_conn() as conn:
            n = conn.execute("DELETE FROM permissoes_papel").rowcount
        invalidar_cache_permissoes()
        return n

    def set_excecao_usuario(self, user_id: int, modulo: str, permitido) -> None:
        """Excecao individual: True concede, False nega, None remove (segue papel)."""
        with self._get_conn() as conn:
            if permitido is None:
                conn.execute(
                    "DELETE FROM permissoes_usuario WHERE user_id = ? AND modulo = ?",
                    (user_id, modulo))
            else:
                conn.execute("""
                    INSERT INTO permissoes_usuario (user_id, modulo, permitido)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, modulo) DO UPDATE SET permitido = excluded.permitido
                """, (user_id, modulo, 1 if permitido else 0))
        invalidar_cache_permissoes()

    # -- bootstrap ---------------------------------------------------------
    def bootstrap_admin(self) -> Optional[str]:
        """Cria o admin com senha provisoria no 1o boot. Retorna a senha ou None."""
        if self.get_by_username("admin") is not None:
            return None
        senha = _senha_provisoria()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, nome, papel, ativo,"
                " must_change, created_at) VALUES (?, ?, ?, 'admin', 1, 1, ?)",
                ("admin", _hash_senha(senha), "Administrador",
                 datetime.now().isoformat(timespec="seconds")),
            )
        self.audit("bootstrap-admin", "sistema", "admin", "usuario admin criado no 1o boot")
        return senha
