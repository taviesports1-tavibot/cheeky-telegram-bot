from app.services.media import validate_media


def test_media_validation() -> None:
    assert validate_media("image/jpeg", 1024, 10).valid
    assert not validate_media("application/x-executable", 1024, 10).valid
    assert not validate_media("image/jpeg", 20 * 1024 * 1024, 10).valid
