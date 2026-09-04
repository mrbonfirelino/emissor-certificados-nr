import sqlite3
from pathlib import Path
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Dict, Any
from src.utils.paths import get_db_path
from src.utils.text_utils import normalize_text


ASO_TIPOS = ["Admissional", "Periódico", "Mudança de Função", "Retorno ao Trabalho", "Demissional"]


class AsoRepository:
    """Repositorio de ASOs (Atestado de Saude Ocupacional) com numeracao sequencial."""

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
                CREATE TABLE IF NOT EXISTS asos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aso_number TEXT UNIQUE NOT NULL,
                    employee_id INTEGER NOT NULL,
                    tipo_aso TEXT NOT NULL,
                    data_exame TEXT NOT NULL,
                    validade_meses INTEGER NOT NULL DEFAULT 12,
                    pdf_path TEXT,
                    aso_doc BLOB,
                    aso_doc_tipo TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                );
                CREATE INDEX IF NOT EXISTS idx_aso_employee ON asos(employee_id);
                CREATE INDEX IF NOT EXISTS idx_aso_exame ON asos(data_exame);

                CREATE TABLE IF NOT EXISTS sequences_aso (
                    name TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO sequences_aso (name, value) VALUES ('aso', 0);
            """)

    # colunas de listagem (BLOB aso_doc fica de fora: carga pesada)
    _LIST_COLS = """
        asos.id, aso_number, employee_id, tipo_aso, data_exame, validade_meses,
        pdf_path, asos.created_at, (aso_doc IS NOT NULL) AS has_doc
    """

    def next_aso_number(self) -> str:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE sequences_aso SET value = value + 1 WHERE name = 'aso' RETURNING value"
            )
            row = cursor.fetchone()
            return f"ASO-{row[0]:06d}"

    def save(self, aso_number: str, employee_id: int, tipo_aso: str,
             data_exame: str, validade_meses: int = 12, pdf_path: str = None) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO asos (aso_number, employee_id, tipo_aso, data_exame, validade_meses, pdf_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (aso_number, employee_id, tipo_aso, data_exame, validade_meses, pdf_path))
            return cursor.lastrowid

    def update_pdf_path(self, aso_id: int, pdf_path: str) -> bool:
        with self._get_conn() as conn:
            conn.execute("UPDATE asos SET pdf_path = ? WHERE id = ?", (pdf_path, aso_id))
            return True

    def get_by_id(self, aso_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(f"""
                SELECT {self._LIST_COLS}, e.nome AS funcionario_nome, e.cpf AS funcionario_cpf
                FROM asos LEFT JOIN employees e ON asos.employee_id = e.id
                WHERE asos.id = ?
            """, (aso_id,)).fetchone()
            return dict(row) if row else None

    def get_by_number(self, aso_number: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(f"""
                SELECT {self._LIST_COLS}, e.nome AS funcionario_nome, e.cpf AS funcionario_cpf
                FROM asos LEFT JOIN employees e ON asos.employee_id = e.id
                WHERE asos.aso_number = ?
            """, (aso_number,)).fetchone()
            return dict(row) if row else None

    def get_by_employee(self, employee_id: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT {self._LIST_COLS}, e.nome AS funcionario_nome, e.cpf AS funcionario_cpf
                FROM asos LEFT JOIN employees e ON asos.employee_id = e.id
                WHERE asos.employee_id = ?
                ORDER BY asos.data_exame DESC, asos.id DESC
            """, (employee_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT {self._LIST_COLS}, e.nome AS funcionario_nome, e.cpf AS funcionario_cpf
                FROM asos LEFT JOIN employees e ON asos.employee_id = e.id
                ORDER BY asos.created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            return [dict(r) for r in rows]

    def count_all(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM asos").fetchone()[0]

    def search(self, query: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        norm = normalize_text(query)
        with self._get_conn() as conn:
            like = f"%{norm}%"
            rows = conn.execute(f"""
                SELECT {self._LIST_COLS}, e.nome AS funcionario_nome, e.cpf AS funcionario_cpf
                FROM asos LEFT JOIN employees e ON asos.employee_id = e.id
                WHERE normalize(e.nome) LIKE ?
                   OR e.cpf LIKE ?
                   OR aso_number LIKE ?
                   OR tipo_aso LIKE ?
                ORDER BY asos.created_at DESC LIMIT ? OFFSET ?
            """, (like, f"%{query}%", like, f"%{query}%", limit, offset)).fetchall()
            return [dict(r) for r in rows]

    def count_search(self, query: str) -> int:
        norm = normalize_text(query)
        with self._get_conn() as conn:
            like = f"%{norm}%"
            return conn.execute("""
                SELECT COUNT(*) FROM asos LEFT JOIN employees e ON asos.employee_id = e.id
                WHERE normalize(e.nome) LIKE ?
                   OR e.cpf LIKE ?
                   OR aso_number LIKE ?
                   OR tipo_aso LIKE ?
            """, (like, f"%{query}%", like, f"%{query}%")).fetchone()[0]

    # --- Documento (ASO real digitalizado) ---

    def attach_doc(self, aso_id: int, data: bytes, tipo: str) -> bool:
        """Anexa (ou substitui) o ASO digitalizado. Valida ext/MIME/50MB."""
        from src.core.employee_repo import EmployeeRepository
        tipo = EmployeeRepository._validar_doc(f"aso.{tipo}", data, tipo)
        if tipo == "jpeg":
            tipo = "jpg"
        with self._get_conn() as conn:
            conn.execute("UPDATE asos SET aso_doc = ?, aso_doc_tipo = ? WHERE id = ?",
                         (sqlite3.Binary(data), tipo, aso_id))
            return True

    def get_doc(self, aso_id: int) -> Optional[tuple]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT aso_doc, aso_doc_tipo FROM asos WHERE id = ?", (aso_id,)
            ).fetchone()
            if row and row["aso_doc"]:
                return row["aso_doc"], (row["aso_doc_tipo"] or "pdf")
            return None

    def remove_doc(self, aso_id: int) -> bool:
        with self._get_conn() as conn:
            conn.execute("UPDATE asos SET aso_doc = NULL, aso_doc_tipo = NULL WHERE id = ?", (aso_id,))
            return True

    # --- Expiracao (formato igual aos certificados p/ vencimentos/dashboard) ---

    def get_asos_with_expiration(self, only_latest: bool = True) -> List[Dict[str, Any]]:
        """ASOs com validade calculada. only_latest=True mantem por funcionario
        apenas o exame mais recente (maior data_exame, desempate por id)."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT a.*, e.nome AS funcionario_nome, e.cpf AS funcionario_cpf, e.funcao AS funcionario_funcao
                FROM asos a LEFT JOIN employees e ON a.employee_id = e.id
                ORDER BY e.nome, a.data_exame, a.id
            """).fetchall()

        today = date.today()
        resultados: Dict[int, Dict[str, Any]] = {}
        todos: List[Dict[str, Any]] = []
        for row in rows:
            validade_meses = row["validade_meses"] or 12
            try:
                data_exame = date.fromisoformat(row["data_exame"])
            except ValueError:
                continue
            data_validade = data_exame + relativedelta(months=validade_meses)
            dias = (data_validade - today).days
            if dias < 0:
                status = "vencido"
            elif dias <= 7:
                status = "urgente"
            elif dias <= 15:
                status = "critico"
            elif dias <= 30:
                status = "atencao"
            elif dias <= 90:
                status = "proximo"
            else:
                status = "ok"
            item = {
                "id": row["id"],
                "cert_number": row["aso_number"],
                "nr_code": "ASO",
                "nr_name": "ASO",
                "employee_id": row["employee_id"],
                "funcionario_nome": row["funcionario_nome"] or "",
                "funcionario_cpf": row["funcionario_cpf"] or "",
                "funcionario_funcao": row["funcionario_funcao"] or "",
                "data_inicio": row["data_exame"],
                "data_fim": row["data_exame"],
                "descricao_treinamento": row["tipo_aso"],
                "validade_meses": validade_meses,
                "data_validade": data_validade.isoformat(),
                "dias_para_vencer": dias,
                "status": status,
                "tipo_aso": row["tipo_aso"],
            }
            resultados[row["employee_id"]] = item
            todos.append(item)

        lista = list(resultados.values()) if only_latest else todos
        lista.sort(key=lambda c: (c["funcionario_nome"], c["nr_code"]))
        return lista
