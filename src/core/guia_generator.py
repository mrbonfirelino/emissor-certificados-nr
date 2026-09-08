"""Gerador do Guia de Introducao do NormaTech (v1.18.0 — roadmap 2.21).

PDF amigavel ao usuario final, linguagem simples, gerado sob demanda em
data/GUIA_NORMATECH.pdf.

- guia_path()                    -> caminho padrao do guia
- garantir_guia()                -> gera se ainda nao existe e retorna o caminho
- generate_guia_pdf(output_path) -> gera o guia completo
"""

from pathlib import Path
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from src.utils.paths import get_data_dir

PRIMARY = colors.HexColor("#1B3A5C")
ACCENT = colors.HexColor("#2E6DA4")
TEXT = colors.HexColor("#222222")
MUTED = colors.HexColor("#666666")

_SECOES = [
    ("1. Bem-vindo ao NormaTech", [
        "O NormaTech organiza toda a parte de segurança do trabalho da empresa: "
        "cadastro de funcionários, certificados de treinamento (NRs), vencimentos, "
        "cartões de bloqueio, crachás, ASO e fichas de EPI.",
        "Tudo que voce emite fica salvo no computador (dentro da pasta 'data') e, se configurado, "
        "tambem e copiado automaticamente para a pasta de rede da empresa.",
    ]),
    ("2. Cadastro de Funcionários", [
        "Aba Funcionarios: use Novo Funcionario para cadastrar nome, CPF, funcao, "
        "telefone, data de nascimento, tipo sanguineo, data de admissao, CTPS e CNH EAR.",
        "A foto 3x4 e obrigatoria para cartoes de bloqueio e crachas — use Importar Fotos "
        "para enviar varias de uma vez (nomeie o arquivo (Foto) com o CPF do funcionario antes de importar).",
        "O botao Docs guarda documentos do funcionario (CNH, certificados, qualquer arquivo "
        "ate 50MB). O botao EPI abre as fichas de EPI dele.",
        "Importar/Exportar Excel: a planilha modelo esta na pasta MODELOS DE IMPORTACAO "
        "(colunas A a I). Linhas com erro nao param a importacao — o aviso mostra o que ajustar.",
    ]),
    ("3. Emissao de Certificados", [
        "Aba Certificados: escolha a NR, digite o nome do funcionario (a lista completa "
        "enquanto voce digita), confira os dados e clique em Emitir.",
        "Antes de gravar aparece a revisao: confira e clique Confirmar. O PDF e salvo em "
        "data/certificados/{Funcionario}/{NR} e copiado para a rede.",
    ]),
    ("4. Vencimentos", [
        "Aba Vencimentos mostra cards por funcionario com quantos certificados/ASOs vencem "
        "em 7, 15, 30 e 90 dias e quantos ja venceram.",
        "Use o filtro por NR ou por periodo. Emitir renova o treinamento; Historico abre a "
        "lista completa com filtros por NR, periodo e situacao (assinado ou nao), com "
        "exportacao para Excel/CSV.",
    ]),
    ("5. Cartões de Bloqueio", [
        "Aba Cartoes de Bloqueio: selecione os funcionarios, o modelo (ALTEC, CSN, LOTOTO, "
        "ArcelorMittal, PPTX) e clique em Gerar.",
        "A revisao permite ajustar nome, funcao, telefone e setor apenas para aquela emissao. "
        "Escolha PDF unico (varios cartoes por folha) ou um arquivo por funcionario.",
    ]),
    ("6. Crachás de Identificação", [
        "No mesmo menu, escolha o modelo CRACHA-ALTEC (horizontal) ou CRACHA-VERTICAL.",
        "Marque ate 8 NRs de cada funcionario (so entram treinamentos validos), confira o "
        "vencimento do ASO e a data de emissao. O cracha sai com campo de assinatura.",
        "Os crachas saem em folha A4 com guias de corte (paisagem 3 por folha, vertical 4). "
        "Voce pode escolher tamanho real ou reduzido 86x54mm.",
        "Regra: o cracha so e gerado para quem tem foto, NR valida e ASO dentro da validade. "
        "Quem nao atende aparece como Pulado com o motivo.",
    ]),
    ("7. ASO", [
        "Aba ASO: Novo ASO escolhe o funcionario, o tipo (Admissional, Periodico, Mudanca de "
        "Funcao, Retorno ao Trabalho, Demissional) e a validade em meses.",
        "O PDF ja sai com os dados e espaco para o documento. Ao Anexar ou Digitalizar o ASO "
        "do medico, ele entra nas paginas seguintes do mesmo PDF.",
        "ASOs vencem junto com os certificados: aparecem na aba Vencimentos, no painel da "
        "tela inicial e no aviso de abertura do programa.",
    ]),
    ("8. Fichas de EPI", [
        "Botao EPI no cadastro do funcionario: Nova Ficha cria a ficha de retirada "
        "(C.A., descricao, quantidade e data) e gera o PDF para assinatura.",
        "O botao Devolucao registra cada item como Pendente, Total ou Parcial, com a data — "
        "e gera um Termo de Devolucao para o funcionario assinar.",
        "As versoes assinadas (digitalizadas) entram pelo botao Anexar: varias versoes podem "
        "conviver sem apagar as anteriores.",
    ]),
    ("9. Backups", [
        "O programa faz backup automatico periodicamente, um backup periodico maior e "
        "backups manuais (aba Backups). Copias ficam em Documents/NormaTech-Backup, "
        "C:/NormaTech-Backup e na rede (se configurada).",
        "Tarefa Agendada (Configuracoes > Backups): ligue para o Windows fazer backup diario "
        "no horario escolhido, mesmo com o programa fechado.",
        "Restaurar volta um backup e reinicia o programa. E recomendado testar a restauracao "
        "de vez em quando.",
    ]),
    ("10. Documentos em Rede", [
        "Configuracoes > Documentos em Rede: informe a pasta de rede e ative. Todo documento "
        "gerado e copiado para {Funcionario}/... na rede (Certificados, Cartoes, Crachas, "
        "ASOs, EPIs, Certificados Assinados, Outros).",
        "Use Sincronizar Agora para reenviar tudo; se a rede falhar, aparece uma notificacao "
        "e a sincronizacao pode ser repetida depois.",
    ]),
    ("11. Configurações", [
        "As configuracoes ficam em secoes recolhiveis: Dados da Empresa, Seguranca, "
        "Aparencia e Notificacoes, Backups, Documentos em Rede e Diagnostico (log de erros).",
        "O botao de tema (claro/escuro) tambem esta na barra lateral. O log de erros pode ser "
        "consultado sem sair do programa.",
    ]),
    ("12. Atalhos de Teclado", [
        "Ctrl+1 a Ctrl+0 — abre as telas na ordem do menu (1 Inicio, 2 Certificados, "
        "3 Funcionarios, 4 Historico, 5 Funcoes, 6 Vencimentos, 7 ASO, 8 Cartoes, "
        "9 Importacao em massa, 0 Backups).",
        "Ctrl+T — alterna tema claro/escuro.  F5 — atualiza a tela atual.  "
        "F1 — abre este guia.",
    ]),
]


