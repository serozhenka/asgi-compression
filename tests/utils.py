import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from copy import copy
from importlib import reload
from types import ModuleType

import pytest
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


def unimport_module(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    to_reload: ModuleType,
) -> None:
    sys_modules = copy(sys.modules)
    sys_modules[module_name] = None  # type: ignore
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    monkeypatch.setattr("sys.modules", sys_modules)
    reload(to_reload)
