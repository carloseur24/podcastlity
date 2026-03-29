from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class ValidationResult:
    is_valid: bool
    value: Optional[str | int | float] = None
    error: Optional[str] = None


class SessionIdValidator:
    DATE_PATTERN = re.compile(r"^\d{8}(_\w+)?$")
    SIMPLE_PATTERN = re.compile(r"^[\w-]+$")
    
    @classmethod
    def validate(cls, value: str) -> ValidationResult:
        if not value:
            return ValidationResult(False, error="ID de sesion no puede estar vacio")
        
        value = value.strip()
        
        if cls.DATE_PATTERN.match(value):
            return ValidationResult(True, value=value)
        
        if len(value) < 2:
            return ValidationResult(False, error="ID muy corto (min 2 caracteres)")
        
        if len(value) > 50:
            return ValidationResult(False, error="ID muy largo (max 50 caracteres)")
        
        if cls.SIMPLE_PATTERN.match(value):
            return ValidationResult(True, value=value)
        
        return ValidationResult(
            False,
            error="Solo letras, numeros, guiones y underscores (ej: mi-video-001)"
        )


class DurationValidator:
    MIN_MINUTES = 0.1
    MAX_MINUTES = 180
    
    @classmethod
    def _parse(cls, value: str) -> float | None:
        value = value.strip().lower().replace(",", ".")
        
        if value.endswith("s") or value.endswith("sec") or value.endswith("seconds"):
            try:
                return float(value[:-3].strip()) / 60
            except ValueError:
                return None
        
        if value.endswith("m") or value.endswith("min") or value.endswith("minutes"):
            try:
                return float(value[:-3].strip())
            except ValueError:
                return None
        
        try:
            return float(value)
        except ValueError:
            return None
    
    @classmethod
    def validate(cls, value: str) -> ValidationResult:
        if not value:
            return ValidationResult(False, error="Duracion no puede estar vacia")
        
        duration = cls._parse(value)
        
        if duration is None:
            return ValidationResult(False, error="Debe ser un numero (ej: 0.5, 30s, 2min)")
        
        if duration < cls.MIN_MINUTES:
            return ValidationResult(
                False,
                error=f"Minimo {cls.MIN_MINUTES} minuto ({int(cls.MIN_MINUTES * 60)} segundos)"
            )
        
        if duration > cls.MAX_MINUTES:
            return ValidationResult(
                False,
                error=f"Maximo {cls.MAX_MINUTES} minutos"
            )
        
        return ValidationResult(True, value=duration)


class TopicValidator:
    MIN_LENGTH = 2
    MAX_LENGTH = 200
    
    @classmethod
    def validate(cls, value: str) -> ValidationResult:
        if not value:
            return ValidationResult(False, error="Tema no puede estar vacio")
        
        value = value.strip()
        
        if len(value) < cls.MIN_LENGTH:
            return ValidationResult(
                False,
                error=f"Tema muy corto (min {cls.MIN_LENGTH} caracteres)"
            )
        
        if len(value) > cls.MAX_LENGTH:
            return ValidationResult(
                False,
                error=f"Tema muy largo (max {cls.MAX_LENGTH} caracteres)"
            )
        
        return ValidationResult(True, value=value)


class FilePathValidator:
    VALID_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".webm"]
    
    @classmethod
    def validate(cls, value: str) -> ValidationResult:
        if not value:
            return ValidationResult(False, error="Ruta no puede estar vacia")
        
        path = value.strip()
        
        if not any(path.lower().endswith(ext) for ext in cls.VALID_EXTENSIONS):
            return ValidationResult(
                False,
                error=f"Extension no valida. Usa: {', '.join(cls.VALID_EXTENSIONS)}"
            )
        
        return ValidationResult(True, value=path)


def sanitize_duration_input(value: str) -> float:
    value = value.strip().replace(",", ".")
    if value.endswith("s") or value.endswith("sec"):
        value = value[:-2]
    if value.endswith("m") or value.endswith("min"):
        value = value[:-3]
    return float(value)
