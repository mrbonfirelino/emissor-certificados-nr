import unicodedata


def normalize_text(text: str) -> str:
    """Remove acentos e normaliza para busca case-insensitive.

    Exemplo:
        'João da Silva' -> 'joao da silva'
        'ÇÃO' -> 'cao'
    """
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
