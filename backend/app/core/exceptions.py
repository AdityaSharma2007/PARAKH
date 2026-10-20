class ParakhException(Exception):
    """Base exception for all PARAKH domain errors."""
    def __init__(self, message: str, status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class EntityNotFoundError(ParakhException):
    def __init__(self, entity_name: str, entity_id: str | int):
        super().__init__(f"{entity_name} with ID '{entity_id}' not found.", status_code=404)

class InvalidStateTransitionError(ParakhException):
    def __init__(self, from_state: str, to_state: str, reason: str = ""):
        msg = f"Cannot transition interview from '{from_state}' to '{to_state}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg, status_code=409)

class ResumeParsingError(ParakhException):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(f"Resume parsing failed: {message}", status_code=422, details=details)

class AIProviderError(ParakhException):
    def __init__(self, provider: str, message: str):
        super().__init__(f"AI Provider ({provider}) error: {message}", status_code=502)

class AudioProcessingError(ParakhException):
    def __init__(self, message: str):
        super().__init__(f"Audio processing error: {message}", status_code=422)
