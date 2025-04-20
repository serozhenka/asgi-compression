import io
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import CompressionAlgorithm, CompressionResponder, ContentEncoding
from .types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    import zstandard


def import_zstandard() -> None:
    global zstandard
    try:
        import zstandard
    except ImportError as e:
        raise ImportError(
            'zstandard is not installed, run `pip install "asgi-compression[zstd]"`'
        ) from e


class ZstdResponder(CompressionResponder):
    """Responder that applies Zstandard compression."""

    content_encoding = ContentEncoding.ZSTD

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int,
        level: int = 3,
        threads: int = 0,
        write_checksum: bool = False,
        write_content_size: bool = True,
    ) -> None:
        super().__init__(app, minimum_size)

        import_zstandard()

        self.zstd_buffer = io.BytesIO()
        self.compressor = zstandard.ZstdCompressor(
            level=level,
            threads=threads,
            write_checksum=write_checksum,
            write_content_size=write_content_size,
        )
        self.compression_stream = self.compressor.stream_writer(
            self.zstd_buffer
        )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        with self.zstd_buffer, self.compression_stream:
            await super().__call__(scope, receive, send)

    def apply_compression(self, body: bytes, *, more_body: bool) -> bytes:
        self.compression_stream.write(body)
        if not more_body:
            self.compression_stream.flush(zstandard.FLUSH_FRAME)

        body = self.zstd_buffer.getvalue()
        self.zstd_buffer.seek(0)
        self.zstd_buffer.truncate()
        return body


@dataclass
class ZstdAlgorithm(CompressionAlgorithm):
    """Zstandard compression algorithm."""

    type: ContentEncoding = ContentEncoding.ZSTD
    level: int = 3
    threads: int = 0
    write_checksum: bool = False
    write_content_size: bool = True

    def create_responder(self, app: ASGIApp) -> ZstdResponder:
        return ZstdResponder(
            app=app,
            minimum_size=self.minimum_size,
            level=self.level,
            threads=self.threads,
            write_checksum=self.write_checksum,
            write_content_size=self.write_content_size,
        )

    def check_available(self) -> None:
        import_zstandard()
