class QuantPlatformError(Exception):
    code = "QUANT_PLATFORM_ERROR"


class NotFoundError(QuantPlatformError):
    code = "NOT_FOUND"


class ValidationError(QuantPlatformError):
    code = "VALIDATION_ERROR"


class TaskSubmitError(QuantPlatformError):
    code = "TASK_SUBMIT_ERROR"

