from aiogram import Bot


async def is_admin(bot: Bot, chat_id: int, user_id: int, superadmin_ids: frozenset[int]) -> bool:
    if user_id in superadmin_ids:
        return True
    if chat_id > 0:
        return user_id == chat_id
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in {"creator", "administrator"}
    except Exception:
        return False
