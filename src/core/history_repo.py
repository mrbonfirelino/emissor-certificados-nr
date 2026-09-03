import sqlite3
import json
from pathlib import Path
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Dict, Any
from src.utils.paths import get_db_path
from src.core.models import CertificateRecord
from src.utils.text_utils import normalize_text


class HistoryRepository:
    """Repositorio de historico de certificados + numeracao sequencial."""

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
                CREATE TABLE IF NOT EXISTS certificates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cert_number TEXT UNIQUE NOT NULL,
                    nr_code TEXT NOT NULL,
                    employee_id INTEGER NOT NULL,
                    funcionario_nome TEXT NOT NULL,
                    funcionario_cpf TEXT NOT NULL,
                    data_inicio TEXT NOT NULL,
                    data_fim TEXT NOT NULL,
                    carga_horaria INTEGER NOT NULL,
                    descricao_treinamento TEXT NOT NULL,
                    campos_extra TEXT,
                    pdf_path TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_cert_number ON certificates(cert_number);
                CREATE INDEX IF NOT EXISTS idx_cert_employee ON certificates(employee_id);
                CREATE INDEX IF NOT EXISTS idx_cert_date ON certificates(data_fim);

                CREATE TABLE IF NOT EXISTS sequences (
                    name TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO sequences (name, value) VALUES ('certificate', 0);

                CREATE TABLE IF NOT EXISTS backup_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
            # documento assinado (escaneado) anexado ao certificado
            try:
                conn.execute("SELECT signed_doc FROM certificates LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE certificates ADD COLUMN signed_doc BLOB")
                conn.execute("ALTER TABLE certificates ADD COLUMN signed_doc_tipo TEXT")

    # colunas de listagem (BLOB signed_doc fica de fora: carga pesada)
    _LIST_COLS = """
        id, cert_number, nr_code, employee_id, funcionario_nome, funcionario_cpf,
        data_inicio, data_fim, carga_horaria, descricao_treinamento, campos_extra,
        pdf_path, created_at, (signed_doc IS NOT NULL) AS has_signed_doc
    """

    def next_certificate_number(self) -> str:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE sequences SET value = value + 1 WHERE name = 'certificate' RETURNING value"
            )
            row = cursor.fetchone()
            return f"CERT-{row[0]:06d}"

    def save(self, record: CertificateRecord) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO certificates (
                    cert_number, nr_code, employee_id, funcionario_nome, funcionario_cpf,
                    data_inicio, data_fim, carga_horaria, descricao_treinamento,
                    campos_extra, pdf_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.cert_number, record.nr_code, record.employee_id,
                record.funcionario_nome, record.funcionario_cpf,
                record.data_inicio, record.data_fim, record.carga_horaria,
                record.descricao_treinamento, record.campos_extra, record.pdf_path
            ))
            return cursor.lastrowid

    def get_all(self, limit: int = 10, offset: int = 0) -> List[CertificateRecord]:
        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT {self._LIST_COLS} FROM certificates ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            return [self._row_to_record(r) for r in rows]

    def count_all(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM certificates").fetchone()[0]

    def get_by_number(self, cert_number: str) -> Optional[CertificateRecord]:
        with self._get_conn() as conn:
            row = conn.execute(
                f"SELECT {self._LIST_COLS} FROM certificates WHERE cert_number = ?", (cert_number,)
            ).fetchone()
            return self._row_to_record(row) if row else None

    def get_by_employee(self, employee_id: int) -> List[CertificateRecord]:
        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT {self._LIST_COLS} FROM certificates WHERE employee_id = ? ORDER BY created_at DESC
            """, (employee_id,)).fetchall()
            return [self._row_to_record(r) for r in rows]

    def search(self, query: str, limit: int = 10, offset: int = 0) -> List[CertificateRecord]:
        """Busca por nome, CPF, numero ou NR (ignora acentos)."""
        return self.query(query=query, limit=limit, offset=offset)

    def count_search(self, query: str) -> int:
        """Conta resultados de busca."""
        return self.count_query(query=query)

    def distinct_nrs(self) -> List[str]:
        """NRs distintos presentes no historico (para filtro da listagem)."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT nr_code FROM certificates ORDER BY nr_code"
            ).fetchall()
            return [r[0] for r in rows]

    def _build_filters(self, query: str, nr_code: Optional[str],
                       data_de: Optional[str], data_ate: Optional[str],
                       assinado: Optional[str] = None) -> tuple:
        where, params = [], []
        q = (query or "").strip()
        if q:
            norm = normalize_text(q)
            like = f"%{norm}%"
            where.append("""(
                normalize(funcionario_nome) LIKE ?
                OR funcionario_cpf LIKE ?
                OR normalize(cert_number) LIKE ?
                OR nr_code LIKE ?
            )""")
            params += [like, f"%{q}%", like, f"%{q}%"]
        if nr_code:
            where.append("nr_code = ?")
            params.append(nr_code)
        if data_de:
            where.append("data_fim >= ?")
            params.append(data_de)
        if data_ate:
            where.append("data_fim <= ?")
            params.append(data_ate)
        if assinado == "sim":
            where.append("(signed_doc IS NOT NULL) = 1")
        elif assinado == "nao":
            where.append("(signed_doc IS NOT NULL) = 0")
        return where, params

    def query(self, query: str = "", nr_code: Optional[str] = None,
              data_de: Optional[str] = None, data_ate: Optional[str] = None,
              assinado: Optional[str] = None,
              limit: int = 10, offset: int = 0) -> List[CertificateRecord]:
        """Busca combinada: texto (nome/CPF/numero/NR) + NR exata + periodo por
        data_fim (ISO) + assinado ('sim'/'nao'/None)."""
        where, params = self._build_filters(query, nr_code, data_de, data_ate, assinado)
        sql = f"SELECT {self._LIST_COLS} FROM certificates"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params + [limit, offset]).fetchall()
            return [self._row_to_record(r) for r in rows]

    def count_query(self, query: str = "", nr_code: Optional[str] = None,
                    data_de: Optional[str] = None, data_ate: Optional[str] = None,
                    assinado: Optional[str] = None) -> int:
        """Conta resultados da busca combinada."""
        where, params = self._build_filters(query, nr_code, data_de, data_ate, assinado)
        sql = "SELECT COUNT(*) FROM certificates"
        if where:
            sql += " WHERE " + " AND ".join(where)
        with self._get_conn() as conn:
            return conn.execute(sql, params).fetchone()[0]

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Indicadores para o painel da tela inicial."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM certificates").fetchone()[0]
            assinados = conn.execute(
                "SELECT COUNT(*) FROM certificates WHERE signed_doc IS NOT NULL"
            ).fetchone()[0]
            por_nr = conn.execute("""
                SELECT nr_code, COUNT(*) AS n FROM certificates
                GROUP BY nr_code ORDER BY n DESC, nr_code ASC LIMIT 5
            """).fetchall()
            por_mes = conn.execute("""
                SELECT substr(data_fim, 1, 7) AS mes, COUNT(*) AS n FROM certificates
                GROUP BY mes ORDER BY mes DESC LIMIT 6
            """).fetchall()

        vencidos = vencer_7 = vencer_30 = 0
        try:
            certs = self.get_certificates_with_expiration()
            for c in certs:
                d = c["dias_para_vencer"]
                if d < 0:
                    vencidos += 1
                elif d <= 7:
                    vencer_7 += 1
                elif d <= 30:
                    vencer_30 += 1
        except Exception:
            pass

        return {
            "total": total,
            "assinados": assinados,
            "por_nr": [(r["nr_code"], r["n"]) for r in por_nr],
            "por_mes": [(r["mes"], r["n"]) for r in por_mes],
            "vencidos": vencidos,
            "vencer_7": vencer_7,
            "vencer_30": vencer_30,
        }

    def count_total(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM certificates").fetchone()[0]

    def _row_to_record(self, row: sqlite3.Row) -> CertificateRecord:
        try:
            has_signed = bool(row["has_signed_doc"])
        except (IndexError, KeyError):
            has_signed = False
        return CertificateRecord(
            id=row["id"],
            cert_number=row["cert_number"],
            nr_code=row["nr_code"],
            employee_id=row["employee_id"],
            funcionario_nome=row["funcionario_nome"],
            funcionario_cpf=row["funcionario_cpf"],
            data_inicio=row["data_inicio"],
            data_fim=row["data_fim"],
            carga_horaria=row["carga_horaria"],
            descricao_treinamento=row["descricao_treinamento"],
            campos_extra=row["campos_extra"] or "{}",
            pdf_path=row["pdf_path"],
            created_at=row["created_at"],
            has_signed_doc=has_signed
        )

    # --- Documento assinado (escaneado) ---

    SIGNED_DOC_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    SIGNED_DOC_TIPOS = {"pdf", "jpg", "jpeg", "png"}

    def attach_signed_doc(self, cert_id: int, data: bytes, tipo: str) -> bool:
        """Anexa (ou substitui) o documento assinado. tipo: pdf|jpg|jpeg|png."""
        tipo = (tipo or "").lower().strip()
        if tipo not in self.SIGNED_DOC_TIPOS:
            raise ValueError(f"Formato invalido: {tipo} (aceitos: PDF, JPG, PNG)")
        if len(data) > self.SIGNED_DOC_MAX_BYTES:
            raise ValueError("Arquivo maior que 10MB")
        if tipo == "jpeg":
            tipo = "jpg"
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE certificates SET signed_doc = ?, signed_doc_tipo = ? WHERE id = ?",
                (data, tipo, cert_id)
            )
            return True

    def get_signed_doc(self, cert_id: int) -> Optional[tuple]:
        """Retorna (bytes, tipo) do documento assinado ou None."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT signed_doc, signed_doc_tipo FROM certificates WHERE id = ?", (cert_id,)
            ).fetchone()
            if row and row["signed_doc"]:
                return row["signed_doc"], (row["signed_doc_tipo"] or "pdf")
            return None

    def remove_signed_doc(self, cert_id: int) -> bool:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE certificates SET signed_doc = NULL, signed_doc_tipo = NULL WHERE id = ?",
                (cert_id,)
            )
            return True

    def get_certificates_with_expiration(self) -> List[Dict[str, Any]]:
        from src.core.template_loader import load_all_templates
        templates = load_all_templates()
        today = date.today()

        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT c.*, e.funcao
                FROM certificates c
                LEFT JOIN employees e ON c.employee_id = e.id
                ORDER BY c.funcionario_nome, c.nr_code
            """).fetchall()

        results = []
        for row in rows:
            nr_code = row["nr_code"]
            tmpl = templates.get(nr_code)
            validade_meses = tmpl.validade_meses if tmpl else 12
            data_fim = date.fromisoformat(row["data_fim"])
            data_validade = data_fim + relativedelta(months=validade_meses)
            dias_para_vencer = (data_validade - today).days

            if dias_para_vencer < 0:
                status = "vencido"
            elif dias_para_vencer <= 7:
                status = "urgente"
            elif dias_para_vencer <= 15:
                status = "critico"
            elif dias_para_vencer <= 30:
                status = "atencao"
            elif dias_para_vencer <= 90:
                status = "proximo"
            else:
                status = "ok"

            results.append({
                "id": row["id"],
                "cert_number": row["cert_number"],
                "nr_code": nr_code,
                "nr_name": tmpl.nr_name if tmpl else nr_code,
                "employee_id": row["employee_id"],
                "funcionario_nome": row["funcionario_nome"],
                "funcionario_cpf": row["funcionario_cpf"],
                "funcionario_funcao": row["funcao"] if row["funcao"] else "",
                "data_inicio": row["data_inicio"],
                "data_fim": row["data_fim"],
                "carga_horaria": row["carga_horaria"],
                "descricao_treinamento": row["descricao_treinamento"],
                "validade_meses": validade_meses,
                "data_validade": data_validade.isoformat(),
                "dias_para_vencer": dias_para_vencer,
                "status": status,
            })

        return results

    # --- Backup meta ---
    def set_backup_meta(self, key: str, value: str):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO backup_meta (key, value) VALUES (?, ?)",
                (key, value)
            )

    def get_backup_meta(self, key: str) -> Optional[str]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT value FROM backup_meta WHERE key = ?", (key,)).fetchone()
            return row[0] if row else None
