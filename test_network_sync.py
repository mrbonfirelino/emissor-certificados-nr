"""Testes do espelhamento em rede + documentos do funcionario + migracao (v1.8.0).

Rodar: python test_network_sync.py
"""

import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import src.core.network_sync as ns
import src.core.employee_repo as er_mod
import src.core.history_repo as hr_mod
from src.core.employee_repo import EmployeeRepository
from src.core.history_repo import HistoryRepository
from src.core.models import CertificateRecord, Employee
from src.utils.folder_utils import employee_folder_name, sanitize_folder_name

PASSOS = []


def check(nome, cond):
    PASSOS.append((nome, bool(cond)))
    print(f"[{'OK' if cond else 'FALHOU'}] {nome}")


def cpf_valido() -> str:
    return "52998224725"


def make_db(tmp: Path) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    db = tmp / "test.db"
    EmployeeRepository(db_path=db)
    HistoryRepository(db_path=db)
    return db


def add_cert(hist, numero, emp_id, nome, nr, data_fim, pdf_path, cpf=""):
    rec = CertificateRecord(
        cert_number=numero, nr_code=nr, employee_id=emp_id,
        funcionario_nome=nome, funcionario_cpf=cpf,
        data_inicio=data_fim, data_fim=data_fim, carga_horaria=8,
        descricao_treinamento="Treinamento teste",
        campos_extra="{}", pdf_path=str(pdf_path),
    )
    return hist.save(rec)


# ── 1. Nome de pasta ─────────────────────────────────────────

def test_folder_utils():
    check("sanitize remove caracteres invalides",
          sanitize_folder_name('Joao/ Pedro: *?"<>|\\') == "Joao Pedro")
    e1 = Employee(id=1, nome="Joao Pedro")
    e2 = Employee(id=2, nome="Joao Pedro", cpf=cpf_valido())
    check("sem colisao fica so o nome",
          employee_folder_name(e1, [e1, Employee(id=2, nome="Maria")]) == "Joao Pedro")
    # o model formata o CPF (529.982.247-25)
    check("colisao anexa CPF",
          employee_folder_name(e2, [e1, e2]) == "Joao Pedro (529.982.247-25)")
    check("colisao sem CPF anexa id",
          employee_folder_name(e1, [e1, Employee(id=2, nome="joao pedro")]) == "Joao Pedro (id1)")


# ── 2. Rede desativada ───────────────────────────────────────

def test_desativado():
    orig_ativo = ns.rede_ativo
    ns.rede_ativo = lambda: False
    try:
        e = Employee(id=1, nome="Joao Pedro")
        cert = CertificateRecord(
            cert_number="CERT-000001", nr_code="NR-35", employee_id=1,
            funcionario_nome="Joao Pedro", funcionario_cpf="",
            data_inicio="2026-01-01", data_fim="2026-01-01", carga_horaria=8,
            descricao_treinamento="x", campos_extra="{}", pdf_path="x.pdf")
        check("desativado: sync_certificate nao faz nada",
              ns.sync_certificate(cert, e) is False)
        check("desativado: sync_all zera stats",
              ns.sync_all() == {"copiados": 0, "erros": 0})
    finally:
        ns.rede_ativo = orig_ativo


# ── 3. Certificado: estrutura + vencidos ─────────────────────

