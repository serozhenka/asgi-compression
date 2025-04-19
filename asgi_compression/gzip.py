import gzip
import io

from .base import IdentityResponder
from .types import ASGIApp, Headers, Receive, Scope, Send


class GZipMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compresslevel: int = 9,
    ) -> None:
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        responder: ASGIApp
        if "gzip" in headers.get("Accept-Encoding", ""):
            responder = GZipResponder(
                app=self.app,
                minimum_size=self.minimum_size,
                compresslevel=self.compresslevel,
            )
        else:
            responder = IdentityResponder(self.app, self.minimum_size)

        await responder(scope, receive, send)


class GZipResponder(IdentityResponder):
    content_encoding = "gzip"

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
        self, scope: Scope, receive: Receive, send: Send
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
