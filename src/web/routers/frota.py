"""Portal Web — Gestão de Frota (ROADMAP 2.29, v1.33.0).

Veículos, empresas de veículos, fornecedores, documentos (pasta virtual),
laudos com vencimento, movimentações (saída/entrada) e solicitações de
abastecimento com PDF. Escrita exige admin/emissor; consulta navega em
modo leitura.
"""

from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote_plus

from fastapi import Request, Form, UploadFile, File
from fastapi.responses import (
    RedirectResponse, Response, FileResponse,
)

from src.web import auth
from src.web.permissions import pode_escrever
from src.core.frota_repo import (
    FrotaRepository, TIPOS_VEICULO, SUBTIPOS_CAMINHAO, TIPOS_COMBUSTIVEL,
    TIPOS_LAUDO, CARROCERIAS, CHECKLIST_GRUPOS, CHECKLIST_DIAS,
    label_tipo, label_subtipo, label_combustivel,
    label_laudo, veiculo_rotulo,
)

_PER_PAGE = 20
_PER_OPCOES = (10, 20, 25, 50)
_MIME = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg",
         "png": "image/png", "gif": "image/gif", "txt": "text/plain"}

# 2.29.7: Arla/Diesel/Arla+Diesel não são combustíveis de carro de passeio
_TIPOS_SEM_DIESEL = {"carro"}
_COMB_BLOQUEADOS_LEVES = {"arla", "diesel", "arla_diesel"}

# tags para documentos do veículo (2.29.7)
TAGS_DOC = [
    ("manutencao", "Manutenção (Nota Fiscal)"),
    ("documento", "Documento"),
    ("abastecimento", "Abastecimento"),
    ("outros", "Outros"),
]


def _br(iso) -> str:
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return ""


