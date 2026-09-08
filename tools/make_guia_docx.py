"""Gera templates/GUIA_NORMATECH.docx — fonte editavel do Guia (v1.19.0).

O app converte este DOCX em PDF via Word (COM) ao abrir o guia (F1/botao);
sem Word, cai no PDF interno (src/core/guia_generator.py). Ao editar o
conteudo do guia, rode este script de novo (conteudo espelhado do gerador).
"""

from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "templates" / "GUIA_NORMATECH.docx"

AZUL = RGBColor(0x1B, 0x3A, 0x5C)
CINZA = RGBColor(0x55, 0x5F, 0x6E)

# (titulo, [paragrafos]) — mesmo conteudo de src/core/guia_generator.py
SECOES = [
    ("Bem-vindo ao NormaTech!", [
        "O NormaTech organiza toda a seguranca do trabalho da empresa: cadastro de "
        "funcionarios, emissa de certificados de treinamento (NRs), cartoes de bloqueio, "
        "crachas, ASO e fichas de EPI, com backup automatico e copia dos documentos na rede.",
        "Nada aqui exige conhecimento tecnico: basta seguir as telas. Em caso de duvida, "
        "pressione F1 a qualquer momento para reabrir este guia.",
    ]),
    ("1. Cadastro de Funcionarios", [
        "Abra a aba Funcionarios (Ctrl+3) e use o botao Novo para cadastrar: nome, CPF, "
        "funcao, telefone, data de nascimento, tipo sanguineo, data de admissao, CTPS e CNH EAR.",
        "A foto 3x4 pode ser adicionada na ficha do funcionario ou em lote pelo botao "
        "Importar Fotos (os arquivos sao reconhecidos pelo CPF no nome ou pelo nome da pessoa).",
        "Importacao em massa: botao Importar Excel aceita planilhas nos modelos da pasta "
        "MODELOS DE IMPORTACAO. Exportar gera uma planilha com todos os cadastros.",
        "O botao Docs guardra documentos do funcionario (qualquer formato, ate 50MB).",
    ]),
    ("2. Emissao de Certificados", [
        "Na aba Certificados (Ctrl+2), escolha o treinamento (NR) no painel esquerdo, "
        "digite o funcionario no campo de busca e selecione na lista.",
        "Confira os dados da empresa em Configuracoes antes de emitir. O numero do "
        "certificado aparece em todas as folhas do PDF.",
        "Use Ver PDF para visualizar antes de emitir. Cada emissao e registrada no Historico.",
    ]),
    ("3. Vencimentos", [
        "A aba Vencimentos (Ctrl+6) mostra certificados e ASOs por periodo: vencidos, "
        "7/15 dias, 1 mes e 3 meses.",
        "Para renovar, use o botao Emitir no cartao do funcionario. Cada card mostra apenas "
        "a emissa mais recente de cada treinamento.",
        "Ao abrir o sistema, um aviso mostra o que vence nos proximos 7 dias.",
    ]),
    ("4. Cartoes de Bloqueio", [
        "A aba Cartoes de Bloqueio (Ctrl+8) emite cartoes de equipamento em "
        "manutencao a partir de modelos por cliente (ArcelorMittal, Altec, CSN, Lototo).",
        "Selecione os funcionarios, clique Gerar e confira a tela de revisao: ali voce pode "
        "corrigir nome, telefone, setor e matricula apenas para aquela emissao.",
        "Importar Excel marca varios funcionarios de uma vez. O PDF unico imprime varios "
        "cartoes por folha; a opcao 1 por pagina gera um por folha.",
    ]),
    ("5. Crachas de Identificacao", [
        "Os crachas (12x7,8cm ou vertical) ficam na mesma aba de Cartoes, com os modelos "
        "CRACHA ALTEC e CRACHA ALTEC VERTICAL.",
        "Na revisao, marque as NRs validas de cada funcionario (ate 8), confira o ASO e a "
        "data de emissao. Escolha Tamanho real ou Reduzido 86x54mm.",
        "A saida vem em folha A4 com guias de corte. O cracha so sai com foto, NR valida e "
        "ASO dentro da validade — funcionarios irregulares aparecem como BLOQUEADO.",
    ]),
    ("6. ASO (Atestado de Saude Ocupacional)", [
        "Na aba ASO (Ctrl+7), Novo ASO cria o numero, a capa com dados do funcionario e o "
        "prazo de validade (padrao 12 meses).",
        "Anexar ou Digitalizar embute o documento do medico nas paginas seguintes do mesmo PDF.",
        "Vencimentos de ASO aparecem junto com os certificados na aba Vencimentos e no painel.",
        "Importacao em lote: use o modelo MODELO ASO.xlsx; a coluna Tipo aceita os codigos "
        "A, P, M, R, D ou o nome completo.",
    ]),
    ("7. Fichas de EPI", [
        "No cadastro do funcionario, o botao EPI abre as fichas dele. Nova Ficha registra a "
        "retirada (C.A., descricao, quantidade e data — que ja vem com o dia atual).",
        "O PDF da ficha tem espaco de assinatura e mostra o estado de cada item: Devolvido "
        "em verde (total) ou laranja (parcial).",
        "Devolucoes sao registradas pelo botao Devolucao: marque Total ou Parcial por item "
        "com a data; o sistema gera o Termo de Devolucao para assinar.",
        "Fichas assinadas podem ser anexadas pelo botao Anexar (mantem todas as versoes).",
    ]),
    ("8. Backups", [
        "O sistema faz backup automatico (diario), periodico (a cada X minutos, configuravel) "
        "e manual na aba Backup (Ctrl+9).",
        "Copias de seguranca vao para Documents\\NormaTech-Backup e C:\\NormaTech-Backup e, "
        "se ativado, para a pasta na rede.",
        "A restauracao pede a senha definida em Configuracoes > Seguranca e reinicia o sistema.",
        "Opcional: em Configuracoes > Backups, ligue a Tarefa Agendada do Windows para o "
        "backup rodar com o programa fechado (padrao 12:00).",
    ]),
    ("9. Documentos em Rede", [
        "Em Configuracoes > Documentos em Rede, informe a pasta da rede: todo PDF gerado "
        "(certificados, cartoes, crachas, ASO, EPI, assinados) e copiado para a pasta do "
        "funcionario automaticamente.",
        "Treinamentos vencidos vao para a subpasta 00_Certificados_OLD. O botao Sincronizar "
        "Agora reenvia tudo que estiver faltando.",
    ]),
    ("10. Configuracoes", [
        "A aba Config (botao Config na barra lateral) reune: dados da empresa, senha de "
        "restauracao, tamanho da fonte, tema claro/escuro, backups, documentos em rede e o "
        "log de erros (Diagnostico). As secoes se abrem e fecham com um clique.",
    ]),
    ("11. Atalhos de Teclado", [
        "Ctrl+1 Tela inicial | Ctrl+2 Certificados | Ctrl+3 Funcionarios | Ctrl+4 Historico",
        "Ctrl+5 Funcoes | Ctrl+6 Vencimentos | Ctrl+7 ASO | Ctrl+8 Cartoes | Ctrl+9 Emissao "
        "em massa | Ctrl+0 Backup",
        "Ctrl+T alterna o tema | F5 atualiza a tela atual | F1 abre este guia.",
    ]),
]


def main():
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    doc = docx.Document()

    titulo = doc.add_heading("NormaTech — Guia de Introdução", level=0)
    for run in titulo.runs:
        run.font.color.rgb = AZUL

    sub = doc.add_paragraph(
        "Guia rápido de uso do sistema, pensado para o dia a dia. "
        "Pressione F1 dentro do NormaTech para abrir este guia a qualquer momento."
    )
    sub.runs[0].font.color.rgb = CINZA

    for titulo_secao, paragrafos in SECOES:
        h = doc.add_heading(titulo_secao, level=1)
        for run in h.runs:
            run.font.color.rgb = AZUL
        for p in paragrafos:
            par = doc.add_paragraph(p)
            par.paragraph_format.space_after = Pt(6)

    rodape = doc.add_paragraph()
    r = rodape.add_run("NormaTech — Emissor de Certificados, Cartões, Crachás, ASO e EPI.")
    r.italic = True
    r.font.color.rgb = CINZA
    rodape.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.save(DESTINO)
    print(f"[OK] {DESTINO}")


if __name__ == "__main__":
    main()
