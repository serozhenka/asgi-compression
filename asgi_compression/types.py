from typing import (
    Any,
    Awaitable,
    Callable,
    List,
    Mapping,
    MutableMapping,
    Optional,
)

from multidict import CIMultiDict

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class Headers(CIMultiDict[str]):
    def __init__(
        self,
        headers: Optional[Mapping[str, str]] = None,
        raw: Optional[list[tuple[bytes, bytes]]] = None,
        scope: Optional[Scope] = None,
    ) -> None:
        headers_list: List[tuple[str, str]] = []
        if headers is not None:
            assert raw is None, 'Cannot set both "headers" and "raw".'
            assert scope is None, 'Cannot set both "headers" and "scope".'
            headers_list = list(headers.items())
        elif raw is not None:
            assert scope is None, 'Cannot set both "raw" and "scope".'
            headers_list = [
                (key.decode("latin-1"), value.decode("latin-1"))
                for key, value in raw
            ]
        elif scope is not None:
            # scope["headers"] isn't necessarily a list
            # it might be a tuple or other iterable
            scope_headers = scope["headers"] = list(scope["headers"])
            headers_list = [
                (key.decode("latin-1"), value.decode("latin-1"))
                for key, value in scope_headers
            ]

        super().__init__(headers_list)

    def add_vary_header(self, vary: str) -> None:
        existing = self.get("vary")
        if existing is not None:
            # Check if the value is already in the Vary header to avoid duplication
            values = [x.strip() for x in existing.split(",")]
            if vary not in values:
                vary = f"{existing}, {vary}"

        self["vary"] = vary

    def encode(self) -> list[tuple[bytes, bytes]]:
        return [
            (key.encode("latin-1"), value.encode("latin-1"))
            for key, value in self.items()
        ]
