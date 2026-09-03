from pathlib import Path
import threading
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from src.core.models import CertificateData, NRTemplate, LayoutConfig
from src.utils.paths import get_assets_dir, get_fonts_dir

_fonts_registered = False
_font_lock = threading.Lock()


def _register_fonts():
    global _fonts_registered
    with _font_lock:
        if _fonts_registered:
            return
        fonts_dir = get_fonts_dir()
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', str(fonts_dir / 'DejaVuSans.ttf')))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', str(fonts_dir / 'DejaVuSans-Bold.ttf')))
            _fonts_registered = True
        except Exception:
            pass


def _hex(color: str) -> HexColor:
    return HexColor(color)


def _get_font_spec(fonts: dict, name: str) -> dict:
    spec = fonts.get(name, {})
    if not spec:
        for key in ['body_bold', 'body', 'small']:
            if key in fonts:
                spec = fonts[key]
                break
    return spec


def _draw_signature_block(canvas, x_center, y_top, label, name, detail, detail2,
                          line_width, sig_font, sig_size, detail_font, detail_size,
                          color, muted_color):
    """Desenha um bloco de assinatura completo no canvas."""
    canvas.saveState()

    # Linha de assinatura
    canvas.setStrokeColor(color)
    canvas.setLineWidth(0.5)
    line_x_start = x_center - line_width / 2
    line_x_end = x_center + line_width / 2
    canvas.line(line_x_start, y_top, line_x_end, y_top)

    # Label (ex: INSTRUTOR/RESPONSAVEL TECNICO)
    canvas.setFillColor(color)
    canvas.setFont(sig_font, sig_size)
    canvas.drawCentredString(x_center, y_top - 4 * mm, label)

    # Nome
    canvas.setFont(sig_font, sig_size)
    canvas.drawCentredString(x_center, y_top - 9 * mm, name)

    # Detalhe 1 (ex: TECNICO EM SEGURANCA DO TRABALHO)
    canvas.setFillColor(muted_color)
    canvas.setFont(detail_font, detail_size)
    canvas.drawCentredString(x_center, y_top - 14 * mm, detail)

    # Detalhe 2 (ex: REGISTRO MTE 44633/RJ)
    if detail2:
        canvas.drawCentredString(x_center, y_top - 18 * mm, detail2)

    canvas.restoreState()


