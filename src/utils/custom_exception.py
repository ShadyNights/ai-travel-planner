"""Custom exception classes with detailed error tracking."""

import sys
from typing import Optional


class CustomException(Exception):
    """
    Enhanced exception with detailed error context including file and line number.
    
    Attributes:
        error_message: Formatted error message with context
    """

    def __init__(self, message: str, error_detail: Optional[Exception] = None):
        """
        Initialize custom exception with context.

        Args:
            message: Human-readable error description
            error_detail: Original exception (if any)
        """
        self.error_message = self._get_detailed_error_message(message, error_detail)
        super().__init__(self.error_message)

    @staticmethod
    def _get_detailed_error_message(
        message: str,
        error_detail: Optional[Exception]
    ) -> str:
        """
        Build detailed error message with file/line context.

        Args:
            message: Base error message
            error_detail: Original exception

        Returns:
            str: Formatted error message
        """
        _, _, exc_tb = sys.exc_info()
        
        if exc_tb:
            file_name = exc_tb.tb_frame.f_code.co_filename
            line_number = exc_tb.tb_lineno
        else:
            file_name = "Unknown"
            line_number = "Unknown"

        error_str = str(error_detail) if error_detail else "No additional details"
        
        return (
            f"{message} | "
            f"Error: {error_str} | "
            f"File: {file_name} | "
            f"Line: {line_number}"
        )

    def __str__(self) -> str:
        """Return formatted error message."""
        return self.error_message
