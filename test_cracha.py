"""Testes do cracha de identificacao (v1.13.0): repo, dados, PDFs e preview.

Rodar: python test_cracha.py
"""

import sys
import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import fitz
from PIL import Image

import src.core.badge_service as badge
import src.core.employee_repo as er_mod
from src.core.cracha_repo import CrachaRepository
from src.core.employee_repo import EmployeeRepository
from src.core.history_repo import HistoryRepository
from src.core.aso_repo import AsoRepository
from src.core.models import CertificateRecord

PASSOS = []


def check(nome, cond):
    PASSOS.append((nome, bool(cond)))
    print(f"[{'OK' if cond else 'FALHOU'}] {nome}")


TEMPLATE = {"card_code": "CRACHA-ALTEC", "template_type": "cracha", "max_nrs": 8}
TEMPLATE_VERTICAL = {"card_code": "CRACHA-VERTICAL", "template_type": "cracha",
                     "card_width_mm": 78, "card_height_mm": 120, "max_nrs": 8}


class Ctx:
    """DB temporario + patches de paths por bloco de testes."""

    def __init__(self, tmp: Path):
        tmp.mkdir(parents=True, exist_ok=True)
        self.tmp = tmp
        self.db = tmp / "test.db"
        self.emp_repo = EmployeeRepository(db_path=self.db)
        self.hist = HistoryRepository(db_path=self.db)
        self.aso = AsoRepository(db_path=self.db)
        self.cracha = CrachaRepository(db_path=self.db)
        self.emp_repo.create("Joao Pedro", None)
        self.emp_repo.create("Maria Silva", None)
        emps = self.emp_repo.get_all()
        self.e1 = next(e for e in emps if e.nome == "Joao Pedro")
        self.e2 = next(e for e in emps if e.nome == "Maria Silva")
        self._add_cert("CERT-000001", self.e1, "NR-10", -30)
        self._add_cert("CERT-000002", self.e1, "NR-12", -10)
        self._add_cert("CERT-000003", self.e1, "NR-35", -20)
        self._add_cert("CERT-000004", self.e2, "NR-35", -5)
        self._add_cert("CERT-000005", self.e2, "NR-11", date(2024, 1, 1))
        self.aso.save("ASO-000001", self.e1.id, "Admissional",
                      date.today().isoformat(), validade_meses=12)
        # patches
        self._orig = (badge.get_crachas_dir, badge.get_logo_path, er_mod.get_db_path)
        logo = tmp / "logo_teste.png"
        Image.new("RGB", (120, 40), (27, 58, 92)).save(logo)
        badge.get_crachas_dir = lambda: tmp / "crachas_out"
        badge.get_logo_path = lambda: logo
        er_mod.get_db_path = lambda: self.db

    def _add_cert(self, numero, emp, nr, data_fim):
        fim = data_fim if isinstance(data_fim, date) else date.today() + timedelta(days=data_fim)
        self.hist.save(CertificateRecord(
            cert_number=numero, nr_code=nr, employee_id=emp.id,
            funcionario_nome=emp.nome, funcionario_cpf=emp.cpf or "",
            data_inicio=fim.isoformat(), data_fim=fim.isoformat(),
            carga_horaria=8, descricao_treinamento="Treinamento teste",
            campos_extra="{}", pdf_path=None,
        ))

    def options(self, nrs1, nrs2):
        return {"data_emissao": date.today().isoformat(),
                "nrs": {self.e1.id: nrs1, self.e2.id: nrs2}}

    def restore(self):
        (badge.get_crachas_dir, badge.get_logo_path, er_mod.get_db_path) = self._orig

    def gerar(self, single, output_dir=None, nrs1=None, nrs2=None, template=None):
        nrs1 = nrs1 if nrs1 is not None else ["NR-10", "NR-12", "NR-35", "NR-99"]
        nrs2 = nrs2 if nrs2 is not None else ["NR-35", "NR-11"]
        return badge.generate_badges(
            [self.e1, self.e2], template or TEMPLATE, single_pdf=single,
            options=self.options(nrs1, nrs2), output_dir=output_dir,
            history_repo=self.hist, aso_repo=self.aso, cracha_repo=self.cracha,
        )


