"""
Repositorio das listas de presenca (v1.36.0).

Tabela `presencas` no mesmo banco do sistema:
- serial LP-{ano da data referente}-{id:05d} (id global, nunca reinicia)
- status: pendente | parcial | assinada
- participantes em JSON [{nome, funcao, cpf}]
- anexo da lista assinada em BLOB (pdf/jpg/png)
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

from src.utils.paths import get_data_dir

DB_PATH = get_data_dir() / "certificados.db"

STATUS_VALIDOS = ("pendente", "parcial", "assinada")


def get_db_path() -> Path:
    return DB_PATH


class PresencaRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else get_db_path()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS presencas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial TEXT UNIQUE,
                    nr_code TEXT NOT NULL,
                    nr_label TEXT,
                    data_ref TEXT NOT NULL,
                    carga_horaria REAL,
                    participantes TEXT NOT NULL DEFAULT '[]',
                    assunto TEXT,
                    status TEXT NOT NULL DEFAULT 'pendente',
                    pdf_path TEXT,
                    signed_dados BLOB,
                    signed_tipo TEXT,
                    signed_filename TEXT,
                    criado_por TEXT,
                    criado_em TEXT
                )
            """)

    @staticmethod
    def _row_to_dict(r) -> dict:
        d = dict(r)
        try:
            d["participantes"] = json.loads(d.get("participantes") or "[]")
        except Exception:
            d["participantes"] = []
        d["tem_assinada"] = d.get("signed_dados") is not None
        return d

    def add(self, nr_code: str, nr_label: str, data_ref: str, carga_horaria: float,
            participantes: list, assunto: str = "", pdf_path: str = "",
            criado_por: str = "") -> Tuple[int, str]:
        """Insere e devolve (id, serial). Serial usa o ano da data referente."""
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO presencas
                   (serial, nr_code, nr_label, data_ref, carga_horaria,
                    participantes, assunto, status, pdf_path, criado_por, criado_em)
                   VALUES ('', ?, ?, ?, ?, ?, ?, 'pendente', ?, ?, datetime('now', 'localtime'))""",
                (nr_code, nr_label, data_ref, carga_horaria,
                 json.dumps(participantes, ensure_ascii=False),
                 assunto, pdf_path, criado_por))
            pid = cur.lastrowid
            serial = f"LP-{data_ref[:4]}-{pid:05d}"
            conn.execute("UPDATE presencas SET serial = ? WHERE id = ?", (serial, pid))
        return pid, serial

    def get(self, presenca_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            r = conn.execute("SELECT * FROM presencas WHERE id = ?", (presenca_id,)).fetchone()
            return self._row_to_dict(r) if r else None

    def list(self, busca: str = "", limit: int = 20, offset: int = 0) -> Tuple[List[dict], int]:
        where, params = [], []
        q = (busca or "").strip().lower()
        if q:
            where.append("""(lower(serial) LIKE ? OR lower(nr_code) LIKE ?
                             OR lower(nr_label) LIKE ? OR lower(coalesce(assunto,'')) LIKE ?
                             OR data_ref LIKE ?)""")
            like = f"%{q}%"
            params += [like, like, like, like, like]
        cond = f" WHERE {' AND '.join(where)}" if where else ""
        with self._get_conn() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM presencas{cond}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM presencas{cond} ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [limit, offset]).fetchall()
        return [self._row_to_dict(r) for r in rows], total

    def list_por_data(self, data_ref: str) -> List[dict]:
        """Listas de UMA data referente (ordenadas por NR) — p/ compilado."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM presencas WHERE data_ref = ? ORDER BY nr_code",
                (data_ref,)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def set_status(self, presenca_id: int, status: str) -> bool:
        if status not in STATUS_VALIDOS:
            raise ValueError("Status invalido")
        with self._get_conn() as conn:
            cur = conn.execute("UPDATE presencas SET status = ? WHERE id = ?",
                               (status, presenca_id))
            return cur.rowcount > 0

    def attach_signed(self, presenca_id: int, dados: bytes, tipo: str, filename: str) -> bool:
        """Anexa a lista assinada e marca status 'assinada'."""
        with self._get_conn() as conn:
            cur = conn.execute(
                """UPDATE presencas
                   SET signed_dados = ?, signed_tipo = ?, signed_filename = ?, status = 'assinada'
                   WHERE id = ?""",
                (dados, tipo, filename, presenca_id))
            return cur.rowcount > 0

    def remove_signed(self, presenca_id: int) -> bool:
        """Remove o anexo assinado; status volta para 'pendente'."""
        with self._get_conn() as conn:
            cur = conn.execute(
                """UPDATE presencas
                   SET signed_dados = NULL, signed_tipo = NULL, signed_filename = NULL,
                       status = 'pendente'
                   WHERE id = ?""",
                (presenca_id,))
            return cur.rowcount > 0

    def get_signed(self, presenca_id: int) -> Optional[Tuple[bytes, str, str]]:
        with self._get_conn() as conn:
            r = conn.execute(
                "SELECT signed_dados, signed_tipo, signed_filename FROM presencas WHERE id = ?",
                (presenca_id,)).fetchone()
            if not r or r["signed_dados"] is None:
                return None
            return bytes(r["signed_dados"]), r["signed_tipo"] or "", r["signed_filename"] or ""

    def set_pdf_path(self, presenca_id: int, pdf_path: str) -> None:
        with self._get_conn() as conn:
            conn.execute("UPDATE presencas SET pdf_path = ? WHERE id = ?",
                         (pdf_path, presenca_id))

    def delete(self, presenca_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM presencas WHERE id = ?", (presenca_id,))
            return cur.rowcount > 0

    def count_por_status(self) -> dict:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS n FROM presencas GROUP BY status").fetchall()
            out = {s: 0 for s in STATUS_VALIDOS}
            for r in rows:
                out[r["status"]] = r["n"]
            return out
