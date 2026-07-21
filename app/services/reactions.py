from __future__ import annotations

import random

from aiogram import Bot
from aiogram.types import ReactionTypeEmoji

NEGATIVE = {"🤡", "💩"}


def choose_reaction(emojis: list[str], rng: random.Random | None = None) -> str:
    randomizer = rng or random
    positive = [emoji for emoji in emojis if emoji not in NEGATIVE]
    if positive and randomizer.random() < 0.8:
        return randomizer.choice(positive)
    return randomizer.choice(emojis or ["😂"])


async def react(bot: Bot, chat_id: int, message_id: int, emoji: str) -> None:
    await bot.set_message_reaction(chat_id, message_id, [ReactionTypeEmoji(emoji=emoji)])
