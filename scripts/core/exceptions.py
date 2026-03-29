"""Pipeline exceptions."""


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class StageError(PipelineError):
    """Exception raised when a pipeline stage fails."""
    def __init__(self, stage: str, message: str):
        self.stage = stage
        super().__init__(f"Stage '{stage}' failed: {message}")


class SessionNotFoundError(PipelineError):
    """Exception raised when a session is not found."""
    pass


class StageNotFoundError(PipelineError):
    """Exception raised when a stage is not found."""
    pass
