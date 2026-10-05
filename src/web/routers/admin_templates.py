"""Admin: editor de templates NR (templates/NR-XX.template.json).

Somente papel admin (módulo 'config'). Salva backup .bak antes de gravar
e valida o JSON com NRTemplate antes de escrever em disco.
"""
from pathlib import Path
import json
import shutil
import sys
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

from src.web import auth
from src.web.permissions import pode_escrever
from src.core.template_loader import list_available_nrs, load_nr_template
from src.core.models import NRTemplate
from src.utils.paths import get_templates_dir


def _caminho(nr_code: str) -> Path:
    return get_templates_dir() / f"{nr_code}.template.json"


def _raw(nr_code: str) -> Optional[dict]:
    p = _caminho(nr_code)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def register(app, deps: dict):
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]
    users = deps["users"]

    def _admin(request: Request) -> Optional[dict]:
        user = auth.current_user(request)
        if not user or user.get("papel") != "admin":
            return None
        return user

    # ---------------- lista ----------------
    @app.get("/admin/templates")
    async def lista(request: Request,
                    user: dict = auth.require_permission("config")):
        if _admin(request) is None:
            flash(request, erro="Acesso restrito ao administrador.")
            return RedirectResponse("/", status_code=303)
        itens = []
        for nr in sorted(list_available_nrs()):
            raw = _raw(nr) or {}
            tmpl = load_nr_template(nr)
            itens.append({
                "nr": nr,
                "nome": (tmpl.nr_name if tmpl else raw.get("nr_name", "—")),
                "carga": raw.get("carga_horaria_minima", "—"),
                "validade": raw.get("validade_meses", "—"),
                "tem_bak": _caminho(nr + ".bak").exists()
                           or Path(str(_caminho(nr)) + ".bak").exists(),
            })
        return templates.TemplateResponse(request, "admin_templates.html",
                                          ctx(request, itens=itens))

    # ---------------- formulário ----------------
    @app.get("/admin/templates/{nr_code}")
    async def form(request: Request, nr_code: str,
                   user: dict = auth.require_permission("config")):
        if _admin(request) is None:
            flash(request, erro="Acesso restrito ao administrador.")
            return RedirectResponse("/", status_code=303)
        raw = _raw(nr_code)
        if raw is None:
            flash(request, erro=f"Template {nr_code} não encontrado.")
            return RedirectResponse("/admin/templates", status_code=303)
        tmpl = load_nr_template(nr_code)
        tem_bak = Path(str(_caminho(nr_code)) + ".bak").exists()
        return templates.TemplateResponse(request, "admin_template_form.html",
                                          ctx(request,
                                              nr=nr_code,
                                              raw=raw,
                                              tmpl=tmpl,
                                              riscos_txt="\n".join(raw.get("riscos", [])),
                                              conteudo_txt="\n".join(raw.get("conteudo_programatico", [])),
                                              extras_txt="\n".join(
                                                  json.dumps(e, ensure_ascii=False)
                                                  for e in raw.get("campos_extra", [])),
                                              tem_bak=tem_bak))

    # ---------------- salvar ----------------
    @app.post("/admin/templates/{nr_code}/salvar")
    async def salvar(request: Request, nr_code: str,
                     user: dict = auth.require_permission("config")):
        u = _admin(request)
        if u is None:
            flash(request, erro="Acesso restrito ao administrador.")
            return RedirectResponse("/", status_code=303)
        form = await request.form()
        raw = _raw(nr_code)
        if raw is None:
            flash(request, erro=f"Template {nr_code} não encontrado.")
            return RedirectResponse("/admin/templates", status_code=303)

        # campos_extra: 1 JSON por linha
        extras = []
        for linha in (form.get("campos_extra") or "").splitlines():
            linha = linha.strip()
            if not linha:
                continue
            try:
                obj = json.loads(linha)
            except Exception:
                flash(request, erro=f"Campo extra inválido (JSON): {linha[:60]}")
                return RedirectResponse(f"/admin/templates/{nr_code}", status_code=303)
            if not isinstance(obj, dict) or not obj.get("id") or not obj.get("label"):
                flash(request, erro="Cada campo extra precisa de 'id' e 'label'.")
                return RedirectResponse(f"/admin/templates/{nr_code}", status_code=303)
            extras.append(obj)

        def _linhas(txt):
            return [l.strip() for l in (txt or "").splitlines() if l.strip()]

        data = dict(raw)
        data["nr_name"] = (form.get("nr_name") or "").strip() or raw.get("nr_name", nr_code)
        try:
            data["carga_horaria_minima"] = max(1, int(form.get("carga_horaria_minima") or 1))
        except (TypeError, ValueError):
            data["carga_horaria_minima"] = raw.get("carga_horaria_minima", 8)
        try:
            data["validade_meses"] = max(1, int(form.get("validade_meses") or 12))
        except (TypeError, ValueError):
            data["validade_meses"] = raw.get("validade_meses", 12)
        data["descricao_padrao"] = (form.get("descricao_padrao") or "").strip()
        data["riscos"] = _linhas(form.get("riscos"))
        data["conteudo_programatico"] = _linhas(form.get("conteudo_programatico"))
        data["campos_extra"] = extras

        # valida antes de gravar
        try:
            NRTemplate(**data)
        except Exception as e:
            flash(request, erro=f"Dados inválidos para o template: {e}")
            return RedirectResponse(f"/admin/templates/{nr_code}", status_code=303)

        path = _caminho(nr_code)
        try:
            if path.exists():
                shutil.copy2(str(path), str(path) + ".bak")
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        except PermissionError:
            flash(request, erro="Sem permissão para gravar o arquivo do template.")
            return RedirectResponse(f"/admin/templates/{nr_code}", status_code=303)
        users.audit("editar-template", u.get("username", ""), nr_code,
                    "template NR atualizado")
        flash(request, msg=f"Template {nr_code} salvo (backup .bak criado).")
        return RedirectResponse(f"/admin/templates/{nr_code}", status_code=303)

    # ---------------- restaurar backup ----------------
    @app.post("/admin/templates/{nr_code}/restaurar")
    async def restaurar(request: Request, nr_code: str,
                        user: dict = auth.require_permission("config")):
        u = _admin(request)
        if u is None:
            flash(request, erro="Acesso restrito ao administrador.")
            return RedirectResponse("/", status_code=303)
        bak = Path(str(_caminho(nr_code)) + ".bak")
        path = _caminho(nr_code)
        if not bak.exists():
            flash(request, erro="Nenhum backup .bak disponível para este template.")
            return RedirectResponse(f"/admin/templates/{nr_code}", status_code=303)
        try:
            shutil.copy2(str(bak), str(path))
        except PermissionError:
            flash(request, erro="Sem permissão para restaurar o arquivo.")
            return RedirectResponse(f"/admin/templates/{nr_code}", status_code=303)
        users.audit("restaurar-template", u.get("username", ""), nr_code,
                    "template restaurado do .bak")
        flash(request, msg=f"Template {nr_code} restaurado do backup.")
        return RedirectResponse(f"/admin/templates/{nr_code}", status_code=303)
