from typing import List, Optional, Union

from .base import CompressionAlgorithm, CompressionResponder
from .identity import IdentityAlgorithm
from .types import ASGIApp, Headers, Receive, Scope, Send


class CompressionMiddleware:
    """
    Unified ASGI middleware for response compression.

    Supports multiple compression algorithms and automatically negotiates
    the best available algorithm based on the client's Accept-Encoding header.
    """

    def __init__(
        self,
        app: ASGIApp,
        algorithms: Optional[List[CompressionAlgorithm]] = None,
        minimum_size: int = 500,
    ) -> None:
        """
        Initialize the compression middleware.

        Args:
            app: The ASGI application.
            algorithms: List of compression algorithms to use, in order of preference.
                If not provided, no compression will be applied.
            minimum_size: The minimum response size to apply compression.
                This will be used as the default for algorithms that don't specify it.
        """

        self.app = app
        self.minimum_size = minimum_size

        self.algorithms = algorithms or []
        self._default_algorithm = IdentityAlgorithm(minimum_size=minimum_size)

        # Set minimum_size if not explicitly set in the algorithm
        for algorithm in self.algorithms:
            if algorithm.minimum_size == 500 and minimum_size != 500:
                algorithm.minimum_size = minimum_size

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """ASGI application interface."""
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        accept_encoding = headers.get("Accept-Encoding", "")

        # Find the first supported algorithm that matches the Accept-Encoding header
        responder: Union[CompressionResponder, None] = None
        for algorithm in self.algorithms:
            if str(algorithm.type.value) in accept_encoding:
                responder = algorithm.create_responder(self.app)
                break

        # If no matching algorithm, use identity (no compression)
        if responder is None:
            responder = self._default_algorithm.create_responder(self.app)

        await responder(scope, receive, send)
