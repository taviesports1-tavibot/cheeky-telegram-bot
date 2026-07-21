from app.ai.moderation import sanitize_user_text


def approximate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def trim_context(messages: list[dict[str, str]], token_limit: int) -> list[dict[str, str]]:
    total = 0
    result: list[dict[str, str]] = []
    for message in reversed(messages):
        item = {"role": message["role"], "content": sanitize_user_text(message["content"])}
        tokens = approximate_tokens(item["content"])
        if result and total + tokens > token_limit:
            break
        result.append(item)
        total += tokens
    return list(reversed(result))
