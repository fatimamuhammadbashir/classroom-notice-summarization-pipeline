"""Configuration loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"


def load_config(path: str | Path | None = None) -> dict:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(
            f"Could not read config file: {config_path.name}",
            details=str(exc),
        ) from None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"Config file is not valid JSON: {config_path.name}",
            details=f"line {exc.lineno}, column {exc.colno}",
        ) from None
    return validate_config(raw)


def validate_config(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValidationError("Config must be a JSON object.")
    for key in ("version", "input", "summarization", "checklist", "storage"):
        if key not in raw:
            raise ValidationError(f"Config is missing required key: {key}")

    input_config = raw["input"]
    if not isinstance(input_config, dict):
        raise ValidationError("Config input must be an object.")
    for key in ("max_characters", "min_characters"):
        value = input_config.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValidationError(f"Config input.{key} must be a positive whole number.")
    if input_config["min_characters"] >= input_config["max_characters"]:
        raise ValidationError("Config min_characters must be less than max_characters.")
    extensions = input_config.get("allowed_extensions")
    if not isinstance(extensions, list) or not extensions:
        raise ValidationError("Config input.allowed_extensions must be a non-empty list.")
    for extension in extensions:
        if not isinstance(extension, str) or not extension.startswith("."):
            raise ValidationError("Config allowed extensions must start with a dot.")

    summary = raw["summarization"]
    if not isinstance(summary, dict):
        raise ValidationError("Config summarization must be an object.")
    for key in ("max_sentences", "max_words", "min_sentence_words"):
        value = summary.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValidationError(f"Config summarization.{key} must be a positive whole number.")
    if summary["max_sentences"] < 2:
        raise ValidationError("Config summarization.max_sentences must be at least 2.")
    if summary["max_words"] < 30:
        raise ValidationError("Config summarization.max_words must be at least 30.")

    if not isinstance(raw["checklist"], dict):
        raise ValidationError("Config checklist must be an object.")
    if not isinstance(raw["storage"], dict):
        raise ValidationError("Config storage must be an object.")
    for key in ("results_dir", "failure_log"):
        if not isinstance(raw["storage"].get(key), str) or not raw["storage"][key].strip():
            raise ValidationError(f"Config storage.{key} must be a non-empty path string.")

    return raw
