"""Type stubs for scripts.core.exceptions module."""

class PipelineError(Exception):
    """Base exception for pipeline errors."""

    pass

class StageError(PipelineError):
    """Exception raised when a pipeline stage fails."""

    stage: str

    def __init__(self, stage: str, message: str) -> None: ...
    def __str__(self) -> str: ...

class SessionNotFoundError(PipelineError):
    """Exception raised when a session is not found."""

    def __init__(self, session_id: str) -> None: ...
    def __str__(self) -> str: ...

class StageNotFoundError(PipelineError):
    """Exception raised when a stage is not found."""

    stage: str

    def __init__(self, stage: str) -> None: ...
    def __str__(self) -> str: ...
