"""
Testes do servico de cartoes PPTX.

1. Testes unitarios (sem PowerPoint): tokens, validacao, fallback matricula
2. Teste E2E (requer PowerPoint): gera PDFs reais para cada template

Uso:  python test_pptx_cards.py [--unit] [--e2e]
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.core.models import Employee
from src.core.pptx_card_service import (
    load_pptx_card_templates,
    validate_employees_for_pptx,
    generate_pptx_cards,
    _replace_tokens_in_text_frame,
    _employee_values,
)
from pptx import Presentation


def make_employees():
    fotos_dir = ROOT / "FOTOS PARA TESTE"
    foto1 = next(fotos_dir.glob("ADELSON*")).read_bytes()
    foto2 = next(fotos_dir.glob("ALCIMAR*")).read_bytes()
    return [
        # nome longo de proposito: estressa o auto-shrink de fonte
        Employee(id=1, nome="Fabricio Carvalho Ferreira Da Silva Santos Junior", cpf="529.982.247-25",
                 funcao="Soldador", telefone="21981586650", foto=foto1),
        Employee(id=2, nome="Ailton Costa Martins", cpf="111.444.777-35",
                 funcao="Tecnico em Seguranca do Trabalho", telefone="22981632680", foto=foto2),
        Employee(id=3, nome="Luciano Dias", cpf="123.456.789-09",
                 funcao="Encarregado", telefone="21984209236", foto=foto1),
        Employee(id=4, nome="Paulo Vitor Barbosa", cpf="987.654.321-00",
                 funcao="Eletricista", telefone="21987654321", foto=foto2),
    ]


E2E_MATRICULAS = {1: "12240721707", 2: "22927112738", 3: "10442439709", 4: "70132975"}


# ── Unitarios ───────────────────────────────────────────────

def test_tokens():
    class FakeRun:
        def __init__(self, t):
            self.text = t

    class FakePara:
        def __init__(self, *ts):
            self.runs = [FakeRun(t) for t in ts]

    class FakeTF:
        def __init__(self, paras):
            self.paragraphs = paras
            self.margin_left = 91440
            self.margin_right = 91440

    class FakeShape:
        def __init__(self, tf):
            self.text_frame = tf
            self.width = 3600000  # 10cm — largo o bastante para nao acionar shrink

    # placeholder quebrado em varios runs
    tf = FakeTF([FakePara("Nome: ", "{{NO", "ME}} | teste")])
    _replace_tokens_in_text_frame(FakeShape(tf), {"NOME": "FABIO"})
    assert tf.paragraphs[0].runs[0].text == "Nome: FABIO | teste", tf.paragraphs[0].runs[0].text
    assert all(r.text == "" for r in tf.paragraphs[0].runs[1:])
    print("[OK] token split em runs")


def test_shrink():
    class FakeRun:
        def __init__(self, t):
            self.text = t
            self.font = type("F", (), {"size": type("S", (), {"pt": 12.0})(), "bold": True})()

    class FakePara:
        def __init__(self, r):
            self.runs = [r]

    class FakeTF:
        def __init__(self, para):
            self.paragraphs = [para]
            self.margin_left = 91440
            self.margin_right = 91440

    class FakeShape:
        def __init__(self, tf, w):
            self.text_frame = tf
            self.width = w

    from src.core.pptx_card_service import _shrink_paragraph_to_fit

    # texto longo em shape estreito (2cm) -> fonte deve encolher
    r = FakeRun("FABRICIO CARVALHO FERREIRA DA SILVA SANTOS JUNIOR")
    _shrink_paragraph_to_fit(FakePara(r), r.text, FakeShape(None, 720000), FakeTF(None))
    assert r.font.size.pt < 12.0, r.font.size.pt
    print(f"[OK] auto-shrink: 12pt -> {r.font.size.pt}pt para caber em 2cm")


def test_matricula_do_popup():
    emps = make_employees()
    tpl = {"empresa_default": "ALTEC"}
    # matricula vem exclusivamente do popup (sem fallback CPF)
    vals = _employee_values(emps[0], tpl, {"matriculas": {emps[0].id: "99988877766"}})
    assert vals["MATRICULA"] == "99988877766", vals["MATRICULA"]
    # sem informar no popup -> vazio (UI bloqueia esse caso antes de chegar aqui)
    vals2 = _employee_values(emps[1], tpl, {})
    assert vals2["MATRICULA"] == "", vals2["MATRICULA"]
    print("[OK] matricula exclusiva do popup (sem fallback CPF)")


def test_validacao_dinamica():
    emps = make_employees()
    tpls = load_pptx_card_templates()

    # sem telefone e sem foto
    sem_tudo = Employee(id=9, nome="Sem Dados", cpf=None)
    valid, missing = validate_employees_for_pptx([sem_tudo], tpls["ARCELORMITTAL"])
    # ARCELORMITTAL nao usa telefone -> so cobra foto
    assert not valid and "foto" in missing[0] and "telefone" not in missing[0], missing
    print("[OK] ARCELORMITTAL exige foto mas nao telefone")

    valid, missing = validate_employees_for_pptx([sem_tudo], tpls["ALTEC-PEQUENO"])
    # ALTEC-PEQUENO usa telefone e foto (placeholders adicionados na preparacao)
    assert not valid and "telefone" in missing[0] and "foto" in missing[0], missing
    print("[OK] ALTEC-PEQUENO exige telefone e foto")

    valid, missing = validate_employees_for_pptx(emps, tpls["CSN"])
    assert len(valid) == 4 and not missing
    print("[OK] funcionarios completos validos")


def test_fill_clone_tokens():
    tpls = load_pptx_card_templates()
    tpl = tpls["LOTOTO"]
    prs = Presentation(tpl["_pptx_path"])
    from src.core.pptx_card_service import _fill_clone
    emps = make_employees()[:2]
    _fill_clone(prs, emps, tpl, {"setor": "Manutencao Mecanica", "papeis": {emps[0].id: "LIDER"},
                                  "matriculas": E2E_MATRICULAS})
    texts = []
    from src.core.pptx_card_service import _iter_all_shapes
    for slide in prs.slides:
        for shp in _iter_all_shapes(slide.shapes):
            if getattr(shp, "has_text_frame", False):
                texts.append(shp.text_frame.text)
    joined = "\n".join(texts)
    assert "{{" not in joined, "tokens remanescentes!"
    assert "FABRICIO CARVALHO FERREIRA DA SILVA SANTOS JUNIOR" in joined
    assert "LIDER" in joined and "Manutencao Mecanica" in joined
    assert "22927112738" in joined  # matricula do slide 2 (via popup)
    print("[OK] _fill_clone LOTOTO (2 slides) sem tokens remanescentes")


# ── E2E ─────────────────────────────────────────────────────

def _check_data_inside_zones(pdf_path, tpl, emps, options):
    """Verifica que todo texto de DADOS preenchido esta dentro da zona do cartao."""
    import fitz

    needles = set()
    for e in emps:
        vals = _employee_values(e, tpl, options)
        needles.update(v for v in vals.values() if isinstance(v, str) and len(v) >= 4)
    needles |= {"LIDER", "LIDERADO"}

    bad = []
    doc = fitz.open(str(pdf_path))
    try:
        for pno in range(len(doc)):
            page = doc[pno]
            pw, ph = page.rect.width, page.rect.height
            zones = [fitz.Rect(z[0] * pw, z[1] * ph, z[2] * pw, z[3] * ph)
                     for z in tpl["card_zones_fraction"]]
            for b in page.get_text("dict")["blocks"]:
                if b["type"] != 0:
                    continue
                for l in b["lines"]:
                    for s in l["spans"]:
                        t = s["text"].strip()
                        if not t or not any(n in t for n in needles):
                            continue
                        r = fitz.Rect(s["bbox"])
                        c = fitz.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
                        z = next((z for z in zones if z.contains(c)), None)
                        if z is None:
                            bad.append((pno, t[:45], "fora de qualquer cartao"))
                            continue
                        tol = 3.0
                        zt = fitz.Rect(z.x0 - tol, z.y0 - tol, z.x1 + tol, z.y1 + tol)
                        if not zt.contains(r):
                            bad.append((pno, t[:45], "estoura a borda do cartao"))
    finally:
        doc.close()
    return bad


def test_e2e():
    tpls = load_pptx_card_templates()
    emps = make_employees()
    options = {"setor": "Manutencao Mecanica", "papeis": {1: "LIDER"},
               "matriculas": E2E_MATRICULAS}
    out = ROOT / "CERTIFICADOS" / "CARTOES" / "_TESTE"
    for code, tpl in tpls.items():
        paths, missing = generate_pptx_cards(emps, tpl, options=options,
                                             single_pdf=True, one_per_page=False,
                                             output_dir=out)
        assert paths, f"{code}: nenhum PDF gerado ({missing})"
        p = paths[0]
        assert p.exists() and p.stat().st_size > 10_000, f"{code}: PDF muito pequeno"
        print(f"[OK] {code}: {p.name} ({p.stat().st_size // 1024} KB)")

        # dados preenchidos precisam caber dentro do cartao (auto-shrink)
        bad = _check_data_inside_zones(p, tpl, emps, options)
        assert not bad, f"{code}: dados fora do cartao: {bad[:5]}"
        print(f"[OK] {code}: dados dentro dos limites dos cartoes")

        # modo 1 cartao por pagina
        paths1, _ = generate_pptx_cards(emps, tpl, options=options,
                                        single_pdf=True, one_per_page=True,
                                        output_dir=out)
        p1 = paths1[0]
        import fitz
        d = fitz.open(str(p1))
        try:
            expected = 4  # 4 funcionarios -> 4 cartoes
            assert len(d) == expected, f"{code}: esperava {expected} paginas, veio {len(d)}"
        finally:
            d.close()
        print(f"[OK] {code} 1/pagina: {p1.name} ({len(fitz.open(str(p1)))} paginas)")


if __name__ == "__main__":
    args = set(sys.argv[1:])
    run_all = not args
    if run_all or "--unit" in args:
        test_tokens()
        test_shrink()
        test_matricula_do_popup()
        test_validacao_dinamica()
        test_fill_clone_tokens()
    if run_all or "--e2e" in args:
        test_e2e()
    print("\nTODOS OS TESTES PASSARAM")
