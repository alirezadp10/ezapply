from bot.exceptions import JobApplyError


class FormFillError(JobApplyError):
    """Raised when we detect an error pebble during form filling."""
