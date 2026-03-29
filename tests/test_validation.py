import pytest
from scripts.utils.validation import (
    SessionIdValidator,
    DurationValidator,
    TopicValidator,
    FilePathValidator,
    ValidationResult,
)


class TestSessionIdValidator:
    def test_valid_simple(self):
        result = SessionIdValidator.validate("20260328")
        assert result.is_valid is True
        assert result.value == "20260328"

    def test_valid_with_slug(self):
        result = SessionIdValidator.validate("20260328_micrypto")
        assert result.is_valid is True

    def test_valid_simple_identifier(self):
        result = SessionIdValidator.validate("mi-video-001")
        assert result.is_valid is True

    def test_valid_ok(self):
        result = SessionIdValidator.validate("ok")
        assert result.is_valid is True

    def test_empty(self):
        result = SessionIdValidator.validate("")
        assert result.is_valid is False
        assert "vacio" in result.error.lower()

    def test_too_short(self):
        result = SessionIdValidator.validate("a")
        assert result.is_valid is False
        assert "corto" in result.error.lower()

    def test_too_long(self):
        result = SessionIdValidator.validate("a" * 60)
        assert result.is_valid is False
        assert "largo" in result.error.lower()

    def test_invalid_chars(self):
        result = SessionIdValidator.validate("test@video")
        assert result.is_valid is False


class TestDurationValidator:
    def test_valid_integer(self):
        result = DurationValidator.validate("10")
        assert result.is_valid is True
        assert result.value == 10.0

    def test_valid_float(self):
        result = DurationValidator.validate("0.5")
        assert result.is_valid is True
        assert result.value == 0.5

    def test_valid_decimal_comma(self):
        result = DurationValidator.validate("0,5")
        assert result.is_valid is True

    def test_valid_short_duration(self):
        result = DurationValidator.validate("0.3")
        assert result.is_valid is True
        assert result.value == 0.3

    def test_too_short(self):
        result = DurationValidator.validate("0.05")
        assert result.is_valid is False
        assert "minimo" in result.error.lower()

    def test_too_long(self):
        result = DurationValidator.validate("200")
        assert result.is_valid is False
        assert "maximo" in result.error.lower()

    def test_not_a_number(self):
        result = DurationValidator.validate("abc")
        assert result.is_valid is False

    def test_empty(self):
        result = DurationValidator.validate("")
        assert result.is_valid is False

    def test_negative(self):
        result = DurationValidator.validate("-5")
        assert result.is_valid is False


class TestTopicValidator:
    def test_valid_simple(self):
        result = TopicValidator.validate("Tutorial de Python")
        assert result.is_valid is True

    def test_valid_long(self):
        result = TopicValidator.validate("A" * 100)
        assert result.is_valid is True

    def test_empty(self):
        result = TopicValidator.validate("")
        assert result.is_valid is False
        assert "vacio" in result.error.lower()

    def test_too_short(self):
        result = TopicValidator.validate("A")
        assert result.is_valid is False

    def test_too_long(self):
        result = TopicValidator.validate("A" * 300)
        assert result.is_valid is False

    def test_whitespace_only(self):
        result = TopicValidator.validate("   ")
        assert result.is_valid is False


class TestFilePathValidator:
    def test_valid_mp4(self):
        result = FilePathValidator.validate("video.mp4")
        assert result.is_valid is True

    def test_valid_mov(self):
        result = FilePathValidator.validate("video.MOV")
        assert result.is_valid is True

    def test_valid_with_path(self):
        result = FilePathValidator.validate("/home/user/videos/recording.mp4")
        assert result.is_valid is True

    def test_empty(self):
        result = FilePathValidator.validate("")
        assert result.is_valid is False

    def test_invalid_extension(self):
        result = FilePathValidator.validate("video.txt")
        assert result.is_valid is False
        assert "extension" in result.error.lower()

    def test_no_extension(self):
        result = FilePathValidator.validate("videofile")
        assert result.is_valid is False


class TestValidationResult:
    def test_successful_validation(self):
        result = ValidationResult(is_valid=True, value="test")
        assert result.is_valid is True
        assert result.value == "test"
        assert result.error is None

    def test_failed_validation(self):
        result = ValidationResult(is_valid=False, error="Some error")
        assert result.is_valid is False
        assert result.value is None
        assert result.error == "Some error"


class TestUnhappyPathIntegration:
    def test_duration_accepts_min_notation(self):
        result = DurationValidator.validate("5min")
        assert result.is_valid is True
        assert result.value == 5.0
