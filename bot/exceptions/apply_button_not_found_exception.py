from .job_apply_error_exception import JobApplyError


class ApplyButtonNotFound(JobApplyError):
    """Raised when the initial apply button cannot be found/clicked."""
