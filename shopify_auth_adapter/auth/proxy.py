"""
auth.proxy
==========
LiveToken — transparent str subclass proxy that delegates to TokenManager.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shopify_auth_adapter.core.protocols import TokenManagerProtocol


class LiveToken(str):
    """
    A str subclass proxy that delegates to a TokenManagerProtocol to dynamically
    return the current valid access token.

    Allows assigning SHOPIFY_ACCESS_TOKEN as a module-level constant while ensuring
    automatic token refresh whenever HTTP libraries call .encode("latin-1") on headers.
    """

    __slots__ = ("_manager",)

    def __new__(cls, manager: TokenManagerProtocol) -> LiveToken:
        instance = super().__new__(cls, "")
        object.__setattr__(instance, "_manager", manager)
        return instance

    def _current(self) -> str:
        """Return the current valid token string."""
        return self._manager.get_token()

    def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """Return the current token encoded into bytes (used by httpx & requests)."""
        return self._current().encode(encoding, errors)

    def __str__(self) -> str:
        return self._current()

    def __repr__(self) -> str:
        return "LiveToken(<masked>)"

    def __format__(self, format_spec: str) -> str:
        return format(self._current(), format_spec)

    def __len__(self) -> int:
        return len(self._current())

    def __bool__(self) -> bool:
        return bool(self._current())

    def __contains__(self, item: object) -> bool:  # type: ignore[override]
        return str(item) in self._current()

    def __iter__(self):  # type: ignore[override]
        return iter(self._current())

    def __getitem__(self, key):  # type: ignore[override]
        return self._current()[key]

    def __add__(self, other: str) -> str:  # type: ignore[override]
        return self._current() + str(other)

    def __radd__(self, other: str) -> str:  # type: ignore[override]
        return str(other) + self._current()

    def __mul__(self, n: int) -> str:  # type: ignore[override]
        return self._current() * n

    def __rmul__(self, n: int) -> str:  # type: ignore[override]
        return n * self._current()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._current() == other
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result  # type: ignore[return-value]
        return not result

    def __lt__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._current() < other
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._current() <= other
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._current() > other
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._current() >= other
        return NotImplemented

    def __hash__(self) -> int:  # type: ignore[override]
        return hash(self._current())

    def lower(self) -> str:
        return self._current().lower()

    def upper(self) -> str:
        return self._current().upper()

    def strip(self, chars=None) -> str:
        return self._current().strip(chars)

    def lstrip(self, chars=None) -> str:
        return self._current().lstrip(chars)

    def rstrip(self, chars=None) -> str:
        return self._current().rstrip(chars)

    def split(self, sep=None, maxsplit=-1):
        return self._current().split(sep, maxsplit)

    def rsplit(self, sep=None, maxsplit=-1):
        return self._current().rsplit(sep, maxsplit)

    def startswith(self, prefix, *args) -> bool:
        return self._current().startswith(prefix, *args)

    def endswith(self, suffix, *args) -> bool:
        return self._current().endswith(suffix, *args)

    def replace(self, old, new, count=-1) -> str:
        return self._current().replace(old, new, count)

    def find(self, sub, *args) -> int:
        return self._current().find(sub, *args)

    def join(self, iterable):
        return self._current().join(iterable)

    def zfill(self, width: int) -> str:
        return self._current().zfill(width)

    def center(self, width: int, fillchar: str = " ") -> str:
        return self._current().center(width, fillchar)

    def ljust(self, width: int, fillchar: str = " ") -> str:
        return self._current().ljust(width, fillchar)

    def rjust(self, width: int, fillchar: str = " ") -> str:
        return self._current().rjust(width, fillchar)
