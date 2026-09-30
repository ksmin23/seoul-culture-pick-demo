class AppError(Exception):
    """사용자에게 표시해도 되는 메시지만 담는다. 원본 HTTP 예외는 노출하지 않는다."""

    def __init__(self, code: str, message: str, *, allow_snapshot: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.allow_snapshot = allow_snapshot
