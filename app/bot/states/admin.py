from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    waiting_confirmation = State()
