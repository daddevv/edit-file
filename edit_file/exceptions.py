"""
Exceptions raised by the edit-file reconciler.
"""


class EditFileError(Exception):
    """Base exception for all edit-file errors."""


class AmbiguousMatchError(EditFileError):
    """
    Raised when old_text matches more than one location in the file.
    The agent must provide a larger context block to anchor the edit uniquely.
    """

    def __init__(self, count: int) -> None:
        self.count = count
        super().__init__(
            f"old_text matched {count} locations in the file. "
            "Provide a larger context block so the target is unambiguous."
        )


class StaleReadError(EditFileError):
    """
    Raised when the file has been modified since the agent's last read_file call.
    The agent must re-read the file before editing.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(
            f"'{path}' was modified after it was last read. "
            "Re-read the file before applying edits."
        )


class NoMatchFoundError(EditFileError):
    """
    Raised when all 9 reconciler passes fail to locate old_text in the file.
    """

    def __init__(self, passes_tried: int = 9) -> None:
        self.passes_tried = passes_tried
        super().__init__(
            f"old_text could not be located after {passes_tried} reconciliation passes. "
            "Ensure old_text represents a real block that exists in the current file."
        )


class UnsupportedLanguageError(EditFileError):
    """Raised by Pass 8 when AST parsing is not available for the file's language."""

    def __init__(self, language: str) -> None:
        self.language = language
        super().__init__(
            f"AST parsing is not supported for language '{language}'. "
            "Pass 8 cannot be used for this file."
        )