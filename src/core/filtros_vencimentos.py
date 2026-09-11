"""Filtros de vencimentos compartilhados entre desktop e portal (v1.28.0).

Extraido de src/ui/pages/vencimentos.py para o portal web reutilizar a mesma
logica sem depender de customtkinter (servidor nao tem interface grafica).
"""

# limites dos filtros por periodo (dias para vencer); vencidos (d < 0) so
# aparecem nos filtros "Todos" e "Vencidos"
PERIOD_RANGES = {
    "dias_7": (0, 7),
    "dias_15": (0, 15),
    "mes_1": (0, 30),
    "meses_3": (0, 90),
}


def filter_certs(certs: list, nr: str, search: str, period: str) -> list:
    """Filtra certificados por NR, busca textual e periodo de vencimento."""
    out = []
    for c in certs:
        if nr != "TODAS" and c["nr_code"] != nr:
            continue
        if search:
            if (search not in c["funcionario_nome"].lower()
                    and search not in c["funcionario_cpf"]
                    and search not in c["nr_code"].lower()):
                continue
        d = c["dias_para_vencer"]
        if period == "vencidos":
            if d >= 0:
                continue
        elif period in PERIOD_RANGES:
            lo, hi = PERIOD_RANGES[period]
            if not (lo <= d <= hi):
                continue
        out.append(c)
    return out
