from app.core.messages import ErrorMessage

class AppException(Exception):
    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = 400, field: str | None = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.field = field


class NotFoundException(AppException):
    def __init__(self, message: str = ErrorMessage.NOT_FOUND):
        super().__init__(message=message, code="NOT_FOUND", status_code=404)


class ValidationException(AppException):
    def __init__(self, message: str = ErrorMessage.VALIDATION_FAILED, errors: list | None = None):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422)
        self.errors = errors or []

class RunCancelledException(Exception):
    pass
