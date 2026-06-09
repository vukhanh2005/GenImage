from __future__ import annotations


class AppError(Exception):
    pass


class ApiError(AppError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.reason = reason


class ResponseParseError(AppError):
    pass