def test_sync_certificate(tmp: Path):
    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    hist = HistoryRepository(db_path=db)
    emp_repo.create("Joao Pedro", None)
    emp = emp_repo.get_all()[0]

    dest = tmp / "rede"
    pdf_ok = tmp / "CERT-000001_NR-35_J.pdf"
    pdf_ok.write_bytes(b"%PDF-ok")
    pdf_velho = tmp / "CERT-000002_NR-35_J.pdf"
    pdf_velho.write_bytes(b"%PDF-velho")
    hoje = date.today().isoformat()
    add_cert(hist, "CERT-000001", emp.id, emp.nome, "NR-35", hoje, pdf_ok)
    add_cert(hist, "CERT-000002", emp.id, emp.nome, "NR-35", "2024-01-01", pdf_velho)

    ns.rede_ativo = lambda: True
    ns.rede_caminho = lambda: dest
    er_mod.get_db_path = lambda: db

    ok = ns.sync_certificate(hist.get_by_number("CERT-000001"), emp)
    check("cert atual copiado", ok and (dest / "Joao Pedro" / "Certificados" / "NR-35"
          / "CERT-000001_NR-35_J.pdf").read_bytes() == b"%PDF-ok")

    check("cert vencido vai para 00_Certificados_OLD",
          ns.sync_certificate(hist.get_by_number("CERT-000002"), emp)
          and (dest / "Joao Pedro" / "Certificados" / "NR-35" / "00_Certificados_OLD"
               / "CERT-000002_NR-35_J.pdf").exists())

    # renovacao: cert 1 vence depois -> copia atual deve mover p/ OLD
    import src.core.network_sync as _ns
    real_vencido = _ns._cert_vencido
    _ns._cert_vencido = lambda c: True
    try:
        ns.sync_certificate(hist.get_by_number("CERT-000001"), emp)
        base = dest / "Joao Pedro" / "Certificados" / "NR-35"
        check("copia atual movida para OLD ao vencer",
              (base / "00_Certificados_OLD" / "CERT-000001_NR-35_J.pdf").exists()
              and not (base / "CERT-000001_NR-35_J.pdf").exists())
    finally:
        _ns._cert_vencido = real_vencido


# ── 4. Cartoes / assinados / outros ──────────────────────────

def test_sync_variados(tmp: Path):
    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    hist = HistoryRepository(db_path=db)
    emp_repo.create("Maria Silva", None)
    emp = emp_repo.get_all()[0]
    dest = tmp / "rede2"
    ns.rede_ativo = lambda: True
    ns.rede_caminho = lambda: dest
    er_mod.get_db_path = lambda: db

    card = tmp / "CARTAO_Maria_Silva_ALTEC.pdf"
    card.write_bytes(b"%PDF-card")
    check("cartao individual", ns.sync_card(card, emp)
          and (dest / "Maria Silva" / "Cartoes" / card.name).exists())

    lote = tmp / "CARTOES_ALTEC_20260903.pdf"
    lote.write_bytes(b"%PDF-lote")
    check("lote em Cartoes_Gerais", ns.sync_card_lote(lote)
          and (dest / "Cartoes_Gerais" / lote.name).exists())

    assinados_local = tmp / "assinados_local"
    ns.get_assinados_dir = lambda: assinados_local
    pdf_ok = tmp / "CERT-000010_M.pdf"
    pdf_ok.write_bytes(b"%PDF-m")
    add_cert(hist, "CERT-000010", emp.id, emp.nome, "NR-35", date.today().isoformat(), pdf_ok)
    cert = hist.get_by_number("CERT-000010")
    hist.attach_signed_doc(cert.id, b"ASSINADO", "pdf")
    check("assinado local + rede", ns.salvar_assinado(cert, b"ASSINADO", "pdf", emp)
          and (assinados_local / "Maria Silva" / "CERT-000010_assinado.pdf").read_bytes() == b"ASSINADO"
          and (dest / "Maria Silva" / "Certificados Assinados" / "CERT-000010_assinado.pdf").exists())

    check("outros docs", ns.sync_doc("CNH.PNG", b"FOTO", emp)
          and (dest / "Maria Silva" / "Outros" / "CNH.PNG").read_bytes() == b"FOTO")
    check("remover doc da rede", ns.remove_doc_network("CNH.PNG", emp)
          and not (dest / "Maria Silva" / "Outros" / "CNH.PNG").exists())


# ── 5. Falha na rede -> toast/log, sem excecao ────────────────

