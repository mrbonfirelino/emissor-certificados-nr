"""Router de Emissão em Lote do portal (v1.27.0) — portabilidade do fluxo
da página desktop 'Emissão em Lote' (v1.23.0).

Uma página: escolhe a NR, marca funcionários (sem CPF = bloqueado), define
dados globais (data/carga/validade/descrição/campos extras) com ajuste
individual opcional por funcionário, e emite em sequência no servidor.
Consulta (somente leitura) não acessa: emissão é operação de admin/emissor.
"""

from datetime import date

from fastapi import Request
from fastapi.responses import RedirectResponse

from src.core.employee_repo import EmployeeRepository
from src.core.template_loader import load_all_templates
from src.utils.validators import validar_data
from src.web import auth
from src.web.permissions import pode_escrever

MAX_LISTA = 500


def _templates_ordenados() -> dict:
    return {k: v for k, v in sorted(load_all_templates().items())}


def register(app, deps: dict):
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    @app.get("/emissao-lote")
    def form(request: Request, nr: str = "", busca: str = "",
             user: dict = auth.require_permission("certificados")):
        if not pode_escrever(user["papel"], "certificados"):
            flash(request, erro="Seu papel é somente leitura neste módulo.")
            return RedirectResponse("/certificados", status_code=303)
        templates_nr = _templates_ordenados()
        nr_sel = nr if nr in templates_nr else (next(iter(templates_nr), None))
        tmpl = templates_nr.get(nr_sel)
        er = EmployeeRepository()
        busca = (busca or "").strip()
        todos = (er.search(busca, limit=1_000_000) if busca
                 else er.get_all(limit=1_000_000))
        funcionarios = sorted(todos, key=lambda e: e.nome.lower())[:MAX_LISTA]
        return templates.TemplateResponse(
            request=request, name="emissao_lote.html",
            context=ctx(request, funcionarios=funcionarios, templates_nr=templates_nr,
                        nr_sel=nr_sel, tmpl=tmpl, busca=busca,
                        hoje_br=date.today().strftime("%d/%m/%Y"),
                        total=len(todos), cortados=max(0, len(todos) - MAX_LISTA)))

    @app.post("/emissao-lote/emitir")
    async def emitir(request: Request,
                     user: dict = auth.require_permission("certificados")):
        def _voltar(erro: str):
            flash(request, erro=erro)
            return RedirectResponse("/emissao-lote", status_code=303)

        if not pode_escrever(user["papel"], "certificados"):
            return _voltar("Seu papel é somente leitura neste módulo.")

        form = await request.form()
        templates_nr = _templates_ordenados()
        nr = form.get("nr") or ""
        tmpl = templates_nr.get(nr)
        if tmpl is None:
            return _voltar("Selecione uma NR válida.")

        data_global = validar_data((form.get("data") or "").strip())
        if data_global is None:
            return _voltar("Data do treinamento inválida (use dd/mm/aaaa).")
        try:
            carga_global = int(form.get("carga") or 0)
        except ValueError:
            carga_global = 0
        if carga_global < tmpl.carga_horaria_minima:
            return _voltar(f"Carga horária mínima para {nr}: "
                           f"{tmpl.carga_horaria_minima}h.")
        validade_global = None
        txt = (form.get("validade") or "").strip()
        if txt:
            try:
                validade_global = int(txt)
                if not 1 <= validade_global <= 120:
                    raise ValueError
            except ValueError:
                return _voltar("Validade inválida (meses entre 1 e 120).")
        descricao = (form.get("descricao") or "").strip()
        if not descricao:
            return _voltar("Informe a descrição do treinamento.")
        campos = {}
        faltando = []
        for extra in tmpl.campos_extra:
            valor = (form.get(f"campo_{extra.id}") or "").strip()
            if extra.obrigatorio and not valor:
                faltando.append(extra.label)
            if valor:
                campos[extra.id] = valor
        if faltando:
            return _voltar("Preencha: " + ", ".join(faltando) + ".")

        selecionados = [k[4:] for k in form.keys() if k.startswith("sel_")]
        if not selecionados:
            return _voltar("Selecione pelo menos um funcionário.")

        er = EmployeeRepository()
        itens = []
        for id_txt in selecionados:
            try:
                emp = er.get_by_id(int(id_txt))
            except ValueError:
                emp = None
            if emp is None:
                itens.append({"emp": None, "nome": f"(id {id_txt})",
                              "erro": "Funcionário não encontrado."})
                continue
            if not (emp.cpf or "").strip():
                itens.append({"emp": emp, "nome": emp.nome,
                              "erro": "Sem CPF cadastrado."})
                continue
            d_txt = (form.get(f"data_{emp.id}") or "").strip()
            data_item = validar_data(d_txt) if d_txt else data_global
            if d_txt and data_item is None:
                itens.append({"emp": emp, "nome": emp.nome,
                              "erro": f"Data individual inválida ({d_txt})."})
                continue
            c_txt = (form.get(f"carga_{emp.id}") or "").strip()
            try:
                carga_item = int(c_txt) if c_txt else carga_global
            except ValueError:
                carga_item = 0
            if carga_item < tmpl.carga_horaria_minima:
                itens.append({"emp": emp, "nome": emp.nome,
                              "erro": f"Carga individual abaixo da mínima "
                                       f"({tmpl.carga_horaria_minima}h)."})
                continue
            v_txt = (form.get(f"validade_{emp.id}") or "").strip()
            validade_item = validade_global
            if v_txt:
                try:
                    validade_item = int(v_txt)
                    if not 1 <= validade_item <= 120:
                        raise ValueError
                except ValueError:
                    itens.append({"emp": emp, "nome": emp.nome,
                                  "erro": f"Validade individual inválida ({v_txt})."})
                    continue
            itens.append({"emp": emp, "nome": emp.nome, "data": data_item,
                          "carga": carga_item, "validade": validade_item,
                          "erro": None})

        from src.core.certificate_service import CertificateService
        service = CertificateService()
        gerados, erros = [], []
        for it in itens:
            if it["erro"]:
                erros.append(f"{it['nome']}: {it['erro']}")
                continue
            try:
                caminho = service.generate_certificate(
                    nr_code=nr, employee=it["emp"], data_treinamento=it["data"],
                    carga_horaria=it["carga"],
                    descricao_treinamento=descricao, campos_extra=campos,
                    validade_meses=it["validade"])
                numero = None
                try:
                    from src.core.history_repo import HistoryRepository
                    registros = HistoryRepository().get_by_employee(it["emp"].id)
                    numero = max(registros, key=lambda r: r.id).cert_number
                except Exception:
                    numero = None
                gerados.append({"nome": it["emp"].nome, "numero": numero,
                                "pdf": bool(caminho)})
            except ValueError as e:
                erros.append(f"{it['emp'].nome}: {e}")
            except Exception:
                erros.append(f"{it['emp'].nome}: falha ao gerar o certificado.")

        return templates.TemplateResponse(
            request=request, name="lote_resultado.html",
            context=ctx(request, nr=nr, gerados=gerados, erros=erros))
