from html import escape


def safe(value: object) -> str:
    return escape(str(value), quote=True)


def truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"
