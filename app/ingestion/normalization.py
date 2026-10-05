import unicodedata


def normalize_name(text: str) -> str:
    """Clave de comparación: minúsculas, sin acentos y con espacios colapsados.

    "Salmón  Rosado" y "salmon rosado" generan la misma clave, así que los
    nombres se pueden cruzar entre fuentes distintas (Excel, PDF, recetas).
    """
    without_accents = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(without_accents.lower().split())
