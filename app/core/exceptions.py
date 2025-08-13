"""
Custom exception classes for the AMT Backend application.
"""

from fastapi import HTTPException, status


class AMTException(Exception):
    """Base exception class for AMT Backend."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TranscriptionNotFoundError(AMTException):
    """Raised when a transcription is not found."""

    def __init__(self, transcription_id: str):
        super().__init__(
            f"Transcription with ID '{transcription_id}' not found",
            status_code=404
        )


class AudioFileError(AMTException):
    """Raised when there's an issue with audio file processing."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class AudioValidationError(AudioFileError):
    """Raised when audio file validation fails."""

    def __init__(self, message: str):
        super().__init__(f"Audio validation failed: {message}")


class AudioProcessingError(AudioFileError):
    """Raised when audio processing fails."""

    def __init__(self, message: str):
        super().__init__(f"Audio processing failed: {message}")


class MIDIGenerationError(AMTException):
    """Raised when MIDI generation fails."""

    def __init__(self, message: str):
        super().__init__(f"MIDI generation failed: {message}", status_code=500)


class FileStorageError(AMTException):
    """Raised when file storage operations fail."""

    def __init__(self, message: str):
        super().__init__(f"File storage error: {message}", status_code=500)


class TranscriptionProcessingError(AMTException):
    """Raised when transcription processing fails."""

    def __init__(self, message: str):
        super().__init__(f"Transcription processing failed: {message}", status_code=500)


class RateLimitExceededError(AMTException):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit: int, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded. Maximum {limit} requests per minute allowed. "
            f"Retry after {retry_after} seconds.",
            status_code=429
        )


class ConfigurationError(AMTException):
    """Raised when there's a configuration error."""

    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}", status_code=500)


# FastAPI exception handlers
def create_http_exception(exception: AMTException) -> HTTPException:
    """Convert AMT exception to FastAPI HTTPException."""
    return HTTPException(
        status_code=exception.status_code,
        detail={
            "error": exception.__class__.__name__,
            "message": exception.message
        }
    )


# Common HTTP exceptions
class BadRequestError(HTTPException):
    """400 Bad Request."""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedError(HTTPException):
    """401 Unauthorized."""

    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenError(HTTPException):
    """403 Forbidden."""

    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundError(HTTPException):
    """404 Not Found."""

    def __init__(self, detail: str = "Not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    """409 Conflict."""

    def __init__(self, detail: str = "Conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnprocessableEntityError(HTTPException):
    """422 Unprocessable Entity."""

    def __init__(self, detail: str = "Unprocessable entity"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class TooManyRequestsError(HTTPException):
    """429 Too Many Requests."""

    def __init__(self, detail: str = "Too many requests"):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class InternalServerError(HTTPException):
    """500 Internal Server Error."""

    def __init__(self, detail: str = "Internal server error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class ServiceUnavailableError(HTTPException):
    """503 Service Unavailable."""

    def __init__(self, detail: str = "Service unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class ComparisonError(AMTException):
    """Raised when MIDI comparison fails."""
    pass


class ExportError(AMTException):
    """Raised when export operation fails."""
    pass


class BatchProcessingError(AMTException):
    """Raised when batch processing fails."""
    pass


class NoteAnalysisError(AMTException):
    """Raised when note analysis fails."""
    pass
