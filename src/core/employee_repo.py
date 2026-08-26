import sqlite3
from pathlib import Path
from typing import Optional, List
from src.utils.paths import get_db_path
from src.core.models import Employee


class EmployeeRepository:
    """CRUD de funcionários (Nome + CPF)."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cpf TEXT NOT NULL UNIQUE,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_emp_cpf ON employees(cpf);
                CREATE INDEX IF NOT EXISTS idx_emp_nome ON employees(nome);
            """)

    def create(self, nome: str, cpf: str) -> Optional[int]:
        """Cria novo funcionário. Retorna ID ou None se CPF duplicado."""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "INSERT INTO employees (nome, cpf) VALUES (?, ?)",
                    (nome.strip(), cpf.strip())
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_by_id(self, emp_id: int) -> Optional[Employee]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()
            return self._row_to_employee(row) if row else None

    def get_by_cpf(self, cpf: str) -> Optional[Employee]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM employees WHERE cpf = ?", (cpf,)).fetchone()
            return self._row_to_employee(row) if row else None

    def search(self, query: str, limit: int = 20) -> List[Employee]:
        """Busca por nome ou CPF (para autocomplete)."""
        with self._get_conn() as conn:
            like = f"%{query}%"
            rows = conn.execute("""
                SELECT * FROM employees 
                WHERE nome LIKE ? OR cpf LIKE ?
                ORDER BY nome LIMIT ?
            """, (like, like, limit)).fetchall()
            return [self._row_to_employee(r) for r in rows]

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Employee]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM employees ORDER BY nome LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [self._row_to_employee(r) for r in rows]

    def update(self, emp_id: int, nome: str, cpf: str) -> bool:
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE employees SET nome = ?, cpf = ? WHERE id = ?",
                    (nome.strip(), cpf.strip(), emp_id)
                )
                return True
        except sqlite3.IntegrityError:
            return False

    def delete(self, emp_id: int) -> bool:
        """Deleta funcionário (se não tiver certificados vinculados)."""
        from src.core.history_repo import HistoryRepository
        history = HistoryRepository(self.db_path)
        certs = history.get_by_employee(emp_id)
        if certs:
            return False  # Tem certificados, não pode deletar
        with self._get_conn() as conn:
            conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
            return True

    def count_total(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]

    def _row_to_employee(self, row: sqlite3.Row) -> Employee:
        return Employee(
            id=row["id"],
            nome=row["nome"],
            cpf=row["cpf"],
            created_at=row["created_at"]
        )