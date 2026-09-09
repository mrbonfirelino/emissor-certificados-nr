import sqlite3
from pathlib import Path
from datetime import date
from typing import Optional, List, Dict, Any
from src.utils.paths import get_db_path
from src.utils.text_utils import normalize_text


class IntegracaoRepository:
    """Empresas clientes (fabricas) e integracoes vinculadas a funcionarios (2.25).

    Integracao = autorizacao/credenciamento do funcionario junto a uma
    empresa cliente, com data de validade — sem geracao de certificado.
    Aparece no menu Vencimentos/dashboard/toast no mesmo formato dos
    certificados/ASOs (nr_code='INTEGRAÇÃO').
    """

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
                CREATE TABLE IF NOT EXISTS empresas_clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cnpj TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS integracoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    empresa_id INTEGER NOT NULL,
                    tipo TEXT DEFAULT '',
                    data_inicio TEXT DEFAULT '',
                    data_validade TEXT NOT NULL,
                    obs TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (empresa_id) REFERENCES empresas_clientes(id)
                );
                CREATE INDEX IF NOT EXISTS idx_integ_employee ON integracoes(employee_id);
                CREATE INDEX IF NOT EXISTS idx_integ_empresa ON integracoes(empresa_id);
                CREATE INDEX IF NOT EXISTS idx_integ_validade ON integracoes(data_validade);
            """)

    # --- Empresas clientes ---

    def add_empresa(self, nome: str, cnpj: str = "") -> int:
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Informe o nome da empresa")
        norm = normalize_text(nome)
        for emp in self.list_empresas():
            if normalize_text(emp["nome"]) == norm:
                raise ValueError(f"Empresa '{emp['nome']}' ja cadastrada")
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO empresas_clientes (nome, cnpj) VALUES (?, ?)",
                (nome, (cnpj or "").strip()),
            )
            return cur.lastrowid

    def update_empresa(self, empresa_id: int, nome: str, cnpj: str = "") -> bool:
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Informe o nome da empresa")
        norm = normalize_text(nome)
        for emp in self.list_empresas():
            if emp["id"] != empresa_id and normalize_text(emp["nome"]) == norm:
                raise ValueError(f"Empresa '{emp['nome']}' ja cadastrada")
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE empresas_clientes SET nome = ?, cnpj = ? WHERE id = ?",
                (nome, (cnpj or "").strip(), empresa_id),
            )
            return True

    def delete_empresa(self, empresa_id: int) -> bool:
        with self._get_conn() as conn:
            uso = conn.execute(
                "SELECT COUNT(*) FROM integracoes WHERE empresa_id = ?",
                (empresa_id,),
            ).fetchone()[0]
            if uso:
                raise ValueError(
                    f"Empresa em uso por {uso} integracao(oes) — remova-as primeiro"
                )
            conn.execute("DELETE FROM empresas_clientes WHERE id = ?", (empresa_id,))
            return True

    def count_integracoes_empresa(self, empresa_id: int) -> int:
        with self._get_conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM integracoes WHERE empresa_id = ?",
                (empresa_id,),
            ).fetchone()[0]

    def list_empresas(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM empresas_clientes ORDER BY nome COLLATE NOCASE"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_empresa(self, empresa_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM empresas_clientes WHERE id = ?", (empresa_id,)
            ).fetchone()
            return dict(row) if row else None

    # --- Integracoes ---

    @staticmethod
    def _validar_data(valor: str, campo: str, obrigatorio: bool = False):
        valor = (valor or "").strip()
        if not valor:
            if obrigatorio:
                raise ValueError(f"Informe a {campo.lower()} (dd/mm/aaaa convertida pelo app)")
            return None
        try:
            return date.fromisoformat(valor[:10]).isoformat()
        except (ValueError, TypeError):
            raise ValueError(f"{campo} inválida (use YYYY-MM-DD)")

    _LIST_COLS = """
        integracoes.id, integracoes.employee_id, integracoes.empresa_id,
        integracoes.tipo, integracoes.data_inicio, integracoes.data_validade,
        integracoes.obs, integracoes.created_at,
        xc.nome AS empresa_nome, xc.cnpj AS empresa_cnpj,
        e.nome AS funcionario_nome, e.cpf AS funcionario_cpf, e.funcao AS funcionario_funcao
    """

    def add_integracao(self, employee_id: int, empresa_id: int, tipo: str,
                       data_inicio: str, data_validade: str, obs: str = "") -> int:
        ini = self._validar_data(data_inicio, "Data de início", obrigatorio=False)
        val = self._validar_data(data_validade, "Data de validade", obrigatorio=True)
        with self._get_conn() as conn:
            cur = conn.execute("""
                INSERT INTO integracoes
                    (employee_id, empresa_id, tipo, data_inicio, data_validade, obs)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (employee_id, empresa_id, (tipo or "").strip(),
                  ini or "", val, (obs or "").strip()))
            return cur.lastrowid

    def update_integracao(self, integracao_id: int, employee_id: int = None,
                          empresa_id: int = None, tipo: str = None,
                          data_inicio: str = None, data_validade: str = None,
                          obs: str = None) -> bool:
        sets, params = [], []
        if employee_id is not None:
            sets.append("employee_id = ?")
            params.append(employee_id)
        if empresa_id is not None:
            sets.append("empresa_id = ?")
            params.append(empresa_id)
        if tipo is not None:
            sets.append("tipo = ?")
            params.append(tipo.strip())
        if data_inicio is not None:
            sets.append("data_inicio = ?")
            params.append(self._validar_data(data_inicio, "Data de início") or "")
        if data_validade is not None:
            sets.append("data_validade = ?")
            params.append(self._validar_data(data_validade, "Data de validade", obrigatorio=True))
        if obs is not None:
            sets.append("obs = ?")
            params.append(obs.strip())
        if not sets:
            return True
        params.append(integracao_id)
        with self._get_conn() as conn:
            conn.execute(f"UPDATE integracoes SET {', '.join(sets)} WHERE id = ?", params)
            return True

    def delete_integracao(self, integracao_id: int) -> bool:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM integracoes WHERE id = ?", (integracao_id,))
            return True

    def get_by_id(self, integracao_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(f"""
                SELECT {self._LIST_COLS}
                FROM integracoes
                LEFT JOIN empresas_clientes xc ON integracoes.empresa_id = xc.id
                LEFT JOIN employees e ON integracoes.employee_id = e.id
                WHERE integracoes.id = ?
            """, (integracao_id,)).fetchone()
            return dict(row) if row else None

    def get_by_employee(self, employee_id: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT {self._LIST_COLS}
                FROM integracoes
                LEFT JOIN empresas_clientes xc ON integracoes.empresa_id = xc.id
                LEFT JOIN employees e ON integracoes.employee_id = e.id
                WHERE integracoes.employee_id = ?
                ORDER BY integracoes.data_validade DESC, integracoes.id DESC
            """, (employee_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT {self._LIST_COLS}
                FROM integracoes
                LEFT JOIN empresas_clientes xc ON integracoes.empresa_id = xc.id
                LEFT JOIN employees e ON integracoes.employee_id = e.id
                ORDER BY integracoes.created_at DESC, integracoes.id DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            return [dict(r) for r in rows]

    def count_all(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM integracoes").fetchone()[0]

    def search(self, query: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        norm = normalize_text(query)
        like = f"%{norm}%"
        raw = f"%{query}%"
        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT {self._LIST_COLS}
                FROM integracoes
                LEFT JOIN empresas_clientes xc ON integracoes.empresa_id = xc.id
                LEFT JOIN employees e ON integracoes.employee_id = e.id
                WHERE normalize(e.nome) LIKE ? OR e.cpf LIKE ?
                   OR normalize(xc.nome) LIKE ? OR normalize(integracoes.tipo) LIKE ?
                ORDER BY integracoes.created_at DESC, integracoes.id DESC
                LIMIT ? OFFSET ?
            """, (like, raw, like, like, limit, offset)).fetchall()
            return [dict(r) for r in rows]

    def count_search(self, query: str) -> int:
        norm = normalize_text(query)
        like = f"%{norm}%"
        raw = f"%{query}%"
        with self._get_conn() as conn:
            return conn.execute("""
                SELECT COUNT(*) FROM integracoes
                LEFT JOIN empresas_clientes xc ON integracoes.empresa_id = xc.id
                LEFT JOIN employees e ON integracoes.employee_id = e.id
                WHERE normalize(e.nome) LIKE ? OR e.cpf LIKE ?
                   OR normalize(xc.nome) LIKE ? OR normalize(integracoes.tipo) LIKE ?
            """, (like, raw, like, like)).fetchone()[0]

    # --- Expiracao (formato certificados p/ vencimentos/dashboard/toast) ---

    def get_integracoes_with_expiration(self, only_latest: bool = True) -> List[Dict[str, Any]]:
        """Integracoes com validade calculada. only_latest=True mantem por
        (funcionario, empresa) apenas a integracao mais recente."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT i.*, xc.nome AS empresa_nome,
                       e.nome AS funcionario_nome, e.cpf AS funcionario_cpf,
                       e.funcao AS funcionario_funcao
                FROM integracoes i
                LEFT JOIN empresas_clientes xc ON i.empresa_id = xc.id
                LEFT JOIN employees e ON i.employee_id = e.id
                ORDER BY e.nome, xc.nome, i.data_validade, i.id
            """).fetchall()

        today = date.today()
        melhores: Dict[tuple, Dict[str, Any]] = {}
        todos: List[Dict[str, Any]] = []
        for row in rows:
            try:
                dv = date.fromisoformat(row["data_validade"])
            except (ValueError, TypeError):
                continue
            dias = (dv - today).days
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
            empresa = row["empresa_nome"] or "Empresa"
            tipo = (row["tipo"] or "").strip()
            descricao = f"{empresa} — {tipo}" if tipo else empresa
            item = {
                "id": row["id"],
                "cert_number": f"INT-{row['id']:06d}",
                "nr_code": "INTEGRAÇÃO",
                "nr_name": "Integração",
                "employee_id": row["employee_id"],
                "funcionario_nome": row["funcionario_nome"] or "",
                "funcionario_cpf": row["funcionario_cpf"] or "",
                "funcionario_funcao": row["funcionario_funcao"] or "",
                "data_inicio": row["data_inicio"],
                "data_fim": row["data_validade"],
                "descricao_treinamento": descricao,
                "empresa_nome": empresa,
                "empresa_id": row["empresa_id"],
                "tipo": tipo,
                "obs": row["obs"] or "",
                "data_validade": row["data_validade"],
                "dias_para_vencer": dias,
                "status": status,
            }
            todos.append(item)
            chave = (row["employee_id"], row["empresa_id"])
            atual = melhores.get(chave)
            if atual is None or (row["data_validade"], row["id"]) > (
                    atual["data_validade"], atual["id"]):
                melhores[chave] = item

        lista = list(melhores.values()) if only_latest else todos
        lista.sort(key=lambda c: (c["funcionario_nome"], c["nr_code"]))
        return lista
