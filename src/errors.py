"""Typed errors for the notice summarization pipeline."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    code = "app_error"

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.details = details

    def to_dict(self) -> dict:
        payload: dict[str, Any] = {
            "error": {
                "type": self.code,
                "message": self.message,
            }
        }
        if self.field:
            payload["error"]["field"] = self.field
        if self.details is not None:
            payload["error"]["details"] = self.details
        return payload


class ValidationError(AppError):
    code = "validation_error"


class StorageError(AppError):
    code = "storage_error"


class EditError(AppError):
    code = "edit_error"
