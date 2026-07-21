from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_forget(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, удалить", callback_data=f"forget:yes:{user_id}"),
                InlineKeyboardButton(text="Отмена", callback_data=f"forget:no:{user_id}"),
            ]
        ]
    )


def welcome_buttons(rules_url: str | None) -> InlineKeyboardMarkup:
    buttons = []
    if rules_url:
        buttons.append(InlineKeyboardButton(text="📜 Правила", url=rules_url))
    buttons.append(InlineKeyboardButton(text="🎮 Развлечения", callback_data="help:games"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="😈 Характер", callback_data="admin:personality"),
                InlineKeyboardButton(text="🎙 Голос", callback_data="admin:voice"),
            ],
            [
                InlineKeyboardButton(text="🖼 Медиа", callback_data="admin:media"),
                InlineKeyboardButton(text="😂 Реакции", callback_data="admin:reactions"),
            ],
            [
                InlineKeyboardButton(text="⏰ Расписание", callback_data="admin:schedule"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
            ],
        ]
    )
