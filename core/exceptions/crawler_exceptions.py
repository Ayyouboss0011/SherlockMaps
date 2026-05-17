"""Custom exception hierarchy for the GoogleMapsCrawler."""


class CrawlerBaseException(Exception):
    """Base exception for all crawler-related errors."""

    def __init__(self, message: str = "An error occurred in the crawler.", cause: Exception | None = None):
        self.message = message
        self.cause = cause
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (Caused by: {self.cause})"
        return self.message


class BrowserInitializationError(CrawlerBaseException):
    """Raised when the browser cannot be initialized or launched."""

    def __init__(self, message: str = "Failed to initialize the browser.", cause: Exception | None = None):
        super().__init__(message=message, cause=cause)


class NavigationError(CrawlerBaseException):
    """Raised when navigation to a page fails."""

    def __init__(self, message: str = "Failed to navigate to the requested URL.", cause: Exception | None = None):
        super().__init__(message=message, cause=cause)


class ExtractionError(CrawlerBaseException):
    """Raised when data extraction from the page fails."""

    def __init__(self, message: str = "Failed to extract data from the page.", cause: Exception | None = None):
        super().__init__(message=message, cause=cause)