"""Custom exceptions for data loading."""


class DataLoadError(Exception):
    """Base exception for data loading errors."""
    pass


class DataNotFoundError(DataLoadError):
    """Raised when no data is found for the given parameters."""

    def __init__(self, symbol: str, freq: str, start: str = None, end: str = None):
        self.symbol = symbol
        self.freq = freq
        self.start = start
        self.end = end

        msg = f"No data found for {symbol} ({freq})"
        if start or end:
            msg += f" from {start or '*'} to {end or '*'}"
        super().__init__(msg)


class DataSourceNotAvailableError(DataLoadError):
    """Raised when no suitable datasource is available."""

    def __init__(self, message: str = "No datasource registered"):
        super().__init__(message)


class InvalidDateRangeError(DataLoadError):
    """Raised when date range is invalid."""

    def __init__(self, start: str, end: str):
        super().__init__(
            f"Invalid date range: start={start}, end={end}. "
            "Start must be before end."
        )
        self.start = start
        self.end = end


class DataValidationError(DataLoadError):
    """Raised when data validation fails."""

    def __init__(self, message: str):
        super().__init__(f"Data validation failed: {message}")