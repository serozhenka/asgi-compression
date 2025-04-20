import io
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .base import CompressionAlgorithm, CompressionResponder, ContentEncoding
from .types import ASGIApp

if TYPE_CHECKING:
    import brotli


def import_brotli() -> None:
    global brotli
    try:
        import brotli
    except ImportError as e:
        raise ImportError(
            "brotli is not installed, run `pip install brotli`]"
        ) from e


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
            assert False, f"Expected code to be unreachable, but got: {self}"


class BrotliResponder(CompressionResponder):
    """Responder that applies brotli compression."""

    content_encoding = ContentEncoding.BROTLI

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

        import_brotli()

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


@dataclass
class BrotliAlgorithm(CompressionAlgorithm):
    """Brotli compression algorithm."""

    type: ContentEncoding = ContentEncoding.BROTLI
    quality: int = 4
    mode: BrotliMode = BrotliMode.TEXT
    lgwin: int = 22
    lgblock: int = 0

    def create_responder(self, app: ASGIApp) -> "BrotliResponder":
        return BrotliResponder(
            app=app,
            minimum_size=self.minimum_size,
            quality=self.quality,
            mode=self.mode,
            lgwin=self.lgwin,
            lgblock=self.lgblock,
        )

    def check_available(self) -> None:
        import_brotli()
