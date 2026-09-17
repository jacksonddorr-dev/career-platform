import pytest

from app.media import validate_media_reference


def test_media_reference_accepts_https_images():
    assert validate_media_reference("https://example.com/photo.webp", "image/webp").startswith("https://")


@pytest.mark.parametrize("value", ["javascript:alert(1)", "relative/path", ""])
def test_media_reference_rejects_unsafe_urls(value):
    with pytest.raises(ValueError):
        validate_media_reference(value)
