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
            # data de nascimento (aniversariantes) — bancos antigos nao tem
            try:
                conn.execute("SELECT data_nascimento FROM employees LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE employees ADD COLUMN data_nascimento TEXT")
            # campos complementares do funcionario (roadmap 2.16)
            try:
                conn.execute("SELECT tipo_sanguineo FROM employees LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE employees ADD COLUMN tipo_sanguineo TEXT")
            try:
                conn.execute("SELECT data_admissao FROM employees LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE employees ADD COLUMN data_admissao TEXT")
            try:
                conn.execute("SELECT registro_ctps FROM employees LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE employees ADD COLUMN registro_ctps TEXT")
            try:
                conn.execute("SELECT cnh_ear FROM employees LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE employees ADD COLUMN cnh_ear INTEGER DEFAULT 0")
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

    def create(self, nome: str, cpf: str = None, funcao: str = None, foto: Optional[bytes] = None, telefone: Optional[str] = None, data_nascimento: Optional[str] = None, tipo_sanguineo: Optional[str] = None, data_admissao: Optional[str] = None, registro_ctps: Optional[str] = None, cnh_ear: bool = False) -> Optional[int]:
        try:
            cpf_val = cpf.strip() if cpf and cpf.strip() else None
            tel_val = telefone.strip() if telefone and telefone.strip() else None
            if tel_val:
                import re
                tel_val = re.sub(r'\D', '', tel_val)
                if tel_val == "":
                    tel_val = None
            nasc_val = self._normalizar_data(data_nascimento)
            adm_val = self._normalizar_data(data_admissao)
            ts_val = self._normalizar_tipo_sanguineo(tipo_sanguineo)
            ctps_val = registro_ctps.strip() if registro_ctps and registro_ctps.strip() else None
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "INSERT INTO employees (nome, cpf, funcao, foto, telefone, data_nascimento, tipo_sanguineo, data_admissao, registro_ctps, cnh_ear) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (nome.strip(), cpf_val, funcao.strip() if funcao else None, foto, tel_val, nasc_val, ts_val, adm_val, ctps_val, 1 if cnh_ear else 0)
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    @staticmethod
    def _normalizar_data(valor: Optional[str]) -> Optional[str]:
        """Normaliza dd/mm/aaaa -> ISO aaaa-mm-dd (None/vazio -> None)."""
        if not valor or not str(valor).strip():
            return None
        s = str(valor).strip()
        if len(s) == 10 and s[2] == "/" and s[5] == "/":
            s = f"{s[6:10]}-{s[3:5]}-{s[0:2]}"
        return s

    _TIPOS_SANGUINEOS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}

    @classmethod
    def _normalizar_tipo_sanguineo(cls, valor: Optional[str]) -> Optional[str]:
        if not valor or not str(valor).strip():
            return None
        s = str(valor).strip().upper().replace(" ", "")
        return s if s in cls._TIPOS_SANGUINEOS else None

    # compat: chamado por codigos antigos
    _normalizar_nascimento = _normalizar_data

    def get_aniversariantes(self, mes: int, dia: Optional[int] = None) -> List[Employee]:
        """Aniversariantes do mes (ou do dia exato, se dia informado). Mes/dia: 1-12/1-31."""
        with self._get_conn() as conn:
            sql = ("SELECT * FROM employees WHERE data_nascimento IS NOT NULL "
                   "AND substr(data_nascimento, 6, 2) = ?")
            params = [f"{mes:02d}"]
            if dia is not None:
                sql += " AND substr(data_nascimento, 9, 2) = ?"
                params.append(f"{dia:02d}")
            sql += " ORDER BY substr(data_nascimento, 9, 2), nome"
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_employee(r) for r in rows]

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

    def update(self, emp_id: int, nome: str, cpf: str = None, funcao: str = None, foto: Optional[bytes] = None, telefone: Optional[str] = None, data_nascimento: Optional[str] = None, limpar_nascimento: bool = False, tipo_sanguineo: Optional[str] = None, limpar_tipo_sanguineo: bool = False, data_admissao: Optional[str] = None, limpar_admissao: bool = False, registro_ctps: Optional[str] = None, limpar_ctps: bool = False, cnh_ear: Optional[bool] = None) -> bool:
        try:
            cpf_val = cpf.strip() if cpf and cpf.strip() else None
            tel_val = telefone.strip() if telefone and telefone.strip() else None
            if tel_val:
                import re
                tel_val = re.sub(r'\D', '', tel_val)
                if tel_val == "":
                    tel_val = None
            nasc_val = self._normalizar_data(data_nascimento)
            adm_val = self._normalizar_data(data_admissao)
            ts_val = self._normalizar_tipo_sanguineo(tipo_sanguineo)
            ctps_val = registro_ctps.strip() if registro_ctps and registro_ctps.strip() else None
            # update sempre grava o nascimento: None com limpar=True apaga,
            # None sem flag mantem o valor atual (compat com chamadas antigas)
            with self._get_conn() as conn:
                sql_cols = "nome = ?, cpf = ?, funcao = ?, telefone = ?"
                params = [nome.strip(), cpf_val, funcao.strip() if funcao else None, tel_val]
                if nasc_val is not None:
                    sql_cols += ", data_nascimento = ?"
                    params.append(nasc_val)
                elif limpar_nascimento:
                    sql_cols += ", data_nascimento = NULL"
                if ts_val is not None:
                    sql_cols += ", tipo_sanguineo = ?"
                    params.append(ts_val)
                elif limpar_tipo_sanguineo:
                    sql_cols += ", tipo_sanguineo = NULL"
                if adm_val is not None:
                    sql_cols += ", data_admissao = ?"
                    params.append(adm_val)
                elif limpar_admissao:
                    sql_cols += ", data_admissao = NULL"
                if ctps_val is not None:
                    sql_cols += ", registro_ctps = ?"
                    params.append(ctps_val)
                elif limpar_ctps:
                    sql_cols += ", registro_ctps = NULL"
                if cnh_ear is not None:
                    sql_cols += ", cnh_ear = ?"
                    params.append(1 if cnh_ear else 0)
                if foto is not None:
                    sql_cols += ", foto = ?"
                    params.append(foto)
                params.append(emp_id)
                conn.execute(f"UPDATE employees SET {sql_cols} WHERE id = ?", params)
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
        try:
            nasc_val = row["data_nascimento"]
        except Exception:
            nasc_val = None
        try:
            ts_val = row["tipo_sanguineo"]
        except Exception:
            ts_val = None
        try:
            adm_val = row["data_admissao"]
        except Exception:
            adm_val = None
        try:
            ctps_val = row["registro_ctps"]
        except Exception:
            ctps_val = None
        try:
            ear_val = bool(row["cnh_ear"])
        except Exception:
            ear_val = False
        return Employee(
            id=row["id"],
            nome=row["nome"],
            cpf=cpf_val,
            funcao=row["funcao"],
            foto=foto_val,
            telefone=tel_val or None,
            data_nascimento=nasc_val or None,
            tipo_sanguineo=ts_val or None,
            data_admissao=adm_val or None,
            registro_ctps=ctps_val or None,
            cnh_ear=ear_val,
            created_at=row["created_at"]
        )
