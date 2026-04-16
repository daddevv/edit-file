"""
edit-file – Reliable, fuzzy-matching code editor for AI agents.

Quick start::

    from edit_file import EditFile

    editor = EditFile()
    content = editor.read_file("mymodule.py")
    result = editor.edit_file(
        path="mymodule.py",
        old_text="def foo():\\n    pass",
        new_text="def foo():\\n    return 42",
    )
    assert result.success
"""
from .core import EditFile
from .exceptions import (AmbiguousMatchError, EditFileError, NoMatchFoundError,
                         StaleReadError)
from .models import EditResult, MatchResult, MatchStrategy
from .reconciler import Reconciler

__all__ = [
    "EditFile",
    "Reconciler",
    "EditResult",
    "MatchResult",
    "MatchStrategy",
    "EditFileError",
    "AmbiguousMatchError",
    "NoMatchFoundError",
    "StaleReadError",
]
__version__ = "0.1.0"
