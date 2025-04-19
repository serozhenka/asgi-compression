import io
from enum import Enum

import brotli
from typing_extensions import assert_never

from .base import IdentityResponder
from .types import ASGIApp, Headers, Receive, Scope, Send


class BrotliMode(Enum):
    TEXT = "text"
    FONT = "font"
    GENERIC = "generic"

    def to_brotli_mode(self) -> int:
        if self == BrotliMode.TEXT:
            return brotli.MODE_TEXT
        elif self == BrotliMode.FONT:
            return brotli.MODE_FONT
        elif self == BrotliMode.GENERIC:
            return brotli.MODE_GENERIC
        else:
            assert_never(self)


class BrotliMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        quality: int = 4,
        mode: BrotliMode = BrotliMode.TEXT,
        lgwin: int = 22,
        lgblock: int = 0,
    ) -> None:
        self.app = app
        self.minimum_size = minimum_size
        self.quality = quality
        self.mode = mode
        self.lgwin = lgwin
        self.lgblock = lgblock

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        responder: ASGIApp
        if "br" in headers.get("Accept-Encoding", ""):
            responder = BrotliResponder(
                app=self.app,
                minimum_size=self.minimum_size,
                quality=self.quality,
                mode=self.mode,
                lgwin=self.lgwin,
                lgblock=self.lgblock,
            )
        else:
            responder = IdentityResponder(self.app, self.minimum_size)

        await responder(scope, receive, send)


class BrotliResponder(IdentityResponder):
    content_encoding = "br"

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int,
        quality: int = 4,
        mode: BrotliMode = BrotliMode.TEXT,
        lgwin: int = 22,
        lgblock: int = 0,
    ) -> None:
        super().__init__(app, minimum_size)

        self.brotli_buffer = io.BytesIO()
        self.compressor = brotli.Compressor(
            quality=quality,
            mode=mode.to_brotli_mode(),
            lgwin=lgwin,
            lgblock=lgblock,
        )

    def apply_compression(self, body: bytes, *, more_body: bool) -> bytes:
        compressed = self.compressor.process(body)
        self.brotli_buffer.write(compressed)

        if not more_body:
            final_data = self.compressor.finish()
            self.brotli_buffer.write(final_data)

        compressed_data = self.brotli_buffer.getvalue()

        self.brotli_buffer.seek(0)
        self.brotli_buffer.truncate()
        return compressed_data
