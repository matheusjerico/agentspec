"""Structural Markdown parsing for contract artifacts.

Public surface for the table layer (remediation spec §7). Contracts import
from here, never from the submodule, so the implementation can be reorganised
without touching consumers.
"""

from .tables import (
    ParsedRow,
    ParsedTable,
    TableError,
    TableErrorKind,
    parse_tables,
)

__all__ = [
    "ParsedRow",
    "ParsedTable",
    "TableError",
    "TableErrorKind",
    "parse_tables",
]
