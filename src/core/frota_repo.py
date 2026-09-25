"""Repositorio da Gestao de Frota (ROADMAP 2.29).

Tabelas: frota_veiculos, frota_veic_empresas, frota_fornecedores,
frota_veic_docs (pasta virtual, espelho de employee_docs),
frota_veic_laudos (com vencimento — entram no menu Vencimentos),
frota_movimentacoes (saida/entrada) e frota_abastecimentos.
"""

import json
import re
import sqlite3
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from src.utils.paths import get_db_path
from src.utils.text_utils import normalize_text


TIPOS_VEICULO = [
    ("caminhao", "Caminhão"),
    ("pickup", "Pickup"),
    ("carro", "Carro"),
    ("van", "Van"),
    ("empilhadeira", "Empilhadeira"),
    ("retroescavadeira", "Retroescavadeira"),
    ("outros", "Outros"),
]

SUBTIPOS_CAMINHAO = [
    ("cacamba", "Caçamba"),
    ("munck", "Munck"),
    ("plataforma", "Plataforma"),
]

TIPOS_COMBUSTIVEL = [
    ("gasolina", "Gasolina"),
    ("alcool", "Álcool"),
    ("diesel", "Diesel"),
    ("arla", "Arla"),
    ("gnv", "GNV"),
    ("arla_diesel", "ARLA + DIESEL"),
    ("outros", "Outros / Ferramentas"),
]

TIPOS_LAUDO = [
    ("certificado_final", "Certificado Final"),
    ("crlv", "CRLV"),
    ("fumaca_preta", "Fumaça Preta"),
    ("laudo_avaliacao", "Laudo de Avaliação"),
    ("laudo_eletromecanico", "Laudo Eletromecânico"),
    ("plano_manutencao", "Plano de Manutenção"),
    ("seguro", "Seguro"),
    ("outro", "Outro"),
]

# tipos SEM placa (2.29.1: nao possuem placa)
SEM_PLACA = {"empilhadeira", "retroescavadeira"}

CARROCERIAS = [
    ("hatch", "Hatch"),
    ("sedan", "Sedan"),
]

# 2.29.5 — itens do checklist semanal de veiculos leves (layout do papel ALTEC)
CHECKLIST_GRUPOS = [
    ("1", "1 - O funcionamento está em Ordem?", [
        ("1.1", "Bateria"), ("1.2", "Radiador"), ("1.3", "Freios"),
        ("1.4", "Direção"), ("1.5", "Buzina"), ("1.6", "Retrovisores"),
        ("1.7", "Faróis"), ("1.8", "Pneus Dianteiros"),
        ("1.9", "Pneus Traseiros"), ("1.10", "Estepe"),
        ("1.11", "Rodas"), ("1.12", "Para Brisa"),
        ("1.13", "Freio de Estacionamento"),
        ("1.14", "Limpador de Para Brisas"), ("1.15", "Combustível"),
        ("1.16", "Água do Limpador"), ("1.17", "Trava do Capô"),
        ("1.18", "Painel Elétrico (Velocímetro)"),
        ("1.19", "Avaria de Pintura"),
    ]),
    ("2", "2 - Os itens abaixo estão no nível?", [
        ("2.1", "Nível água do Radiador"), ("2.2", "Nível do óleo do Motor"),
        ("2.3", "Carga da Bateria"), ("2.4", "Filtro de Óleo"),
        ("2.5", "Pressão dos Pneus"), ("2.6", "Purificador de Ar"),
        ("2.7", "Nível do óleo hidráulico"), ("2.8", "Lubrificação"),
        ("2.9", "Limpeza geral"),
    ]),
    ("3", "3. Segurança do Trabalho", [
        ("3.1", "Carteira de Habilitação"), ("3.2", "Doc. do Veículo"),
        ("3.3", "Direção Defensiva"), ("3.4", "Cintos de Segurança"),
        ("3.5", "Extintor de Incêndio"),
        ("3.6", "Equipamentos de Segurança"),
    ]),
]

CHECKLIST_DIAS = ["2ª", "3ª", "4ª", "5ª", "6ª", "sab"]


def _label(tuplas, valor):
    for cod, rot in tuplas:
        if cod == valor:
            return rot
    return valor or ""


def label_tipo(tipo):
    return _label(TIPOS_VEICULO, tipo)


def label_subtipo(sub):
    return _label(SUBTIPOS_CAMINHAO, sub)


def label_combustivel(c):
    return _label(TIPOS_COMBUSTIVEL, c)


def rotulo_revisao(rev) -> str:
    """0 -> '', 1 -> 'REV_A', 2 -> 'REV_B' ... 27 -> 'REV_AA'."""
    if not rev:
        return ""
    r = int(rev)
    letras = ""
    while r > 0:
        r, resto = divmod(r - 1, 26)
        letras = chr(65 + resto) + letras
    return f"REV_{letras}"


def _extras_pack(extras) -> tuple:
    """Normaliza a lista de itens extras (2.35.2) para (json_str, total).

    Cada item aceita {'desc': str, 'qtd': str, 'valor': float}; itens sem
    descricao E sem valor sao descartados. Devolve ('[]', 0.0) quando vazio.
    """
    limpos = []
    total = 0.0
    for it in (extras or []):
        if not isinstance(it, dict):
            continue
        desc = str(it.get("desc") or "").strip()
        qtd = str(it.get("qtd") or "").strip()
        try:
            valor = float(str(it.get("valor") or "").replace(",", "."))
        except (TypeError, ValueError):
            valor = None
        if valor is not None and valor < 0:
            valor = None
        if not desc and valor is None:
            continue
        if valor is not None:
            total += valor
        limpos.append({"desc": desc, "qtd": qtd,
                       "valor": round(valor, 2) if valor is not None else None})
    return json.dumps(limpos, ensure_ascii=False), round(total, 2)


def label_laudo(t):
    return _label(TIPOS_LAUDO, t)


def veiculo_rotulo(v: dict) -> str:
    """Rotulo curto do veiculo para listas: 'Fiat Strada ABC1D23'."""
    partes = [p for p in (v.get("marca"), v.get("modelo")) if p]
    base = " ".join(partes) or "Veículo"
    placa = v.get("placa")
    return f"{base} {placa}" if placa else base


