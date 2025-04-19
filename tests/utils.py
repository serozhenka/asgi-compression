from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient

from asgi_compression.types import ASGIApp


@asynccontextmanager
async def get_test_client(
    middleware: ASGIApp,
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=middleware),
        base_url="http://test",
    ) as client:
        yield client
