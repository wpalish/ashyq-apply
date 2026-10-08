"""Pipeline control signals that source adapters must never relabel as website failures."""


class RunCancelled(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    """The worker no longer owns the job; it must write nothing further."""


class UniversityReadStopped(RuntimeError):
    """Local read allowance refusal, not HTTP failure or evidence of absence."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"University read allowance refused: {reason}")
