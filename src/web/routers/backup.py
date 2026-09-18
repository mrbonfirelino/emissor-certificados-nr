"""Portal Web — Backups (admin).

Fase 4: dispara backup manual e lista os existentes. Sem restore pela web
(substituiria o banco em uso).
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from src.web import auth

_PER_PAGE = 20


def _br_dt(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "—"


def register(app, deps):
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    @app.get("/backup")
    def backup_lista(request: Request, page: int = 1,
                     user: dict = auth.require_permission("backup")):
        from src.core.backup_manager import BackupManager
        arquivos = BackupManager(start_jobs=False).list_backups()
        itens = []
        for p in arquivos:
            path = Path(p)
            try:
                tam = path.stat().st_size
            except OSError:
                tam = 0
            itens.append({
                "nome": path.name,
                "path": str(path),
                "tam_kb": max(1, tam // 1024),
                "quando": _br_dt(path.stat().st_mtime) if tam else "—",
            })
        itens.reverse()
        total = len(itens)
        paginas = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)
        page = max(1, min(page, paginas))
        return templates.TemplateResponse(
            request, "backup.html",
            ctx(request,
                itens=itens[(page - 1) * _PER_PAGE:page * _PER_PAGE],
                total=total, page=page, paginas=paginas,
                pg_base="/backup"))

    @app.get("/backup/{nome}/download")
    def backup_download(nome: str, request: Request,
                        user: dict = auth.require_permission("backup")):
        from src.core.backup_manager import BackupManager
        # anti-traversal: só serve arquivos que estão na lista do manager
        for p in BackupManager(start_jobs=False).list_backups():
            if Path(p).name == nome:
                return FileResponse(
                    str(p), media_type="application/octet-stream",
                    filename=nome)
        flash(request, erro="Backup não encontrado.")
        return RedirectResponse("/backup", status_code=303)

    @app.post("/backup/criar")
    def backup_criar(request: Request,
                     user: dict = auth.require_permission("backup")):
        from src.core.backup_manager import BackupManager
        try:
            caminho = BackupManager(start_jobs=False).create_backup()
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("portal-backup", e)
            flash(request, erro=f"Falha ao gerar backup: {e}")
            return RedirectResponse("/backup", status_code=303)
        if caminho:
            users = deps["users"]
            try:
                users.audit("backup-manual", user["username"], Path(caminho).name)
            except Exception:
                pass
            flash(request, msg=f"Backup gerado: {Path(caminho).name}")
        else:
            flash(request, erro="O backup não foi gerado (verifique o log).")
        return RedirectResponse("/backup", status_code=303)
