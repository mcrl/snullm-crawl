"""Defines frequently used exceptions"""


class TooManyRequestsError(Exception):
    """Raised when too many requests are made to the server"""

    def __init__(self, message):
        super().__init__(message)


class TooManyConsecutiveErrors(Exception):
    """Raised when too many consecutive errors occur"""

    def __init__(self, message):
        super().__init__(message)


class NoResponseError(Exception):
    """
    Raised when the server does not respond to a request.
    """

    def __init__(self, message):
        super().__init__(message)


class ResponseException(Exception):
    """
    Raised when the server responds with an error.
    """

    def __init__(self, message):
        super().__init__(message)
