# -*- coding: utf-8 -*-
"""Repositorio do modulo Controle de Cintos e Talabartes (v1.83.0).

Tabelas:
- cintos: itens do estoque (marca, modelo, CA, lote, numero de serie, fabricacao, validade, antichama, arquivamento)
- cinto_inspecoes: inspecoes periodicas (a cada 3 meses), com relatorio anexado OU relatorio interno (texto + fotos)
- cinto_movimentacoes: entrada/saida com localizacao e confirmacao de teste/apto para uso
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from src.utils.paths import get_db_path

# limite de anexo de relatorio/foto (mesmo padrao dos documentos assinados: 30 MB, v1.80.2)
CINTO_DOC_MAX_BYTES = 30 * 1024 * 1024
CINTO_DOC_TIPOS = {"pdf", "jpg", "jpeg", "png"}

# intervalo padrao entre inspecoes (meses)
INTERVALO_INSPESAO_MESES = 3


def _add_months(d: date, meses: int) -> date:
    mes = d.month - 1 + meses
    ano = d.year + mes // 12
    mes = mes % 12 + 1
    dia = min(d.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return date(ano, mes, dia)


class CintoRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_db_path()
        self._init_db()

    # ------------------------------------------------------------------ infra
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS cintos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    marca TEXT NOT NULL,
                    modelo TEXT NOT NULL,
                    ca TEXT NOT NULL,
                    lote TEXT NOT NULL,
                    numero_serie TEXT NOT NULL UNIQUE,
                    data_fabricacao TEXT NOT NULL,
                    validade_meses INTEGER NOT NULL DEFAULT 60,
                    data_validade TEXT NOT NULL,
                    antichama INTEGER NOT NULL DEFAULT 0,
                    observacoes TEXT,
                    localizacao TEXT,
                    arquivado INTEGER NOT NULL DEFAULT 0,
                    motivo_arquivamento TEXT,
                    arquivado_em TEXT,
                    arquivado_por TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_cintos_arquivado ON cintos(arquivado);
                CREATE TABLE IF NOT EXISTS cinto_inspecoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cinto_id INTEGER NOT NULL REFERENCES cintos(id),
                    data_inspecao TEXT NOT NULL,
                    proxima_inspecao TEXT NOT NULL,
                    tipo TEXT NOT NULL DEFAULT 'interno',
                    filename TEXT,
                    dados BLOB,
                    tipo_arquivo TEXT,
                    tamanho INTEGER,
                    texto TEXT,
                    fotos BLOB,
                    fotos_tipo TEXT,
                    usuario TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_cinto_insp_cinto ON cinto_inspecoes(cinto_id);
                CREATE TABLE IF NOT EXISTS cinto_movimentacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cinto_id INTEGER NOT NULL REFERENCES cintos(id),
                    tipo TEXT NOT NULL DEFAULT 'saida',
                    data TEXT NOT NULL,
                    destino TEXT,
                    responsavel TEXT,
                    testado INTEGER,
                    confirmacao TEXT,
                    observacoes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_cinto_mov_cinto ON cinto_movimentacoes(cinto_id);
                CREATE TABLE IF NOT EXISTS cinto_descarte_anexos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cinto_id INTEGER NOT NULL REFERENCES cintos(id),
                    filename TEXT NOT NULL,
                    dados BLOB,
                    tipo_arquivo TEXT,
                    tamanho INTEGER,
                    usuario TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_cinto_desc_cinto ON cinto_descarte_anexos(cinto_id);
                CREATE TABLE IF NOT EXISTS sequences (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
            """)
            self._migrar(conn)

    def _migrar(self, conn):
        """Migracoes idempotentes (v1.84.0): tipo, nome e codigo do item."""
        cols = {r[1] for r in conn.execute("PRAGMA table_info(cintos)").fetchall()}
        for col, ddl in (("tipo", "TEXT NOT NULL DEFAULT 'cinto'"),
                         ("nome", "TEXT NOT NULL DEFAULT ''"),
                         ("codigo", "TEXT")):
            if col not in cols:
                conn.execute(f"ALTER TABLE cintos ADD COLUMN {col} {ddl}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cintos_codigo ON cintos(codigo)")
        # codigos para itens antigos (sem codigo)
        for row in conn.execute("SELECT id, tipo FROM cintos WHERE codigo IS NULL OR codigo=''").fetchall():
            conn.execute("UPDATE cintos SET codigo=? WHERE id=?",
                         (self._gera_codigo(conn, row["tipo"] or "cinto"), row["id"]))
        # v1.84.1: resultado da entrada (apto / danificado)
        movs = {r[1] for r in conn.execute("PRAGMA table_info(cinto_movimentacoes)").fetchall()}
        if "resultado" not in movs:
            conn.execute("ALTER TABLE cinto_movimentacoes ADD COLUMN resultado TEXT DEFAULT ''")

    @staticmethod
    def _prefixo(tipo: str) -> str:
        return "TALAB" if (tipo or "").lower() == "talabarte" else "CINTO"

    def _gera_codigo(self, conn, tipo: str) -> str:
        """Numero identificador proprio: CINTO-0001 / TALAB-0001 (v1.84.0)."""
        name = self._prefixo(tipo).lower()
        conn.execute("INSERT OR IGNORE INTO sequences (name, value) VALUES (?, 0)", (name,))
        row = conn.execute(
            "UPDATE sequences SET value = value + 1 WHERE name = ? RETURNING value",
            (name,)).fetchone()
        return f"{self._prefixo(tipo)}-{row[0]:04d}"

    def proximo_codigo(self, tipo: str) -> str:
        with self._get_conn() as conn:
            return self._gera_codigo(conn, tipo)

    # ----------------------------------------------------------------- cintos
    def save(self, *, id: Optional[int] = None, marca: str, modelo: str, ca: str,
             lote: str, numero_serie: str, data_fabricacao: str,
             validade_meses: int = 60, data_validade: str,
             antichama: int = 0, observacoes: str = "",
             tipo: str = "cinto", nome: str = "") -> int:
        """Insere ou atualiza um item. data_validade ja vem calculada pelo router.
        Em insert, gera o codigo proprio (CINTO-0001 / TALAB-0001)."""
        with self._get_conn() as conn:
            if id:
                conn.execute(
                    """UPDATE cintos SET marca=?, modelo=?, ca=?, lote=?, numero_serie=?,
                       data_fabricacao=?, validade_meses=?, data_validade=?, antichama=?, observacoes=?,
                       tipo=?, nome=?
                       WHERE id=?""",
                    (marca, modelo, ca, lote, numero_serie, data_fabricacao,
                     validade_meses, data_validade, antichama, observacoes,
                     tipo, nome, id))
                return id
            codigo = self._gera_codigo(conn, tipo)
            cur = conn.execute(
                """INSERT INTO cintos (marca, modelo, ca, lote, numero_serie,
                   data_fabricacao, validade_meses, data_validade, antichama, observacoes,
                   tipo, nome, codigo)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (marca, modelo, ca, lote, numero_serie, data_fabricacao,
                 validade_meses, data_validade, antichama, observacoes,
                 tipo, nome, codigo))
            return cur.lastrowid

    def get(self, cinto_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM cintos WHERE id=?", (cinto_id,)).fetchone()
            return self._to_dict(row) if row else None

    def get_by_serie(self, numero_serie: str) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM cintos WHERE numero_serie=?",
                               (numero_serie,)).fetchone()
            return self._to_dict(row) if row else None

    def list_items(self, *, busca: str = "", antichama: str = "", arquivado: str = "nao",
                   situacao: str = "", tipo: str = "", limit: int = 20, offset: int = 0) -> tuple:
        """Lista com filtros. situacao: valido | vencido | descartado. tipo: cinto | talabarte."""
        where, params = [], []
        if arquivado == "sim":
            where.append("arquivado=1")
        elif arquivado == "nao":
            where.append("arquivado=0")
        if antichama == "sim":
            where.append("antichama=1")
        elif antichama == "nao":
            where.append("antichama=0")
        if tipo in ("cinto", "talabarte"):
            where.append("tipo=?")
            params.append(tipo)
        if busca:
            where.append("(nome LIKE ? OR marca LIKE ? OR modelo LIKE ? OR ca LIKE ? OR lote LIKE ? OR numero_serie LIKE ? OR localizacao LIKE ? OR codigo LIKE ?)")
            like = f"%{busca}%"
            params += [like] * 8
        sql_where = (" WHERE " + " AND ".join(where)) if where else ""
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM cintos{sql_where} ORDER BY tipo, nome, marca, modelo, id LIMIT ? OFFSET ?",
                params + [limit, offset]).fetchall()
            total = conn.execute(f"SELECT COUNT(*) FROM cintos{sql_where}", params).fetchone()[0]
        itens = [self._to_dict(r) for r in rows]
        if situacao in ("valido", "vencido", "descartado"):
            itens = [i for i in itens if i["situacao"] == situacao]
        return itens, total

    def set_arquivado(self, cinto_id: int, arquivado: bool, motivo: str = "", usuario: str = ""):
        with self._get_conn() as conn:
            if arquivado:
                conn.execute(
                    """UPDATE cintos SET arquivado=1, motivo_arquivamento=?, arquivado_em=?, arquivado_por=? WHERE id=?""",
                    (motivo, datetime.now().strftime("%d/%m/%Y %H:%M"), usuario, cinto_id))
            else:
                conn.execute(
                    """UPDATE cintos SET arquivado=0, motivo_arquivamento=NULL, arquivado_em=NULL, arquivado_por=NULL WHERE id=?""",
                    (cinto_id,))

    def counts_situacao(self) -> dict:
        """Contadores por situacao (ativos apenas) + alertas de inspecao."""
        hoje = date.today().strftime("%Y-%m-%d")
        limite = _add_months(date.today(), 1).strftime("%Y-%m-%d")
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM cintos WHERE arquivado=0").fetchone()[0]
            vencidos = conn.execute(
                "SELECT COUNT(*) FROM cintos WHERE arquivado=0 AND date(substr(data_validade,7,4)||'-'||substr(data_validade,4,2)||'-'||substr(data_validade,1,2)) < ?",
                (hoje,)).fetchone()[0]
            insp_vencidas = conn.execute(
                """SELECT COUNT(*) FROM cintos c WHERE c.arquivado=0 AND NOT EXISTS (
                     SELECT 1 FROM cinto_inspecoes i WHERE i.cinto_id=c.id
                       AND date(substr(i.proxima_inspecao,7,4)||'-'||substr(i.proxima_inspecao,4,2)||'-'||substr(i.proxima_inspecao,1,2)) >= ?)""",
                (hoje,)).fetchone()[0]
            insp_proximas = conn.execute(
                """SELECT COUNT(*) FROM cintos c WHERE c.arquivado=0 AND EXISTS (
                     SELECT 1 FROM cinto_inspecoes i WHERE i.cinto_id=c.id
                       AND date(substr(i.proxima_inspecao,7,4)||'-'||substr(i.proxima_inspecao,4,2)||'-'||substr(i.proxima_inspecao,1,2)) >= ?
                       AND date(substr(i.proxima_inspecao,7,4)||'-'||substr(i.proxima_inspecao,4,2)||'-'||substr(i.proxima_inspecao,1,2)) <= ?)""",
                (hoje, limite)).fetchone()[0]
            antichama = conn.execute(
                "SELECT COUNT(*) FROM cintos WHERE arquivado=0 AND antichama=1").fetchone()[0]
        return {"total": total, "vencidos": vencidos, "insp_vencidas": insp_vencidas,
                "insp_proximas": insp_proximas, "antichama": antichama}

    # -------------------------------------------------------------- inspecoes
    def add_inspecao(self, *, cinto_id: int, data_inspecao: str, proxima_inspecao: str,
                     tipo: str = "interno", filename: str = "", dados: bytes = b"",
                     tipo_arquivo: str = "", texto: str = "", fotos: bytes = b"",
                     fotos_tipo: str = "", usuario: str = "") -> int:
        if dados and len(dados) > CINTO_DOC_MAX_BYTES:
            raise ValueError("Anexo maior que 30MB")
        if fotos and len(fotos) > CINTO_DOC_MAX_BYTES:
            raise ValueError("Foto maior que 30MB")
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO cinto_inspecoes (cinto_id, data_inspecao, proxima_inspecao, tipo,
                   filename, dados, tipo_arquivo, tamanho, texto, fotos, fotos_tipo, usuario)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (cinto_id, data_inspecao, proxima_inspecao, tipo, filename or None,
                 dados or None, tipo_arquivo, len(dados) if dados else 0, texto,
                 fotos or None, fotos_tipo, usuario))
            return cur.lastrowid

    def list_inspecoes(self, cinto_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM cinto_inspecoes WHERE cinto_id=? ORDER BY id DESC",
                (cinto_id,)).fetchall()
        return [self._to_dict(r) for r in rows]

    def get_inspecao(self, inspecao_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM cinto_inspecoes WHERE id=?", (inspecao_id,)).fetchone()
            return self._to_dict(row) if row else None

    def ultima_inspecao(self, cinto_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM cinto_inspecoes WHERE cinto_id=? ORDER BY id DESC LIMIT 1",
                (cinto_id,)).fetchone()
            return self._to_dict(row) if row else None

    # ------------------------------------------------- anexos do descarte (v1.85.0)
    def add_descarte_anexo(self, *, cinto_id: int, filename: str, dados: bytes,
                           tipo_arquivo: str = "", usuario: str = "") -> int:
        if dados and len(dados) > CINTO_DOC_MAX_BYTES:
            raise ValueError("Anexo excede o limite de 30 MB.")
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO cinto_descarte_anexos (cinto_id, filename, dados,
                   tipo_arquivo, tamanho, usuario) VALUES (?,?,?,?,?,?)""",
                (cinto_id, filename, dados, tipo_arquivo, len(dados or b""), usuario))
            return cur.lastrowid

    def list_descarte_anexos(self, cinto_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM cinto_descarte_anexos WHERE cinto_id=? ORDER BY id DESC",
                (cinto_id,)).fetchall()
        return [self._to_dict(r) for r in rows]

    def get_descarte_anexo(self, anexo_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM cinto_descarte_anexos WHERE id=?", (anexo_id,)).fetchone()
            return self._to_dict(row) if row else None

    # ----------------------------------------------------------- movimentacoes
    def add_movimentacao(self, *, cinto_id: int, tipo: str, data: str, destino: str = "",
                         responsavel: str = "", testado: int = 0, confirmacao: str = "",
                         observacoes: str = "", resultado: str = "") -> int:
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO cinto_movimentacoes (cinto_id, tipo, data, destino, responsavel,
                   testado, confirmacao, observacoes, resultado) VALUES (?,?,?,?,?,?,?,?,?)""",
                (cinto_id, tipo, data, destino, responsavel, testado, confirmacao, observacoes,
                 resultado))
            return cur.lastrowid

    def list_movimentacoes(self, cinto_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM cinto_movimentacoes WHERE cinto_id=? ORDER BY id DESC",
                (cinto_id,)).fetchall()
        return [self._to_dict(r) for r in rows]

    def saida_aberta(self, cinto_id: int) -> Optional[dict]:
        """Ultima saida sem entrada correspondente (uma saida aberta por vez, como na frota)."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM cinto_movimentacoes WHERE cinto_id=? AND tipo='saida' ORDER BY id DESC LIMIT 1",
                (cinto_id,)).fetchone()
            if not row:
                return None
            entrada = conn.execute(
                "SELECT id FROM cinto_movimentacoes WHERE cinto_id=? AND tipo='entrada' AND id>?",
                (cinto_id, row["id"])).fetchone()
            if entrada:
                return None
            return self._to_dict(row)

    def set_localizacao(self, cinto_id: int, localizacao: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE cintos SET localizacao=? WHERE id=?", (localizacao, cinto_id))

    # ------------------------------------------------------------------ utils
    def _to_dict(self, row: sqlite3.Row) -> dict:
        d = {k: row[k] for k in row.keys()}
        d["antichama"] = bool(d.get("antichama"))
        # situacao do item: descartado (arquivado) / vencido / valido
        if d.get("arquivado"):
            d["situacao"] = "descartado"
        else:
            try:
                dv = datetime.strptime(d.get("data_validade", ""), "%d/%m/%Y").date()
                d["situacao"] = "vencido" if dv < date.today() else "valido"
            except Exception:
                d["situacao"] = "valido"
        # status da inspecao (baseado na ultima inspecao)
        # v1.84.0: NAO sobrescrever colunas reais — _to_dict tambem serve as
        # inspecoes; so preenche placeholders se a chave nao existir
        if "inspecao_status" not in d:
            d["inspecao_status"] = ""  # '' | 'proxima' | 'vencida' | 'ok'
        if "proxima_inspecao" not in d:
            d["proxima_inspecao"] = ""
        # v1.84.0: fabricacao/validade em mes-ano (armazenamos dia 01/mm/aaaa)
        try:
            dv = datetime.strptime(d.get("data_fabricacao", ""), "%d/%m/%Y")
            d["data_fabricacao_br"] = dv.strftime("%m/%Y")
        except Exception:
            d["data_fabricacao_br"] = d.get("data_fabricacao", "")
        d.setdefault("tipo", "cinto")
        d.setdefault("nome", "")
        d.setdefault("codigo", "")
        return d
