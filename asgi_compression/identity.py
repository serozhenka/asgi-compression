from dataclasses import dataclass

from .base import CompressionAlgorithm, CompressionResponder, ContentEncoding
from .types import ASGIApp


class IdentityResponder(CompressionResponder):
    """Responder that doesn't apply any compression."""

    content_encoding = ContentEncoding.IDENTITY

    def apply_compression(self, body: bytes, *, more_body: bool) -> bytes:
        return body


@dataclass
class IdentityAlgorithm(CompressionAlgorithm):
    """No compression, identity algorithm."""

    type: ContentEncoding = ContentEncoding.IDENTITY

    def create_responder(self, app: ASGIApp) -> IdentityResponder:
        return IdentityResponder(app=app, minimum_size=self.minimum_size)
