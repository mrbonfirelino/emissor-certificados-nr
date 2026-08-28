import sqlite3
from pathlib import Path
from typing import Optional, List
from src.utils.paths import get_db_path
from src.core.models import Employee
from src.utils.text_utils import normalize_text


class EmployeeRepository:
    """CRUD de funcionarios (Nome + CPF opcional + Funcao)."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.create_function("normalize", 1, normalize_text)
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cpf TEXT,
                    funcao TEXT,
                    foto BLOB,
                    telefone TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_emp_cpf ON employees(cpf);
                CREATE INDEX IF NOT EXISTS idx_emp_nome ON employees(nome);
            """)
            try:
                conn.execute("SELECT funcao FROM employees LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE employees ADD COLUMN funcao TEXT")
            try:
                conn.execute("SELECT foto FROM employees LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE employees ADD COLUMN foto BLOB")
            try:
                conn.execute("SELECT telefone FROM employees LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE employees ADD COLUMN telefone TEXT")
            try:
                conn.execute("SELECT cpf FROM employees WHERE cpf IS NULL LIMIT 1")
            except Exception:
                pass

    def create(self, nome: str, cpf: str = None, funcao: str = None, foto: Optional[bytes] = None, telefone: Optional[str] = None) -> Optional[int]:
        try:
            cpf_val = cpf.strip() if cpf and cpf.strip() else None
            tel_val = telefone.strip() if telefone and telefone.strip() else None
            if tel_val:
                import re
                tel_val = re.sub(r'\D', '', tel_val)
                if tel_val == "":
                    tel_val = None
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "INSERT INTO employees (nome, cpf, funcao, foto, telefone) VALUES (?, ?, ?, ?, ?)",
                    (nome.strip(), cpf_val, funcao.strip() if funcao else None, foto, tel_val)
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
        """Busca por nome, CPF, funcao ou telefone (ignora acentos)."""
        norm = normalize_text(query)
        with self._get_conn() as conn:
            like = f"%{norm}%"
            rows = conn.execute("""
                SELECT * FROM employees
                WHERE normalize(nome) LIKE ? OR cpf LIKE ? OR normalize(funcao) LIKE ? OR telefone LIKE ?
                ORDER BY nome LIMIT ?
            """, (like, f"%{query}%", like, f"%{query}%", limit)).fetchall()
            return [self._row_to_employee(r) for r in rows]

    def count_search(self, query: str) -> int:
        """Conta resultados de busca."""
        norm = normalize_text(query)
        with self._get_conn() as conn:
            like = f"%{norm}%"
            return conn.execute("""
                SELECT COUNT(*) FROM employees
                WHERE normalize(nome) LIKE ? OR cpf LIKE ? OR normalize(funcao) LIKE ? OR telefone LIKE ?
            """, (like, f"%{query}%", like, f"%{query}%")).fetchone()[0]

    def get_all(self, limit: int = 10, offset: int = 0) -> List[Employee]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM employees ORDER BY nome LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [self._row_to_employee(r) for r in rows]

    def count_all(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]

    def get_all_funcoes(self) -> List[str]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT funcao FROM employees WHERE funcao IS NOT NULL AND funcao != '' ORDER BY funcao"
            ).fetchall()
            return [row["funcao"] for row in rows]

    def update(self, emp_id: int, nome: str, cpf: str = None, funcao: str = None, foto: Optional[bytes] = None, telefone: Optional[str] = None) -> bool:
        try:
            cpf_val = cpf.strip() if cpf and cpf.strip() else None
            tel_val = telefone.strip() if telefone and telefone.strip() else None
            if tel_val:
                import re
                tel_val = re.sub(r'\D', '', tel_val)
                if tel_val == "":
                    tel_val = None
            with self._get_conn() as conn:
                if foto is not None:
                    conn.execute(
                        "UPDATE employees SET nome = ?, cpf = ?, funcao = ?, foto = ?, telefone = ? WHERE id = ?",
                        (nome.strip(), cpf_val, funcao.strip() if funcao else None, foto, tel_val, emp_id)
                    )
                else:
                    conn.execute(
                        "UPDATE employees SET nome = ?, cpf = ?, funcao = ?, telefone = ? WHERE id = ?",
                        (nome.strip(), cpf_val, funcao.strip() if funcao else None, tel_val, emp_id)
                    )
                return True
        except sqlite3.IntegrityError:
            return False

    def update_foto(self, emp_id: int, foto: Optional[bytes]) -> bool:
        try:
            with self._get_conn() as conn:
                conn.execute("UPDATE employees SET foto = ? WHERE id = ?", (foto, emp_id))
                return True
        except sqlite3.IntegrityError:
            return False

    def update_telefone(self, emp_id: int, telefone: Optional[str]) -> bool:
        try:
            tel_val = telefone.strip() if telefone and telefone.strip() else None
            if tel_val:
                import re
                tel_val = re.sub(r'\D', '', tel_val)
            with self._get_conn() as conn:
                conn.execute("UPDATE employees SET telefone = ? WHERE id = ?", (tel_val, emp_id))
                return True
        except sqlite3.IntegrityError:
            return False

    def delete(self, emp_id: int) -> bool:
        from src.core.history_repo import HistoryRepository
        history = HistoryRepository(self.db_path)
        certs = history.get_by_employee(emp_id)
        if certs:
            return False
        with self._get_conn() as conn:
            conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
            return True

    def count_total(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]

    def _row_to_employee(self, row: sqlite3.Row) -> Employee:
        cpf_val = row["cpf"] if row["cpf"] else ""
        try:
            foto_val = row["foto"]
        except Exception:
            foto_val = None
        try:
            tel_val = row["telefone"]
        except Exception:
            tel_val = None
        return Employee(
            id=row["id"],
            nome=row["nome"],
            cpf=cpf_val,
            funcao=row["funcao"],
            foto=foto_val,
            telefone=tel_val or None,
            created_at=row["created_at"]
        )
