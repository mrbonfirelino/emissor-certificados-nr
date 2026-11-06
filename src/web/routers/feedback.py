"""Feedback de usuarios (v1.87.0).

- POST /feedbacks/enviar       qualquer usuario logado envia texto + anexos
- GET  /feedbacks              SOMENTE admin: lista de feedbacks
- POST /feedbacks/{id}/arquivar  admin arquiva com motivo
- GET  /feedbacks/{id}/anexo/{nome}  download do anexo
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse

from src.web import auth
from src.core.feedback_repo import FeedbackRepository
from src.utils.error_log import log_error

_MIME = {"pdf": "application/pdf", "jpg": "image/jpeg",
         "jpeg": "image/jpeg", "png": "image/png"}
_ANEXO_MAX = 50 * 1024 * 1024  # por arquivo
_MAX_ANEXOS = 8

_MOTIVOS = ["Realizado", "Corrigido", "Cancelado"]


def register(app, deps):
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]
    users = deps["users"]
    router = APIRouter()

    @router.post("/feedbacks/enviar")
    async def enviar(request: Request,
                     texto: str = Form(""),
                     pagina: str = Form(""),
                     anexo: list[UploadFile] = File(None),
                     user=Depends(auth.require_user)):
        """Qualquer usuario logado pode enviar feedback (botao do header)."""
        texto = (texto or "").strip()
        if not texto:
            flash(request, erro="Escreva o feedback antes de enviar.")
            return RedirectResponse(request.headers.get("referer") or "/",
                                    status_code=303)
        anexos = []
        ok = True
        for f in (anexo or [])[:_MAX_ANEXOS]:
            if not f or not f.filename:
                continue
            ext = Path(f.filename).suffix.lower().lstrip(".")
            if ext not in _MIME:
                flash(request, erro=f"Anexo '{f.filename}' ignorado: formato não "
                                    "permitido (use PDF, JPG ou PNG).")
                continue
            dados = await f.read()
            if len(dados) > _ANEXO_MAX:
                flash(request, erro=f"Anexo '{f.filename}' ignorado: maior que 50 MB.")
                continue
            anexos.append((dados, f.filename))
        try:
            repo = FeedbackRepository()
            fb_criado = repo.add(texto, (user.get("username") or ""),
                                 (pagina or "").strip(), anexos)
            fid = fb_criado.get("id") if isinstance(fb_criado, dict) else fb_criado
        except Exception as e:
            ok = False
            log_error("portal-feedback", e)
        if ok:
            try:
                users.audit("feedback-enviar", user.get("username", ""), fid,
                            (pagina or "")[:80])
            except Exception:
                pass
            flash(request, msg="Feedback enviado. Obrigado!")
        else:
            flash(request, erro="Não foi possível salvar o feedback.")
        return RedirectResponse(request.headers.get("referer") or "/",
                                status_code=303)

    @router.get("/feedbacks")
    def lista(request: Request, user=auth.require_permission("feedbacks"),
              busca: str = "", arquivado: str = "nao"):
        repo = FeedbackRepository()
        busca = (busca or "").strip()
        arquivado = arquivado if arquivado in ("nao", "sim", "todos") else "nao"
        itens = repo.list(arquivado=arquivado, busca=busca)
        for it in itens:  # data_hora ISO -> dd/mm/aaaa hh:mm
            dh = it.get("data_hora") or ""
            it["data_br"] = (f"{dh[8:10]}/{dh[5:7]}/{dh[0:4]} "
                             f"{dh[11:16]}") if len(dh) >= 16 else dh
        return templates.TemplateResponse(request, "feedbacks.html", ctx(
            request, user=user,
            itens=itens, busca=busca, arquivado=arquivado,
            motivos=_MOTIVOS,
            abertos=repo.contagem_abertos(),
        ))

    @router.post("/feedbacks/{fid}/arquivar")
    async def arquivar(request: Request, fid: str,
                       user=auth.require_permission("feedbacks"),
                       motivo: str = Form("")):
        it = FeedbackRepository().get(fid)
        if it is None:
            flash(request, erro="Feedback não encontrado.")
            return RedirectResponse("/feedbacks", status_code=303)
        motivo = (motivo or "").strip()
        if not motivo:
            flash(request, erro="Informe o motivo do arquivamento.")
            return RedirectResponse("/feedbacks", status_code=303)
        FeedbackRepository().arquivar(fid, motivo)
        try:
            users.audit("feedback-arquivar", user.get("username", ""), fid,
                        motivo[:80])
        except Exception:
            pass
        flash(request, msg=f"Feedback {fid} arquivado ({motivo}).")
        return RedirectResponse("/feedbacks", status_code=303)

    @router.get("/feedbacks/{fid}/anexo/{nome}")
    def anexo(fid: str, nome: str, user=auth.require_permission("feedbacks")):
        cam = FeedbackRepository().caminho_anexo(fid, nome)
        if cam is None or not cam.exists():
            return RedirectResponse("/feedbacks", status_code=303)
        ext = cam.suffix.lower().lstrip(".")
        return FileResponse(cam, media_type=_MIME.get(ext, "application/octet-stream"),
                            filename=cam.name)

    app.include_router(router)
