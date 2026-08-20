"""
auth.proxy
==========
LiveToken — transparent str subclass proxy that delegates to TokenManagerProtocol.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, SupportsIndex

if TYPE_CHECKING:
    from shopify_auth_adapter.core.protocols import TokenManagerProtocol


class LiveToken(str):
    """
    A str subclass proxy that delegates to a TokenManagerProtocol to dynamically
    return the current valid access token.

    Allows assigning SHOPIFY_ACCESS_TOKEN as a module-level constant while ensuring
    automatic token refresh whenever HTTP libraries call .encode("latin-1") on headers.
    """

    _manager: TokenManagerProtocol

    def __new__(cls, manager: TokenManagerProtocol) -> LiveToken:
        instance = super().__new__(cls, "")
        object.__setattr__(instance, "_manager", manager)
        return instance

    def _current(self) -> str:
        """Return the current valid token string."""
        return str(self._manager.get_token())

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

    def __contains__(self, item: object) -> bool:
        return str(item) in self._current()

    def __iter__(self) -> Iterator[str]:
        return iter(self._current())

    def __getitem__(self, key: Any) -> str:
        return self._current()[key]

    def __add__(self, other: str) -> str:
        return self._current() + str(other)

    def __radd__(self, other: str) -> str:
        return str(other) + self._current()

    def __mul__(self, n: SupportsIndex) -> str:
        return self._current() * n

    def __rmul__(self, n: SupportsIndex) -> str:
        return n * self._current()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return bool(self._current() == str(other))
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._current() < str(other)
        return False

    def __le__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._current() <= str(other)
        return False

    def __gt__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._current() > str(other)
        return False

    def __ge__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._current() >= str(other)
        return False

    def __hash__(self) -> int:
        return hash(self._current())

    def lower(self) -> str:
        return self._current().lower()

    def upper(self) -> str:
        return self._current().upper()

    def strip(self, chars: str | None = None) -> str:
        return self._current().strip(chars)

    def lstrip(self, chars: str | None = None) -> str:
        return self._current().lstrip(chars)

    def rstrip(self, chars: str | None = None) -> str:
        return self._current().rstrip(chars)

    def split(self, sep: str | None = None, maxsplit: SupportsIndex = -1) -> list[str]:
        return self._current().split(sep, maxsplit)

    def rsplit(self, sep: str | None = None, maxsplit: SupportsIndex = -1) -> list[str]:
        return self._current().rsplit(sep, maxsplit)

    def startswith(
        self,
        prefix: str | tuple[str, ...],
        start: SupportsIndex | None = None,
        end: SupportsIndex | None = None,
    ) -> bool:
        return self._current().startswith(prefix, start, end)

    def endswith(
        self,
        suffix: str | tuple[str, ...],
        start: SupportsIndex | None = None,
        end: SupportsIndex | None = None,
    ) -> bool:
        return self._current().endswith(suffix, start, end)

    def replace(self, old: str, new: str, count: SupportsIndex = -1) -> str:
        return self._current().replace(old, new, count)

    def find(
        self,
        sub: str,
        start: SupportsIndex | None = None,
        end: SupportsIndex | None = None,
    ) -> int:
        return self._current().find(sub, start, end)

    def join(self, iterable: Any) -> str:
        return self._current().join(iterable)

    def zfill(self, width: SupportsIndex) -> str:
        return self._current().zfill(width)

    def center(self, width: SupportsIndex, fillchar: str = " ") -> str:
        return self._current().center(width, fillchar)

    def ljust(self, width: SupportsIndex, fillchar: str = " ") -> str:
        return self._current().ljust(width, fillchar)

    def rjust(self, width: SupportsIndex, fillchar: str = " ") -> str:
        return self._current().rjust(width, fillchar)