def generate_guia_pdf(output_path) -> Path:
    """Gera o guia completo em output_path e retorna o caminho."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="NormaTech - Guia de Introducao",
        author="NormaTech",
    )
    base = getSampleStyleSheet()
    st_title = ParagraphStyle("GuiaTitulo", parent=base["Title"],
                              textColor=PRIMARY, fontSize=22, spaceAfter=4)
    st_sub = ParagraphStyle("GuiaSub", parent=base["Normal"],
                            textColor=MUTED, fontSize=11, spaceAfter=18)
    st_h2 = ParagraphStyle("GuiaH2", parent=base["Heading2"],
                           textColor=ACCENT, fontSize=13,
                           spaceBefore=16, spaceAfter=4)
    st_body = ParagraphStyle("GuiaBody", parent=base["BodyText"],
                             textColor=TEXT, fontSize=10, leading=14)
    st_bul = ParagraphStyle("GuiaBul", parent=st_body,
                            leftIndent=12, spaceAfter=3)

    story = [
        Paragraph("NormaTech — Guia de Introdução", st_title),
        Paragraph("Guia rapido de uso do sistema, voltado para o dia a dia. "
                  "Pressione F1 a qualquer momento para reabrir este guia.", st_sub),
    ]

    for titulo, paragrafos in _SECOES:
        story.append(Paragraph(titulo, st_h2))
        for p in paragrafos:
            if p.startswith("- "):
                story.append(Paragraph("• " + p[2:], st_bul))
            else:
                story.append(Paragraph(p, st_body))

    story.append(Spacer(1, 24))
    story.append(Paragraph(
        "NormaTech — emissor de certificados, ASO, crachas e fichas de EPI.",
        ParagraphStyle("GuiaRodape", parent=st_sub, fontSize=9)))

    doc.build(story)
    return output_path


def guia_path() -> Path:
    """Caminho padrao do guia (data/GUIA_NORMATECH.pdf)."""
    return get_data_dir() / "GUIA_NORMATECH.pdf"


def guia_docx_path() -> Path:
    """Fonte editavel do guia (templates/GUIA_NORMATECH.docx)."""
    from src.utils.paths import get_templates_dir
    return get_templates_dir() / "GUIA_NORMATECH.docx"


def _converter_docx_para_pdf(docx_path: Path, pdf_path: Path):
    """Converte o DOCX do guia em PDF usando o Microsoft Word (COM).

    Levanta excecao se o Word nao estiver instalado — o chamador faz
    fallback para o PDF interno (ReportLab).
    """
    import comtypes.client

    word = comtypes.client.CreateObject("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(docx_path), ReadOnly=True)
        try:
            doc.SaveAs2(str(pdf_path), FileFormat=17)  # 17 = wdFormatPDF
        finally:
            doc.Close(False)
    finally:
        word.Quit()


def garantir_guia() -> Path:
    """Garante o PDF do guia e retorna o caminho.

    Se existir templates/GUIA_NORMATECH.docx (v1.19.0), converte via Word
    (regenerando quando o DOCX for mais novo que o PDF). Sem Word, ou sem
    DOCX, usa o PDF interno (ReportLab) como fallback.
    """
    path = guia_path()
    docx = guia_docx_path()
    if docx.exists():
        desatualizado = (
            not path.exists()
            or docx.stat().st_mtime > path.stat().st_mtime
        )
        if desatualizado:
            try:
                _converter_docx_para_pdf(docx, path)
                return path
            except Exception:
                from src.utils.error_log import log_error
                log_error("guia-docx-word", sys.exc_info()[1])
                if path.exists():
                    return path  # PDF antigo ainda serve
        else:
            return path
    if not path.exists():
        generate_guia_pdf(path)
    return path
