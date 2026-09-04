"""Repositorio de crachas de identificacao (12x7,8cm) — emissoes gravadas no banco."""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from src.utils.paths import get_db_path


class CrachaRepository:
    """Tabela crachas + numeracao sequencial CRACHA-%06d."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS crachas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cracha_number TEXT UNIQUE NOT NULL,
                    employee_id INTEGER NOT NULL,
                    employee_nome TEXT NOT NULL,
                    data_emissao TEXT NOT NULL,
                    nrs TEXT,
                    aso_number TEXT,
                    aso_validade TEXT,
                    pdf_path TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_cracha_employee ON crachas(employee_id);
                CREATE INDEX IF NOT EXISTS idx_cracha_date ON crachas(data_emissao);
                CREATE TABLE IF NOT EXISTS sequences (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
                INSERT OR IGNORE INTO sequences (name, value) VALUES ('cracha', 0);
            """)
            # sequences pode nao existir se este repo abrir antes dos outros
            try:
                conn.execute("SELECT value FROM sequences LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sequences (
                        name TEXT PRIMARY KEY,
                        value INTEGER NOT NULL
                    )
                """)
                conn.execute("INSERT OR IGNORE INTO sequences (name, value) VALUES ('cracha', 0)")

    def next_cracha_number(self) -> str:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE sequences SET value = value + 1 WHERE name = 'cracha' RETURNING value"
            )
            row = cursor.fetchone()
            return f"CRACHA-{row[0]:06d}"

    def peek_cracha_number(self) -> str:
        """Proximo numero SEM consumir a sequencia (preview)."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value + 1 FROM sequences WHERE name = 'cracha'"
            ).fetchone()
            return f"CRACHA-{row[0]:06d}" if row else "CRACHA-000001"

    def save(
        self,
        cracha_number: str,
        employee_id: int,
        employee_nome: str,
        data_emissao: str,
        nrs: List[dict],
        aso_number: Optional[str] = None,
        aso_validade: Optional[str] = None,
        pdf_path: Optional[str] = None,
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO crachas (
                    cracha_number, employee_id, employee_nome, data_emissao,
                    nrs, aso_number, aso_validade, pdf_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cracha_number, employee_id, employee_nome, data_emissao,
                json.dumps(nrs, ensure_ascii=False), aso_number, aso_validade, pdf_path,
            ))
            return cursor.lastrowid

    def get_by_employee(self, employee_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM crachas WHERE employee_id = ? ORDER BY created_at DESC, id DESC",
                (employee_id,)
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_all(self, limit: int = 500) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM crachas ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def count_all(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM crachas").fetchone()[0]

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        try:
            nrs = json.loads(row["nrs"] or "[]")
        except Exception:
            nrs = []
        return {
            "id": row["id"],
            "cracha_number": row["cracha_number"],
            "employee_id": row["employee_id"],
            "employee_nome": row["employee_nome"],
            "data_emissao": row["data_emissao"],
            "nrs": nrs,
            "aso_number": row["aso_number"],
            "aso_validade": row["aso_validade"],
            "pdf_path": row["pdf_path"],
            "created_at": row["created_at"],
        }