def generate_certificate_pdf(
    data: CertificateData,
    template: NRTemplate,
    output_path: Path,
    layout: LayoutConfig = None
) -> Path:
    _register_fonts()

    if layout is None:
        from src.core.template_loader import load_layout_config
        layout = load_layout_config()

    page_width, page_height = landscape(A4)
    margins = layout.margins
    content_width = page_width - (margins["left"] + margins["right"]) * mm

    fonts = layout.fonts
    colors = layout.colors
    spacers_cfg = layout.spacers
    border_cfg = layout.border
    divider_cfg = layout.divider

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        topMargin=margins["top"] * mm,
        bottomMargin=margins["bottom"] * mm,
        leftMargin=margins["left"] * mm,
        rightMargin=margins["right"] * mm,
        title=f"Certificado {data.cert_number}",
        author=data.empresa_nome
    )

    styles = getSampleStyleSheet()

    # === ESTILOS ===
    title_spec = _get_font_spec(fonts, 'title')
    subtitle_spec = _get_font_spec(fonts, 'subtitle')
    body_bold_spec = _get_font_spec(fonts, 'body_bold')
    small_spec = _get_font_spec(fonts, 'small')
    sig_spec = _get_font_spec(fonts, 'signature')
    sig_bold_spec = _get_font_spec(fonts, 'signature_bold')
    sig_detail_spec = _get_font_spec(fonts, 'signature_detail')
    content_item_spec = _get_font_spec(fonts, 'content_item')

    style_title = ParagraphStyle(
        'CertTitle', parent=styles['Title'],
        fontName=title_spec.get('family', 'Helvetica-Bold'),
        fontSize=title_spec.get('size', 26),
        textColor=_hex(title_spec.get('color', '#1B3A5C')),
        alignment=TA_CENTER,
        spaceAfter=title_spec.get('space_after', 4),
        leading=title_spec.get('size', 26) * title_spec.get('leading_multiplier', 1.3)
    )
    style_subtitle = ParagraphStyle(
        'CertSubtitle', parent=styles['Heading2'],
        fontName=subtitle_spec.get('family', 'Helvetica-Bold'),
        fontSize=subtitle_spec.get('size', 14),
        textColor=_hex(subtitle_spec.get('color', '#1B3A5C')),
        alignment=TA_CENTER,
        spaceAfter=subtitle_spec.get('space_after', 4),
        leading=subtitle_spec.get('size', 14) * subtitle_spec.get('leading_multiplier', 1.4)
    )
    style_body_bold = ParagraphStyle(
        'CertBodyBold', parent=styles['Normal'],
        fontName=body_bold_spec.get('family', 'Helvetica-Bold'),
        fontSize=body_bold_spec.get('size', 13),
        textColor=_hex(body_bold_spec.get('color', '#333333')),
        alignment=TA_JUSTIFY,
        leading=body_bold_spec.get('size', 13) * body_bold_spec.get('leading_multiplier', 1.5),
        spaceAfter=body_bold_spec.get('space_after', 6)
    )
    style_date_line = ParagraphStyle(
        'DateLine', parent=styles['Normal'],
        fontName=body_bold_spec.get('family', 'Helvetica-Bold'),
        fontSize=body_bold_spec.get('size', 13),
        textColor=_hex(body_bold_spec.get('color', '#333333')),
        alignment=TA_RIGHT,
        leading=body_bold_spec.get('size', 13) * body_bold_spec.get('leading_multiplier', 1.5),
        spaceAfter=body_bold_spec.get('space_after', 6)
    )
    style_title_center = ParagraphStyle(
        'CertTitleCenter', parent=style_title,
        alignment=TA_CENTER
    )
    style_content_item = ParagraphStyle(
        'ContentItem', parent=styles['Normal'],
        fontName=content_item_spec.get('family', 'Helvetica-Bold'),
        fontSize=content_item_spec.get('size', 12),
        textColor=_hex(content_item_spec.get('color', '#333333')),
        alignment=TA_LEFT,
        leading=content_item_spec.get('size', 12) * content_item_spec.get('leading_multiplier', 1.4),
        spaceAfter=content_item_spec.get('space_after', 3),
        leftIndent=content_item_spec.get('left_indent_mm', 5) * mm
    )

    story = []

    # =============================================
    # PRIMEIRA FOLHA
    # =============================================

    # 1. Logo + Titulo
    logo_cfg = layout.logo
    logo_path = get_assets_dir() / Path(logo_cfg.get('path', 'assets/LOGO TIPO ALTEC.png')).name
    nr_num = data.nr_code.replace("NR-", "")
    title_text = layout.title_format.format(nr_num=nr_num)

    logo_w = logo_cfg.get('width', 28) * mm
    logo_h = logo_cfg.get('height', 18) * mm

    if logo_path.exists():
        try:
            img = Image(str(logo_path), width=logo_w, height=logo_h)
            img.hAlign = 'LEFT'
            title_para = Paragraph(f"<b>{title_text}</b>", style_title_center)
            header_table = Table(
                [[img, title_para]],
                colWidths=[logo_w + 2 * mm, content_width - logo_w - 2 * mm]
            )
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(header_table)
        except Exception:
            story.append(Paragraph(f"<b>{title_text}</b>", style_title))
    else:
        story.append(Paragraph(f"<b>{title_text}</b>", style_title))

    story.append(Spacer(1, spacers_cfg.get('after_header_mm', 4) * mm))

    # 2. Linha divisoria
    divider_data = [['']]
    divider_table = Table(divider_data, colWidths=[content_width])
    divider_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), divider_cfg.get('line_width', 2), _hex(colors['divider'])),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(divider_table)
    story.append(Spacer(1, spacers_cfg.get('after_divider_mm', 8) * mm))

    # 3. Texto principal
    texto = template.texto_certificado.format(**data.to_dict())
    story.append(Paragraph(f"<b>{texto}</b>", style_body_bold))
    story.append(Spacer(1, spacers_cfg.get('after_text_mm', 8) * mm))

    # 4. Cidade, Data (direita)
    meses_pt = {
        1: "janeiro", 2: "fevereiro", 3: "marco", 4: "abril",
        5: "maio", 6: "junho", 7: "julho", 8: "agosto",
        9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
    }
    d = data.data_treinamento
    data_extensa = f"{d.day} de {meses_pt[d.month]} de {d.year}"
    city = layout.city
    story.append(Paragraph(f"<b>{city}, {data_extensa}</b>", style_date_line))

    # NAO ha mais Spacer de empurro nem tabela de assinaturas no story.
    # Assinaturas e numero do certificado sao desenhados no canvas (onFirstPage).

    # =============================================
    # QUEBRA DE PAGINA
    # =============================================
    story.append(PageBreak())

    # =============================================
    # SEGUNDA FOLHA - CONTEUDO PROGRAMATICO
    # =============================================

    story.append(Paragraph(layout.content_title, style_subtitle))
    story.append(Spacer(1, spacers_cfg.get('after_content_title_mm', 6) * mm))

    items = template.conteudo_programatico
    for item in items:
        story.append(Paragraph(f"<b>- {item}</b>", style_content_item))

    # =============================================
    # BORDA + ASSINATURAS + NUMERO (desenhados no canvas)
    # =============================================
    border_inset = border_cfg.get('inset_mm', 5) * mm
    border_lw = border_cfg.get('line_width', 2)
    sig_blocks = layout.signature_blocks
    sig_line_len = layout.signature_line_length

    # Pre-calcula dados das assinaturas para o callback
    sig_data = {
        'blocks': [],
        'cert_number': f"{layout.certificate_number.get('prefix', 'CERT-')}{data.cert_number.split('-')[-1]}",
        'cert_font_size': layout.certificate_number.get('font_size', 7),
        'cert_color': layout.certificate_number.get('color', '#CCCCCC'),
    }

    # Bloco do instrutor
    if len(sig_blocks) >= 1:
        sig_data['blocks'].append({
            'label': sig_blocks[0].get('label', 'INSTRUTOR'),
            'name': data.instrutor_nome,
            'detail': "TECNICO EM SEGURANCA DO TRABALHO",
            'detail2': f"REGISTRO MTE {data.instrutor_registro_mte}",
        })

    # Bloco do participante
    if len(sig_blocks) >= 2:
        sig_data['blocks'].append({
            'label': sig_blocks[1].get('label', 'PARTICIPANTE'),
            'name': data.funcionario_nome,
            'detail': data.funcionario_cpf,
            'detail2': '',
        })

    def add_border(canvas, doc):
        canvas.saveState()

        # Borda
        canvas.setStrokeColor(_hex(colors['divider']))
        canvas.setLineWidth(border_lw)
        bw = page_width - 2 * border_inset
        bh = page_height - 2 * border_inset
        canvas.rect(border_inset, border_inset, bw, bh)

        # Assinaturas (apenas na primeira pagina)
        if doc.page == 1:
            num_blocks = len(sig_data['blocks'])
            if num_blocks > 0:
                # Posicao Y das assinaturas (fixa, 35mm da borda inferior)
                sig_y = border_inset + 35 * mm

                # Largura da linha de assinatura
                line_w = sig_line_len * 0.45 * mm  # Converte caracteres para mm aproximado

                # Espacamento entre blocos
                total_sig_width = content_width * 0.8
                block_spacing = total_sig_width / num_blocks

                # Posicao X inicial (centralizado)
                x_start = margins["left"] * mm + (content_width - total_sig_width) / 2

                for i, block in enumerate(sig_data['blocks']):
                    x_center = x_start + block_spacing * i + block_spacing / 2

                    sig_block_cfg = layout.signature_block
                    _draw_signature_block(
                        canvas, x_center, sig_y,
                        block['label'], block['name'],
                        block['detail'], block['detail2'],
                        line_w,
                        'Helvetica-Bold', sig_block_cfg.get('name_size', 10),
                        'Helvetica', sig_block_cfg.get('detail_size', 8),
                        _hex(colors['text']),
                        _hex(sig_block_cfg.get('detail_color', '#000000'))
                    )

        # Numero do certificado (canto inferior direito, EM TODAS as paginas)
        canvas.setFillColor(_hex(sig_data['cert_color']))
        canvas.setFont('Helvetica', sig_data['cert_font_size'])
        canvas.drawRightString(
            page_width - margins["right"] * mm,
            border_inset + 8 * mm,
            sig_data['cert_number']
        )

        canvas.restoreState()

    doc.build(story, onFirstPage=add_border, onLaterPages=add_border)
    return output_path
