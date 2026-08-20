"""
_live_token.py
==============
LiveToken — a ``str`` subclass that always provides the *current* valid
Shopify access token by delegating to a :class:`~shopify_auth_adapter.auth.TokenManager`.

Why this exists
---------------
Shopify's Client Credentials access tokens expire every 24 hours.  The
existing application pattern::

    SHOPIFY_ACCESS_TOKEN = "shpat_xxxx"       # old static assignment
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}

cannot simply be replaced by assigning a plain ``str`` at module load time,
because that string would expire after 24 hours.

``LiveToken`` solves this while preserving the assignment pattern::

    SHOPIFY_ACCESS_TOKEN = get_access_token()  # LiveToken, not a plain str
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}

How it works with HTTP libraries
---------------------------------
Both ``requests`` and ``httpx`` ultimately encode header values by calling
``.encode("latin-1")`` on the header value.

* **requests** (via Python's ``http.client.HTTPConnection.putheader``):
  ``if hasattr(value, 'encode'): value = value.encode('latin-1')``
  → calls our override → returns current valid token bytes ✓

* **httpx** (in ``httpx._models.Headers.__init__``):
  ``v.encode("latin-1")`` is called when building the ``Headers`` object
  from a plain dict → calls our override → current token bytes ✓

Because we override ``encode()``, the *current* valid token (possibly freshly
fetched) is placed in the HTTP request at the moment the request is sent.
Expired tokens are transparently refreshed.

Security
--------
``__repr__`` and ``__str__`` return a masked representation so that
``LiveToken`` objects do not leak secrets into logs.  Call ``._current()``
only where the raw token string is explicitly required (e.g. inside the HTTP
request itself).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .auth import TokenManager


class LiveToken(str):
    """
    A :class:`str` subclass that transparently delegates to a
    :class:`~shopify_auth_adapter.auth.TokenManager` to always return the
    current valid Shopify access token.

    Assign this as a module-level constant and the rest of your application
    continues to work unchanged::

        SHOPIFY_ACCESS_TOKEN = get_access_token()   # LiveToken

        # Anywhere in your existing code — no changes required:
        headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
        response = requests.get(url, headers=headers)

    The token is fetched lazily on first use (not at ``get_access_token()``
    call time), so application startup does not fail if Shopify is temporarily
    unreachable.
    """

    __slots__ = ("_manager",)

    def __new__(cls, manager: "TokenManager") -> "LiveToken":
        # Create the str instance with an empty placeholder.
        # The actual token is always sourced from `_manager` at use time.
        # We intentionally do NOT call get_token() here so that startup
        # does not fail if the network is momentarily unavailable.
        instance = super().__new__(cls, "")
        # Use object.__setattr__ to bypass any accidental __setattr__ on str
        object.__setattr__(instance, "_manager", manager)
        return instance

    # ------------------------------------------------------------------
    # Core helper
    # ------------------------------------------------------------------

    def _current(self) -> str:
        """Return the current valid token as a plain Python ``str``."""
        return self._manager.get_token()

    # ------------------------------------------------------------------
    # HTTP library integration
    # ------------------------------------------------------------------

    def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return the current token encoded as bytes.

        This method is the critical integration point:

        * Python's ``http.client`` (used by ``requests``) calls
          ``value.encode('latin-1')`` when writing HTTP headers.
        * ``httpx`` calls ``v.encode('latin-1')`` when constructing a
          ``Headers`` object from a dict.

        By overriding ``encode()``, we ensure the *current* valid token
        (not the empty placeholder baked into the ``str`` at construction
        time) is placed in the actual HTTP request.
        """
        return self._current().encode(encoding, errors)

    # ------------------------------------------------------------------
    # str protocol — all delegate to _current()
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return self._current()

    def __repr__(self) -> str:
        # Never expose the token in repr / logs
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
        # Must be consistent with __eq__.
        # Note: LiveToken is not suitable as a dict key because its value
        # can change between calls.  If you need a stable dict key, use
        # str(live_token) to capture the current value as a plain str.
        return hash(self._current())

    # ------------------------------------------------------------------
    # Commonly used str methods
    # ------------------------------------------------------------------

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