def test_falha_rede(tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    bloqueador = tmp / "bloqueio.txt"
    bloqueador.write_text("x")
    ns.rede_ativo = lambda: True
    ns.rede_caminho = lambda: bloqueador  # caminho e um ARQUIVO -> mkdir falha
    chamadas = []
    orig = ns._notify_fail
    ns._notify_fail = lambda o, e: chamadas.append(o)
    try:
        e = Employee(id=1, nome="Joao Pedro")
        card = tmp / "CARTAO_X.pdf"
        card.write_bytes(b"%PDF")
        check("falha silenciosa com toast", ns.sync_card(card, e) is False and len(chamadas) == 1)
    finally:
        ns._notify_fail = orig


# ── 6. sync_all completo ─────────────────────────────────────

def test_sync_all(tmp: Path):
    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    hist = HistoryRepository(db_path=db)
    emp_repo.create("Joao Pedro", None)
    emp = emp_repo.get_all()[0]
    dest = tmp / "rede3"
    cartoes_local = tmp / "cartoes_local"
    ns.rede_ativo = lambda: True
    ns.rede_caminho = lambda: dest
    ns.get_cartoes_dir = lambda: cartoes_local
    er_mod.get_db_path = lambda: db
    hr_mod.get_db_path = lambda: db

    pdf_ok = tmp / "CERT-000020_J.pdf"
    pdf_ok.write_bytes(b"%PDF-j")
    add_cert(hist, "CERT-000020", emp.id, emp.nome, "NR-35", date.today().isoformat(), pdf_ok)
    cert = hist.get_by_number("CERT-000020")
    hist.attach_signed_doc(cert.id, b"ASS", "pdf")
    emp_repo.add_doc(emp.id, "CNH.PNG", b"FOTO", "png")

    card = cartoes_local / "Joao Pedro" / "CARTAO_J_ALTEC.pdf"
    card.parent.mkdir(parents=True)
    card.write_bytes(b"%PDF-card")
    lote = cartoes_local / "LOTES" / "CARTOES_ALTEC_1.pdf"
    lote.parent.mkdir(parents=True)
    lote.write_bytes(b"%PDF-lote")

    stats = ns.sync_all()
    check("sync_all copia tudo",
          (dest / "Joao Pedro" / "Certificados" / "NR-35" / "CERT-000020_J.pdf").exists()
          and (dest / "Joao Pedro" / "Certificados Assinados" / "CERT-000020_assinado.pdf").exists()
          and (dest / "Joao Pedro" / "Outros" / "CNH.PNG").exists()
          and (dest / "Joao Pedro" / "Cartoes" / "CARTAO_J_ALTEC.pdf").exists()
          and (dest / "Cartoes_Gerais" / "CARTOES_ALTEC_1.pdf").exists())
    check("sync_all stats sem erros", stats["erros"] == 0 and stats["copiados"] >= 5)


# ── 7. Documentos do funcionario (BLOB) ──────────────────────

def test_employee_docs(tmp: Path):
    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    emp_repo.create("Maria Silva", None)
    emp = emp_repo.get_all()[0]

    doc_id = emp_repo.add_doc(emp.id, "CNH.PNG", b"FOTO", "png")
    docs = emp_repo.list_docs(emp.id)
    check("add/list docs", len(docs) == 1 and docs[0]["filename"] == "CNH.PNG"
          and docs[0]["tipo"] == "png" and docs[0]["tamanho"] == 4)

    res = emp_repo.get_doc(doc_id)
    check("get doc", res and res[0] == emp.id and res[2] == b"FOTO")

    emp_repo.delete_doc(doc_id)
    check("delete doc", emp_repo.list_docs(emp.id) == [] and emp_repo.get_doc(doc_id) is None)

    # formatos universais (2.14): qualquer extensao nao bloqueada, ate 50MB
    emp_repo.add_doc(emp.id, "grande.pdf", b"x" * (11 * 1024 * 1024), "pdf")
    emp_repo.add_doc(emp.id, "contrato.docx", b"DOCX", "docx")
    emp_repo.add_doc(emp.id, "planilha.xlsx", b"XLSX", "xlsx")
    emp_repo.add_doc(emp.id, "video.mp4", b"MP4", "mp4")
    check("formatos universais aceitos (11MB pdf/docx/xlsx/mp4)",
          len(emp_repo.list_docs(emp.id)) == 4)

    try:
        emp_repo.add_doc(emp.id, "malicioso.exe", b"MZ", "exe")
        check("exe bloqueado", False)
    except ValueError:
        check("exe bloqueado", True)
    try:
        emp_repo.add_doc(emp.id, "script.bat", b"@echo", "bat")
        check("bat bloqueado", False)
    except ValueError:
        check("bat bloqueado", True)
    try:
        emp_repo.add_doc(emp.id, "codigo.js", b"alert", "js")
        check("js bloqueado (extensao/MIME)", False)
    except ValueError:
        check("js bloqueado (extensao/MIME)", True)
    try:
        emp_repo.add_doc(emp.id, "sem_ext", b"x", "")
        check("arquivo sem extensao rejeitado", False)
    except ValueError:
        check("arquivo sem extensao rejeitado", True)
    try:
        emp_repo.add_doc(emp.id, "gigante.zip", b"x" * (51 * 1024 * 1024), "zip")
        check("limite 50MB", False)
    except ValueError:
        check("limite 50MB", True)
    check("bloqueados nao foram gravados",
          len([d for d in emp_repo.list_docs(emp.id)
               if d["filename"] in ("malicioso.exe", "script.bat", "codigo.js", "gigante.zip")]) == 0)


# ── 8. Migracao de pastas ────────────────────────────────────

def test_migracao(tmp: Path):
    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    hist = HistoryRepository(db_path=db)
    emp_repo.create("Joao Pedro", None)
    emp = emp_repo.get_all()[0]

    legacy = tmp / "CERTIFICADOS"
    cert_root = tmp / "novo" / "certificados"
    cartoes_root = tmp / "novo" / "cartoes"

    old_pdf = legacy / "Joao_Pedro" / "CERT-000001_NR-35_Joao_Pedro.pdf"
    old_pdf.parent.mkdir(parents=True)
    old_pdf.write_bytes(b"%PDF-velho")
    add_cert(hist, "CERT-000001", emp.id, emp.nome, "NR-35", "2026-01-01", old_pdf)

    lote = legacy / "CARTOES" / "ALTEC" / "CARTOES_ALTEC_20260101_000000.pdf"
    lote.parent.mkdir(parents=True)
    lote.write_bytes(b"%PDF-lote")
    indiv = legacy / "CARTOES" / "ALTEC" / "CARTAO_Joao_Pedro_ALTEC.pdf"
    indiv.write_bytes(b"%PDF-indiv")
    orfao = legacy / "Fantasma" / "CERT-000009_X.pdf"
    orfao.parent.mkdir(parents=True)
    orfao.write_bytes(b"%PDF-orfao")

    guard = {}
    def fake_get(k, d=None):
        return guard.get(k, d)
    def fake_set(k, v):
        guard[k] = v

    stats = __import__("src.core.storage_migration", fromlist=["migrate_storage_if_needed"]) \
        .migrate_storage_if_needed(
            legacy_dir=legacy, cert_root=cert_root, cartoes_root=cartoes_root,
            settings=(fake_get, fake_set), db_path=db)

    novo_pdf = cert_root / "Joao Pedro" / "NR-35" / "CERT-000001_NR-35_Joao_Pedro.pdf"
    check("cert migrado p/ data/certificados/{Func}/{NR}",
          novo_pdf.exists() and not old_pdf.exists())
    check("pdf_path atualizado no banco",
          hist.get_by_number("CERT-000001").pdf_path == str(novo_pdf))
    check("lote -> LOTES", (cartoes_root / "LOTES" / lote.name).exists())
    check("cartao individual -> pasta do funcionario",
          (cartoes_root / "Joao Pedro" / indiv.name).exists())
    check("orfao -> _ORFAOS", (cert_root / "_ORFAOS" / "Fantasma" / "CERT-000009_X.pdf").exists())
    check("guard gravado", guard.get("migracao_pastas_v2") is True)
    check("idempotente (2a chamada nao faz nada)",
          __import__("src.core.storage_migration", fromlist=["migrate_storage_if_needed"])
          .migrate_storage_if_needed(legacy_dir=legacy, cert_root=cert_root,
                                     cartoes_root=cartoes_root, settings=(fake_get, fake_set),
                                     db_path=db)["certificados"] == 0)


def main():
    with tempfile.TemporaryDirectory(prefix="normatech_sync_", ignore_cleanup_errors=True) as td:
        tmp = Path(td)
        test_folder_utils()
        test_desativado()
        test_sync_certificate(tmp / "t3")
        test_sync_variados(tmp / "t4")
        test_falha_rede(tmp / "t5")
        test_sync_all(tmp / "t6")
        test_employee_docs(tmp / "t7")
        test_migracao(tmp / "t8")

    falhas = [n for n, ok in PASSOS if not ok]
    print(f"\n{len(PASSOS) - len(falhas)}/{len(PASSOS)} testes OK")
    if falhas:
        print("FALHARAM:", falhas)
        sys.exit(1)


if __name__ == "__main__":
    main()
