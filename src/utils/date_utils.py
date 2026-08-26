from datetime import date, timedelta


def hoje() -> date:
    """Retorna a data de hoje."""
    return date.today()


def adicionar_dias(data: date, dias: int) -> date:
    """Adiciona dias a uma data."""
    return data + timedelta(days=dias)


def adicionar_anos(data: date, anos: int) -> date:
    """Adiciona anos a uma data (aproximado)."""
    try:
        return data.replace(year=data.year + anos)
    except ValueError:
        # 29/02 em ano não bissexto
        return data.replace(year=data.year + anos, day=28)


def dias_ate(data: date) -> int:
    """Retorna quantos dias até a data (negativo se passou)."""
    return (data - hoje()).days


def data_para_str(data: date) -> str:
    """Converte date para string DD/MM/YYYY."""
    return data.strftime("%d/%m/%Y")


def str_para_data(s: str) -> date | None:
    """Converte string DD/MM/YYYY para date."""
    try:
        return date.fromisoformat(s) if '-' in s else None
    except ValueError:
        try:
            from datetime import datetime
            return datetime.strptime(s, "%d/%m/%Y").date()
        except ValueError:
            return None