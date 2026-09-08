"""Testes do cracha de identificacao (v1.13.0+): repo, dados, PDFs, preview
e bloqueios de emissao (v1.15.1).

Rodar: python test_cracha.py
"""

import sys
import io
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


def _foto_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (60, 80), (120, 150, 180)).save(buf, format="PNG")
    return buf.getvalue()


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
        foto = _foto_bytes()
        self.emp_repo.create("Joao Pedro", None, foto=foto)
        self.emp_repo.create("Maria Silva", None, foto=foto)
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
        self.aso.save("ASO-000002", self.e2.id, "Periódico",
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

    def options(self, nrs1, nrs2, tamanho=None):
        opt = {"data_emissao": date.today().isoformat(),
               "nrs": {self.e1.id: nrs1, self.e2.id: nrs2}}
        if tamanho:
            opt["tamanho"] = tamanho
        return opt

    def restore(self):
        (badge.get_crachas_dir, badge.get_logo_path, er_mod.get_db_path) = self._orig

    def gerar(self, single, output_dir=None, nrs1=None, nrs2=None, template=None,
              tamanho=None):
        nrs1 = nrs1 if nrs1 is not None else ["NR-10", "NR-12", "NR-35", "NR-99"]
        nrs2 = nrs2 if nrs2 is not None else ["NR-35", "NR-11"]
        return badge.generate_badges(
            [self.e1, self.e2], template or TEMPLATE, single_pdf=single,
            options=self.options(nrs1, nrs2, tamanho), output_dir=output_dir,
            history_repo=self.hist, aso_repo=self.aso, cracha_repo=self.cracha,
        )


A4_W_PT, A4_H_PT = 595.28, 841.89


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
        check("ASO do funcionario 2 presente",
              d2["aso_number"] == "ASO-000002" and d2["aso_validade"])
        check("NR vencida nunca entra (v1.15.1)",
              [r["nr_code"] for r in d2["nrs"]] == ["NR-35"])
    finally:
        ctx.restore()


def test_single_pdf(tmp: Path):
    ctx = Ctx(tmp)
    try:
        paths, msgs = ctx.gerar(single=True)
        check("1 arquivo de lote", len(paths) == 1 and not msgs)
        doc = fitz.open(paths[0])
        check("lote: 2 crachas na MESMA folha A4 (3/folha)", doc.page_count == 1)
        r = doc[0].rect
        check("lote: folha A4 (~595.28x841.89 pts)",
              abs(r.width - A4_W_PT) <= 1 and abs(r.height - A4_H_PT) <= 1)
        t1 = doc[0].get_text().upper()
        check("conteudo cracha 1", all(s in t1 for s in (
            "CARTÃO DE IDENTIFICAÇÃO", "JOAO PEDRO", "NR-35",
            "ASS COLABORADOR:", "CRACHA-0000", "PROIBIDO")))
        check("ASO vencimento no cracha 1", "ASO" in t1)
        check("conteudo cracha 2 na mesma folha (vencida EXCLUIDA v1.15.1)",
              "MARIA SILVA" in t1 and "NR-11" not in t1)
        doc.close()
        check("gravou 2 registros", ctx.cracha.count_all() == 2)
        nrs_db = json.loads(json.dumps(ctx.cracha.get_by_employee(ctx.e1.id)[0]["nrs"]))
        check("nrs gravadas no banco", nrs_db == ["NR-12", "NR-35", "NR-10"])
        check("nrs do func 2 sem a vencida",
              ctx.cracha.get_by_employee(ctx.e2.id)[0]["nrs"] == ["NR-35"])
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
        doc = fitz.open(paths[0])
        r = doc[0].rect
        t = doc[0].get_text().upper()
        check("individual: folha A4 com cracha centrado",
              doc.page_count == 1
              and abs(r.width - A4_W_PT) <= 1 and abs(r.height - A4_H_PT) <= 1
              and "JOAO PEDRO" in t and "CARTÃO DE IDENTIFICAÇÃO" in t)
        doc.close()
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
    """Cracha retrato 7,8x12cm (CRACHA-VERTICAL) — v1.14.0; folha A4 v1.15.0."""
    ctx = Ctx(tmp)
    try:
        paths, msgs = ctx.gerar(single=True, template=TEMPLATE_VERTICAL)
        check("vertical: 1 arquivo de lote", len(paths) == 1 and not msgs)
        doc = fitz.open(paths[0])
        check("vertical: 2 crachas na MESMA folha A4 (4/folha)", doc.page_count == 1)
        r = doc[0].rect
        check("vertical: folha A4 (~595.28x841.89 pts)",
              abs(r.width - A4_W_PT) <= 1 and abs(r.height - A4_H_PT) <= 1)
        t1 = doc[0].get_text().upper()
        check("vertical: conteudo cracha 1", all(s in t1 for s in (
            "CARTÃO DE IDENTIFICAÇÃO", "JOAO PEDRO", "NR-35",
            "ASS COLABORADOR:", "CRACHA-0000", "PROIBIDO", "EMISSÃO:")))
        check("vertical: ASO no cracha 1", "ASO" in t1)
        check("vertical: conteudo cracha 2 na mesma folha (vencida EXCLUIDA)",
              "MARIA SILVA" in t1 and "NR-11" not in t1)
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
        check("vertical individual: 2 arquivos A4", len(paths) == 2
              and all(p.name.startswith("CRACHA_") for p in paths))
        check("vertical individual: pastas por funcionario",
              {p.parent.name for p in paths} == {"Joao Pedro", "Maria Silva"})
        doc = fitz.open(paths[0])
        check("vertical individual: folha A4",
              abs(doc[0].rect.width - A4_W_PT) <= 1)
        doc.close()

        out = tmp / "preview"
        paths1, _ = ctx.gerar(single=True, output_dir=out, template=TEMPLATE_VERTICAL)
        check("vertical preview: NAO grava nem consome sequencia",
              ctx.cracha.count_all() == 2)  # apenas os 2 do individual acima
        t = fitz.open(paths1[0])[0].get_text()
        check("vertical preview: numero peek CRACHA-000003 (apos 2 consumidos)",
              "CRACHA-000003" in t)
    finally:
        ctx.restore()


def test_paisagem_a4(tmp: Path):
    """Template paisagem agora sai em folha A4 (grade 3/folha), conteudo intacto."""
    ctx = Ctx(tmp)
    try:
        paths, _ = ctx.gerar(single=True)
        doc = fitz.open(paths[0])
        r = doc[0].rect
        t = doc[0].get_text().upper()
        check("paisagem A4: folha A4 com 2 crachas",
              doc.page_count == 1
              and abs(r.width - A4_W_PT) <= 1 and abs(r.height - A4_H_PT) <= 1
              and "JOAO PEDRO" in t and "MARIA SILVA" in t)
        doc.close()
    finally:
        ctx.restore()


def test_tamanho_reduzido(tmp: Path):
    """Opcao tamanho 'reduzido': escala p/ caber em 86x54mm (v1.15.0)."""
    # metricas puras
    m_real = badge._badge_metrics(TEMPLATE, "real")
    m_red = badge._badge_metrics(TEMPLATE, "reduzido")
    mv_red = badge._badge_metrics(TEMPLATE_VERTICAL, "reduzido")
    check("metrics real: escala 1.0 slot nativo",
          m_real == (120.0, 78.0, 1.0, 120.0, 78.0))
    check("metrics reduzido paisagem: slot ~86x54",
          abs(m_red[3] - 83.08) < 0.5 and abs(m_red[4] - 54.0) < 0.5
          and abs(m_red[2] - min(86 / 120, 54 / 78)) < 1e-6)
    check("metrics reduzido retrato: slot ~54x83",
          abs(mv_red[3] - 54.0) < 0.5 and abs(mv_red[4] - 83.08) < 0.5)
    check("grades A4: paisagem 1x3, retrato 2x2, reduzidos 2x5/3x3",
          badge._a4_grid(120, 78) == (1, 3)
          and badge._a4_grid(78, 120) == (2, 2)
          and badge._a4_grid(83.08, 54) == (2, 5)
          and badge._a4_grid(54, 83.08) == (3, 3))

    ctx = Ctx(tmp)
    try:
        paths, _ = ctx.gerar(single=True, tamanho="reduzido")
        doc = fitz.open(paths[0])
        r = doc[0].rect
        t = doc[0].get_text().upper()
        check("reduzido: 2 crachas na mesma folha A4", doc.page_count == 1
              and abs(r.width - A4_W_PT) <= 1 and abs(r.height - A4_H_PT) <= 1)
        check("reduzido: conteudo integro (texto escalado)",
              all(s in t for s in ("CARTÃO DE IDENTIFICAÇÃO", "JOAO PEDRO",
                                   "MARIA SILVA", "ASS COLABORADOR:", "CRACHA-0000")))
        doc.close()
        check("reduzido: gravou 2 registros",
              ctx.cracha.count_all() == 2)
    finally:
        ctx.restore()


def test_bloqueios(tmp: Path):
    """v1.15.1: sem foto / sem NR valida / ASO vencido bloqueiam a emissao."""
    ctx = Ctx(tmp)
    try:
        foto = _foto_bytes()
        ctx.emp_repo.create("Carlos Souza", None, foto=None)   # sem foto
        ctx.emp_repo.create("Bia Alves", None, foto=foto)      # so NR vencida
        ctx.emp_repo.create("Rui Lima", None, foto=foto)       # ASO vencido
        emps = {e.nome: e for e in ctx.emp_repo.get_all()}
        carlos, bia, rui = emps["Carlos Souza"], emps["Bia Alves"], emps["Rui Lima"]

        ctx._add_cert("CERT-000010", carlos, "NR-10", -5)
        ctx.aso.save("ASO-000010", carlos.id, "Admissional",
                     date.today().isoformat(), validade_meses=12)
        ctx._add_cert("CERT-000011", bia, "NR-11", date(2024, 1, 1))
        ctx.aso.save("ASO-000011", bia.id, "Admissional",
                     date.today().isoformat(), validade_meses=12)
        ctx._add_cert("CERT-000012", rui, "NR-35", -5)
        ctx.aso.save("ASO-000012", rui.id, "Admissional",
                     (date.today() - timedelta(days=400)).isoformat(), validade_meses=12)

        maps = badge._expiration_maps(ctx.hist, ctx.aso)
        certs_map, asos = maps
        check("elegivel sem motivos", badge.cracha_block_reasons(
            ctx.e1, list(certs_map.get(ctx.e1.id, {}).values()), asos.get(ctx.e1.id)) == [])
        check("bloqueio sem foto", badge.cracha_block_reasons(
            carlos, list(certs_map.get(carlos.id, {}).values()), asos.get(carlos.id))
            == ["sem foto"])
        check("bloqueio sem NR valida", badge.cracha_block_reasons(
            bia, list(certs_map.get(bia.id, {}).values()), asos.get(bia.id))
            == ["nenhuma NR dentro da validade"])
        check("bloqueio ASO vencido", badge.cracha_block_reasons(
            rui, list(certs_map.get(rui.id, {}).values()), asos.get(rui.id))
            == ["ASO ausente ou vencido"])

        # gerar com um elegivel + um bloqueado: so o elegivel sai
        antes = ctx.cracha.count_all()
        paths, faltantes = badge.generate_badges(
            [ctx.e1, carlos], TEMPLATE, single_pdf=True,
            options={"data_emissao": date.today().isoformat(),
                     "nrs": {ctx.e1.id: ["NR-35"], carlos.id: ["NR-10"]}},
            history_repo=ctx.hist, aso_repo=ctx.aso, cracha_repo=ctx.cracha)
        check("lote gerado apenas para o elegivel",
              len(paths) == 1 and ctx.cracha.count_all() == antes + 1)
        check("bloqueado vira mensagem de pulado",
              len(faltantes) == 1 and "Carlos Souza" in faltantes[0]
              and "sem foto" in faltantes[0])
        t = fitz.open(paths[0])[0].get_text().upper()
        check("PDF so com o elegivel", "JOAO PEDRO" in t and "CARLOS" not in t)

        # todos bloqueados: nada gerado
        paths2, faltantes2 = badge.generate_badges(
            [carlos], TEMPLATE, single_pdf=True,
            options={"data_emissao": date.today().isoformat(), "nrs": {carlos.id: ["NR-10"]}},
            history_repo=ctx.hist, aso_repo=ctx.aso, cracha_repo=ctx.cracha)
        check("todos bloqueados: nenhum PDF e mensagem",
              paths2 == [] and len(faltantes2) == 1)
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
        test_paisagem_a4(tmp / "t8")
        test_tamanho_reduzido(tmp / "t9")
        test_bloqueios(tmp / "t10")

    falhas = [n for n, ok in PASSOS if not ok]
    print(f"\n{len(PASSOS) - len(falhas)}/{len(PASSOS)} testes OK")
    if falhas:
        print("FALHARAM:", falhas)
        sys.exit(1)


if __name__ == "__main__":
    main()
