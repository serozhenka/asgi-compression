import gzip
import io
from dataclasses import dataclass

from .base import CompressionAlgorithm, CompressionResponder, ContentEncoding
from .types import ASGIApp, Receive, Scope, Send


class GzipResponder(CompressionResponder):
    """Responder that applies gzip compression."""

    content_encoding = ContentEncoding.GZIP

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int,
        compresslevel: int = 9,
    ) -> None:
        super().__init__(app, minimum_size)

        self.gzip_buffer = io.BytesIO()
        self.gzip_file = gzip.GzipFile(
            mode="wb",
            fileobj=self.gzip_buffer,
            compresslevel=compresslevel,
        )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        with self.gzip_buffer, self.gzip_file:
            await super().__call__(scope, receive, send)

    def apply_compression(self, body: bytes, *, more_body: bool) -> bytes:
        self.gzip_file.write(body)
        if not more_body:
            self.gzip_file.close()

        body = self.gzip_buffer.getvalue()
        self.gzip_buffer.seek(0)
        self.gzip_buffer.truncate()
        return body


@dataclass
class GzipAlgorithm(CompressionAlgorithm):
    """Gzip compression algorithm."""

    type: ContentEncoding = ContentEncoding.GZIP
    compresslevel: int = 9

    def create_responder(self, app: ASGIApp) -> GzipResponder:
        return GzipResponder(
            app=app,
            minimum_size=self.minimum_size,
            compresslevel=self.compresslevel,
        )
