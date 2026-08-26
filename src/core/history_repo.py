import sqlite3
import json
from pathlib import Path
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Dict, Any
from src.utils.paths import get_db_path
from src.core.models import CertificateRecord


class HistoryRepository:
    """Repositório de histórico de certificados + numeração sequencial."""

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

    def next_certificate_number(self) -> str:
        """Gera próximo número sequencial: CERT-000001"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE sequences SET value = value + 1 WHERE name = 'certificate' RETURNING value"
            )
            row = cursor.fetchone()
            return f"CERT-{row[0]:06d}"

    def save(self, record: CertificateRecord) -> int:
        """Salva certificado no histórico. Retorna ID."""
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

    def get_all(self, limit: int = 100, offset: int = 0) -> List[CertificateRecord]:
        """Lista certificados (mais recentes primeiro)."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM certificates ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            return [self._row_to_record(r) for r in rows]

    def get_by_number(self, cert_number: str) -> Optional[CertificateRecord]:
        """Busca certificado pelo número."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM certificates WHERE cert_number = ?", (cert_number,)
            ).fetchone()
            return self._row_to_record(row) if row else None

    def get_by_employee(self, employee_id: int) -> List[CertificateRecord]:
        """Certificados de um funcionário."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM certificates WHERE employee_id = ? ORDER BY created_at DESC
            """, (employee_id,)).fetchall()
            return [self._row_to_record(r) for r in rows]

    def search(self, query: str, limit: int = 50) -> List[CertificateRecord]:
        """Busca por nome, CPF, número ou NR."""
        with self._get_conn() as conn:
            like = f"%{query}%"
            rows = conn.execute("""
                SELECT * FROM certificates 
                WHERE cert_number LIKE ? OR funcionario_nome LIKE ? 
                   OR funcionario_cpf LIKE ? OR nr_code LIKE ?
                ORDER BY created_at DESC LIMIT ?
            """, (like, like, like, like, limit)).fetchall()
            return [self._row_to_record(r) for r in rows]

    def count_total(self) -> int:
        """Total de certificados emitidos."""
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM certificates").fetchone()[0]

    def _row_to_record(self, row: sqlite3.Row) -> CertificateRecord:
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
            created_at=row["created_at"]
        )

    def get_certificates_with_expiration(self) -> List[Dict[str, Any]]:
        """Retorna todos certificados com data_validade e dias_para_vencer calculados."""
        from src.core.template_loader import load_all_templates
        templates = load_all_templates()
        today = date.today()

        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM certificates ORDER BY funcionario_nome, nr_code
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