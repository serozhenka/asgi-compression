import sys
import types
from typing import AsyncGenerator, get_args

import django
import pytest_asyncio
from django.conf import settings
from django.core.asgi import get_asgi_application
from django.http import HttpResponse, StreamingHttpResponse
from django.urls import path
from django_eventstream.utils import sse_encode_event
from httpx import AsyncClient
from litestar import Litestar, get
from litestar.response import ServerSentEvent, ServerSentEventMessage
from pytest import FixtureRequest
from sse_starlette import EventSourceResponse
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import (
    PlainTextResponse,
    StreamingResponse,
)
from starlette.routing import Route
from typing_extensions import assert_never

from asgi_compression.brotli import BrotliAlgorithm
from asgi_compression.gzip import GzipAlgorithm
from asgi_compression.middleware import CompressionMiddleware
from asgi_compression.types import ASGIApp
from asgi_compression.zstd import ZstdAlgorithm

from .types import Encoding, Framework
from .utils import get_test_client


def get_django_app() -> ASGIApp:
    if not settings.configured:
        settings.configure(
            ROOT_URLCONF="test_urls",
            INSTALED_APPS=[
                "django.contrib.contenttypes",
                "django_eventstream",
            ],
            EVENTSTREAM_STORAGE_CLASS="django_eventstream.storage.DjangoModelStorage",
        )
        django.setup()

    urls_module = types.ModuleType("test_urls")
    sys.modules["test_urls"] = urls_module

    def homepage(_):
        return HttpResponse(b"x" * 4000, content_type="text/plain")

    def small_response(_):
        return HttpResponse(b"Hello world!", content_type="text/plain")

    def streaming_response(_: Request) -> StreamingHttpResponse:
        async def generator(
            bytes: bytes,
            count: int,
        ) -> AsyncGenerator[bytes, None]:
            for _ in range(count):
                yield bytes

        streaming = generator(bytes=b"x" * 400, count=10)
        return StreamingHttpResponse(streaming)

    def streaming_response_with_content_encoding(
        _: Request,
    ) -> StreamingHttpResponse:
        async def generator(
            bytes: bytes,
            count: int,
        ) -> AsyncGenerator[bytes, None]:
            for _ in range(count):
                yield bytes

        streaming = generator(bytes=b"x" * 400, count=10)
        return StreamingHttpResponse(
            streaming, headers={"Content-Encoding": "text"}
        )

    def server_sent_events(_: Request) -> StreamingHttpResponse:
        async def sse_stream() -> AsyncGenerator[bytes, None]:
            for i in range(10):
                event = {"id": str(i), "event": "message", "data": "x" * 400}
                encoded_event = sse_encode_event(
                    data=event["data"],
                    event_id=event["id"],
                    event_type=event["event"],
                )
                yield encoded_event.encode("utf-8")

        return StreamingHttpResponse(
            sse_stream(),
            content_type="text/event-stream",
        )

    setattr(
        urls_module,
        "urlpatterns",
        [
            path("", homepage),
            path("small_response", small_response),
            path("streaming_response", streaming_response),
            path(
                "streaming_response_with_content_encoding",
                streaming_response_with_content_encoding,
            ),
            path("server_sent_events", server_sent_events),
        ],
    )

    return get_asgi_application()


def get_starlette_app() -> ASGIApp:
    def homepage(_: Request) -> PlainTextResponse:
        return PlainTextResponse("x" * 4000)

    def small_response(_: Request) -> PlainTextResponse:
        return PlainTextResponse("Hello world!")

    def streaming_response(_: Request) -> StreamingResponse:
        async def generator(
            bytes: bytes,
            count: int,
        ) -> AsyncGenerator[bytes, None]:
            for _ in range(count):
                yield bytes

        streaming = generator(bytes=b"x" * 400, count=10)
        return StreamingResponse(streaming, status_code=200)

    def streaming_response_with_content_encoding(
        _: Request,
    ) -> StreamingResponse:
        async def generator(
            bytes: bytes,
            count: int,
        ) -> AsyncGenerator[bytes, None]:
            for _ in range(count):
                yield bytes

        streaming = generator(bytes=b"x" * 400, count=10)
        return StreamingResponse(
            streaming,
            status_code=200,
            headers={"Content-Encoding": "text"},
        )

    def server_sent_events(_: Request) -> EventSourceResponse:
        async def generator() -> AsyncGenerator[dict, None]:
            for i in range(10):
                yield {"event": "message", "id": str(i), "data": "x" * 400}

        return EventSourceResponse(generator())

    return Starlette(
        routes=[
            Route("/", endpoint=homepage),
            Route("/small_response", endpoint=small_response),
            Route("/streaming_response", endpoint=streaming_response),
            Route(
                "/streaming_response_with_content_encoding",
                endpoint=streaming_response_with_content_encoding,
            ),
            Route(
                "/server_sent_events",
                endpoint=server_sent_events,
            ),
        ]
    )


def get_litestar_app() -> ASGIApp:
    @get("/")
    async def homepage(request: Request) -> str:
        return "x" * 4000

    @get("/small_response")
    async def small_response(request: Request) -> str:
        return "Hello world!"

    @get("/streaming_response")
    async def streaming_response(request: Request) -> StreamingResponse:
        async def generator(
            bytes: bytes,
            count: int,
        ) -> AsyncGenerator[bytes, None]:
            for _ in range(count):
                yield bytes

        streaming = generator(bytes=b"x" * 400, count=10)
        return StreamingResponse(streaming, status_code=200)

    @get("/streaming_response_with_content_encoding")
    async def streaming_response_with_content_encoding(
        request: Request,
    ) -> StreamingResponse:
        async def generator(
            bytes: bytes,
            count: int,
        ) -> AsyncGenerator[bytes, None]:
            for _ in range(count):
                yield bytes

        streaming = generator(bytes=b"x" * 400, count=10)
        return StreamingResponse(
            streaming,
            status_code=200,
            headers={"Content-Encoding": "text"},
        )

    @get("/server_sent_events")
    async def server_sent_events(request: Request) -> ServerSentEvent:
        async def event_generator() -> AsyncGenerator[
            ServerSentEventMessage, None
        ]:
            for i in range(10):
                yield ServerSentEventMessage(
                    id=str(i),
                    event="message",
                    data="x" * 400,
                )

        return ServerSentEvent(event_generator())

    return Litestar(
        route_handlers=[
            homepage,
            small_response,
            streaming_response,
            streaming_response_with_content_encoding,
            server_sent_events,
        ],
        logging_config=None,
    )  # type: ignore


@pytest_asyncio.fixture(
    scope="session",
    params=[
        f"{framework}-{encoding}"
        for framework in get_args(Framework)
        for encoding in get_args(Encoding)
    ],
)
async def client(request: FixtureRequest) -> AsyncGenerator[AsyncClient, None]:
    framework_name, encoding_name = request.param.split("-")

    if framework_name == "django":
        app = get_django_app()
    elif framework_name == "starlette":
        app = get_starlette_app()
    elif framework_name == "litestar":
        app = get_litestar_app()
    else:
        assert_never(framework_name)

    if encoding_name == "gzip":
        algorithm = GzipAlgorithm()
    elif encoding_name == "br":
        algorithm = BrotliAlgorithm()
    elif encoding_name == "zstd":
        algorithm = ZstdAlgorithm()
    else:
        assert_never(encoding_name)

    middleware = CompressionMiddleware(app=app, algorithms=[algorithm])

    async with get_test_client(middleware) as client:
        yield client
