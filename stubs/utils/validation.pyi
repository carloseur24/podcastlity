"""Type stubs for scripts.utils.validation module."""

from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ValidationResult:
    is_valid: bool
    value: Optional[str] = None
    errors: list[str] = None

    def __init__(
        self,
        is_valid: bool,
        value: Optional[str] = None,
        errors: Optional[list[str]] = None,
    ) -> None: ...

class SessionIdValidator:
    def validate(self, value: str) -> ValidationResult: ...

class DurationValidator:
    def validate(self, value: str) -> ValidationResult: ...

class TopicValidator:
    def validate(self, value: str) -> ValidationResult: ...

class FilePathValidator:
    def __init__(self, allowed_extensions: Optional[list[str]] = None) -> None: ...
    def validate(self, value: str) -> ValidationResult: ...