class FrotaRepository:
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
                CREATE TABLE IF NOT EXISTS frota_veic_empresas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cnpj TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS frota_fornecedores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cnpj TEXT,
                    endereco TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS frota_veiculos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    modelo TEXT NOT NULL,
                    marca TEXT,
                    tipo TEXT NOT NULL,
                    subtipo TEXT,
                    placa TEXT,
                    proprio INTEGER NOT NULL DEFAULT 1,
                    contratante TEXT,
                    empresa_id INTEGER,
                    obs TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (empresa_id) REFERENCES frota_veic_empresas(id)
                );
                CREATE INDEX IF NOT EXISTS idx_frota_veic_empresa
                    ON frota_veiculos(empresa_id);

                CREATE TABLE IF NOT EXISTS frota_veic_docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    veiculo_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    tamanho INTEGER NOT NULL DEFAULT 0,
                    dados BLOB,
                    tag TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (veiculo_id) REFERENCES frota_veiculos(id)
                );
                CREATE INDEX IF NOT EXISTS idx_frotadocs_veic
                    ON frota_veic_docs(veiculo_id);

                CREATE TABLE IF NOT EXISTS frota_veic_laudos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    veiculo_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    descricao TEXT,
                    filename TEXT NOT NULL,
                    tipo_arquivo TEXT,
                    tamanho INTEGER NOT NULL DEFAULT 0,
                    dados BLOB,
                    data_emissao TEXT,
                    data_validade TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (veiculo_id) REFERENCES frota_veiculos(id)
                );
                CREATE INDEX IF NOT EXISTS idx_frotalaudo_veic
                    ON frota_veic_laudos(veiculo_id);

                CREATE TABLE IF NOT EXISTS frota_movimentacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    veiculo_id INTEGER NOT NULL,
                    data_saida TEXT NOT NULL,
                    hora_saida TEXT NOT NULL,
                    km_inicial INTEGER NOT NULL,
                    destino TEXT,
                    motivo TEXT,
                    obs TEXT,
                    motorista TEXT,
                    autorizado_por TEXT,
                    data_entrada TEXT,
                    hora_entrada TEXT,
                    km_final INTEGER,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (veiculo_id) REFERENCES frota_veiculos(id)
                );
                CREATE INDEX IF NOT EXISTS idx_frotamov_veic
                    ON frota_movimentacoes(veiculo_id);

                CREATE TABLE IF NOT EXISTS frota_abastecimentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial TEXT UNIQUE NOT NULL,
                    veiculo_id INTEGER NOT NULL,
                    fornecedor_id INTEGER,
                    combustivel TEXT NOT NULL,
                    data TEXT NOT NULL,
                    viagem_servico TEXT,
                    km INTEGER,
                    condutor TEXT,
                    superior TEXT,
                    obs TEXT,
                    pdf_path TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (veiculo_id) REFERENCES frota_veiculos(id),
                    FOREIGN KEY (fornecedor_id) REFERENCES frota_fornecedores(id)
                );
                CREATE INDEX IF NOT EXISTS idx_frotaabast_veic
                    ON frota_abastecimentos(veiculo_id);

                CREATE TABLE IF NOT EXISTS frota_abast_nfs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    abastecimento_id INTEGER NOT NULL,
                    numero TEXT,
                    data TEXT,
                    valor REAL,
                    filename TEXT NOT NULL,
                    tipo_arquivo TEXT,
                    tamanho INTEGER NOT NULL DEFAULT 0,
                    dados BLOB,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (abastecimento_id)
                        REFERENCES frota_abastecimentos(id)
                );
                CREATE INDEX IF NOT EXISTS idx_frotanf_abast
                    ON frota_abast_nfs(abastecimento_id);

                CREATE TABLE IF NOT EXISTS frota_checklists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial TEXT UNIQUE NOT NULL,
                    veiculo_id INTEGER NOT NULL,
                    data_inicial TEXT NOT NULL,
                    data_final TEXT NOT NULL,
                    km_rodado INTEGER,
                    placa TEXT,
                    motorista TEXT,
                    lider TEXT,
                    pode_operar TEXT,
                    itens TEXT,
                    observacoes TEXT,
                    pdf_path TEXT,
                    criado_por TEXT,
                    assinado_dados BLOB,
                    assinado_tipo TEXT,
                    assinado_filename TEXT,
                    assinado_em TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (veiculo_id) REFERENCES frota_veiculos(id)
                );
                CREATE INDEX IF NOT EXISTS idx_frotachk_veic
                    ON frota_checklists(veiculo_id);

                CREATE TABLE IF NOT EXISTS frota_manutencoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    veiculo_id INTEGER NOT NULL,
                    descricao TEXT NOT NULL,
                    intervalo_km INTEGER NOT NULL,
                    km_ultima INTEGER NOT NULL DEFAULT 0,
                    data_ultima TEXT,
                    obs TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (veiculo_id) REFERENCES frota_veiculos(id)
                );
                CREATE INDEX IF NOT EXISTS idx_frotamanut_veic
                    ON frota_manutencoes(veiculo_id);
            """)
            self._migrar(conn)

    def _migrar(self, conn: sqlite3.Connection):
        """Colunas novas (v1.34.0) com ALTER TABLE idempotente."""
        veic = {r[1] for r in conn.execute(
            "PRAGMA table_info(frota_veiculos)").fetchall()}
        for col, ddl in (
            ("cor", "TEXT"), ("carroceria", "TEXT"), ("ano", "TEXT"),
            ("fim_contrato_aluguel", "TEXT"), ("foto", "BLOB"),
            ("foto_tipo", "TEXT"), ("km_l_esperado", "REAL"),
        ):
            if col not in veic:
                conn.execute(f"ALTER TABLE frota_veiculos ADD COLUMN {col} {ddl}")
        abast = {r[1] for r in conn.execute(
            "PRAGMA table_info(frota_abastecimentos)").fetchall()}
        for col, ddl in (("litros", "REAL"), ("valor", "REAL"),
                         ("revisao", "INTEGER DEFAULT 0"),
                         ("assinado_dados", "BLOB"), ("assinado_tipo", "TEXT"),
                         ("assinado_filename", "TEXT"),
                         ("assinado_em", "TEXT"),
                         ("extras", "TEXT"), ("extras_total", "REAL"),
                         ("tmp_fornecedor", "TEXT"), ("tmp_cnpj", "TEXT"),
                         ("status", "TEXT"), ("motivo_status", "TEXT"),
                         ("status_em", "TEXT"), ("status_por", "TEXT")):
            if col not in abast:
                conn.execute(f"ALTER TABLE frota_abastecimentos ADD COLUMN {col} {ddl}")
        docs_t = {r[1] for r in conn.execute(
            "PRAGMA table_info(frota_veic_docs)").fetchall()}
        if "tag" not in docs_t:
            conn.execute("ALTER TABLE frota_veic_docs ADD COLUMN tag TEXT")
        chk_t = {r[1] for r in conn.execute(
            "PRAGMA table_info(frota_checklists)").fetchall()}
        for col, ddl in (("assinado_dados", "BLOB"), ("assinado_tipo", "TEXT"),
                         ("assinado_filename", "TEXT"), ("assinado_em", "TEXT")):
            if col not in chk_t:
                conn.execute(f"ALTER TABLE frota_checklists ADD COLUMN {col} {ddl}")
        # v1.53.0: backfill — extras com JSON gravado mas extras_total NULL
        # (registros criados antes da v1.48 não entravam nos relatórios de custo)
        for r in conn.execute(
            "SELECT id, extras FROM frota_abastecimentos"
            " WHERE extras IS NOT NULL AND TRIM(extras) NOT IN ('', '[]')"
            " AND extras_total IS NULL").fetchall():
            try:
                itens = json.loads(r["extras"])
            except Exception:
                continue
            if not isinstance(itens, list):
                continue
            tot = 0.0
            for e in itens:
                if not isinstance(e, dict):
                    continue
                try:
                    v = float(str(e.get("valor", "")).replace(",", ".") or 0)
                except ValueError:
                    v = 0.0
                try:
                    q = float(str(e.get("qtd", "")).replace(",", ".") or 1)
                except ValueError:
                    q = 1.0
                if v > 0:
                    tot += v * (q if q > 0 else 1)
            if tot > 0:
                conn.execute(
                    "UPDATE frota_abastecimentos SET extras_total=? WHERE id=?",
                    (round(tot, 2), r["id"]))
        # v1.53.0: normalizar datas não-ISO (ex. dd/mm/aaaa gravadas fora do
        # sistema) — sem isso o registro sumia das séries/relatórios de custo
        for r in conn.execute(
            "SELECT id, data FROM frota_abastecimentos"
            " WHERE data IS NOT NULL").fetchall():
            d = (r["data"] or "").strip()
            m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", d)
            if m:
                iso = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            elif re.match(r"^\d{4}-\d{2}-\d{2}$", d):
                continue
            else:
                try:
                    iso = date.fromisoformat(d).isoformat()
                except ValueError:
                    continue
            conn.execute(
                "UPDATE frota_abastecimentos SET data=? WHERE id=?",
                (iso, r["id"]))

    # ---------- veiculos ----------

    def _validar_veiculo(self, modelo, tipo, placa, proprio,
                         contratante, subtipo, carroceria=None,
                         fim_contrato=None):
        if not (modelo or "").strip():
            raise ValueError("Informe o modelo do veículo.")
        if tipo not in dict(TIPOS_VEICULO):
            raise ValueError("Tipo de veículo inválido.")
        if tipo == "caminhao" and not subtipo:
            raise ValueError("Selecione o subtipo do caminhão.")
        if tipo != "caminhao":
            subtipo = None
        placa = (placa or "").strip().upper() or None
        if tipo in SEM_PLACA:
            if placa:
                raise ValueError(
                    f"{label_tipo(tipo)} não possui placa — deixe o campo vazio.")
            placa = None
        elif not placa:
            raise ValueError(
                f"Placa obrigatória para {label_tipo(tipo)}.")
        if not proprio and not (contratante or "").strip():
            raise ValueError(
                "Veículo alugado: informe o nome de quem contratou.")
        if proprio:
            contratante = None
            fim_contrato = None
        # carroceria: apenas para carros
        if tipo != "carro":
            carroceria = None
        elif carroceria and carroceria not in dict(CARROCERIAS):
            raise ValueError("Carroceria inválida (use hatch ou sedan).")
        if fim_contrato:
            try:
                fim_contrato = date.fromisoformat(fim_contrato).isoformat()
            except (TypeError, ValueError):
                raise ValueError("Data de fim do contrato inválida.")
        return placa, contratante or None, subtipo, carroceria or None, \
            fim_contrato or None

    def add_veiculo(self, modelo: str, marca: str, tipo: str, subtipo: str,
                    placa: str, proprio: bool, contratante: str,
                    empresa_id: Optional[int], obs: str = "",
                    cor: str = "", carroceria: str = "", ano: str = "",
                    fim_contrato_aluguel: str = "",
                    km_l_esperado: Optional[float] = None) -> int:
        placa, contratante, subtipo, carroceria, fim_contrato = \
            self._validar_veiculo(
                modelo, tipo, placa, proprio, contratante, subtipo,
                carroceria, fim_contrato_aluguel)
        if empresa_id is not None and not self.get_empresa(empresa_id):
            empresa_id = None
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO frota_veiculos (modelo, marca, tipo, subtipo, placa,"
                " proprio, contratante, empresa_id, obs, cor, carroceria, ano,"
                " fim_contrato_aluguel, km_l_esperado)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (modelo.strip(), (marca or "").strip(), tipo, subtipo, placa,
                 1 if proprio else 0, contratante, empresa_id,
                 (obs or "").strip() or None, (cor or "").strip() or None,
                 carroceria, (ano or "").strip() or None, fim_contrato,
                 km_l_esperado))
            return cur.lastrowid

    def update_veiculo(self, veiculo_id: int, modelo: str, marca: str,
                       tipo: str, subtipo: str, placa: str, proprio: bool,
                       contratante: str, empresa_id: Optional[int],
                       obs: str = "", cor: str = "", carroceria: str = "",
                       ano: str = "", fim_contrato_aluguel: str = "",
                       km_l_esperado: Optional[float] = None) -> bool:
        placa, contratante, subtipo, carroceria, fim_contrato = \
            self._validar_veiculo(
                modelo, tipo, placa, proprio, contratante, subtipo,
                carroceria, fim_contrato_aluguel)
        if empresa_id is not None and not self.get_empresa(empresa_id):
            empresa_id = None
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_veiculos SET modelo=?, marca=?, tipo=?, subtipo=?,"
                " placa=?, proprio=?, contratante=?, empresa_id=?, obs=?, cor=?,"
                " carroceria=?, ano=?, fim_contrato_aluguel=?, km_l_esperado=?"
                " WHERE id=?",
                (modelo.strip(), (marca or "").strip(), tipo, subtipo, placa,
                 1 if proprio else 0, contratante, empresa_id,
                 (obs or "").strip() or None, (cor or "").strip() or None,
                 carroceria, (ano or "").strip() or None, fim_contrato,
                 km_l_esperado, veiculo_id))
            return cur.rowcount > 0

    def update_foto(self, veiculo_id: int, data: bytes, tipo: str) -> bool:
        if not data:
            raise ValueError("Selecione uma imagem.")
        if len(data) > 10 * 1024 * 1024:
            raise ValueError("Imagem maior que 10MB.")
        if tipo not in ("jpg", "png", "gif", "webp"):
            tipo = "jpg"
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_veiculos SET foto=?, foto_tipo=? WHERE id=?",
                (sqlite3.Binary(data), tipo, veiculo_id))
            return cur.rowcount > 0

    def get_foto(self, veiculo_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT foto, foto_tipo FROM frota_veiculos WHERE id=?",
                (veiculo_id,)).fetchone()
        if not row or not row["foto"]:
            return None
        return {"dados": bytes(row["foto"]),
                "tipo": row["foto_tipo"] or "jpg"}

    def get_veiculo(self, veiculo_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT v.*, e.nome AS empresa_nome FROM frota_veiculos v"
                " LEFT JOIN frota_veic_empresas e ON v.empresa_id = e.id"
                " WHERE v.id=?", (veiculo_id,)).fetchone()
        return dict(row) if row else None

    def list_veiculos(self, busca: str = "",
                      limit: int = 500, offset: int = 0):
        q = f"%{(busca or '').strip().lower()}%"
        where = ""
        params: list = []
        if busca and busca.strip():
            where = ("WHERE lower(coalesce(v.modelo,''))||' '||"
                     "lower(coalesce(v.marca,''))||' '||"
                     "lower(coalesce(v.placa,''))||' '||"
                     "lower(coalesce(e.nome,''))||' '||"
                     "lower(coalesce(v.cor,''))||' '||"
                     "lower(coalesce(v.ano,'')) LIKE ?")
            params.append(q)
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT v.*, e.nome AS empresa_nome,"
                f" (v.foto IS NOT NULL) AS tem_foto"
                f" FROM frota_veiculos v"
                f" LEFT JOIN frota_veic_empresas e ON v.empresa_id = e.id"
                f" {where} ORDER BY v.modelo, v.marca LIMIT ? OFFSET ?",
                params + [limit, offset]).fetchall()
            total = conn.execute(
                f"SELECT COUNT(*) FROM frota_veiculos v"
                f" LEFT JOIN frota_veic_empresas e ON v.empresa_id = e.id"
                f" {where}", params).fetchone()[0]
        return [dict(r) for r in rows], total

    def count_veiculos(self) -> int:
        with self._get_conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM frota_veiculos").fetchone()[0]

    def delete_veiculo(self, veiculo_id: int) -> bool:
        """Exclui o veiculo e seus registros vinculados."""
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM frota_abast_nfs WHERE abastecimento_id IN"
                " (SELECT id FROM frota_abastecimentos WHERE veiculo_id=?)",
                (veiculo_id,))
            for tabela, col in (("frota_veic_docs", "veiculo_id"),
                                ("frota_veic_laudos", "veiculo_id"),
                                ("frota_movimentacoes", "veiculo_id"),
                                ("frota_abastecimentos", "veiculo_id"),
                                ("frota_checklists", "veiculo_id"),
                                ("frota_manutencoes", "veiculo_id")):
                conn.execute(
                    f"DELETE FROM {tabela} WHERE {col}=?", (veiculo_id,))
            cur = conn.execute(
                "DELETE FROM frota_veiculos WHERE id=?", (veiculo_id,))
            return cur.rowcount > 0

    # ---------- empresas (veiculos) ----------

    def add_empresa(self, nome: str, cnpj: str = "") -> int:
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Informe o nome da empresa.")
        if self.get_empresa_por_nome(nome):
            raise ValueError(f"Empresa '{nome}' já está cadastrada.")
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO frota_veic_empresas (nome, cnpj) VALUES (?,?)",
                (nome, (cnpj or "").strip() or None))
            return cur.lastrowid

    def update_empresa(self, empresa_id: int, nome: str,
                       cnpj: str = "") -> bool:
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Informe o nome da empresa.")
        dup = self.get_empresa_por_nome(nome)
        if dup and dup["id"] != empresa_id:
            raise ValueError(f"Empresa '{nome}' já está cadastrada.")
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_veic_empresas SET nome=?, cnpj=? WHERE id=?",
                (nome, (cnpj or "").strip() or None, empresa_id))
            return cur.rowcount > 0

    def delete_empresa(self, empresa_id: int) -> bool:
        with self._get_conn() as conn:
            usos = conn.execute(
                "SELECT COUNT(*) FROM frota_veiculos WHERE empresa_id=?",
                (empresa_id,)).fetchone()[0]
            if usos:
                raise ValueError(
                    f"Não é possível excluir: {usos} veículo(s) usam esta empresa.")
            cur = conn.execute(
                "DELETE FROM frota_veic_empresas WHERE id=?", (empresa_id,))
            return cur.rowcount > 0

    def list_empresas(self) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT e.*, (SELECT COUNT(*) FROM frota_veiculos v"
                " WHERE v.empresa_id = e.id) AS veiculos"
                " FROM frota_veic_empresas e ORDER BY nome").fetchall()
        return [dict(r) for r in rows]

    def get_empresa(self, empresa_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM frota_veic_empresas WHERE id=?",
                (empresa_id,)).fetchone()
        return dict(row) if row else None

    def get_empresa_por_nome(self, nome: str) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM frota_veic_empresas WHERE normalize(nome)=?",
                (normalize_text((nome or "").strip()),)).fetchone()
        return dict(row) if row else None

    # ---------- fornecedores ----------

    def add_fornecedor(self, nome: str, cnpj: str = "",
                       endereco: str = "") -> int:
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Informe o nome do fornecedor.")
        if self.get_fornecedor_por_nome(nome):
            raise ValueError(f"Fornecedor '{nome}' já está cadastrado.")
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO frota_fornecedores (nome, cnpj, endereco)"
                " VALUES (?,?,?)",
                (nome, (cnpj or "").strip() or None,
                 (endereco or "").strip() or None))
            return cur.lastrowid

    def update_fornecedor(self, forn_id: int, nome: str, cnpj: str = "",
                          endereco: str = "") -> bool:
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Informe o nome do fornecedor.")
        dup = self.get_fornecedor_por_nome(nome)
        if dup and dup["id"] != forn_id:
            raise ValueError(f"Fornecedor '{nome}' já está cadastrado.")
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_fornecedores SET nome=?, cnpj=?, endereco=?"
                " WHERE id=?",
                (nome, (cnpj or "").strip() or None,
                 (endereco or "").strip() or None, forn_id))
            return cur.rowcount > 0

    def delete_fornecedor(self, forn_id: int) -> bool:
        with self._get_conn() as conn:
            usos = conn.execute(
                "SELECT COUNT(*) FROM frota_abastecimentos WHERE fornecedor_id=?",
                (forn_id,)).fetchone()[0]
            if usos:
                raise ValueError(
                    f"Não é possível excluir: {usos} abastecimento(s) usam"
                    " este fornecedor.")
            cur = conn.execute(
                "DELETE FROM frota_fornecedores WHERE id=?", (forn_id,))
            return cur.rowcount > 0

    def list_fornecedores(self) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT f.*, (SELECT COUNT(*) FROM frota_abastecimentos a"
                " WHERE a.fornecedor_id = f.id) AS abastecimentos"
                " FROM frota_fornecedores f ORDER BY nome").fetchall()
        return [dict(r) for r in rows]

    def get_fornecedor(self, forn_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM frota_fornecedores WHERE id=?",
                (forn_id,)).fetchone()
        return dict(row) if row else None

    def get_fornecedor_por_nome(self, nome: str) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM frota_fornecedores WHERE normalize(nome)=?",
                (normalize_text((nome or "").strip()),)).fetchone()
        return dict(row) if row else None

    # ---------- pasta virtual (docs) ----------

    DOC_MAX_BYTES = 50 * 1024 * 1024  # 50MB

    DOC_EXT_BLOQUEADAS = {
        ".exe", ".bat", ".cmd", ".ps1", ".sh", ".js", ".vbs", ".com",
        ".scr", ".msi", ".jar", ".py", ".rb", ".pl",
    }

    def _validar_doc(self, filename: str, data: bytes) -> str:
        ext = Path(filename).suffix.lower()
        if not ext:
            raise ValueError("Arquivo sem extensão.")
        if ext in self.DOC_EXT_BLOQUEADAS:
            raise ValueError(f"Tipo de arquivo bloqueado ({ext}).")
        if len(data) > self.DOC_MAX_BYTES:
            raise ValueError("Arquivo maior que 50MB.")
        mapa = {".pdf": "pdf", ".jpg": "jpg", ".jpeg": "jpg",
                ".png": "png", ".gif": "gif", ".txt": "txt"}
        return mapa.get(ext, ext.lstrip("."))

    def add_doc(self, veiculo_id: int, filename: str, data: bytes,
                tag: str = "") -> int:
        tipo = self._validar_doc(filename, data)
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO frota_veic_docs (veiculo_id, filename, tipo,"
                " tamanho, dados, tag) VALUES (?,?,?,?,?,?)",
                (veiculo_id, Path(filename).name, tipo, len(data),
                 sqlite3.Binary(data), (tag or "").strip() or None))
            return cur.lastrowid

    def list_docs(self, veiculo_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, filename, tipo, tamanho, tag, created_at"
                " FROM frota_veic_docs WHERE veiculo_id=? ORDER BY filename",
                (veiculo_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_doc(self, doc_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM frota_veic_docs WHERE id=?", (doc_id,)).fetchone()
        return dict(row) if row else None

    def delete_doc(self, doc_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM frota_veic_docs WHERE id=?", (doc_id,))
            return cur.rowcount > 0

    # ---------- laudos com vencimento ----------

    def add_laudo(self, veiculo_id: int, tipo: str, filename: str,
                  data: bytes, data_emissao: str, data_validade: str,
                  descricao: str = "") -> int:
        if tipo not in dict(TIPOS_LAUDO):
            raise ValueError("Tipo de laudo inválido.")
        if not data_validade:
            raise ValueError("Informe a data de validade do laudo.")
        tipo_arq = self._validar_doc(filename, data) if data else None
        if not data:
            raise ValueError("Selecione o arquivo do laudo.")
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO frota_veic_laudos (veiculo_id, tipo, descricao,"
                " filename, tipo_arquivo, tamanho, dados, data_emissao,"
                " data_validade) VALUES (?,?,?,?,?,?,?,?,?)",
                (veiculo_id, tipo, (descricao or "").strip() or None,
                 Path(filename).name, tipo_arq, len(data),
                 sqlite3.Binary(data), data_emissao or None, data_validade))
            return cur.lastrowid

    def list_laudos(self, veiculo_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, tipo, descricao, filename, tipo_arquivo, tamanho,"
                " data_emissao, data_validade, created_at"
                " FROM frota_veic_laudos WHERE veiculo_id=?"
                " ORDER BY data_validade", (veiculo_id,)).fetchall()
        hoje = date.today()
        out = []
        for r in rows:
            d = dict(r)
            try:
                dias = (date.fromisoformat(r["data_validade"]) - hoje).days
            except (TypeError, ValueError):
                dias = 0
            d["dias"] = dias
            d["status"] = ("vencido" if dias < 0 else "urgente"
                           if dias <= 7 else "atenção" if dias <= 30 else "ok")
            d["tipo_label"] = label_laudo(r["tipo"])
            out.append(d)
        return out

    def get_laudo(self, laudo_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM frota_veic_laudos WHERE id=?",
                (laudo_id,)).fetchone()
        return dict(row) if row else None

    def delete_laudo(self, laudo_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM frota_veic_laudos WHERE id=?", (laudo_id,))
            return cur.rowcount > 0

    def get_laudos_with_expiration(self) -> List[Dict[str, Any]]:
        """Laudos de frota no formato consumido por Vencimentos/Dashboard."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT l.id, l.tipo, l.descricao, l.data_validade,"
                " v.modelo, v.marca, v.placa, v.id AS veiculo_id"
                " FROM frota_veic_laudos l"
                " JOIN frota_veiculos v ON l.veiculo_id = v.id").fetchall()
        hoje = date.today()
        itens = []
        for r in rows:
            try:
                dv = date.fromisoformat(r["data_validade"])
            except (TypeError, ValueError):
                continue
            dias = (dv - hoje).days
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
            rot = veiculo_rotulo({"marca": r["marca"], "modelo": r["modelo"],
                                  "placa": r["placa"]})
            nome_tipo = label_laudo(r["tipo"])
            desc = r["descricao"] or ""
            itens.append({
                "id": r["id"],
                "cert_number": f"L-{r['id']:05d}",
                "nr_code": "FROTA",
                "nr_name": "FROTA",
                "funcionario_nome": rot,
                "funcionario_cpf": "",
                "descricao_treinamento":
                    f"{nome_tipo}{' — ' + desc if desc else ''}",
                "data_validade": r["data_validade"],
                "dias_para_vencer": dias,
                "status": status,
                "tipo_laudo": r["tipo"],
                "veiculo_id": r["veiculo_id"],
            })
        itens.sort(key=lambda i: (i["dias_para_vencer"],
                                  i["funcionario_nome"].lower()))
        return itens

    # ---------- movimentacoes (saida/entrada) ----------

    def add_mov_saida(self, veiculo_id: int, data_saida: str,
                      hora_saida: str, km_inicial: int, destino: str,
                      motivo: str, obs: str, motorista: str,
                      autorizado_por: str) -> int:
        if not data_saida or not hora_saida:
            raise ValueError("Informe data e hora da saída.")
        if km_inicial is None:
            raise ValueError("Informe o KM inicial.")
        if not (motorista or "").strip():
            raise ValueError("Informe o nome do motorista.")
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO frota_movimentacoes (veiculo_id, data_saida,"
                " hora_saida, km_inicial, destino, motivo, obs, motorista,"
                " autorizado_por) VALUES (?,?,?,?,?,?,?,?,?)",
                (veiculo_id, data_saida, hora_saida, int(km_inicial),
                 (destino or "").strip() or None, (motivo or "").strip() or None,
                 (obs or "").strip() or None, motorista.strip(),
                 (autorizado_por or "").strip() or None))
            return cur.lastrowid

    def registrar_entrada(self, mov_id: int, data_entrada: str,
                          hora_entrada: str, km_final: int) -> bool:
        if not data_entrada or not hora_entrada:
            raise ValueError("Informe data e hora da entrada.")
        if km_final is None:
            raise ValueError("Informe o KM final.")
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT km_inicial FROM frota_movimentacoes WHERE id=?",
                (mov_id,)).fetchone()
            if not row:
                raise ValueError("Movimentação não encontrada.")
            if km_final < row["km_inicial"]:
                raise ValueError(
                    f"KM final ({km_final}) menor que o KM inicial"
                    f" ({row['km_inicial']}).")
            cur = conn.execute(
                "UPDATE frota_movimentacoes SET data_entrada=?,"
                " hora_entrada=?, km_final=? WHERE id=?",
                (data_entrada, hora_entrada, int(km_final), mov_id))
            return cur.rowcount > 0

    def list_movimentacoes(self, veiculo_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM frota_movimentacoes WHERE veiculo_id=?"
                " ORDER BY data_saida DESC, hora_saida DESC, id DESC",
                (veiculo_id,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["aberta"] = d["data_entrada"] is None
            if d["km_final"] is not None:
                d["km_rodado"] = d["km_final"] - d["km_inicial"]
            out.append(d)
        return out

    def get_mov(self, mov_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM frota_movimentacoes WHERE id=?",
                (mov_id,)).fetchone()
        return dict(row) if row else None

    def delete_mov(self, mov_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM frota_movimentacoes WHERE id=?", (mov_id,))
            return cur.rowcount > 0

    # ---------- abastecimentos ----------

    def add_abastecimento(self, veiculo_id: int, fornecedor_id: Optional[int],
                          combustivel: str, data_abast: str,
                          viagem_servico: str, km: Optional[int],
                          condutor: str, superior: str = "", obs: str = "",
                          pdf_path: Optional[str] = None,
                          litros: Optional[float] = None,
                          valor: Optional[float] = None,
                          extras: Optional[List[dict]] = None,
                          tmp_fornecedor: str = "", tmp_cnpj: str = ""):
        """Insere e devolve (id, serial). Serial AB-{ano}-{id:05d}: o
        sequencial (id) nunca reinicia; o ano vem da data da solicitacao.
        extras = itens adicionais (2.35.2): [{'desc','qtd','valor'}].
        tmp_fornecedor/tmp_cnpj = posto temporário sem cadastro (2.37.1)."""
        if combustivel not in dict(TIPOS_COMBUSTIVEL):
            raise ValueError("Tipo de combustível inválido.")
        if not data_abast:
            raise ValueError("Informe a data da solicitação.")
        if not (condutor or "").strip():
            raise ValueError("Informe o nome do condutor.")
        if veiculo_id is None or not self.get_veiculo(veiculo_id):
            raise ValueError("Selecione um veículo cadastrado.")
        litros = float(litros) if litros not in (None, "") else None
        valor = float(valor) if valor not in (None, "") else None
        if litros is not None and litros <= 0:
            litros = None
        if valor is not None and valor <= 0:
            valor = None
        extras_json, extras_total = _extras_pack(extras)
        tmp_forn = (tmp_fornecedor or "").strip() or None
        tmp_cnpj_v = (tmp_cnpj or "").strip() or None
        if tmp_forn:
            fornecedor_id = None
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO frota_abastecimentos (serial, veiculo_id,"
                " fornecedor_id, combustivel, data, viagem_servico, km,"
                " condutor, superior, obs, pdf_path, litros, valor,"
                " extras, extras_total, tmp_fornecedor, tmp_cnpj)"
                " VALUES ('',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (veiculo_id, fornecedor_id, combustivel, data_abast,
                 (viagem_servico or "").strip() or None, km,
                 condutor.strip(), superior.strip(),
                 (obs or "").strip() or None, pdf_path, litros, valor,
                 extras_json, extras_total or None, tmp_forn, tmp_cnpj_v))
            novo_id = cur.lastrowid
            try:
                ano = date.fromisoformat(data_abast).year
            except ValueError:
                ano = datetime.now().year
            serial = f"AB-{ano}-{novo_id:05d}"
            conn.execute("UPDATE frota_abastecimentos SET serial=? WHERE id=?",
                         (serial, novo_id))
        return novo_id, serial

    def list_abastecimentos(self, busca: str = "",
                            limit: int = 20, offset: int = 0,
                            ordem: str = "data", situacao: str = "todas"):
        """Lista solicitações (2.35). ordem: 'data' (recentes primeiro, padrão)
        ou 'serial'. situacao: 'todas' | 'ativas' | 'bloqueadas'."""
        q = f"%{(busca or '').strip().lower()}%"
        where = ""
        params: list = []
        if busca and busca.strip():
            where = ("WHERE lower(a.serial)||' '||"
                     "lower(coalesce(v.modelo,''))||' '||"
                     "lower(coalesce(v.placa,''))||' '||"
                     "lower(coalesce(f.nome,''))||' '||"
                     "lower(coalesce(a.tmp_fornecedor,''))||' '||"
                     "lower(coalesce(a.condutor,'')) LIKE ?")
            params.append(q)
        if situacao == "ativas":
            where = (where + " AND a.status IS NULL") if where \
                else "WHERE a.status IS NULL"
        elif situacao == "bloqueadas":
            where = (where + " AND a.status = 'bloqueada'") if where \
                else "WHERE a.status = 'bloqueada'"
        # 2.38.1: ordena só datas ISO (aaaa-mm-dd); datas quebradas vão
        # para o fim — evita AB recente cair por último na lista.
        order = ("a.serial DESC" if ordem == "serial"
                 else "(CASE WHEN length(a.data)=10"
                      " AND substr(a.data,5,1)='-'"
                      " THEN a.data ELSE '' END) DESC, a.id DESC")
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT a.*, v.modelo, v.marca, v.placa,"
                " COALESCE(f.nome, a.tmp_fornecedor) AS fornecedor"
                " FROM frota_abastecimentos a"
                " JOIN frota_veiculos v ON a.veiculo_id = v.id"
                " LEFT JOIN frota_fornecedores f ON a.fornecedor_id = f.id"
                f" {where} ORDER BY {order} LIMIT ? OFFSET ?",
                params + [limit, offset]).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM frota_abastecimentos a"
                " JOIN frota_veiculos v ON a.veiculo_id = v.id"
                " LEFT JOIN frota_fornecedores f ON a.fornecedor_id = f.id"
                f" {where}", params).fetchone()[0]
        out = []
        for r in rows:
            d = dict(r)
            d["veiculo_rotulo"] = veiculo_rotulo(
                {"marca": d["marca"], "modelo": d["modelo"],
                 "placa": d["placa"]})
            d["combustivel_label"] = label_combustivel(d["combustivel"])
            d["extras_lista"] = json.loads(d.get("extras") or "[]")
            out.append(d)
        return out, total

    def tem_nf(self, abast_ids: List[int]) -> Dict[int, Optional[str]]:
        """Mapa abastecimento_id -> numero da NF (2.35.2) ou None."""
        if not abast_ids:
            return {}
        marks = ",".join("?" for _ in abast_ids)
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT abastecimento_id, numero FROM frota_abast_nfs"
                f" WHERE abastecimento_id IN ({marks})"
                f" ORDER BY id", abast_ids).fetchall()
        mapa: Dict[int, Optional[str]] = {i: None for i in abast_ids}
        for r in rows:
            if mapa.get(r[0]) is None:
                mapa[r[0]] = r[1]
        return mapa

    def get_abastecimento(self, abast_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT a.*, v.modelo, v.marca, v.placa, v.tipo AS veic_tipo,"
                " v.proprio, v.contratante,"
                " COALESCE(f.nome, a.tmp_fornecedor) AS fornecedor,"
                " COALESCE(f.cnpj, a.tmp_cnpj) AS fornecedor_cnpj,"
                " f.endereco AS fornecedor_endereco"
                " FROM frota_abastecimentos a"
                " JOIN frota_veiculos v ON a.veiculo_id = v.id"
                " LEFT JOIN frota_fornecedores f ON a.fornecedor_id = f.id"
                " WHERE a.id=?", (abast_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["extras_lista"] = json.loads(d.get("extras") or "[]")
        return d

    def list_abast_por_veiculo(self, veiculo_id: int) -> List[dict]:
        """Abastecimentos do veículo (query dedicada, 2.35) — recentes primeiro."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT a.*, v.modelo, v.marca, v.placa,"
                " COALESCE(f.nome, a.tmp_fornecedor) AS fornecedor"
                " FROM frota_abastecimentos a"
                " JOIN frota_veiculos v ON a.veiculo_id = v.id"
                " LEFT JOIN frota_fornecedores f ON a.fornecedor_id = f.id"
                " WHERE a.veiculo_id=? ORDER BY a.data DESC, a.id DESC",
                (veiculo_id,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["veiculo_rotulo"] = veiculo_rotulo(
                {"marca": d["marca"], "modelo": d["modelo"],
                 "placa": d["placa"]})
            d["combustivel_label"] = label_combustivel(d["combustivel"])
            d["extras_lista"] = json.loads(d.get("extras") or "[]")
            out.append(d)
        return out

    def set_pdf_path(self, abast_id: int, pdf_path: str) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE frota_abastecimentos SET pdf_path=? WHERE id=?",
                (pdf_path, abast_id))

    def update_abast_valores(self, abast_id: int, litros: Optional[float],
                             valor: Optional[float]) -> bool:
        """Preenche/ajusta litros e valor DEPOIS da emissão (ex.: com a NF)."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_abastecimentos SET litros=?, valor=? WHERE id=?",
                (litros, valor, abast_id))
            return cur.rowcount > 0

    def update_abastecimento(self, abast_id: int, fornecedor_id: Optional[int],
                             combustivel: str, data_abast: str,
                             viagem_servico: str, km: Optional[int],
                             condutor: str, obs: str = "",
                             litros: Optional[float] = None,
                             valor: Optional[float] = None,
                             extras: Optional[List[dict]] = None,
                             tmp_fornecedor: str = "",
                             tmp_cnpj: str = "") -> int:
        """Edita a solicitação (2.33.2) e incrementa a revisão.
        Devolve a revisão resultante (0 = original, 1 = REV_A, ...).
        extras = itens adicionais (2.35.2); regravá-los também conta revisão.
        tmp_fornecedor/tmp_cnpj = posto temporário sem cadastro (2.37.1)."""
        if combustivel not in dict(TIPOS_COMBUSTIVEL):
            raise ValueError("Tipo de combustível inválido.")
        if not data_abast:
            raise ValueError("Informe a data da solicitação.")
        if not (condutor or "").strip():
            raise ValueError("Informe o nome do condutor.")
        litros = float(litros) if litros not in (None, "") else None
        valor = float(valor) if valor not in (None, "") else None
        if litros is not None and litros <= 0:
            litros = None
        if valor is not None and valor <= 0:
            valor = None
        extras_json, extras_total = _extras_pack(extras)
        tmp_forn = (tmp_fornecedor or "").strip() or None
        tmp_cnpj_v = (tmp_cnpj or "").strip() or None
        if tmp_forn:
            fornecedor_id = None
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_abastecimentos SET fornecedor_id=?,"
                " combustivel=?, data=?, viagem_servico=?, km=?, condutor=?,"
                " obs=?, litros=?, valor=?, extras=?, extras_total=?,"
                " tmp_fornecedor=?, tmp_cnpj=?,"
                " revisao=COALESCE(revisao,0)+1"
                " WHERE id=?",
                (fornecedor_id, combustivel, data_abast,
                 (viagem_servico or "").strip() or None, km,
                 condutor.strip(), (obs or "").strip() or None,
                 litros, valor, extras_json, extras_total or None,
                 tmp_forn, tmp_cnpj_v, abast_id))
            if cur.rowcount == 0:
                raise ValueError("Solicitação não encontrada.")
            rev = conn.execute(
                "SELECT COALESCE(revisao, 0) FROM frota_abastecimentos"
                " WHERE id=?", (abast_id,)).fetchone()[0]
        return rev

    # ---------- bloqueio / exclusao de abastecimentos (2.35.2) ----------

    def bloquear_abastecimento(self, abast_id: int, motivo: str,
                               por: str = "") -> bool:
        """Bloqueia a solicitação: sai dos totais de custo (ficha/dashboard),
        permanece na lista com badge e motivo. Devolve False se não existir."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_abastecimentos SET status='bloqueada',"
                " motivo_status=?, status_em=?, status_por=? WHERE id=?",
                ((motivo or "").strip() or None,
                 datetime.now().strftime("%Y-%m-%d %H:%M"),
                 (por or "").strip() or None, abast_id))
            return cur.rowcount > 0

    def desbloquear_abastecimento(self, abast_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_abastecimentos SET status=NULL,"
                " motivo_status=NULL, status_em=NULL, status_por=NULL"
                " WHERE id=?", (abast_id,))
            return cur.rowcount > 0

    def pode_excluir_abastecimento(self, abast_id: int) -> bool:
        """Regra do roadmap 2.35: só pode excluir se for o registro mais
        recente; senão, apenas bloquear (mantém a sequência dos seriais)."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT MAX(id) FROM frota_abastecimentos").fetchone()
        return bool(row) and row[0] is not None and int(abast_id) == int(row[0])

    def delete_abastecimento(self, abast_id: int) -> bool:
        """Exclui a solicitação (e NFs/anexo assinado vinculados).
        Chame apenas após pode_excluir_abastecimento()."""
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM frota_abast_nfs WHERE abastecimento_id=?",
                (abast_id,))
            cur = conn.execute(
                "DELETE FROM frota_abastecimentos WHERE id=?", (abast_id,))
            return cur.rowcount > 0

    # ---------- notas fiscais de abastecimento (2.29.6) ----------

    def add_nf(self, abast_id: int, numero: str, data_nf: str,
               valor: Optional[float], filename: str, data: bytes) -> int:
        if not self.get_abastecimento(abast_id):
            raise ValueError("Abastecimento não encontrado.")
        tipo = self._validar_doc(filename, data)
        valor = float(valor) if valor not in (None, "") else None
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO frota_abast_nfs (abastecimento_id, numero, data,"
                " valor, filename, tipo_arquivo, tamanho, dados)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (abast_id, (numero or "").strip() or None,
                 data_nf or None, valor, Path(filename).name, tipo,
                 len(data), sqlite3.Binary(data)))
            return cur.lastrowid

    def list_nfs(self, abast_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, abastecimento_id, numero, data, valor, filename,"
                " tipo_arquivo, tamanho, created_at FROM frota_abast_nfs"
                " WHERE abastecimento_id=? ORDER BY id DESC",
                (abast_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_nf(self, nf_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM frota_abast_nfs WHERE id=?", (nf_id,)).fetchone()
        return dict(row) if row else None

    def delete_nf(self, nf_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM frota_abast_nfs WHERE id=?", (nf_id,))
            return cur.rowcount > 0

    # ---------- checklists semanais (2.29.5) ----------

    def add_checklist(self, veiculo_id: int, data_inicial: str,
                      data_final: str, km_rodado: Optional[int],
                      motorista: str, lider: str, pode_operar: str,
                      itens: dict, observacoes: dict,
                      criado_por: str = "") -> tuple:
        """itens: {'1.1': {'2ª': 'S', ...}, ...}; observacoes: {'2ª': 'texto'}.
        Devolve (id, serial). Serial CKL-{ano}-{id:05d} (id global)."""
        if veiculo_id is None or not self.get_veiculo(veiculo_id):
            raise ValueError("Selecione um veículo cadastrado.")
        if not data_inicial or not data_final:
            raise ValueError("Informe a data inicial e a data final.")
        if not (motorista or "").strip():
            raise ValueError("Informe o nome do motorista.")
        if not (lider or "").strip():
            raise ValueError("Informe o nome do líder.")
        if pode_operar not in ("S", "N"):
            raise ValueError("Responda se pode-se operar com segurança.")
        with self._get_conn() as conn:
            import json as _json
            cur = conn.execute(
                "INSERT INTO frota_checklists (serial, veiculo_id,"
                " data_inicial, data_final, km_rodado, placa, motorista,"
                " lider, pode_operar, itens, observacoes, criado_por)"
                " VALUES ('',?,?,?,?,?,?,?,?,?,?,?)",
                (veiculo_id, data_inicial, data_final, km_rodado,
                 None, motorista.strip(), lider.strip(), pode_operar,
                 _json.dumps(itens or {}, ensure_ascii=False),
                 _json.dumps(observacoes or {}, ensure_ascii=False),
                 (criado_por or "").strip() or None))
            # placa snapshot do veiculo
            v = self.get_veiculo(veiculo_id)
            novo_id = cur.lastrowid
            try:
                ano = date.fromisoformat(data_final).year
            except (TypeError, ValueError):
                ano = datetime.now().year
            serial = f"CKL-{ano}-{novo_id:05d}"
            conn.execute(
                "UPDATE frota_checklists SET serial=?, placa=? WHERE id=?",
                (serial, v.get("placa"), novo_id))
        return novo_id, serial

    def list_checklists(self, veiculo_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, serial, data_inicial, data_final, km_rodado,"
                " placa, motorista, lider, pode_operar, pdf_path, created_at,"
                " (assinado_dados IS NOT NULL) AS tem_assinado"
                " FROM frota_checklists WHERE veiculo_id=?"
                " ORDER BY id DESC", (veiculo_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_checklist(self, chk_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM frota_checklists WHERE id=?",
                (chk_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        import json as _json
        try:
            d["itens"] = _json.loads(d["itens"] or "{}")
        except ValueError:
            d["itens"] = {}
        try:
            d["observacoes"] = _json.loads(d["observacoes"] or "{}")
        except ValueError:
            d["observacoes"] = {}
        return d

    def set_checklist_pdf(self, chk_id: int, pdf_path: str) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE frota_checklists SET pdf_path=? WHERE id=?",
                (pdf_path, chk_id))

    def attach_checklist_signed(self, chk_id: int, data: bytes,
                                tipo: str, filename: str) -> bool:
        """Anexa o checklist impresso preenchido/assinado (foto ou PDF)."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_checklists SET assinado_dados=?,"
                " assinado_tipo=?, assinado_filename=?,"
                " assinado_em=datetime('now') WHERE id=?",
                (sqlite3.Binary(data), tipo, Path(filename).name, chk_id))
            return cur.rowcount > 0

    def get_checklist_signed(self, chk_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT assinado_dados, assinado_tipo, assinado_filename,"
                " assinado_em FROM frota_checklists WHERE id=?",
                (chk_id,)).fetchone()
        if not row or not row["assinado_dados"]:
            return None
        return dict(row)

    def remove_checklist_signed(self, chk_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_checklists SET assinado_dados=NULL,"
                " assinado_tipo=NULL, assinado_filename=NULL,"
                " assinado_em=NULL WHERE id=?", (chk_id,))
            return cur.rowcount > 0

    def attach_abast_signed(self, abast_id: int, data: bytes,
                            tipo: str, filename: str) -> bool:
        """Anexa o abastecimento assinado (foto ou PDF)."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_abastecimentos SET assinado_dados=?,"
                " assinado_tipo=?, assinado_filename=?,"
                " assinado_em=datetime('now') WHERE id=?",
                (sqlite3.Binary(data), tipo, Path(filename).name, abast_id))
            return cur.rowcount > 0

    def get_abast_signed(self, abast_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT assinado_dados, assinado_tipo, assinado_filename,"
                " assinado_em FROM frota_abastecimentos WHERE id=?",
                (abast_id,)).fetchone()
        if not row or not row["assinado_dados"]:
            return None
        return dict(row)

    def remove_abast_signed(self, abast_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_abastecimentos SET assinado_dados=NULL,"
                " assinado_tipo=NULL, assinado_filename=NULL,"
                " assinado_em=NULL WHERE id=?", (abast_id,))
            return cur.rowcount > 0

    def delete_checklist(self, chk_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM frota_checklists WHERE id=?", (chk_id,))
            return cur.rowcount > 0

    # ---------- manutenção preventiva por KM ----------

    def add_manutencao(self, veiculo_id: int, descricao: str,
                       intervalo_km: int, km_ultima: int,
                       data_ultima: str = "", obs: str = "") -> int:
        if not (descricao or "").strip():
            raise ValueError("Informe a descrição da manutenção.")
        intervalo_km = int(intervalo_km or 0)
        if intervalo_km <= 0:
            raise ValueError("Informe o intervalo em KM (maior que zero).")
        km_ultima = int(km_ultima or 0)
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO frota_manutencoes (veiculo_id, descricao,"
                " intervalo_km, km_ultima, data_ultima, obs)"
                " VALUES (?,?,?,?,?,?)",
                (veiculo_id, descricao.strip(), intervalo_km, km_ultima,
                 data_ultima or None, (obs or "").strip() or None))
            return cur.lastrowid

    def concluir_manutencao(self, manut_id: int, km_feito: int,
                            data_feito: str) -> bool:
        """Registra a realização: zera a contagem a partir do KM informado."""
        km_feito = int(km_feito or 0)
        if km_feito <= 0:
            raise ValueError("Informe o KM em que a manutenção foi feita.")
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE frota_manutencoes SET km_ultima=?, data_ultima=?"
                " WHERE id=?", (km_feito, data_feito, manut_id))
            return cur.rowcount > 0

    def list_manutencoes(self, veiculo_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM frota_manutencoes WHERE veiculo_id=?"
                " ORDER BY id DESC", (veiculo_id,)).fetchall()
        km_atual = self._km_atual(conn, veiculo_id)
        out = []
        for r in rows:
            d = dict(r)
            d["km_atual"] = km_atual
            d["km_desde"] = max(0, (km_atual or 0) - (d["km_ultima"] or 0))
            d["restante"] = d["intervalo_km"] - d["km_desde"]
            if d["restante"] < 0:
                d["status"] = "vencido"
            elif d["restante"] <= 100:
                d["status"] = "urgente"
            elif d["restante"] <= 250:
                d["status"] = "critico"
            elif d["restante"] <= 500:
                d["status"] = "atencao"
            elif d["restante"] <= 1000:
                d["status"] = "proximo"
            else:
                d["status"] = "ok"
            out.append(d)
        return out

    def get_manutencao(self, manut_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM frota_manutencoes WHERE id=?",
                (manut_id,)).fetchone()
        return dict(row) if row else None

    def delete_manutencao(self, manut_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM frota_manutencoes WHERE id=?", (manut_id,))
            return cur.rowcount > 0

    def get_manutencoes_with_expiration(self) -> List[Dict[str, Any]]:
        """Manutenções vencendo por KM, no formato de Vencimentos/Dashboard."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT m.*, v.modelo, v.marca, v.placa"
                " FROM frota_manutencoes m"
                " JOIN frota_veiculos v ON m.veiculo_id = v.id").fetchall()
        itens = []
        for r in rows:
            d = dict(r)
            km_atual = self._km_atual(conn, d["veiculo_id"]) or 0
            km_desde = max(0, km_atual - (d["km_ultima"] or 0))
            restante = d["intervalo_km"] - km_desde
            if restante < 0:
                status = "vencido"
            elif restante <= 100:
                status = "urgente"
            elif restante <= 250:
                status = "critico"
            elif restante <= 500:
                status = "atencao"
            elif restante <= 1000:
                status = "proximo"
            else:
                status = "ok"
            if status in ("ok",):
                continue
            rot = veiculo_rotulo({"marca": d["marca"], "modelo": d["modelo"],
                                  "placa": d["placa"]})
            if restante < 0:
                det = f"vencida há {-restante} km"
            else:
                det = f"faltam {restante} km"
            itens.append({
                "id": d["id"],
                "cert_number": f"M-{d['id']:05d}",
                "nr_code": "FROTA",
                "nr_name": "FROTA",
                "funcionario_nome": rot,
                "funcionario_cpf": "",
                "descricao_treinamento":
                    f"Manutenção: {d['descricao']} — {det}",
                "data_validade": None,
                "dias_para_vencer": restante,
                "status": status,
                "tipo_laudo": "manutencao",
                "veiculo_id": d["veiculo_id"],
                "por_km": True,
            })
        itens.sort(key=lambda i: (i["dias_para_vencer"],
                                  i["funcionario_nome"].lower()))
        return itens

    @staticmethod
    def _km_atual(conn: sqlite3.Connection, veiculo_id: int) -> Optional[int]:
        row = conn.execute(
            "SELECT MAX(COALESCE(km_final, km_inicial))"
            " FROM frota_movimentacoes WHERE veiculo_id=?",
            (veiculo_id,)).fetchone()
        return row[0] if row and row[0] is not None else None

    # ---------- custo / consumo (2.29.6) ----------

    def resumo_custo_veiculo(self, veiculo_id: int) -> Dict[str, Any]:
        """Totais de combustível e consumo médio (KM/L) do veículo.

        Solicitações bloqueadas (2.35.2) saem de todos os totais e da média.
        valor = combustível + itens extras; valor_extras traz o desglose."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT km, litros, valor FROM frota_abastecimentos"
                " WHERE veiculo_id=? AND litros IS NOT NULL"
                " AND status IS NULL"
                " ORDER BY km", (veiculo_id,)).fetchall()
            tot = conn.execute(
                "SELECT COALESCE(SUM(litros),0),"
                " COALESCE(SUM(valor),0)+COALESCE(SUM(extras_total),0),"
                " COALESCE(SUM(extras_total),0), COUNT(*)"
                " FROM frota_abastecimentos"
                " WHERE veiculo_id=? AND status IS NULL",
                (veiculo_id,)).fetchone()
        litros_total = float(tot[0] or 0)
        valor_total = float(tot[1] or 0)
        extras_total = float(tot[2] or 0)
        media_km_l = None
        custo_km = None
        pts = [(r["km"], float(r["litros"])) for r in rows
               if r["km"] is not None]
        pts.sort()
        km_diff = 0.0
        litros_usados = 0.0
        for (km1, l1), (km2, l2) in zip(pts, pts[1:]):
            d = km2 - km1
            if d > 0:
                km_diff += d
                litros_usados += l1
        if km_diff > 0 and litros_usados > 0:
            media_km_l = km_diff / litros_usados
            custo_km = valor_total / km_diff if valor_total else None
        esperado = None
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT km_l_esperado FROM frota_veiculos WHERE id=?",
                (veiculo_id,)).fetchone()
            if row and row[0]:
                esperado = float(row[0])
        return {
            "litros": round(litros_total, 2),
            "valor": round(valor_total, 2),
            "valor_combustivel": round(valor_total - extras_total, 2),
            "valor_extras": round(extras_total, 2),
            "media_km_l": round(media_km_l, 2) if media_km_l else None,
            "km_l_esperado": esperado,
            "custo_km": round(custo_km, 2) if custo_km else None,
        }

    def custo_serie_veiculo(self, veiculo_id: int, meses: int = 12) -> List[dict]:
        """Série mensal (2.35.1) dos últimos `meses` meses: custo combustível
        + extras e litros, ignorando bloqueadas. Sempre devolve `meses` itens."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT substr(data,1,7) AS mes,"
                " SUM(COALESCE(valor,0)) AS combustivel,"
                " SUM(COALESCE(extras_total,0)) AS extras,"
                " SUM(COALESCE(litros,0)) AS litros"
                " FROM frota_abastecimentos"
                " WHERE veiculo_id=? AND status IS NULL"
                " GROUP BY substr(data,1,7)", (veiculo_id,)).fetchall()
        mapa = {r["mes"]: dict(r) for r in rows if r["mes"]}
        serie = []
        base = date.today()
        for i in range(meses - 1, -1, -1):
            y = base.year
            m = base.month - i
            while m <= 0:
                m += 12
                y -= 1
            chave = f"{y:04d}-{m:02d}"
            r = mapa.get(chave, {})
            serie.append({
                "mes": chave,
                "rotulo": f"{m:02d}/{str(y)[2:]}",
                "combustivel": round(float(r.get("combustivel") or 0), 2),
                "extras": round(float(r.get("extras") or 0), 2),
                "litros": round(float(r.get("litros") or 0), 2),
            })
        return serie

    @staticmethod
    def _data_corte(dias):
        """Data ISO de corte para período (2.39.3): hoje - dias."""
        if not dias or dias <= 0:
            return None
        return (date.today() - timedelta(days=int(dias))).isoformat()

    def custo_serie_todos(self, meses: int = 12,
                          dias: Optional[int] = None) -> List[dict]:
        """Série mensal (2.37.2) dos últimos `meses` meses com detalhe POR
        VEÍCULO: cada item é {mes, rotulo, por_veiculo: {vid: {rotulo,
        combustivel, extras, litros}}}. Ignora bloqueadas. Sempre devolve
        `meses` itens (meses sem dados têm por_veiculo vazio).
        2.39.3: `dias` filtra por data real no SQL (período do relatório)."""
        corte = self._data_corte(dias)
        if dias:
            meses = {30: 1, 90: 3, 180: 6}.get(dias, meses)
        with self._get_conn() as conn:
            sql = (
                "SELECT a.veiculo_id AS vid, v.modelo, v.marca, v.placa,"
                " substr(a.data,1,7) AS mes,"
                " SUM(COALESCE(a.valor,0)) AS combustivel,"
                " SUM(COALESCE(a.extras_total,0)) AS extras,"
                " SUM(COALESCE(a.litros,0)) AS litros"
                " FROM frota_abastecimentos a"
                " JOIN frota_veiculos v ON v.id = a.veiculo_id"
                " WHERE a.status IS NULL")
            params = []
            if corte:
                sql += " AND a.data >= ?"
                params.append(corte)
            sql += " GROUP BY a.veiculo_id, substr(a.data,1,7)"
            rows = conn.execute(sql, params).fetchall()
        rotulos = {}
        por_mes = {}
        for r in rows:
            d = dict(r)
            if d["vid"] not in rotulos:
                rotulos[d["vid"]] = veiculo_rotulo(
                    {"marca": d["marca"], "modelo": d["modelo"],
                     "placa": d["placa"]})
            por_mes.setdefault(d["mes"], {})[d["vid"]] = {
                "rotulo": rotulos[d["vid"]],
                "combustivel": round(float(d["combustivel"] or 0), 2),
                "extras": round(float(d["extras"] or 0), 2),
                "litros": round(float(d["litros"] or 0), 2),
            }
        serie = []
        base = date.today()
        for i in range(meses - 1, -1, -1):
            y = base.year
            m = base.month - i
            while m <= 0:
                m += 12
                y -= 1
            chave = f"{y:04d}-{m:02d}"
            serie.append({
                "mes": chave,
                "rotulo": f"{m:02d}/{str(y)[2:]}",
                "por_veiculo": por_mes.get(chave, {}),
            })
        return serie

    def custo_por_combustivel(self, dias: Optional[int] = None) -> List[dict]:
        """Total por veículo × tipo de combustível (2.37.2), incluindo extras,
        ignorando bloqueadas. 2.39.2/2.39.3: `dias` filtra por data; ordenado
        por TOTAL gasto (combustível+extras) DESC, depois veículo."""
        corte = self._data_corte(dias)
        with self._get_conn() as conn:
            sql = (
                "SELECT a.veiculo_id AS vid, a.combustivel AS comb,"
                " v.modelo, v.marca, v.placa,"
                " SUM(COALESCE(a.valor,0)) AS combustivel,"
                " SUM(COALESCE(a.extras_total,0)) AS extras,"
                " SUM(COALESCE(a.litros,0)) AS litros"
                " FROM frota_abastecimentos a"
                " JOIN frota_veiculos v ON v.id = a.veiculo_id"
                " WHERE a.status IS NULL")
            params = []
            if corte:
                sql += " AND a.data >= ?"
                params.append(corte)
            sql += (" GROUP BY a.veiculo_id, a.combustivel"
                    " ORDER BY (SUM(COALESCE(a.valor,0))"
                    " + SUM(COALESCE(a.extras_total,0))) DESC,"
                    " a.veiculo_id, combustivel DESC")
            rows = conn.execute(sql, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["veiculo_rotulo"] = veiculo_rotulo(
                {"marca": d["marca"], "modelo": d["modelo"],
                 "placa": d["placa"]})
            out.append(d)
        return out

    def resumo_custo_todos(self, dias: Optional[int] = None) -> List[dict]:
        """Resumo de custo por veículo (2.35.1) para o export geral.
        Ignora bloqueadas; separa combustível x itens extras.
        2.39: `dias` filtra por data; inclui tipo/subtipo, km_l_esperado e
        media_km_l (pares consecutivos de KM dentro do período); ordenado
        por TOTAL gasto (combustível+extras) DESC."""
        corte = self._data_corte(dias)
        with self._get_conn() as conn:
            cond = "a.status IS NULL"
            params = []
            if corte:
                cond += " AND a.data >= ?"
                params.append(corte)
            rows = conn.execute(
                "SELECT v.id, v.modelo, v.marca, v.placa, v.tipo, v.subtipo,"
                " v.km_l_esperado,"
                " COALESCE(SUM(CASE WHEN " + cond +
                "   THEN COALESCE(a.valor,0) END),0) AS combustivel,"
                " COALESCE(SUM(CASE WHEN " + cond +
                "   THEN COALESCE(a.extras_total,0) END),0) AS extras,"
                " COALESCE(SUM(CASE WHEN " + cond +
                "   THEN COALESCE(a.litros,0) END),0) AS litros,"
                " SUM(CASE WHEN a.id IS NOT NULL AND " + cond +
                " THEN 1 ELSE 0 END) AS qtd"
                " FROM frota_veiculos v"
                " LEFT JOIN frota_abastecimentos a ON a.veiculo_id = v.id"
                " GROUP BY v.id", params * 4).fetchall()
            # KM/L por veículo no mesmo período (pares consecutivos de KM)
            km_rows = conn.execute(
                "SELECT a.veiculo_id AS vid, a.km, a.litros"
                " FROM frota_abastecimentos a"
                " WHERE " + cond + " AND a.km IS NOT NULL"
                " AND a.litros IS NOT NULL ORDER BY a.veiculo_id, a.km",
                params).fetchall()
        medias = {}
        for r in km_rows:
            pts = medias.setdefault(r["vid"], [])
            pts.append((r["km"], float(r["litros"])))
        out = []
        for r in rows:
            d = dict(r)
            d["veiculo_rotulo"] = veiculo_rotulo(
                {"marca": d["marca"], "modelo": d["modelo"],
                 "placa": d["placa"]})
            media = None
            pts = medias.get(d["id"]) or []
            km_diff = 0.0
            litros_usados = 0.0
            for (km1, l1), (km2, _l2) in zip(pts, pts[1:]):
                delta = float(km2) - float(km1)
                if delta > 0:
                    km_diff += delta
                    litros_usados += l1
            if km_diff > 0 and litros_usados > 0:
                media = round(km_diff / litros_usados, 2)
            d["media_km_l"] = media
            d["total"] = round(float(d["combustivel"] or 0)
                               + float(d["extras"] or 0), 2)
            out.append(d)
        out.sort(key=lambda x: (-(x["total"]), x["id"]))
        return out

    def list_extras_veiculo(self, veiculo_id: int) -> List[dict]:
        """Itens extras individuais (2.38.2) das solicitações ATIVAS do
        veículo, com o serial de origem. Bloqueadas ficam fora."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT serial, data, extras, extras_total"
                " FROM frota_abastecimentos"
                " WHERE veiculo_id=? AND status IS NULL"
                " ORDER BY data DESC, id DESC",
                (veiculo_id,)).fetchall()
        out = []
        for r in rows:
            try:
                lista = json.loads(r["extras"] or "[]")
            except (TypeError, ValueError):
                lista = []
            for ex in lista:
                desc = str(ex.get("desc") or "").strip()
                if not desc:
                    continue
                out.append({
                    "serial": r["serial"], "data": r["data"],
                    "desc": desc,
                    "qtd": ex.get("qtd"),
                    "valor": ex.get("valor"),
                })
        return out

    def custo_mes(self) -> float:
        """Total gasto em abastecimentos no mês corrente (dashboard).
        Solicitações bloqueadas (2.35.2) não somam."""
        mes = datetime.now().strftime("%Y-%m")
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(valor),0)+COALESCE(SUM(extras_total),0)"
                " FROM frota_abastecimentos"
                " WHERE substr(data,1,7)=? AND status IS NULL",
                (mes,)).fetchone()
        return float(row[0] or 0)

    def count_movs_abertas(self) -> int:
        """Movimentações de saída sem entrada registrada (dashboard)."""
        with self._get_conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM frota_movimentacoes"
                " WHERE data_entrada IS NULL").fetchone()[0]
