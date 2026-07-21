from __future__ import annotations

import random
import re

from app.ai.moderation import safe_roast_target

ROULETTE = (
    "Сегодня тебе везёт. Подозрительно. Проверь карманы.",
    "Выпало: сделать вид, что всё под контролем. Классика.",
    "Джекпот! Ты официально главный красавчик ближайшие 15 минут.",
    "Барабан решил: хватит думскроллить, налей воды и вернись.",
)
WHO_TODAY = (
    "сегодня красавчик",
    "главный душнила",
    "первым уйдёт с вечеринки",
    "сегодня король чата",
    "подозрительно тихий",
)
TRUTHS = (
    "Какую самую нелепую ложь ты говорил(а), чтобы отменить встречу?",
    "Какой твой guilty pleasure, который ты обычно скрываешь?",
    "Какое сообщение ты однажды отправил(а) не тому человеку?",
)
DARES = (
    "Пришли самый смешной безопасный мем из галереи.",
    "Напиши комплимент последнему человеку в чате, но как герой боевика.",
    "Поставь себе смешной статус на 10 минут.",
)
PREDICTIONS = (
    "Сегодня тебя ждёт внезапная удача и один очень странный диалог.",
    "Скоро появится повод сказать: «Ну я же говорил(а)!».",
    "Твоя неделя будет на 73% продуктивнее, если перестанешь открывать холодильник без цели.",
)
ROASTS = (
    "{name}, твоя уверенность прекрасна. Особенно когда факты ушли на обед.",
    "{name}, ты не опоздал(а) с мыслью — просто она пришла следующим поездом.",
    "{name}, у тебя талант превращать простой вопрос в сезон сериала.",
)


def roulette(rng: random.Random | None = None) -> str:
    return (rng or random).choice(ROULETTE)


def who_today(users: list[str], rng: random.Random | None = None) -> str:
    if not users:
        return "Активных героев не найдено. Все затаились, как должники."
    randomizer = rng or random
    return (
        f"{randomizer.choice(users)} — {randomizer.choice(WHO_TODAY)}. "
        "Решение суда окончательное 😈"
    )


def duel(first: str, second: str, rng: random.Random | None = None) -> str:
    winner, loser = (rng or random).sample([first, second], 2)
    return (
        f"⚔️ {winner} побеждает! {loser} красиво смотрел(а) в горизонт "
        "и делал(а) вид, что так и задумано."
    )


def truth_or_dare(rng: random.Random | None = None) -> str:
    randomizer = rng or random
    kind = randomizer.choice(("Правда", "Действие"))
    value = randomizer.choice(TRUTHS if kind == "Правда" else DARES)
    return f"<b>{kind}:</b> {value}"


def prediction(rng: random.Random | None = None) -> str:
    return "🔮 " + (rng or random).choice(PREDICTIONS)


def rate(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip()).casefold()
    score = (sum(ord(char) for char in normalized) % 11) if normalized else 0
    comments = {
        0: "Это даже шкала отказалась оценивать.",
        10: "Абсолютная десятка. Без взяток, честно.",
    }
    return (
        f"Ставлю <b>{score}/10</b>. {comments.get(score, 'Научно необоснованно, зато уверенно.')}"
    )


def roast(name: str, context: str = "", rng: random.Random | None = None) -> str:
    if not safe_roast_target(context):
        return (
            "Эту тему не жарю — тут уже не шутка, а дешёвая травля. "
            "Выбери что-нибудь без личной жести."
        )
    return (rng or random).choice(ROASTS).format(name=name)
