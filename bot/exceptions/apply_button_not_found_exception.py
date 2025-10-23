from bot.exceptions import JobApplyError


class ApplyButtonNotFound(JobApplyError):
    """Raised when the initial apply button cannot be found/clicked."""
