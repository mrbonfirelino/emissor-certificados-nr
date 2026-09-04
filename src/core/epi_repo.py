import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from src.utils.paths import get_db_path
from src.utils.text_utils import normalize_text


class EpiRepository:
    """Repositorio de Fichas de EPI com numeracao sequencial + anexos multi-versionados."""

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
                CREATE TABLE IF NOT EXISTS epis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    epi_number TEXT UNIQUE NOT NULL,
                    employee_id INTEGER NOT NULL,
                    data_emissao TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'aberto',
                    items TEXT NOT NULL DEFAULT '[]',
                    pdf_path TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                );
                CREATE INDEX IF NOT EXISTS idx_epi_employee ON epis(employee_id);

                CREATE TABLE IF NOT EXISTS epi_docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    epi_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    tamanho INTEGER NOT NULL DEFAULT 0,
                    dados BLOB,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (epi_id) REFERENCES epis(id)
                );
                CREATE INDEX IF NOT EXISTS idx_epidocs_epi ON epi_docs(epi_id);

                CREATE TABLE IF NOT EXISTS sequences_epi (
                    name TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO sequences_epi (name, value) VALUES ('epi', 0);
            """)

    _LIST_COLS = ("epis.id, epis.epi_number, epis.employee_id, epis.data_emissao, "
                  "epis.status, epis.items, epis.pdf_path, epis.created_at")

    def next_epi_number(self) -> str:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE sequences_epi SET value = value + 1 WHERE name = 'epi' RETURNING value"
            )
            row = cursor.fetchone()
            return f"EPI-{row[0]:06d}"

    @staticmethod
    def _validar_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            raise ValueError("Items invalidos")
        limpos = []
        for it in items:
            limpos.append({
                "ca": str(it.get("ca", "") or "").strip(),
                "descricao": str(it.get("descricao", "") or "").strip(),
                "quantidade": str(it.get("quantidade", "") or "").strip(),
                "data_entrega": str(it.get("data_entrega", "") or "").strip(),
                "dev_quantidade": str(it.get("dev_quantidade", "") or "").strip(),
                "dev_data": str(it.get("dev_data", "") or "").strip(),
            })
        return limpos

    def save(self, epi_number: str, employee_id: int, data_emissao: str,
             items: List[Dict[str, Any]], pdf_path: str = None, status: str = "aberto") -> int:
        items_json = json.dumps(self._validar_items(items), ensure_ascii=False)
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO epis (epi_number, employee_id, data_emissao, status, items, pdf_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (epi_number, employee_id, data_emissao, status, items_json, pdf_path))
            return cursor.lastrowid

    def update_items(self, epi_id: int, items: List[Dict[str, Any]]) -> bool:
        items_json = json.dumps(self._validar_items(items), ensure_ascii=False)
        with self._get_conn() as conn:
            conn.execute("UPDATE epis SET items = ? WHERE id = ?", (items_json, epi_id))
            return True

    def update_pdf_path(self, epi_id: int, pdf_path: str) -> bool:
        with self._get_conn() as conn:
            conn.execute("UPDATE epis SET pdf_path = ? WHERE id = ?", (pdf_path, epi_id))
            return True

    def toggle_status(self, epi_id: int) -> str:
        """Alterna aberto<->fechado. Retorna o novo status."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT status FROM epis WHERE id = ?", (epi_id,)).fetchone()
            novo = "fechado" if (row and row["status"] != "fechado") else "aberto"
            conn.execute("UPDATE epis SET status = ? WHERE id = ?", (novo, epi_id))
            return novo

    def get_by_id(self, epi_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(f"""
                SELECT {self._LIST_COLS}, e.nome AS funcionario_nome, e.cpf AS funcionario_cpf
                FROM epis LEFT JOIN employees e ON epis.employee_id = e.id
                WHERE epis.id = ?
            """, (epi_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def get_by_employee(self, employee_id: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT {self._LIST_COLS}, e.nome AS funcionario_nome, e.cpf AS funcionario_cpf
                FROM epis LEFT JOIN employees e ON epis.employee_id = e.id
                WHERE epis.employee_id = ?
                ORDER BY epis.data_emissao DESC, epis.id DESC
            """, (employee_id,)).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def count_docs(self, epi_id: int) -> int:
        with self._get_conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM epi_docs WHERE epi_id = ?", (epi_id,)
            ).fetchone()[0]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["items"] = json.loads(d.get("items") or "[]")
        except (ValueError, TypeError):
            d["items"] = []
        return d

    # --- Documentos anexos (fichas digitalizadas; multiplas versoes) ---

    def add_doc(self, epi_id: int, filename: str, data: bytes, tipo: str) -> int:
        """Anexa mais uma digitalizacao da ficha (NAO apaga as anteriores)."""
        from src.core.employee_repo import EmployeeRepository
        tipo = EmployeeRepository._validar_doc(filename, data, tipo)
        if tipo == "jpeg":
            tipo = "jpg"
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO epi_docs (epi_id, filename, tipo, tamanho, dados) VALUES (?, ?, ?, ?, ?)",
                (epi_id, filename, tipo, len(data), sqlite3.Binary(data))
            )
            return cursor.lastrowid

    def list_docs(self, epi_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, filename, tipo, tamanho, created_at FROM epi_docs "
                "WHERE epi_id = ? ORDER BY created_at DESC, id DESC",
                (epi_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_doc(self, doc_id: int) -> Optional[tuple]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT epi_id, filename, dados, tipo FROM epi_docs WHERE id = ?", (doc_id,)
            ).fetchone()
            if row and row["dados"]:
                return row["epi_id"], row["filename"], row["dados"], (row["tipo"] or "pdf")
            return None

    def delete_doc(self, doc_id: int) -> bool:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM epi_docs WHERE id = ?", (doc_id,))
            return True
