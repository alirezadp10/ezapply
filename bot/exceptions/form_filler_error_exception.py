from .job_apply_error_exception import JobApplyError


class FormFillError(JobApplyError):
    """Raised when we detect an error pebble during form filling."""
