"""Notice upload validation."""

from __future__ import annotations

from pathlib import Path

from .errors import ValidationError
from .text_processing import normalize_text


def load_notice_file(path: str | Path, config: dict) -> tuple[str, str]:
    notice_path = Path(path)
    if not notice_path.exists():
        raise ValidationError(
            f"Notice file not found: {notice_path.name}",
            field="notice",
        )
    if not notice_path.is_file():
        raise ValidationError(
            f"Notice path is not a file: {notice_path.name}",
            field="notice",
        )
    allowed = {extension.casefold() for extension in config["input"]["allowed_extensions"]}
    if notice_path.suffix.casefold() not in allowed:
        raise ValidationError(
            f"Unsupported notice type: {notice_path.suffix or '(no extension)'}",
            field="notice",
            details={"allowed_extensions": sorted(allowed)},
        )
    try:
        raw = notice_path.read_bytes()
    except OSError as exc:
        raise ValidationError(
            f"Could not read notice: {notice_path.name}",
            details=str(exc),
        ) from None
    if len(raw) > config["input"]["max_characters"] * 4:
        raise ValidationError(
            "Notice file is too large.",
            field="notice",
            details={"max_characters": config["input"]["max_characters"]},
        )
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError(
            "Notice file must be UTF-8 encoded.",
            field="notice",
            details=f"byte {exc.start}",
        ) from None
    return validate_notice_text(text, config), notice_path.name


def validate_notice_text(text: str, config: dict) -> str:
    if not isinstance(text, str):
        raise ValidationError("Notice text must be a string.", field="text")
    normalized = normalize_text(text)
    if len(normalized) < config["input"]["min_characters"]:
        raise ValidationError(
            f"Notice is too short; minimum is {config['input']['min_characters']} characters.",
            field="text",
        )
    if len(normalized) > config["input"]["max_characters"]:
        raise ValidationError(
            f"Notice is too long; maximum is {config['input']['max_characters']} characters.",
            field="text",
        )
    if "\x00" in normalized:
        raise ValidationError("Notice must not contain null characters.", field="text")
    return normalized