def _iso(data_br: str) -> str:
    """dd/mm/aaaa -> aaaa-mm-dd (None se inválida)."""
    try:
        return datetime.strptime((data_br or "").strip(),
                                 "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _mime(tipo: str) -> str:
    return _MIME.get((tipo or "").lower(), "application/octet-stream")


def register(app, deps):
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]
    users = deps["users"]

    def _audit(request: Request, acao: str, username: str,
               alvo: str = "", detalhe: str = ""):
        try:
            users.audit(acao, username, alvo, detalhe)
        except Exception:
            pass

    def _bloqueio(request: Request, user: dict, url: str):
        if pode_escrever(user["papel"], "frota"):
            return None
        flash(request, erro="Seu papel é somente leitura neste módulo.")
        return RedirectResponse(url, status_code=303)

    def _repo() -> FrotaRepository:
        return FrotaRepository()

    def _paginacao(request: Request, total: int, page: int, per: int = _PER_PAGE):
        total_paginas = max(1, (total + per - 1) // per)
        page = min(max(1, page), total_paginas)
        return page, total_paginas

    def _funcionarios_nomes() -> list:
        try:
            from src.core.employee_repo import EmployeeRepository
            return sorted(
                (e.nome or "" for e in
                 EmployeeRepository().get_all(limit=100000) if e.nome))
        except Exception:
            return []

    # ================= veiculos =================

    _STATUS_FROTA = {
        "viagem": ("Em Viagem", "b-azul"),
        "manutencao": ("Em Manutenção", "b-amarelo"),
        "indisponivel": ("Indisponível", "b-cinza"),
        "disponivel": ("Disponível", "b-verde"),
    }

    def _status_veiculo(repo, v: dict):
        """Deriva status/motorista/destino: viagem > manutenção/indisponível > disponível."""
        vid = v["id"]
        movs = repo.list_movimentacoes(vid)
        aberta = next((m for m in movs if m["aberta"]), None)
        pior = None
        for m in repo.list_manutencoes(vid):
            if pior is None or m["restante"] < pior["restante"]:
                pior = m
        if aberta:
            status, motorista, destino = "viagem", aberta["motorista"], aberta["destino"]
        elif pior and pior["status"] == "vencido":
            status, motorista, destino = "indisponivel", "", ""
        elif pior and pior["status"] == "urgente":
            status, motorista, destino = "manutencao", "", ""
        else:
            status, motorista, destino = "disponivel", "", ""
        if status != "viagem" and not v["proprio"] and v.get("fim_contrato_aluguel") \
                and v["fim_contrato_aluguel"] < date.today().isoformat():
            status = "indisponivel"
        label, classe = _STATUS_FROTA[status]
        v["status"] = status
        v["status_label"] = label
        v["status_classe"] = classe
        v["motorista_atual"] = motorista or ""
        v["destino_atual"] = destino or ""

    @app.get("/frota")
    def frota_lista(request: Request, busca: str = "", page: int = 1,
                    per: int = 20,
                    user: dict = auth.require_permission("frota")):
        repo = _repo()
        per_val = per if per in _PER_OPCOES else 20
        pagina = max(1, page)
        veiculos, total = repo.list_veiculos(busca=busca,
                                             limit=per_val,
                                             offset=(pagina - 1) * per_val)
        for v in veiculos:
            v["rotulo"] = veiculo_rotulo(v)
            v["tipo_label"] = label_tipo(v["tipo"])
            v["sub_label"] = label_subtipo(v["subtipo"])
            v["posse"] = "Próprio" if v["proprio"] else \
                f"Alugado — {v['contratante'] or '?'}"
            _status_veiculo(repo, v)
        page_n, paginas = _paginacao(request, total, pagina, per_val)
        qs = f"busca={quote_plus((busca or '').strip())}" \
            if (busca or "").strip() else ""
        if per_val != 20:
            qs = (qs + "&" if qs else "") + f"per={per_val}"
        return templates.TemplateResponse(
            request=request, name="frota.html",
            context=ctx(request, veiculos=veiculos, total=total,
                        busca=(busca or "").strip(), page=page_n,
                        paginas=paginas,
                        per=per_val, per_opcoes=_PER_OPCOES,
                        pg_base=("/frota?" + qs) if qs else "/frota",
                        pode_escrever=auth.pode_escrever(user["papel"],
                                                         "frota")))

    def _form_context(v=None, erro: str = "", valores: dict = None):
        emp_opts = sorted(_repo().list_empresas(), key=lambda e: e["nome"])
        vals = valores or {}
        return dict(
            v=v, erro=erro, emp_opts=emp_opts,
            tipos=TIPOS_VEICULO, subtipos=SUBTIPOS_CAMINHAO,
            carroc=CARROCERIAS,
            f_modelo=vals.get("modelo", v["modelo"] if v else ""),
            f_marca=vals.get("marca", v["marca"] if v else ""),
            f_tipo=vals.get("tipo", v["tipo"] if v else "carro"),
            f_subtipo=vals.get("subtipo", v["subtipo"] if v else ""),
            f_placa=vals.get("placa", v["placa"] if v else ""),
            f_proprio=vals.get("proprio", bool(v["proprio"]) if v else True),
            f_contratante=vals.get("contratante",
                                   v["contratante"] if v else ""),
            f_empresa_id=vals.get("empresa_id",
                                  v["empresa_id"] if v else None),
            f_obs=vals.get("obs", v["obs"] if v else ""),
            f_cor=vals.get("cor", v["cor"] if v else ""),
            f_carroceria=vals.get("carroceria",
                                  v["carroceria"] if v else ""),
            f_ano=vals.get("ano", v["ano"] if v else ""),
            f_fim_contrato=vals.get("fim_contrato_aluguel",
                                    _br(v["fim_contrato_aluguel"])
                                    if v else ""),
            f_km_l=vals.get("km_l_esperado",
                            v["km_l_esperado"] if v else ""),
        )

    @app.get("/frota/novo")
    def frota_novo(request: Request,
                   user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota")
        if red:
            return red
        return templates.TemplateResponse(
            request=request, name="frota_form.html",
            context=ctx(request, **_form_context()))

    def _campos_extras(cor: str, carroceria: str, ano: str,
                       fim_contrato: str, km_l: str):
        fim_iso = _iso(fim_contrato)
        if fim_contrato and fim_contrato.strip() and fim_iso is None:
            raise ValueError("Data de fim do contrato inválida (dd/mm/aaaa).")
        try:
            km_l_val = float(str(km_l).replace(",", "."))
        except (TypeError, ValueError):
            km_l_val = None
        return dict(cor=cor, carroceria=carroceria, ano=ano,
                    fim_contrato_aluguel=fim_iso, km_l_esperado=km_l_val)

    @app.post("/frota/criar")
    def frota_criar(request: Request, modelo: str = Form(""),
                    marca: str = Form(""), tipo: str = Form(""),
                    subtipo: str = Form(""), placa: str = Form(""),
                    proprio: str = Form(""), contratante: str = Form(""),
                    empresa_id: str = Form(""), obs: str = Form(""),
                    cor: str = Form(""), carroceria: str = Form(""),
                    ano: str = Form(""), fim_contrato: str = Form(""),
                    km_l: str = Form(""),
                    user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota")
        if red:
            return red
        vals = dict(modelo=modelo, marca=marca, tipo=tipo, subtipo=subtipo,
                    placa=placa, proprio=proprio == "1",
                    contratante=contratante, empresa_id=empresa_id, obs=obs,
                    cor=cor, carroceria=carroceria, ano=ano,
                    fim_contrato_aluguel=fim_contrato, km_l_esperado=km_l)
        try:
            extras = _campos_extras(cor, carroceria, ano, fim_contrato, km_l)
            emp_id = int(empresa_id) if empresa_id else None
            novo = _repo().add_veiculo(
                modelo, marca, tipo, subtipo, placa, vals["proprio"],
                contratante, emp_id, obs, **extras)
        except ValueError as e:
            return templates.TemplateResponse(
                request=request, name="frota_form.html",
                context=ctx(request, **_form_context(erro=str(e),
                                                     valores=vals)))
        _audit(request, "frota-veiculo-criar", user["username"],
               str(novo), f"{modelo} {placa}")
        flash(request, msg="Veículo cadastrado.")
        return RedirectResponse(f"/frota/{novo}", status_code=303)

    @app.get("/frota/{veiculo_id}/editar")
    def frota_editar(veiculo_id: int, request: Request,
                     user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        v = _repo().get_veiculo(veiculo_id)
        if not v:
            flash(request, erro="Veículo não encontrado.")
            return RedirectResponse("/frota", status_code=303)
        return templates.TemplateResponse(
            request=request, name="frota_form.html",
            context=ctx(request, **_form_context(v=v)))

    @app.post("/frota/{veiculo_id}/editar")
    def frota_salvar(veiculo_id: int, request: Request,
                     modelo: str = Form(""), marca: str = Form(""),
                     tipo: str = Form(""), subtipo: str = Form(""),
                     placa: str = Form(""), proprio: str = Form(""),
                     contratante: str = Form(""), empresa_id: str = Form(""),
                     obs: str = Form(""), cor: str = Form(""),
                     carroceria: str = Form(""), ano: str = Form(""),
                     fim_contrato: str = Form(""), km_l: str = Form(""),
                     user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        vals = dict(modelo=modelo, marca=marca, tipo=tipo, subtipo=subtipo,
                    placa=placa, proprio=proprio == "1",
                    contratante=contratante, empresa_id=empresa_id, obs=obs,
                    cor=cor, carroceria=carroceria, ano=ano,
                    fim_contrato_aluguel=fim_contrato, km_l_esperado=km_l)
        try:
            extras = _campos_extras(cor, carroceria, ano, fim_contrato, km_l)
            emp_id = int(empresa_id) if empresa_id else None
            _repo().update_veiculo(
                veiculo_id, modelo, marca, tipo, subtipo, placa,
                vals["proprio"], contratante, emp_id, obs, **extras)
        except ValueError as e:
            v = _repo().get_veiculo(veiculo_id)
            return templates.TemplateResponse(
                request=request, name="frota_form.html",
                context=ctx(request, **_form_context(v=v, erro=str(e),
                                                     valores=vals)))
        _audit(request, "frota-veiculo-editar", user["username"],
               str(veiculo_id), f"{modelo} {placa}")
        flash(request, msg="Veículo atualizado.")
        return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)

    @app.post("/frota/{veiculo_id}/excluir")
    def frota_excluir(veiculo_id: int, request: Request,
                      user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota")
        if red:
            return red
        v = _repo().get_veiculo(veiculo_id)
        if not v:
            flash(request, erro="Veículo não encontrado.")
            return RedirectResponse("/frota", status_code=303)
        try:
            _repo().delete_veiculo(veiculo_id)
            _audit(request, "frota-veiculo-excluir", user["username"],
                   str(veiculo_id), veiculo_rotulo(v))
            flash(request, msg=f"Veículo '{veiculo_rotulo(v)}' excluído.")
        except ValueError as e:
            flash(request, erro=str(e))
        return RedirectResponse("/frota", status_code=303)

    @app.post("/frota/{veiculo_id}/foto")
    async def frota_foto_upload(veiculo_id: int, request: Request,
                                arquivo: UploadFile = File(None),
                                user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        if arquivo is None or not arquivo.filename:
            flash(request, erro="Selecione uma imagem.")
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        data = await arquivo.read()
        ext = Path(arquivo.filename).suffix.lower().lstrip(".")
        tipo = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "gif": "gif",
                "webp": "webp"}.get(ext)
        try:
            if tipo is None:
                raise ValueError("Formato não suportado (use JPG, PNG, GIF"
                                 " ou WEBP).")
            _repo().update_foto(veiculo_id, data, tipo)
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        flash(request, msg="Foto atualizada.")
        return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)

    @app.get("/frota/{veiculo_id}/foto")
    def frota_foto(veiculo_id: int):
        f = _repo().get_foto(veiculo_id)
        if not f:
            return Response(status_code=404)
        return Response(content=f["dados"],
                        media_type=f"image/{'jpeg' if f['tipo'] == 'jpg' else f['tipo']}")

    @app.get("/frota/exportar")
    def frota_exportar(request: Request,
                       user: dict = auth.require_permission("frota")):
        """2.29.7: exporta a frota para Excel (base para reimportar)."""
        import io
        import openpyxl
        veiculos, _t = _repo().list_veiculos(limit=100000, offset=0)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Veiculos"
        ws.append(["Modelo", "Marca", "Tipo", "Subtipo", "Placa", "Proprio",
                   "Contratante", "Empresa", "Cor", "Carroceria", "Ano",
                   "Fim do contrato", "KM/L esperado", "Obs"])
        for v in veiculos:
            ws.append([
                v["modelo"], v["marca"] or "", label_tipo(v["tipo"]),
                label_subtipo(v["subtipo"]) if v["subtipo"] else "",
                v["placa"] or "", "Sim" if v["proprio"] else "Não",
                v["contratante"] or "", v["empresa_nome"] or "",
                v["cor"] or "", label_subtipo(v["carroceria"])
                if v["carroceria"] in ("hatch", "sedan") else (v["carroceria"]
                                                               or ""),
                v["ano"] or "",
                _br(v["fim_contrato_aluguel"])
                if v["fim_contrato_aluguel"] else "",
                v["km_l_esperado"] or "", v["obs"] or "",
            ])
        buf = io.BytesIO()
        wb.save(buf)
        wb.close()
        _audit(request, "frota-exportar", user["username"], "",
               f"{len(veiculos)} veiculo(s)")
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument"
                       ".spreadsheetml.sheet",
            headers={"Content-Disposition":
                     'attachment; filename="veiculos.xlsx"'})

    @app.post("/frota/importar")
    async def frota_importar(request: Request,
                             arquivo: UploadFile = File(None),
                             user: dict = auth.require_permission("frota")):
        """2.29.7: importa veículos de planilha (modelo MODELO VEICULOS.xlsx)."""
        red = _bloqueio(request, user, "/frota")
        if red:
            return red
        from src.web.routers.importacoes import ler_upload_xlsx
        caminho, erro = await ler_upload_xlsx(arquivo)
        if erro:
            flash(request, erro=erro)
            return RedirectResponse("/frota", status_code=303)
        try:
            from src.utils.veiculo_importer import import_veiculos_from_excel
            importados, erros = import_veiculos_from_excel(
                caminho, _repo())
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("portal-frota-importar", e)
            flash(request, erro=f"Falha ao ler a planilha: {e}")
            return RedirectResponse("/frota", status_code=303)
        finally:
            try:
                caminho.unlink()
            except OSError:
                pass
        if erros:
            resumo = "; ".join(erros[:5])
            if len(erros) > 5:
                resumo += f" (e mais {len(erros) - 5} erro(s))"
            flash(request, msg=f"{importados} veículo(s) importado(s).",
                  erro=resumo)
        else:
            flash(request, msg=f"{importados} veículo(s) importado(s).")
        _audit(request, "frota-importar", user["username"], "",
               f"{importados} importado(s), {len(erros)} erro(s)")
        return RedirectResponse("/frota", status_code=303)

    # ================= empresas de veiculos =================

    @app.get("/frota/empresas")
    def frota_empresas(request: Request,
                       user: dict = auth.require_permission("frota")):
        return templates.TemplateResponse(
            request=request, name="frota_empresas.html",
            context=ctx(request, empresas=_repo().list_empresas(),
                        pode_escrever=auth.pode_escrever(user["papel"],
                                                         "frota")))

    @app.post("/frota/empresas/criar")
    def frota_empresa_criar(request: Request, nome: str = Form(""),
                            cnpj: str = Form(""),
                            user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota/empresas")
        if red:
            return red
        try:
            _repo().add_empresa(nome, cnpj)
            flash(request, msg="Empresa cadastrada.")
        except ValueError as e:
            flash(request, erro=str(e))
        return RedirectResponse("/frota/empresas", status_code=303)

    @app.post("/frota/empresas/{empresa_id}/editar")
    def frota_empresa_editar(empresa_id: int, request: Request,
                             nome: str = Form(""), cnpj: str = Form(""),
                             user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota/empresas")
        if red:
            return red
        try:
            _repo().update_empresa(empresa_id, nome, cnpj)
            flash(request, msg="Empresa atualizada.")
        except ValueError as e:
            flash(request, erro=str(e))
        return RedirectResponse("/frota/empresas", status_code=303)

    @app.post("/frota/empresas/{empresa_id}/excluir")
    def frota_empresa_excluir(empresa_id: int, request: Request,
                              user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota/empresas")
        if red:
            return red
        try:
            _repo().delete_empresa(empresa_id)
            flash(request, msg="Empresa excluída.")
        except ValueError as e:
            flash(request, erro=str(e))
        return RedirectResponse("/frota/empresas", status_code=303)

    # ================= fornecedores =================

    @app.get("/frota/fornecedores")
    def frota_fornecedores(request: Request,
                           user: dict = auth.require_permission("frota")):
        return templates.TemplateResponse(
            request=request, name="frota_fornecedores.html",
            context=ctx(request, fornecedores=_repo().list_fornecedores(),
                        pode_escrever=auth.pode_escrever(user["papel"],
                                                         "frota")))

    @app.post("/frota/fornecedores/criar")
    def frota_fornecedor_criar(request: Request, nome: str = Form(""),
                               cnpj: str = Form(""),
                               endereco: str = Form(""),
                               user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota/fornecedores")
        if red:
            return red
        try:
            _repo().add_fornecedor(nome, cnpj, endereco)
            flash(request, msg="Fornecedor cadastrado.")
        except ValueError as e:
            flash(request, erro=str(e))
        return RedirectResponse("/frota/fornecedores", status_code=303)

    @app.post("/frota/fornecedores/{forn_id}/editar")
    def frota_fornecedor_editar(forn_id: int, request: Request,
                                nome: str = Form(""), cnpj: str = Form(""),
                                endereco: str = Form(""),
                                user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota/fornecedores")
        if red:
            return red
        try:
            _repo().update_fornecedor(forn_id, nome, cnpj, endereco)
            flash(request, msg="Fornecedor atualizado.")
        except ValueError as e:
            flash(request, erro=str(e))
        return RedirectResponse("/frota/fornecedores", status_code=303)

    @app.post("/frota/fornecedores/{forn_id}/excluir")
    def frota_fornecedor_excluir(forn_id: int, request: Request,
                                 user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota/fornecedores")
        if red:
            return red
        try:
            _repo().delete_fornecedor(forn_id)
            flash(request, msg="Fornecedor excluído.")
        except ValueError as e:
            flash(request, erro=str(e))
        return RedirectResponse("/frota/fornecedores", status_code=303)

    # ================= abastecimentos =================

    @app.get("/frota/abastecimentos")
    def frota_abast_lista(request: Request, busca: str = "", page: int = 1,
                          per: int = 20,
                          user: dict = auth.require_permission("frota")):
        repo = _repo()
        per_val = per if per in _PER_OPCOES else 20
        pagina = max(1, page)
        itens, total = repo.list_abastecimentos(
            busca=busca, limit=per_val, offset=(pagina - 1) * per_val)
        nf_map = repo.tem_nf([a["id"] for a in itens])
        for a in itens:
            a["data_br"] = _br(a["data"])
            a["tem_nf"] = nf_map.get(a["id"], False)
        page_n, paginas = _paginacao(request, total, pagina, per_val)
        qs = f"busca={quote_plus((busca or '').strip())}" \
            if (busca or "").strip() else ""
        if per_val != 20:
            qs = (qs + "&" if qs else "") + f"per={per_val}"
        return templates.TemplateResponse(
            request=request, name="frota_abastecimentos.html",
            context=ctx(request, itens=itens, total=total,
                        busca=(busca or "").strip(), page=page_n,
                        paginas=paginas,
                        per=per_val, per_opcoes=_PER_OPCOES,
                        pg_base=("/frota/abastecimentos?" + qs) if qs
                        else "/frota/abastecimentos",
                        pode_escrever=auth.pode_escrever(user["papel"],
                                                         "frota")))

    @app.get("/frota/abastecimentos/novo")
    def frota_abast_novo(request: Request, veiculo: int = 0,
                         user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota/abastecimentos")
        if red:
            return red
        repo = _repo()
        veiculo_sel = veiculo if repo.get_veiculo(veiculo) else None
        return templates.TemplateResponse(
            request=request, name="frota_abast_form.html",
            context=ctx(request, erro="",
                        veiculo_sel=veiculo_sel,
                        funcionarios=_funcionarios_nomes(),
                        veiculos=sorted(repo.list_veiculos(limit=500)[0],
                                        key=lambda v: (v["modelo"] or "",
                                                       v["marca"] or "")),
                        fornecedores=sorted(repo.list_fornecedores(),
                                            key=lambda f: f["nome"]),
                        combustiveis=TIPOS_COMBUSTIVEL,
                        hoje=date.today().strftime("%d/%m/%Y")))

    @app.post("/frota/abastecimentos/criar")
    def frota_abast_criar(request: Request, veiculo_id: str = Form(""),
                          fornecedor_id: str = Form(""),
                          combustivel: str = Form(""), data: str = Form(""),
                          viagem_servico: str = Form(""), km: str = Form(""),
                          condutor: str = Form(""),
                          obs: str = Form(""), litros: str = Form(""),
                          valor: str = Form(""),
                          user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, "/frota/abastecimentos")
        if red:
            return red
        data_iso = _iso(data)
        repo = _repo()

        def _re_render(erro):
            return templates.TemplateResponse(
                request=request, name="frota_abast_form.html",
                context=ctx(request, erro=erro,
                            veiculo_sel=None,
                            funcionarios=_funcionarios_nomes(),
                            veiculos=sorted(
                                repo.list_veiculos(limit=500)[0],
                                key=lambda v: (v["modelo"] or "",
                                               v["marca"] or "")),
                            fornecedores=sorted(repo.list_fornecedores(),
                                                key=lambda f: f["nome"]),
                            combustiveis=TIPOS_COMBUSTIVEL,
                            hoje=data.strip() or
                            date.today().strftime("%d/%m/%Y")))

        if data_iso is None:
            return _re_render("Data inválida (dd/mm/aaaa).")
        try:
            def _num(txt):
                return float(str(txt).replace(",", ".")) if str(txt).strip() \
                    else None
            vid = int(veiculo_id)
            # 2.29.7: combustível compatível com o tipo do veículo
            v_info = repo.get_veiculo(vid)
            if not v_info:
                return _re_render("Veículo inválido.")
            if v_info["tipo"] in _TIPOS_SEM_DIESEL and \
                    combustivel in _COMB_BLOQUEADOS_LEVES:
                from src.core.frota_repo import label_combustivel as _lc
                return _re_render(
                    f"{_lc(combustivel)} não se aplica a "
                    f"{label_tipo(v_info['tipo'])}.")
            fid = int(fornecedor_id) if fornecedor_id else None
            km_val = int(km) if km.strip() else None
            abast_id, serial = repo.add_abastecimento(
                vid, fid, combustivel, data_iso, viagem_servico, km_val,
                condutor, obs, litros=_num(litros),
                valor=_num(valor))
        except (ValueError, TypeError) as e:
            return _re_render(str(e))
        # PDF
        pdf_path = None
        try:
            from src.core.pdf_abastecimento import gerar_pdf_abastecimento
            from src.core.config import load_company_config
            abast = repo.get_abastecimento(abast_id)
            pdf = gerar_pdf_abastecimento({
                "serial": serial,
                "data_br": _br(abast["data"]),
                "veiculo": abast,
                "fornecedor": {"nome": abast.get("fornecedor"),
                               "cnpj": abast.get("fornecedor_cnpj"),
                               "endereco": abast.get("fornecedor_endereco")},
                "combustivel": abast["combustivel"],
                "condutor": abast["condutor"],
                "viagem_servico": abast["viagem_servico"],
                "km": abast["km"],
                "obs": abast["obs"],
                "config": load_company_config(),
            })
            pdf_path = str(pdf)
            repo.set_pdf_path(abast_id, pdf_path)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("portal-frota-pdf", e)
        _audit(request, "frota-abastecimento", user["username"],
               serial, f"veiculo={vid}")
        flash(request, msg=f"Solicitação {serial} registrada.")
        return RedirectResponse("/frota/abastecimentos", status_code=303)

    @app.get("/frota/abastecimentos/exportar")
    def frota_abast_exportar(request: Request,
                             user: dict = auth.require_permission("frota")):
        import io
        import openpyxl
        repo = _repo()
        itens, _total = repo.list_abastecimentos(limit=5000, offset=0)
        nf_map = repo.tem_nf([a["id"] for a in itens])
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Abastecimentos"
        ws.append(["Serial", "Data", "Veículo", "Combustível", "KM", "Litros",
                   "Valor (R$)", "Fornecedor", "Condutor",
                   "Viagem/Serviço", "NF anexada", "Observações"])
        for a in itens:
            ws.append([
                a["serial"], _br(a["data"]), a["veiculo_rotulo"],
                a["combustivel_label"], a["km"], a["litros"], a["valor"],
                a.get("fornecedor") or "", a.get("condutor") or "",
                a.get("viagem_servico") or "",
                "Sim" if nf_map.get(a["id"]) else "Não", a.get("obs") or "",
            ])
        buf = io.BytesIO()
        wb.save(buf)
        wb.close()
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument"
                       ".spreadsheetml.sheet",
            headers={"Content-Disposition":
                     'attachment; filename="abastecimentos.xlsx"'})

    @app.get("/frota/abastecimentos/{abast_id}/nfs")
    def frota_nfs_lista(abast_id: int, request: Request,
                        user: dict = auth.require_permission("frota")):
        repo = _repo()
        a = repo.get_abastecimento(abast_id)
        if not a:
            flash(request, erro="Abastecimento não encontrado.")
            return RedirectResponse("/frota/abastecimentos", status_code=303)
        return templates.TemplateResponse(
            request=request, name="frota_nfs.html",
            context=ctx(request, a=a, data_br=_br(a["data"]),
                        veiculo_rotulo=veiculo_rotulo(a),
                        combustivel_label=label_combustivel(a["combustivel"]),
                        nfs=repo.list_nfs(abast_id),
                        assinado=repo.get_abast_signed(abast_id),
                        pode_escrever=auth.pode_escrever(user["papel"],
                                                         "frota")))

    @app.post("/frota/abastecimentos/{abast_id}/nfs")
    async def frota_nf_add(abast_id: int, request: Request,
                           numero: str = Form(""), data_nf: str = Form(""),
                           valor: str = Form(""),
                           arquivo: UploadFile = File(None),
                           user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user,
                        f"/frota/abastecimentos/{abast_id}/nfs")
        if red:
            return red
        if arquivo is None or not arquivo.filename:
            flash(request, erro="Selecione o arquivo da nota fiscal.")
            return RedirectResponse(
                f"/frota/abastecimentos/{abast_id}/nfs", status_code=303)
        data = await arquivo.read()
        try:
            val = float(str(valor).replace(",", ".")) if str(valor).strip() \
                else None
            _repo().add_nf(abast_id, numero, _iso(data_nf), val,
                           Path(arquivo.filename).name, data)
        except (ValueError, TypeError) as e:
            flash(request, erro=str(e))
            return RedirectResponse(
                f"/frota/abastecimentos/{abast_id}/nfs", status_code=303)
        _audit(request, "frota-nf-anexar", user["username"], numero or "",
               f"abast={abast_id}")
        flash(request, msg="Nota fiscal anexada.")
        return RedirectResponse(
            f"/frota/abastecimentos/{abast_id}/nfs", status_code=303)

    @app.get("/frota/nfs/{nf_id}/download")
    def frota_nf_download(nf_id: int):
        nf = _repo().get_nf(nf_id)
        if not nf:
            return Response(status_code=404)
        return Response(content=bytes(nf["dados"]),
                        media_type=_mime(nf["tipo_arquivo"]),
                        headers={"Content-Disposition":
                                 f'attachment; filename="{nf["filename"]}"'})

    @app.post("/frota/nfs/{nf_id}/excluir")
    def frota_nf_excluir(nf_id: int, request: Request,
                         user: dict = auth.require_permission("frota")):
        nf = _repo().get_nf(nf_id)
        if not nf:
            flash(request, erro="Nota fiscal não encontrada.")
            return RedirectResponse("/frota/abastecimentos", status_code=303)
        url = f"/frota/abastecimentos/{nf['abastecimento_id']}/nfs"
        red = _bloqueio(request, user, url)
        if red:
            return red
        _repo().delete_nf(nf_id)
        flash(request, msg="Nota fiscal excluída.")
        return RedirectResponse(url, status_code=303)

    @app.post("/frota/abastecimentos/{abast_id}/valores")
    def frota_abast_valores(abast_id: int, request: Request,
                            litros: str = Form(""), valor: str = Form(""),
                            user: dict = auth.require_permission("frota")):
        """2.29.7: completa litros/valor DEPOIS (ex.: com a NF em mãos)."""
        a = _repo().get_abastecimento(abast_id)
        if not a:
            flash(request, erro="Abastecimento não encontrado.")
            return RedirectResponse("/frota/abastecimentos", status_code=303)
        url = f"/frota/abastecimentos/{abast_id}/nfs"
        red = _bloqueio(request, user, url)
        if red:
            return red

        def _num(txt):
            return float(str(txt).replace(",", ".")) if str(txt).strip() \
                else None
        try:
            l, v = _num(litros), _num(valor)
            if l is not None and l <= 0:
                raise ValueError("Litros deve ser maior que zero.")
            if v is not None and v < 0:
                raise ValueError("Valor não pode ser negativo.")
            _repo().update_abast_valores(abast_id, l, v)
        except (ValueError, TypeError) as e:
            flash(request, erro=str(e))
            return RedirectResponse(url, status_code=303)
        _audit(request, "frota-abast-valores", user["username"],
               a["serial"], f"litros={l} valor={v}")
        flash(request, msg="Valores atualizados.")
        return RedirectResponse(url, status_code=303)

    @app.get("/frota/abastecimentos/{abast_id}/pdf")
    def frota_abast_pdf(abast_id: int):
        a = _repo().get_abastecimento(abast_id)
        if not a or not a.get("pdf_path"):
            return Response(status_code=404)
        p = Path(a["pdf_path"])
        if not p.exists():
            return Response(status_code=404)
        return FileResponse(p, media_type="application/pdf")

    @app.get("/frota/abastecimentos/{abast_id}/pdf/download")
    def frota_abast_pdf_download(abast_id: int):
        a = _repo().get_abastecimento(abast_id)
        if not a or not a.get("pdf_path"):
            return Response(status_code=404)
        p = Path(a["pdf_path"])
        if not p.exists():
            return Response(status_code=404)
        return FileResponse(p, media_type="application/pdf",
                            filename=f"{a['serial']}.pdf")


# ================= ficha do veiculo =================

    @app.get("/frota/{veiculo_id}")
    def frota_ficha(veiculo_id: int, request: Request,
                    user: dict = auth.require_permission("frota")):
        repo = _repo()
        v = repo.get_veiculo(veiculo_id)
        if not v:
            flash(request, erro="Veículo não encontrado.")
            return RedirectResponse("/frota", status_code=303)
        v["rotulo"] = veiculo_rotulo(v)
        docs = repo.list_docs(veiculo_id)
        laudos = repo.list_laudos(veiculo_id)
        movs = repo.list_movimentacoes(veiculo_id)
        abasts = repo.list_abast_por_veiculo(veiculo_id)
        checklists = repo.list_checklists(veiculo_id)
        manutencoes = repo.list_manutencoes(veiculo_id)
        resumo = repo.resumo_custo_veiculo(veiculo_id)
        return templates.TemplateResponse(
            request=request, name="frota_ficha.html",
            context=ctx(request, v=v, rotulo=v["rotulo"],
                        tipo_label=label_tipo(v["tipo"]),
                        sub_label=label_subtipo(v["subtipo"]),
                        docs=docs, laudos=laudos, movs=movs, abasts=abasts,
                        checklists=checklists, manutencoes=manutencoes,
                        resumo=resumo,
                        tags_doc=TAGS_DOC,
                        funcionarios=_funcionarios_nomes(),
                        combustiveis=TIPOS_COMBUSTIVEL,
                        tipos_laudo=TIPOS_LAUDO,
                        hoje=date.today().strftime("%d/%m/%Y"),
                        pode_escrever=auth.pode_escrever(user["papel"],
                                                         "frota")))

    # ---- documentos (pasta virtual) ----

    @app.post("/frota/{veiculo_id}/docs")
    async def frota_doc_upload(veiculo_id: int, request: Request,
                               tag: str = Form(""),
                               arquivo: UploadFile = File(None),
                               user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        if arquivo is None or not arquivo.filename:
            flash(request, erro="Selecione um arquivo.")
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        data = await arquivo.read()
        try:
            _repo().add_doc(veiculo_id, Path(arquivo.filename).name, data,
                            tag=tag)
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        flash(request, msg=f"Documento '{Path(arquivo.filename).name}'"
                           " anexado.")
        return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)

    @app.get("/frota/{veiculo_id}/docs/{doc_id}/download")
    def frota_doc_download(veiculo_id: int, doc_id: int):
        doc = _repo().get_doc(doc_id)
        if not doc or doc["veiculo_id"] != veiculo_id:
            return Response(status_code=404)
        return Response(content=bytes(doc["dados"]),
                        media_type=_mime(doc["tipo"]),
                        headers={"Content-Disposition":
                                 f'attachment; filename="{doc["filename"]}"'})

    @app.post("/frota/{veiculo_id}/docs/{doc_id}/excluir")
    def frota_doc_excluir(veiculo_id: int, doc_id: int, request: Request,
                          user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        _repo().delete_doc(doc_id)
        flash(request, msg="Documento excluído.")
        return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)

    # ---- laudos ----

    @app.post("/frota/{veiculo_id}/laudos")
    async def frota_laudo_add(veiculo_id: int, request: Request,
                              tipo: str = Form(""),
                              descricao: str = Form(""),
                              emissao: str = Form(""),
                              validade: str = Form(""),
                              arquivo: UploadFile = File(None),
                              user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        data_emi = _iso(emissao)
        data_val = _iso(validade)
        if data_emi is None or data_val is None:
            flash(request, erro="Datas em formato inválido (dd/mm/aaaa).")
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        if arquivo is None or not arquivo.filename:
            flash(request, erro="Selecione o arquivo do laudo.")
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        data = await arquivo.read()
        try:
            _repo().add_laudo(veiculo_id, tipo,
                              Path(arquivo.filename).name, data,
                              data_emi, data_val, descricao)
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        flash(request, msg="Laudo registrado.")
        return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)

    @app.get("/frota/{veiculo_id}/laudos/{laudo_id}/download")
    def frota_laudo_download(veiculo_id: int, laudo_id: int):
        laudo = _repo().get_laudo(laudo_id)
        if not laudo or laudo["veiculo_id"] != veiculo_id:
            return Response(status_code=404)
        return Response(content=bytes(laudo["dados"]),
                        media_type=_mime(laudo["tipo_arquivo"]),
                        headers={"Content-Disposition":
                                 f'attachment; filename="{laudo["filename"]}"'})

    @app.post("/frota/{veiculo_id}/laudos/{laudo_id}/excluir")
    def frota_laudo_excluir(veiculo_id: int, laudo_id: int,
                            request: Request,
                            user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        _repo().delete_laudo(laudo_id)
        flash(request, msg="Laudo excluído.")
        return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)

    # ---- movimentacoes ----

    @app.post("/frota/{veiculo_id}/movimentacoes")
    def frota_mov_saida(veiculo_id: int, request: Request,
                        data_saida: str = Form(""), hora: str = Form(""),
                        km_inicial: str = Form(""), destino: str = Form(""),
                        motivo: str = Form(""), obs: str = Form(""),
                        motorista: str = Form(""),
                        autorizado_por: str = Form(""),
                        user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        data_iso = _iso(data_saida)
        if data_iso is None:
            flash(request, erro="Data de saída inválida (dd/mm/aaaa).")
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        # 2.29.7: não permite segunda saída com uma ainda aberta
        abertas = [m for m in _repo().list_movimentacoes(veiculo_id)
                   if m.get("aberta")]
        if abertas:
            m0 = abertas[0]
            flash(request, erro="Já existe uma saída aberta neste veículo "
                  f"({_br(m0['data_saida'])} {m0['hora_saida']} — "
                  f"{m0['motorista']}). Registre a entrada antes de uma nova"
                  " saída.")
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        try:
            km = int(km_inicial) if km_inicial.strip() else None
            _repo().add_mov_saida(veiculo_id, data_iso, hora.strip(), km,
                                  destino, motivo, obs, motorista,
                                  autorizado_por)
        except (ValueError, TypeError) as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        flash(request, msg="Saída registrada.")
        return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)

    @app.post("/frota/movimentacoes/{mov_id}/entrada")
    def frota_mov_entrada(mov_id: int, request: Request,
                          data_entrada: str = Form(""),
                          hora_entrada: str = Form(""),
                          km_final: str = Form(""),
                          user: dict = auth.require_permission("frota")):
        mov = _repo().get_mov(mov_id)
        if not mov:
            flash(request, erro="Movimentação não encontrada.")
            return RedirectResponse("/frota", status_code=303)
        url = f"/frota/{mov['veiculo_id']}"
        red = _bloqueio(request, user, url)
        if red:
            return red
        data_iso = _iso(data_entrada)
        if data_iso is None:
            flash(request, erro="Data de entrada inválida (dd/mm/aaaa).")
            return RedirectResponse(url, status_code=303)
        try:
            km = int(km_final) if km_final.strip() else None
            _repo().registrar_entrada(mov_id, data_iso,
                                      hora_entrada.strip(), km)
        except (ValueError, TypeError) as e:
            flash(request, erro=str(e))
            return RedirectResponse(url, status_code=303)
        flash(request, msg="Entrada registrada.")
        return RedirectResponse(url, status_code=303)

    @app.post("/frota/movimentacoes/{mov_id}/excluir")
    def frota_mov_excluir(mov_id: int, request: Request,
                          user: dict = auth.require_permission("frota")):
        mov = _repo().get_mov(mov_id)
        if not mov:
            flash(request, erro="Movimentação não encontrada.")
            return RedirectResponse("/frota", status_code=303)
        url = f"/frota/{mov['veiculo_id']}"
        red = _bloqueio(request, user, url)
        if red:
            return red
        _repo().delete_mov(mov_id)
        flash(request, msg="Movimentação excluída.")
        return RedirectResponse(url, status_code=303)

    # ---- manutenções preventivas por KM ----

    @app.post("/frota/{veiculo_id}/manutencoes")
    def frota_manut_add(veiculo_id: int, request: Request,
                        descricao: str = Form(""), intervalo_km: str = Form(""),
                        km_ultima: str = Form(""), data_ultima: str = Form(""),
                        obs: str = Form(""),
                        user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        data_iso = _iso(data_ultima) if data_ultima.strip() else ""
        try:
            _repo().add_manutencao(
                veiculo_id, descricao, int(intervalo_km) if intervalo_km.strip()
                else 0, int(km_ultima) if km_ultima.strip() else 0,
                data_iso or "", obs)
        except (ValueError, TypeError) as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)
        _audit(request, "frota-manutencao-criar", user["username"],
               str(veiculo_id), descricao)
        flash(request, msg="Manutenção cadastrada.")
        return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)

    @app.post("/frota/manutencoes/{manut_id}/concluir")
    def frota_manut_concluir(manut_id: int, request: Request,
                             km_feito: str = Form(""), data_feito: str = Form(""),
                             user: dict = auth.require_permission("frota")):
        m = _repo().get_manutencao(manut_id)
        if not m:
            flash(request, erro="Manutenção não encontrada.")
            return RedirectResponse("/frota", status_code=303)
        url = f"/frota/{m['veiculo_id']}"
        red = _bloqueio(request, user, url)
        if red:
            return red
        try:
            data_iso = _iso(data_feito) or date.today().isoformat()
            _repo().concluir_manutencao(manut_id, int(km_feito), data_iso)
        except (ValueError, TypeError) as e:
            flash(request, erro=str(e))
            return RedirectResponse(url, status_code=303)
        flash(request, msg="Manutenção registrada como realizada.")
        return RedirectResponse(url, status_code=303)

    @app.post("/frota/manutencoes/{manut_id}/excluir")
    def frota_manut_excluir(manut_id: int, request: Request,
                            user: dict = auth.require_permission("frota")):
        m = _repo().get_manutencao(manut_id)
        if not m:
            flash(request, erro="Manutenção não encontrada.")
            return RedirectResponse("/frota", status_code=303)
        url = f"/frota/{m['veiculo_id']}"
        red = _bloqueio(request, user, url)
        if red:
            return red
        _repo().delete_manutencao(manut_id)
        flash(request, msg="Manutenção excluída.")
        return RedirectResponse(url, status_code=303)

    # ---- checklist semanal (2.29.5) ----

    @app.get("/frota/{veiculo_id}/checklist/branco")
    def frota_checklist_branco(veiculo_id: int, request: Request,
                               user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        repo = _repo()
        v = repo.get_veiculo(veiculo_id)
        if not v:
            flash(request, erro="Veículo não encontrado.")
            return RedirectResponse("/frota", status_code=303)
        hoje = date.today().isoformat()
        movs = repo.list_movimentacoes(veiculo_id)
        kms = [m["km_final"] if m.get("km_final") is not None else m["km_inicial"]
               for m in movs]
        km_atual = max([k for k in kms if k is not None], default=None)
        chk_id, serial = repo.add_checklist(
            veiculo_id, hoje, hoje, km_atual,
            "(a preencher)", "(a preencher)", "S", {}, {},
            criado_por=user["username"])
        try:
            from src.core.pdf_checklist import gerar_pdf_checklist
            from src.core.config import load_company_config
            from src.utils.error_log import log_error
            pdf = gerar_pdf_checklist({
                "serial": serial, "veiculo": v,
                "data_inicial_br": _br(hoje), "data_final_br": _br(hoje),
                "km_rodado": km_atual, "placa": v.get("placa"),
                "motorista": "(a preencher)", "lider": "(a preencher)",
                "pode_operar": "", "itens": {}, "observacoes": {},
                "config": load_company_config()})
            repo.set_checklist_pdf(chk_id, str(pdf))
        except Exception as e:
            log_error("portal-frota-checklist-pdf", e)
        users.audit("frota-checklist-branco", user["username"], serial)
        flash(request, msg=f"Checklist {serial} gerado para preenchimento manual.")
        return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)

    @app.get("/frota/{veiculo_id}/checklist/novo")
    def frota_checklist_novo(veiculo_id: int, request: Request,
                             user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        v = _repo().get_veiculo(veiculo_id)
        if not v:
            flash(request, erro="Veículo não encontrado.")
            return RedirectResponse("/frota", status_code=303)
        return templates.TemplateResponse(
            request=request, name="frota_checklist_form.html",
            context=ctx(request, v=v, rotulo=veiculo_rotulo(v),
                        grupos=CHECKLIST_GRUPOS, dias=CHECKLIST_DIAS,
                        hoje=date.today().strftime("%d/%m/%Y"),
                        pode_escrever=auth.pode_escrever(user["papel"],
                                                         "frota")))

    @app.post("/frota/{veiculo_id}/checklist")
    async def frota_checklist_criar(veiculo_id: int, request: Request,
                                    data_inicial: str = Form(""),
                                    data_final: str = Form(""),
                                    km_rodado: str = Form(""),
                                    motorista: str = Form(""),
                                    lider: str = Form(""),
                                    pode_operar: str = Form(""),
                                    user: dict = auth.require_permission("frota")):
        red = _bloqueio(request, user, f"/frota/{veiculo_id}")
        if red:
            return red
        url_novo = f"/frota/{veiculo_id}/checklist/novo"
        form = await request.form()
        itens: dict = {}
        observacoes: dict = {}
        for k, val in form.items():
            v_str = str(val)
            if k.startswith("item_") and v_str in ("S", "N"):
                num, _, dia = k[5:].rpartition("_")
                if num and dia:
                    itens.setdefault(num, {})[dia] = v_str
            elif k.startswith("obs_") and v_str.strip():
                observacoes[k[4:]] = v_str.strip()
        data_ini_iso = _iso(data_inicial)
        data_fim_iso = _iso(data_final)
        if data_ini_iso is None or data_fim_iso is None:
            flash(request, erro="Datas inválidas (dd/mm/aaaa).")
            return RedirectResponse(url_novo, status_code=303)
        try:
            km = int(km_rodado) if km_rodado.strip() else None
            chk_id, serial = _repo().add_checklist(
                veiculo_id, data_ini_iso, data_fim_iso, km,
                motorista, lider, pode_operar, itens, observacoes,
                user["username"])
        except (ValueError, TypeError) as e:
            flash(request, erro=str(e))
            return RedirectResponse(url_novo, status_code=303)
        try:
            from src.core.pdf_checklist import gerar_pdf_checklist
            from src.core.config import load_company_config
            v = _repo().get_veiculo(veiculo_id)
            pdf = gerar_pdf_checklist({
                "serial": serial,
                "veiculo": v,
                "data_inicial_br": _br(data_ini_iso),
                "data_final_br": _br(data_fim_iso),
                "km_rodado": km,
                "placa": v.get("placa"),
                "motorista": motorista,
                "lider": lider,
                "pode_operar": pode_operar,
                "itens": itens,
                "observacoes": observacoes,
                "config": load_company_config(),
            })
            _repo().set_checklist_pdf(chk_id, str(pdf))
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("portal-frota-checklist-pdf", e)
        _audit(request, "frota-checklist", user["username"],
               serial, f"veiculo={veiculo_id}")
        flash(request, msg=f"Checklist {serial} registrado.")
        return RedirectResponse(f"/frota/{veiculo_id}", status_code=303)

    @app.get("/frota/checklists/{chk_id}/pdf")
    def frota_checklist_pdf(chk_id: int):
        c = _repo().get_checklist(chk_id)
        if not c or not c.get("pdf_path"):
            return Response(status_code=404)
        p = Path(c["pdf_path"])
        if not p.exists():
            return Response(status_code=404)
        return FileResponse(p, media_type="application/pdf")

    @app.get("/frota/checklists/{chk_id}/pdf/download")
    def frota_checklist_pdf_download(chk_id: int):
        c = _repo().get_checklist(chk_id)
        if not c or not c.get("pdf_path"):
            return Response(status_code=404)
        p = Path(c["pdf_path"])
        if not p.exists():
            return Response(status_code=404)
        return FileResponse(p, media_type="application/pdf",
                            filename=f"{c['serial']}.pdf")

    @app.post("/frota/checklists/{chk_id}/assinado")
    async def frota_checklist_assinado(chk_id: int, request: Request,
                                       arquivo: UploadFile = File(None),
                                       user: dict = auth.require_permission(
                                           "frota")):
        """2.29.7: fluxo papel — imprime, preenche, assina e ANEXA de volta."""
        c = _repo().get_checklist(chk_id)
        if not c:
            flash(request, erro="Checklist não encontrado.")
            return RedirectResponse("/frota", status_code=303)
        url = f"/frota/{c['veiculo_id']}"
        red = _bloqueio(request, user, url)
        if red:
            return red
        if arquivo is None or not arquivo.filename:
            flash(request, erro="Selecione o arquivo assinado (PDF, JPG ou"
                                " PNG).")
            return RedirectResponse(url, status_code=303)
        ext = Path(arquivo.filename).suffix.lower().lstrip(".")
        tipo = {"pdf": "pdf", "jpg": "jpg", "jpeg": "jpg",
                "png": "png"}.get(ext)
        data = await arquivo.read()
        if tipo is None:
            flash(request, erro="Formato não suportado (use PDF, JPG ou"
                                " PNG).")
            return RedirectResponse(url, status_code=303)
        if len(data) > 50 * 1024 * 1024:
            flash(request, erro="Arquivo maior que 50MB.")
            return RedirectResponse(url, status_code=303)
        _repo().attach_checklist_signed(
            chk_id, data, tipo, Path(arquivo.filename).name)
        _audit(request, "frota-checklist-assinado", user["username"],
               c["serial"], Path(arquivo.filename).name)
        flash(request, msg="Checklist assinado anexado.")
        return RedirectResponse(url, status_code=303)

    @app.get("/frota/checklists/{chk_id}/assinado/download")
    def frota_checklist_assinado_download(chk_id: int):
        s = _repo().get_checklist_signed(chk_id)
        if not s:
            return Response(status_code=404)
        media = {"pdf": "application/pdf", "jpg": "image/jpeg",
                 "png": "image/png"}.get(s["assinado_tipo"],
                                         "application/octet-stream")
        return Response(content=bytes(s["assinado_dados"]), media_type=media,
                        headers={"Content-Disposition":
                                 f'attachment; '
                                 f'filename="{s["assinado_filename"]}"'})

    @app.post("/frota/checklists/{chk_id}/assinado/excluir")
    def frota_checklist_assinado_excluir(chk_id: int, request: Request,
                                         user: dict = auth.require_permission(
                                             "frota")):
        c = _repo().get_checklist(chk_id)
        if not c:
            flash(request, erro="Checklist não encontrado.")
            return RedirectResponse("/frota", status_code=303)
        url = f"/frota/{c['veiculo_id']}"
        red = _bloqueio(request, user, url)
        if red:
            return red
        _repo().remove_checklist_signed(chk_id)
        flash(request, msg="Anexo assinado removido.")
        return RedirectResponse(url, status_code=303)

    @app.post("/frota/abastecimentos/{abast_id}/assinado")
    async def frota_abast_assinado(abast_id: int, request: Request,
                                   arquivo: UploadFile = File(None),
                                   user: dict = auth.require_permission(
                                       "frota")):
        """2.31: abastecimento assinado anexado de volta (foto ou PDF)."""
        a = _repo().get_abastecimento(abast_id)
        if not a:
            flash(request, erro="Abastecimento não encontrado.")
            return RedirectResponse("/frota/abastecimentos", status_code=303)
        url = f"/frota/abastecimentos/{abast_id}/nfs"
        red = _bloqueio(request, user, url)
        if red:
            return red
        if arquivo is None or not arquivo.filename:
            flash(request, erro="Selecione o arquivo assinado (PDF, JPG ou"
                                " PNG).")
            return RedirectResponse(url, status_code=303)
        ext = Path(arquivo.filename).suffix.lower().lstrip(".")
        tipo = {"pdf": "pdf", "jpg": "jpg", "jpeg": "jpg",
                "png": "png"}.get(ext)
        data = await arquivo.read()
        if tipo is None:
            flash(request, erro="Formato não suportado (use PDF, JPG ou"
                                " PNG).")
            return RedirectResponse(url, status_code=303)
        if len(data) > 50 * 1024 * 1024:
            flash(request, erro="Arquivo maior que 50MB.")
            return RedirectResponse(url, status_code=303)
        _repo().attach_abast_signed(
            abast_id, data, tipo, Path(arquivo.filename).name)
        _audit(request, "frota-abast-assinado", user["username"],
               a["serial"], Path(arquivo.filename).name)
        flash(request, msg="Abastecimento assinado anexado.")
        return RedirectResponse(url, status_code=303)

    @app.get("/frota/abastecimentos/{abast_id}/assinado/download")
    def frota_abast_assinado_download(abast_id: int):
        s = _repo().get_abast_signed(abast_id)
        if not s:
            return Response(status_code=404)
        media = {"pdf": "application/pdf", "jpg": "image/jpeg",
                 "png": "image/png"}.get(s["assinado_tipo"],
                                         "application/octet-stream")
        return Response(content=bytes(s["assinado_dados"]), media_type=media,
                        headers={"Content-Disposition":
                                 f'attachment; '
                                 f'filename="{s["assinado_filename"]}"'})

    @app.post("/frota/abastecimentos/{abast_id}/assinado/excluir")
    def frota_abast_assinado_excluir(abast_id: int, request: Request,
                                     user: dict = auth.require_permission(
                                         "frota")):
        a = _repo().get_abastecimento(abast_id)
        if not a:
            flash(request, erro="Abastecimento não encontrado.")
            return RedirectResponse("/frota/abastecimentos", status_code=303)
        url = f"/frota/abastecimentos/{abast_id}/nfs"
        red = _bloqueio(request, user, url)
        if red:
            return red
        _repo().remove_abast_signed(abast_id)
        flash(request, msg="Anexo assinado removido.")
        return RedirectResponse(url, status_code=303)

    @app.post("/frota/checklists/{chk_id}/excluir")
    def frota_checklist_excluir(chk_id: int, request: Request,
                                user: dict = auth.require_permission("frota")):
        c = _repo().get_checklist(chk_id)
        if not c:
            flash(request, erro="Checklist não encontrado.")
            return RedirectResponse("/frota", status_code=303)
        url = f"/frota/{c['veiculo_id']}"
        red = _bloqueio(request, user, url)
        if red:
            return red
        _repo().delete_checklist(chk_id)
        flash(request, msg="Checklist excluído.")
        return RedirectResponse(url, status_code=303)

    
