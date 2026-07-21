import random

from app.services import games


def test_games_are_deterministic_with_seed() -> None:
    rng = random.Random(10)
    assert games.roulette(rng)
    assert "побеждает" in games.duel("Антон", "Макс", rng)
    assert "Решение суда" in games.who_today(["Антон"], rng)


def test_rate_is_stable() -> None:
    assert games.rate("тест") == games.rate("тест")


def test_safe_roast_refuses_sensitive_target() -> None:
    result = games.roast("Человек", "шутка про инвалидность")
    assert "не жарю" in result
