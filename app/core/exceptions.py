class AppError(Exception):
    """Base class for application errors that should map to a specific HTTP status."""

    status_code = 500
    detail = "Internal server error"

    def __init__(self, detail: str | None = None):
        super().__init__(detail or self.detail)
        if detail:
            self.detail = detail


class DatabaseUnavailableError(AppError):
    status_code = 503
    detail = "Database is currently unavailable"


class SQLValidationError(AppError):
    status_code = 400
    detail = "Generated SQL failed validation"


class LLMUnavailableError(AppError):
    status_code = 502
    detail = "LLM provider is currently unavailable"


class QuestionNotUnderstoodError(AppError):
    status_code = 400
    detail = "The question could not be mapped to a supported SQL query"
