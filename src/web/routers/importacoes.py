"""Portal Web — Importações Excel/CSV (Fase 3).

Porta os 4 importadores do desktop para o navegador: funcionários,
certificados em lote (com prévia), ASOs em lote e lista de bloqueios de
cartões. Serve também os modelos de MODELOS DE IMPORTACAO/ para download.
Módulo só para admin/emissor (matriz docs/PORTAL/01 §6).
"""

import json
import secrets
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

from fastapi import Request, UploadFile
from fastapi.responses import (FileResponse, JSONResponse, RedirectResponse,
                               Response)

from src.utils.paths import get_data_dir, get_project_root
from src.web import auth, jobs

MAX_MB = 50  # decisão D5 (docs/PORTAL/01 §7)

# slug -> arquivo na pasta MODELOS DE IMPORTACAO
_MODELOS = {
    "funcionarios": "MODELO FUNCIONARIOS.xlsx",
    "certificados": "MODELO CERTIFICADOS.xlsx",
    "aso": "MODELO ASO.xlsx",
    "cartoes": "MODELO CARTOES BLOQUEIO.xlsx",
    "veiculos": "MODELO VEICULOS.xlsx",
    "leiame": "LEIA-ME.txt",
}

_MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def ler_upload_xlsx(upload: Optional[UploadFile],
                          max_mb: int = MAX_MB) -> Tuple[Optional[Path], str]:
    """Salva o upload em arquivo temporário (.xlsx). Retorna (caminho, erro)."""
    if upload is None or not (upload.filename or "").strip():
        return None, "Selecione um arquivo .xlsx."
    if not upload.filename.lower().endswith(".xlsx"):
        return None, "Formato inválido — envie um arquivo .xlsx."
    try:
        dados = await upload.read(max_mb * 1024 * 1024 + 1)
    except Exception:
        return None, "Falha ao ler o arquivo enviado."
    if len(dados) > max_mb * 1024 * 1024:
        return None, f"Arquivo maior que {max_mb} MB."
    if not dados:
        return None, "Arquivo vazio."
    fd, nome = tempfile.mkstemp(prefix="webimp_", suffix=".xlsx")
    with open(fd, "wb") as f:
        f.write(dados)
    return Path(nome), ""


def _pasta_modelos() -> Path:
    return get_project_root() / "MODELOS DE IMPORTACAO"


def _dir_previews() -> Path:
    """Pasta de prévias de importação (fora do cookie — cookie tem limite
    de ~4 KB nos navegadores e a prévia de certificados estourava)."""
    d = get_data_dir() / "tmp_importacoes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _limpar_previews_antigas() -> None:
    agora = time.time()
    for p in _dir_previews().glob("*.json"):
        try:
            if agora - p.stat().st_mtime > 24 * 3600:
                p.unlink(missing_ok=True)
        except OSError:
            continue


def _gravar_preview(rows: list) -> str:
    """Grava as linhas da prévia em arquivo; devolve o token para a session."""
    _limpar_previews_antigas()
    token = secrets.token_urlsafe(16)
    arquivo = _dir_previews() / f"{token}.json"
    arquivo.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return token


def _ler_preview(token: str) -> Optional[list]:
    """Lê e apaga a prévia gravada. None se token/arquivo inválido."""
    if not token or not isinstance(token, str) or "/" in token or "\\" in token:
        return None
    arquivo = _dir_previews() / f"{token}.json"
    if not arquivo.exists():
        return None
    try:
        rows = json.loads(arquivo.read_text(encoding="utf-8"))
    except Exception:
        return None
    finally:
        try:
            arquivo.unlink(missing_ok=True)
        except OSError:
            pass
    return rows if isinstance(rows, list) else None


