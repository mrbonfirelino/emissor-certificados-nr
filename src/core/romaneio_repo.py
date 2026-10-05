"""Repositorio de Romaneios (FASE: Romaneios).

Romaneios NUNCA sao excluidos: apenas bloqueados (flag + auditoria).
Serial unico gerado por sequencia (ROM-000001, ROM-000002, ...).
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.paths import get_db_path

# Blocos fixos do modelo (4+ = blocos dinamicos "Outros")
BLOCOS_FIXOS = {1: "EQUIPAMENTOS E COMPONENTES",
                2: "PARAFUSOS E COMPONENTES",
                3: "COMPONENTES"}

_PER_PAGE = 20

_LIST_COLS = ("romaneios.id, serial, os, cliente, ordem_compra, responsavel, "
              "data_elaboracao, transportadora, transportadora_doc, veiculo, "
              "placa, motorista, data_embarque, emitido_por, pdf_path, "
              "romaneios.created_at, COALESCE(romaneios.bloqueado, 0) AS bloqueado, "
              "romaneios.bloqueado_por, romaneios.bloqueado_em, "
"(romaneios.assinatura_altec IS NOT NULL) AS tem_ass_altec, "
"(romaneios.assinatura_transp IS NOT NULL) AS tem_ass_transp")


class RomaneioRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else get_db_path()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        try:
            with conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS romaneios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        serial TEXT UNIQUE NOT NULL,
                        os TEXT DEFAULT '',
                        cliente TEXT DEFAULT '',
                        ordem_compra TEXT DEFAULT '',
                        responsavel TEXT DEFAULT '',
                        data_elaboracao TEXT DEFAULT '',
                        transportadora TEXT DEFAULT '',
                        transportadora_doc TEXT DEFAULT '',
                        veiculo TEXT DEFAULT '',
                        placa TEXT DEFAULT '',
                        motorista TEXT DEFAULT '',
                        data_embarque TEXT DEFAULT '',
                        emitido_por TEXT DEFAULT '',
                        pdf_path TEXT,
                        bloqueado INTEGER DEFAULT 0,
                        bloqueado_por TEXT,
                        bloqueado_em TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    );
                    CREATE INDEX IF NOT EXISTS idx_romaneio_serial
                        ON romaneios(serial);
                    CREATE TABLE IF NOT EXISTS romaneio_itens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        romaneio_id INTEGER NOT NULL REFERENCES romaneios(id),
                        bloco INTEGER NOT NULL DEFAULT 1,
                        bloco_titulo TEXT DEFAULT '',
                        codigo TEXT DEFAULT '',
                        descricao TEXT DEFAULT '',
                        unidade TEXT DEFAULT '',
                        qtd TEXT DEFAULT '',
                        dimensoes TEXT DEFAULT '',
                        peso TEXT DEFAULT '',
                        tipo TEXT DEFAULT '',
                        observacoes TEXT DEFAULT '',
                        ordem INTEGER DEFAULT 0
                    );
                    CREATE INDEX IF NOT EXISTS idx_romaneio_item
                        ON romaneio_itens(romaneio_id);
                    CREATE TABLE IF NOT EXISTS sequences_romaneio (
                        name TEXT PRIMARY KEY,
                        value INTEGER NOT NULL
                    );
                    INSERT OR IGNORE INTO sequences_romaneio (name, value)
                        VALUES ('romaneio', 0);
                    """
                )
                # v1.62.0: assinaturas capturadas no navegador (PNG)
                cols = {r[1] for r in conn.execute("PRAGMA table_info(romaneios)")}
                for _col in ("assinatura_altec", "assinatura_transp"):
                    if _col not in cols:
                        conn.execute(
                            "ALTER TABLE romaneios "
                            f"ADD COLUMN {_col} BLOB")
        finally:
            conn.close()

    # ---------------------------------------------------------------- serial
    def next_serial(self) -> str:
        conn = self._get_conn()
        try:
            with conn:
                row = conn.execute(
                    "UPDATE sequences_romaneio SET value = value + 1 "
                    "WHERE name = 'romaneio' RETURNING value"
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO sequences_romaneio (name, value) "
                        "VALUES ('romaneio', 1)"
                    )
                    n = 1
                else:
                    n = row[0]
            return f"ROM-{n:06d}"
        finally:
            conn.close()

    # ------------------------------------------------------------------ CRUD
    def save(self, dados: Dict[str, Any],
             itens: Optional[List[Dict[str, Any]]] = None) -> int:
        """Insere o romaneio + itens; retorna o id."""
        conn = self._get_conn()
        try:
            with conn:
                cur = conn.execute(
                    "INSERT INTO romaneios (serial, os, cliente, ordem_compra, "
                    "responsavel, data_elaboracao, transportadora, "
                    "transportadora_doc, veiculo, placa, motorista, "
                    "data_embarque, emitido_por) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (dados.get("serial", ""),
                     dados.get("os", ""),
                     dados.get("cliente", ""),
                     dados.get("ordem_compra", ""),
                     dados.get("responsavel", ""),
                     dados.get("data_elaboracao", ""),
                     dados.get("transportadora", ""),
                     dados.get("transportadora_doc", ""),
                     dados.get("veiculo", ""),
                     dados.get("placa", ""),
                     dados.get("motorista", ""),
                     dados.get("data_embarque", ""),
                     dados.get("emitido_por", "")),
                )
                romaneio_id = cur.lastrowid
                for i, it in enumerate(itens or []):
                    conn.execute(
                        "INSERT INTO romaneio_itens (romaneio_id, bloco, "
                        "bloco_titulo, codigo, descricao, unidade, qtd, "
                        "dimensoes, peso, tipo, observacoes, ordem) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (romaneio_id, int(it.get("bloco", 1) or 1),
                         it.get("bloco_titulo", ""), it.get("codigo", ""),
                         it.get("descricao", ""), it.get("unidade", ""),
                         it.get("qtd", ""), it.get("dimensoes", ""),
                         it.get("peso", ""), it.get("tipo", ""),
                         it.get("observacoes", ""), i),
                    )
            return romaneio_id
        finally:
            conn.close()

    # ------------------------------------------------ assinaturas (v1.62.0)
    def set_assinatura(self, romaneio_id: int, qual: str,
                       data: Optional[bytes]) -> bool:
        col = {"altec": "assinatura_altec",
               "transp": "assinatura_transp"}.get(qual)
        if col is None:
            return False
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    f"UPDATE romaneios SET {col} = ? WHERE id = ?",
                    (data, romaneio_id))
        finally:
            conn.close()
        return True

    def get_assinatura(self, romaneio_id: int, qual: str) -> Optional[bytes]:
        col = {"altec": "assinatura_altec",
               "transp": "assinatura_transp"}.get(qual)
        if col is None:
            return None
        conn = self._get_conn()
        try:
            row = conn.execute(
                f"SELECT {col} FROM romaneios WHERE id = ?",
                (romaneio_id,)).fetchone()
            return row[0] if row is not None else None
        finally:
            conn.close()

    def update_pdf_path(self, romaneio_id: int, pdf_path: str) -> None:
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    "UPDATE romaneios SET pdf_path = ? WHERE id = ?",
                    (str(pdf_path), romaneio_id))
        finally:
            conn.close()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {k: row[k] for k in row.keys()}

    def _itens(self, conn: sqlite3.Connection,
               romaneio_id: int) -> List[Dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM romaneio_itens WHERE romaneio_id = ? "
            "ORDER BY bloco, ordem, id", (romaneio_id,)).fetchall()
        return [{k: r[k] for k in r.keys()} for r in rows]

    def get_by_id(self, romaneio_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                f"SELECT {_LIST_COLS} FROM romaneios WHERE romaneios.id = ?",
                (romaneio_id,)).fetchone()
            if row is None:
                return None
            d = self._row_to_dict(row)
            d["itens"] = self._itens(conn, romaneio_id)
            return d
        finally:
            conn.close()

    def get_by_serial(self, serial: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                f"SELECT {_LIST_COLS} FROM romaneios WHERE serial = ?",
                (serial,)).fetchone()
            if row is None:
                return None
            d = self._row_to_dict(row)
            d["itens"] = self._itens(conn, row["id"])
            return d
        finally:
            conn.close()

    # ------------------------------------------------------ listagem / busca
    def get_all(self, limit: int = _PER_PAGE, offset: int = 0) -> List[Dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                f"SELECT {_LIST_COLS} FROM romaneios "
                "ORDER BY romaneios.id DESC LIMIT ? OFFSET ?",
                (limit, offset)).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def count_all(self) -> int:
        conn = self._get_conn()
        try:
            return conn.execute(
                "SELECT COUNT(*) FROM romaneios").fetchone()[0]
        finally:
            conn.close()

    def search(self, query: str, limit: int = _PER_PAGE,
               offset: int = 0) -> List[Dict]:
        like = f"%{query}%"
        conn = self._get_conn()
        try:
            rows = conn.execute(
                f"SELECT {_LIST_COLS} FROM romaneios "
                "WHERE serial LIKE ? OR os LIKE ? OR cliente LIKE ? "
                "OR ordem_compra LIKE ? OR transportadora LIKE ? "
                "OR motorista LIKE ? OR placa LIKE ? "
                "ORDER BY romaneios.id DESC LIMIT ? OFFSET ?",
                (like, like, like, like, like, like, like,
                 limit, offset)).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def count_search(self, query: str) -> int:
        like = f"%{query}%"
        conn = self._get_conn()
        try:
            return conn.execute(
                "SELECT COUNT(*) FROM romaneios WHERE serial LIKE ? "
                "OR os LIKE ? OR cliente LIKE ? OR ordem_compra LIKE ? "
                "OR transportadora LIKE ? OR motorista LIKE ? OR placa LIKE ?",
                (like, like, like, like, like, like, like)).fetchone()[0]
        finally:
            conn.close()

    # -------------------------------------------------------------- bloqueio
    def set_bloqueio(self, romaneio_id: int, bloqueado: bool,
                     usuario: str) -> None:
        """Bloqueia/desbloqueia. Romaneio nunca e excluido (roadmap 909)."""
        conn = self._get_conn()
        try:
            with conn:
                if bloqueado:
                    conn.execute(
                        "UPDATE romaneios SET bloqueado = 1, bloqueado_por = ?, "
                        "bloqueado_em = ? WHERE id = ?",
                        (usuario, datetime.now().isoformat(timespec="seconds"),
                         romaneio_id))
                else:
                    conn.execute(
                        "UPDATE romaneios SET bloqueado = 0, bloqueado_por = NULL, "
                        "bloqueado_em = NULL WHERE id = ?", (romaneio_id,))
        finally:
            conn.close()
