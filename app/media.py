from urllib.parse import urlparse

ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


def validate_media_reference(value: str, content_type: str | None = None) -> str:
    if not value or len(value) > 1000:
        raise ValueError("media reference is required and must be short")
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("media reference must be an absolute http(s) URL")
    if content_type and content_type.lower() not in ALLOWED_MEDIA_TYPES:
        raise ValueError("unsupported media type")
    return value
