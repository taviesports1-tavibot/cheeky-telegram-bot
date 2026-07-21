import re

INJECTION_PATTERNS = (
    r"ignore (all|previous) instructions",
    r"забудь (все|предыдущие) инструкции",
    r"покажи (системный|скрытый) промпт",
    r"reveal (the )?(system|developer) prompt",
    r"выполни (команду|код) в (системе|терминале)",
)

SENSITIVE_PATTERNS = (
    r"\b(?:\d[ -]*?){13,19}\b",
    r"\b\d{3}-\d{2}-\d{4}\b",
)


def sanitize_user_text(text: str, max_length: int = 4000) -> str:
    clean = text.replace("\x00", " ").strip()[:max_length]
    for pattern in SENSITIVE_PATTERNS:
        clean = re.sub(pattern, "[СКРЫТО]", clean)
    return clean


def looks_like_prompt_injection(text: str) -> bool:
    lowered = text.casefold()
    return any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS)


def safe_roast_target(text: str) -> bool:
    forbidden = {
        "инвалид",
        "рак",
        "больной",
        "сирота",
        "мертв",
        "умер",
        "раса",
        "нация",
        "религия",
        "гей",
        "лесбиян",
        "транс",
        "толст",
        "урод",
        "внешност",
    }
    lowered = text.casefold()
    return not any(term in lowered for term in forbidden)
