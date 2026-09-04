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
            # nota: coluna matricula pode existir em bancos antigos — permanece ignorada
            try:
                conn.execute("SELECT cpf FROM employees WHERE cpf IS NULL LIMIT 1")
            except Exception:
                pass
            # documentos gerais do funcionario ("Outros": CNH, identidade, etc.)
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS employee_docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    tamanho INTEGER NOT NULL DEFAULT 0,
                    dados BLOB,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                );
                CREATE INDEX IF NOT EXISTS idx_empdocs_employee ON employee_docs(employee_id);
            """)

    # --- Documentos gerais ("Outros") ---

    DOC_MAX_BYTES = 50 * 1024 * 1024  # 50MB (qualquer formato nao bloqueado)

    # extensoes executaveis/scripts bloqueadas por seguranca
    DOC_EXT_BLOQUEADAS = {
        "exe", "msi", "msp", "mst", "bat", "cmd", "com", "scr", "pif", "cpl",
        "msc", "hta", "jar", "vbs", "vbe", "js", "jse", "ws", "wsf", "wsh",
        "ps1", "psm1", "psd1", "sh", "bash", "reg", "dll", "sys", "drv",
        "lnk", "url", "apk", "gadget",
    }

    # tipos MIME bloqueados (executaveis/scripts Windows)
    _MIME_BLOQUEADOS = {
        "application/x-msdownload", "application/x-msdos-program",
        "application/x-msi", "application/x-ms-installer",
        "application/x-bat", "application/x-sh", "application/x-sh",
        "application/x-windows-script", "text/vbscript", "text/javascript",
    }

    @classmethod
    def _validar_doc(cls, filename: str, data: bytes, tipo: str) -> str:
        """Valida extensao/MIME/tamanho. Retorna extensao normalizada."""
        import mimetypes
        tipo = (tipo or "").lower().strip().lstrip(".")
        if not tipo:
            raise ValueError("Arquivo sem extensao")
        if tipo in cls.DOC_EXT_BLOQUEADAS:
            raise ValueError(f"Formato bloqueado por seguranca: .{tipo}")
        mime, _ = mimetypes.guess_type(filename or f"arquivo.{tipo}")
        if mime and (mime in cls._MIME_BLOQUEADOS or mime.startswith("application/x-ms")):
            raise ValueError(f"Tipo de arquivo bloqueado: {mime}")
        if len(data) > cls.DOC_MAX_BYTES:
            raise ValueError("Arquivo maior que 50MB")
        return tipo

    def add_doc(self, employee_id: int, filename: str, data: bytes, tipo: str) -> int:
        """Anexa documento do funcionario (qualquer formato nao bloqueado, ate 50MB)."""
        tipo = self._validar_doc(filename, data, tipo)
        if tipo == "jpeg":
            tipo = "jpg"
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO employee_docs (employee_id, filename, tipo, tamanho, dados) VALUES (?, ?, ?, ?, ?)",
                (employee_id, filename, tipo, len(data), sqlite3.Binary(data))
            )
            return cursor.lastrowid

    def list_docs(self, employee_id: int) -> List[dict]:
        """Lista documentos do funcionario (sem o BLOB)."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, filename, tipo, tamanho, created_at FROM employee_docs "
                "WHERE employee_id = ? ORDER BY filename",
                (employee_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_doc(self, doc_id: int) -> Optional[tuple]:
        """Retorna (employee_id, filename, bytes, tipo) do documento ou None."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT employee_id, filename, dados, tipo FROM employee_docs WHERE id = ?",
                (doc_id,)
            ).fetchone()
            if row and row["dados"]:
                return row["employee_id"], row["filename"], row["dados"], (row["tipo"] or "pdf")
            return None

    def delete_doc(self, doc_id: int) -> bool:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM employee_docs WHERE id = ?", (doc_id,))
            return True

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