def test_repo(tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    db = tmp / "repo.db"
    EmployeeRepository(db_path=db)  # employees p/ FK
    repo = CrachaRepository(db_path=db)
    check("primeiro numero CRACHA-000001", repo.next_cracha_number() == "CRACHA-000001")
    check("peek nao consome", repo.peek_cracha_number() == "CRACHA-000002"
          and repo.peek_cracha_number() == "CRACHA-000002")
    check("segundo numero CRACHA-000002", repo.next_cracha_number() == "CRACHA-000002")
    rid = repo.save("CRACHA-000001", 1, "Joao Pedro", "2026-09-04",
                    ["NR-10", "NR-35"], "ASO-000001", "2027-09-04", "x.pdf")
    check("save retorna id", rid >= 1)
    rows = repo.get_by_employee(1)
    check("get_by_employee com nrs JSON",
          len(rows) == 1 and rows[0]["nrs"] == ["NR-10", "NR-35"]
          and rows[0]["aso_number"] == "ASO-000001")
    check("count_all", repo.count_all() == 1)


def test_build_badge_data(tmp: Path):
    ctx = Ctx(tmp)
    try:
        dados = badge.build_badge_data([ctx.e1, ctx.e2], ctx.options(
            ["NR-10", "NR-12", "NR-35", "NR-99"], ["NR-35", "NR-11"]),
            history_repo=ctx.hist, aso_repo=ctx.aso)
        check("um badge por funcionario", len(dados) == 2)
        d1 = next(d for d in dados if d["employee"].id == ctx.e1.id)
        d2 = next(d for d in dados if d["employee"].id == ctx.e2.id)
        codigos = [r["nr_code"] for r in d1["nrs"]]
        check("NR inexistente filtrada e ordenacao DESC (mais recente 1a)",
              "NR-99" not in codigos and codigos == ["NR-12", "NR-35", "NR-10"])
        check("rows com datas do certificado",
              all({"nr_code", "data_capacitacao", "data_validade"} <= set(r) for r in d1["nrs"]))
        check("ASO do funcionario 1 presente",
              d1["aso_number"] == "ASO-000001" and d1["aso_validade"])
        check("funcionario 2 sem ASO", d2["aso_number"] is None)
    finally:
        ctx.restore()


def test_single_pdf(tmp: Path):
    ctx = Ctx(tmp)
    try:
        paths, msgs = ctx.gerar(single=True)
        check("1 arquivo de lote", len(paths) == 1 and not msgs)
        doc = fitz.open(paths[0])
        check("2 paginas (1 cracha/folha)", doc.page_count == 2)
        r = doc[0].rect
        check("pagina 120x78mm (~340.16x221.10 pts)",
              abs(r.width - 340.16) <= 1 and abs(r.height - 221.10) <= 1)
        t1 = doc[0].get_text().upper()
        t2 = doc[1].get_text().upper()
        check("conteudo cracha 1", all(s in t1 for s in (
            "CARTÃO DE IDENTIFICAÇÃO", "JOAO PEDRO", "NR-35",
            "ASS COLABORADOR:", "CRACHA-0000", "PROIBIDO")))
        check("ASO vencimento no cracha 1", "ASO" in t1)
        check("conteudo cracha 2 (validade vencida presente)",
              "MARIA SILVA" in t2 and "NR-11" in t2 and "CRACHA-0000" in t2)
        doc.close()
        check("gravou 2 registros", ctx.cracha.count_all() == 2)
        nrs_db = json.loads(json.dumps(ctx.cracha.get_by_employee(ctx.e1.id)[0]["nrs"]))
        check("nrs gravadas no banco", nrs_db == ["NR-12", "NR-35", "NR-10"])
    finally:
        ctx.restore()


def test_individual(tmp: Path):
    ctx = Ctx(tmp)
    try:
        paths, _ = ctx.gerar(single=False)
        check("2 arquivos individuais", len(paths) == 2
              and all(p.name.startswith("CRACHA_") for p in paths))
        check("pastas por funcionario",
              {p.parent.name for p in paths} == {"Joao Pedro", "Maria Silva"})
        check("get_by_employee apos gravar",
              ctx.cracha.count_all() == 2
              and len(ctx.cracha.get_by_employee(ctx.e2.id)) == 1)
    finally:
        ctx.restore()


def test_preview_nao_grava(tmp: Path):
    ctx = Ctx(tmp)
    try:
        out = tmp / "preview"
        paths1, _ = ctx.gerar(single=True, output_dir=out)
        p1 = paths1[0]
        check("preview gerou arquivo", p1.exists() and out.exists())
        check("preview NAO grava nem consome sequencia", ctx.cracha.count_all() == 0)
        paths2, _ = ctx.gerar(single=True, output_dir=out)
        p2 = paths2[0]
        t = fitz.open(p2)[0].get_text()
        check("numeros do preview repetidos (peek)",
              "CRACHA-000001" in fitz.open(p1)[0].get_text()
              and "CRACHA-000001" in t)
    finally:
        ctx.restore()


def test_vertical(tmp: Path):
    """Cracha retrato 7,8x12cm (CRACHA-VERTICAL) — v1.14.0."""
    ctx = Ctx(tmp)
    try:
        paths, msgs = ctx.gerar(single=True, template=TEMPLATE_VERTICAL)
        check("vertical: 1 arquivo de lote", len(paths) == 1 and not msgs)
        doc = fitz.open(paths[0])
        check("vertical: 2 paginas", doc.page_count == 2)
        r = doc[0].rect
        check("vertical: pagina 78x120mm (~221.10x340.16 pts)",
              abs(r.width - 221.10) <= 1 and abs(r.height - 340.16) <= 1)
        t1 = doc[0].get_text().upper()
        t2 = doc[1].get_text().upper()
        check("vertical: conteudo cracha 1", all(s in t1 for s in (
            "CARTÃO DE IDENTIFICAÇÃO", "JOAO PEDRO", "NR-35",
            "ASS COLABORADOR:", "CRACHA-0000", "PROIBIDO", "EMISSÃO:")))
        check("vertical: ASO no cracha 1", "ASO" in t1)
        check("vertical: conteudo cracha 2 (vencida presente)",
              "MARIA SILVA" in t2 and "NR-11" in t2)
        doc.close()
        check("vertical: gravou 2 registros", ctx.cracha.count_all() == 2)
        check("vertical: nrs gravadas",
              ctx.cracha.get_by_employee(ctx.e1.id)[0]["nrs"] == ["NR-12", "NR-35", "NR-10"])
    finally:
        ctx.restore()


def test_vertical_individual_preview(tmp: Path):
    ctx = Ctx(tmp)
    try:
        paths, _ = ctx.gerar(single=False, template=TEMPLATE_VERTICAL)
        check("vertical individual: 2 arquivos", len(paths) == 2
              and all(p.name.startswith("CRACHA_") for p in paths))
        check("vertical individual: pastas por funcionario",
              {p.parent.name for p in paths} == {"Joao Pedro", "Maria Silva"})

        out = tmp / "preview"
        paths1, _ = ctx.gerar(single=True, output_dir=out, template=TEMPLATE_VERTICAL)
        check("vertical preview: NAO grava nem consome sequencia",
              ctx.cracha.count_all() == 2)  # apenas os 2 do individual acima
        t = fitz.open(paths1[0])[0].get_text()
        check("vertical preview: numero peek CRACHA-000003 (apos 2 consumidos)",
              "CRACHA-000003" in t)
    finally:
        ctx.restore()


def test_paisagem_intacta(tmp: Path):
    """O template paisagem original continua idêntico (mesma pagina)."""
    ctx = Ctx(tmp)
    try:
        paths, _ = ctx.gerar(single=True)
        r = fitz.open(paths[0])[0].rect
        check("paisagem intacta: 120x78mm",
              abs(r.width - 340.16) <= 1 and abs(r.height - 221.10) <= 1)
    finally:
        ctx.restore()


def main():
    with tempfile.TemporaryDirectory(prefix="normatech_cracha_",
                                     ignore_cleanup_errors=True) as td:
        tmp = Path(td)
        test_repo(tmp / "t1")
        test_build_badge_data(tmp / "t2")
        test_single_pdf(tmp / "t3")
        test_individual(tmp / "t4")
        test_preview_nao_grava(tmp / "t5")
        test_vertical(tmp / "t6")
        test_vertical_individual_preview(tmp / "t7")
        test_paisagem_intacta(tmp / "t8")

    falhas = [n for n, ok in PASSOS if not ok]
    print(f"\n{len(PASSOS) - len(falhas)}/{len(PASSOS)} testes OK")
    if falhas:
        print("FALHARAM:", falhas)
        sys.exit(1)


if __name__ == "__main__":
    main()
