"""Public error types with stable machine-readable codes."""


class CapabilityProofError(Exception):
    """Base class for an expected, non-secret operational error."""

    code = "capabilityproof_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class InputRejected(CapabilityProofError):
    code = "input_rejected"


class LimitExceeded(InputRejected):
    code = "limit_exceeded"


class PathRejected(InputRejected):
    code = "path_rejected"
