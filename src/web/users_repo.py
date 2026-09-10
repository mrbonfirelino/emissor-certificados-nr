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

ROLES = ("admin", "emissor", "consulta")
ROLE_LABELS = {"admin": "Administrador", "emissor": "Emissor", "consulta": "Consulta"}

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