def register(app, deps: dict):
    users = deps["users"]
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    def _via_fetch(request: Request) -> bool:
        return (request.headers.get("x-requested-with") or "").lower() == "fetch"

    def _iniciar_job(titulo: str, alvo) -> JSONResponse:
        """Roda `alvo(progresso)` em thread de fundo (roadmap 2.32.1).

        `alvo` devolve dict para a página de resultado (titulo/resumo/detalhes)
        ou {"redirect": url}. Caminho comum (sem fetch) permanece síncrono.
        """
        job = jobs.criar_job(titulo=titulo)
        jid = job["id"]

        def progresso(atual, total, nome):
            jobs.job_iniciar(jid, total)
            jobs.job_progresso(jid, atual, nome)

        def rodar():
            try:
                res = alvo(progresso)
                jobs.job_resultado(jid, res)
                jobs.job_finalizar(jid,
                                   redirect=f"/importacoes/resultado/{jid}")
            except Exception as e:
                from src.utils.error_log import log_error
                log_error("portal-job-importacao", e)
                jobs.job_finalizar(jid, erro_fatal=str(e))

        threading.Thread(target=rodar, daemon=True).start()
        return JSONResponse({"ok": True, "job": jid,
                             "status_url": f"/jobs/{jid}"})

    def _voltar_import(request: Request, erro: str):
        if _via_fetch(request):
            return JSONResponse({"ok": False, "erro": erro,
                                 "redirect": "/importacoes"})
        flash(request, erro=erro)
        return RedirectResponse("/importacoes", status_code=303)

    # ---------------- página principal ----------------
    @app.get("/importacoes")
    def importacoes(request: Request,
                    user: dict = auth.require_permission("importacoes")):
        pasta = _pasta_modelos()
        modelos = [{"slug": slug, "arquivo": nome,
                    "disponivel": (pasta / nome).exists()}
                   for slug, nome in _MODELOS.items()]
        return templates.TemplateResponse(
            request=request, name="importacoes.html",
            context=ctx(request, modelos=modelos,
                        pode_escrever=auth.pode_escrever(user["papel"], "importacoes")))

    @app.get("/importacoes/modelo/{slug}")
    def importacoes_modelo(request: Request, slug: str,
                           user: dict = auth.require_permission("importacoes")):
        nome = _MODELOS.get(slug)
        if not nome:
            return Response("Modelo não encontrado.", status_code=404)
        path = _pasta_modelos() / nome
        if not path.exists():
            return Response("Modelo não encontrado no servidor.", status_code=404)
        media = "text/plain; charset=utf-8" if slug == "leiame" else _MIME_XLSX
        return FileResponse(str(path), media_type=media, filename=nome)

    # ---------------- funcionários ----------------
    @app.post("/importacoes/funcionarios")
    async def imp_funcionarios(request: Request, arquivo: UploadFile = None,
                               user: dict = auth.require_permission("importacoes")):
        if not auth.pode_escrever(user["papel"], "importacoes"):
            return _voltar_import(request, "Somente administrador ou emissor podem importar.")
        from src.core.employee_repo import EmployeeRepository
        from src.utils.excel_importer import import_employees_from_excel
        caminho, erro = await ler_upload_xlsx(arquivo)
        if erro:
            return _voltar_import(request, erro)
        nome_arquivo = arquivo.filename

        def importar(progresso=None):
            try:
                importados, duplicados, erros, detalhes = \
                    import_employees_from_excel(str(caminho), EmployeeRepository(),
                                                on_progress=progresso)
            except Exception as e:
                importados, duplicados, erros, detalhes = 0, 0, 1, [f"Erro inesperado: {e}"]
            finally:
                try:
                    caminho.unlink(missing_ok=True)
                except OSError:
                    pass
            users.audit("importar-funcionarios", user["username"], nome_arquivo,
                        f"importados={importados}")
            return {"titulo": "Importação de funcionários",
                    "resumo": [("Importados", importados),
                               ("Já cadastrados (ignorados)", duplicados),
                               ("Linhas com erro", erros)],
                    "detalhes": detalhes}

        if _via_fetch(request):
            return _iniciar_job("Importação de funcionários", importar)

        resultado = importar()
        return templates.TemplateResponse(
            request=request, name="importacoes_resultado.html",
            context=ctx(request, titulo=resultado["titulo"],
                        resumo=resultado["resumo"],
                        detalhes=resultado["detalhes"]))

    # ---------------- certificados em lote (prévia + confirmar) ----------------
    @app.post("/importacoes/certificados")
    async def imp_certificados(request: Request, arquivo: UploadFile = None,
                               user: dict = auth.require_permission("importacoes")):
        if not auth.pode_escrever(user["papel"], "importacoes"):
            return _voltar_import(request, "Somente administrador ou emissor podem importar.")
        from src.core.employee_repo import EmployeeRepository
        from src.utils.batch_importer import (check_missing_employees,
                                              read_batch_spreadsheet)
        caminho, erro = await ler_upload_xlsx(arquivo)
        if erro:
            return _voltar_import(request, erro)
        try:
            rows, erros = read_batch_spreadsheet(str(caminho))
            faltando = check_missing_employees(rows, EmployeeRepository()) \
                if rows else []
        except Exception as e:
            rows, erros, faltando = [], [f"Erro ao ler a planilha: {e}"], []
        finally:
            try:
                caminho.unlink(missing_ok=True)
            except OSError:
                pass
        if not rows:
            return templates.TemplateResponse(
                request=request, name="importacoes_resultado.html",
                context=ctx(request, titulo="Importação de certificados",
                            resumo=[("Linhas válidas", 0)],
                            detalhes=erros or ["Nenhuma linha válida na planilha."]))
        # prévia vai em ARQUIVO no servidor (cookie de session estoura o
        # limite de ~4 KB dos navegadores e a lista nunca chegaria ao
        # /confirmar — bug "Nenhuma prévia pendente" com planilhas grandes)
        request.session["imp_cert_token"] = _gravar_preview(
            [{"nome": r["nome"], "nr_code": r["nr_code"],
              "data": r["data"].isoformat()} for r in rows])
        return templates.TemplateResponse(
            request=request, name="importacoes_preview.html",
            context=ctx(request, linhas=rows, erros=erros,
                        faltando=faltando, total=len(rows)))

    @app.post("/importacoes/certificados/confirmar")
    async def imp_certificados_confirmar(request: Request,
                                         user: dict = auth.require_permission("importacoes")):
        if not auth.pode_escrever(user["papel"], "importacoes"):
            return _voltar_import(request, "Somente administrador ou emissor podem importar.")
        from datetime import date as date_cls
        from src.core.certificate_service import CertificateService
        from src.core.employee_repo import EmployeeRepository
        from src.utils.batch_importer import generate_batch_certificates
        token = request.session.pop("imp_cert_token", None)
        sessao = _ler_preview(token) if token else None
        if not sessao:
            return _voltar_import(request, "Nenhuma prévia pendente — envie a planilha novamente.")
        rows = [{**r, "data": date_cls.fromisoformat(r["data"])} for r in sessao]

        def gerar(progresso=None, log_cb=None):
            try:
                resultado = generate_batch_certificates(
                    rows, EmployeeRepository(), CertificateService(),
                    on_progress=progresso, on_log=log_cb)
            except Exception as e:
                from src.utils.error_log import log_error
                log_error("portal-imp-certificados", e)
                return {"erro_fatal": "Falha ao gerar os certificados do lote."}
            users.audit("importar-certificados", user["username"], "",
                        f"gerados={resultado['gerados']}")
            return {"titulo": "Importação de certificados",
                    "resumo": [("PDFs gerados", resultado["gerados"]),
                               ("Registrados sem PDF (sem CPF)",
                                resultado["registrados_sem_pdf"]),
                               ("Erros", len(resultado["erros"]))],
                    "detalhes": resultado["erros"], "log": resultado["log"]}

        if _via_fetch(request):
            return _iniciar_job("Importação de certificados", gerar)

        resultado = gerar()
        if "erro_fatal" in resultado:
            flash(request, erro=resultado["erro_fatal"])
            return RedirectResponse("/importacoes", status_code=303)
        return templates.TemplateResponse(
            request=request, name="importacoes_resultado.html",
            context=ctx(request, titulo=resultado["titulo"],
                        resumo=resultado["resumo"], detalhes=resultado["detalhes"],
                        log=resultado["log"]))

    # ---------------- ASOs em lote ----------------
    @app.post("/importacoes/asos")
    async def imp_asos(request: Request, arquivo: UploadFile = None,
                       user: dict = auth.require_permission("importacoes")):
        if not auth.pode_escrever(user["papel"], "importacoes"):
            return _voltar_import(request, "Somente administrador ou emissor podem importar.")
        from src.core.aso_repo import AsoRepository
        from src.core.employee_repo import EmployeeRepository
        from src.utils.aso_importer import import_asos_from_excel
        caminho, erro = await ler_upload_xlsx(arquivo)
        if erro:
            return _voltar_import(request, erro)
        nome_arquivo = arquivo.filename

        def importar(progresso=None):
            try:
                resultado = import_asos_from_excel(str(caminho), AsoRepository(),
                                                   EmployeeRepository(),
                                                   on_progress=progresso)
            except Exception as e:
                resultado = {"criados": [], "erros": 1,
                             "detalhes": [f"Erro inesperado: {e}"]}
            finally:
                try:
                    caminho.unlink(missing_ok=True)
                except OSError:
                    pass
            users.audit("importar-asos", user["username"], nome_arquivo,
                        f"criados={len(resultado['criados'])}")
            return {"titulo": "Importação de ASOs",
                    "resumo": [("ASOs criados", len(resultado["criados"])),
                               ("Linhas com erro", resultado["erros"])],
                    "detalhes": resultado["detalhes"],
                    "criados": resultado["criados"]}

        if _via_fetch(request):
            return _iniciar_job("Importação de ASOs", importar)

        resultado = importar()
        return templates.TemplateResponse(
            request=request, name="importacoes_resultado.html",
            context=ctx(request, titulo=resultado["titulo"],
                        resumo=resultado["resumo"],
                        detalhes=resultado["detalhes"],
                        criados=resultado["criados"]))

    # ---------------- lista de bloqueios (alimenta Cartões) ----------------
    @app.post("/importacoes/cartoes")
    async def imp_cartoes(request: Request, arquivo: UploadFile = None,
                          user: dict = auth.require_permission("importacoes")):
        if not auth.pode_escrever(user["papel"], "importacoes"):
            return _voltar_import(request, "Somente administrador ou emissor podem importar.")
        from src.core.employee_repo import EmployeeRepository
        from src.utils.blocking_importer import import_blocking_list
        caminho, erro = await ler_upload_xlsx(arquivo)
        if erro:
            return _voltar_import(request, erro)
        nome_arquivo = arquivo.filename

        def importar(progresso=None):
            try:
                encontrados, fora = import_blocking_list(str(caminho),
                                                         EmployeeRepository(),
                                                         on_progress=progresso)
            except Exception as e:
                return {"erro_fatal": f"Falha ao ler a planilha ({e})."}
            finally:
                try:
                    caminho.unlink(missing_ok=True)
                except OSError:
                    pass
            if encontrados:
                sel = ",".join(str(e.id) for e in encontrados)
                msg = (f"{len(encontrados)} funcionário(s) da lista prontos "
                       f"para emissão.")
                if fora:
                    msg += f" Sem correspondência: {', '.join(fora)}."
                users.audit("importar-cartoes", user["username"], nome_arquivo,
                            f"encontrados={len(encontrados)}")
                return {"redirect": f"/cartoes/novo?sel={sel}", "msg": msg}
            return {"erro_fatal": "Nenhum funcionário da planilha foi "
                                  "encontrado no cadastro."
                                  + (f" Fora da lista: {', '.join(fora)}."
                                     if fora else "")}

        if _via_fetch(request):
            return _iniciar_job("Importação de cartões", importar)

        resultado = importar()
        if "erro_fatal" in resultado:
            flash(request, erro=resultado["erro_fatal"])
            return RedirectResponse("/importacoes", status_code=303)
        flash(request, msg=resultado["msg"])
        return RedirectResponse(resultado["redirect"], status_code=303)

    # ---------------- resultado de jobs (progresso 2.32.1) ----------------
    @app.get("/importacoes/resultado/{jid}")
    def imp_resultado(jid: str, request: Request,
                      user: dict = auth.require_permission("importacoes")):
        data = jobs.dados_resultado(jid)
        if not data or data.get("resultado") is None:
            flash(request, erro="Resultado não encontrado ou expirado.")
            return RedirectResponse("/importacoes", status_code=303)
        res = data["resultado"]
        if res.get("redirect"):
            if res.get("msg"):
                flash(request, msg=res["msg"])
            return RedirectResponse(res["redirect"], status_code=303)
        return templates.TemplateResponse(
            request=request, name="importacoes_resultado.html",
            context=ctx(request, titulo=res.get("titulo", ""),
                        resumo=res.get("resumo", []),
                        detalhes=res.get("detalhes", []),
                        log=res.get("log"), criados=res.get("criados")))
