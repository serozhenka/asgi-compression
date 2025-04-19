from __future__ import annotations

from httpx import AsyncClient


async def test_gzip_responses(client: AsyncClient) -> None:
    response = await client.get("/", headers={"accept-encoding": "gzip"})
    assert response.status_code == 200
    assert response.text == "x" * 4000
    assert response.headers["Content-Encoding"] == "gzip"
    assert response.headers["Vary"] == "Accept-Encoding"
    assert int(response.headers["Content-Length"]) < 4000


async def test_gzip_not_in_accept_encoding(client: AsyncClient) -> None:
    response = await client.get("/", headers={"accept-encoding": "identity"})
    assert response.status_code == 200
    assert response.text == "x" * 4000
    assert "Content-Encoding" not in response.headers
    assert response.headers["Vary"] == "Accept-Encoding"
    content_length = response.headers.get("Content-Length")
    if content_length:
        # Django doesn't set 'Content-Length' header automatically
        assert int(content_length) == 4000


async def test_gzip_ignored_for_small_responses(client: AsyncClient) -> None:
    response = await client.get(
        "/small_response",
        headers={"accept-encoding": "gzip"},
    )
    expected_response = "Hello world!"
    assert response.status_code == 200
    assert response.text == expected_response
    assert "Content-Encoding" not in response.headers
    assert "Vary" not in response.headers
    content_length = response.headers.get("Content-Length")
    if content_length:
        # Django doesn't set 'Content-Length' header automatically
        assert int(content_length) == len(expected_response)


async def test_gzip_streaming_response(client: AsyncClient) -> None:
    response = await client.get(
        "/streaming_response",
        headers={"accept-encoding": "gzip"},
    )
    assert response.status_code == 200
    assert response.text == "x" * 4000
    assert response.headers["Content-Encoding"] == "gzip"
    assert response.headers["Vary"] == "Accept-Encoding"
    assert "Content-Length" not in response.headers


async def test_gzip_streaming_response_identity(client: AsyncClient) -> None:
    response = await client.get(
        "/streaming_response",
        headers={"accept-encoding": "identity"},
    )
    assert response.status_code == 200
    assert response.text == "x" * 4000
    assert "Content-Encoding" not in response.headers
    assert response.headers["Vary"] == "Accept-Encoding"
    assert "Content-Length" not in response.headers


async def test_gzip_ignored_for_responses_with_encoding_set(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/streaming_response_with_content_encoding",
        headers={"accept-encoding": "gzip, text"},
    )
    assert response.status_code == 200
    assert response.text == "x" * 4000
    assert response.headers["Content-Encoding"] == "text"
    assert "Vary" not in response.headers
    assert "Content-Length" not in response.headers


async def test_gzip_ignored_on_server_sent_events(client: AsyncClient) -> None:
    async with client.stream(
        "GET",
        "/server_sent_events",
        headers={"accept-encoding": "gzip"},
    ) as response:
        assert response.status_code == 200
        assert "Content-Encoding" not in response.headers
        assert "Content-Length" not in response.headers
        assert response.headers.get("Content-Type", "").startswith(
            "text/event-stream"
        )

        current_message = {}
        completed_messages = []

        async for line in response.aiter_lines():
            line = line.rstrip("\r")

            if not line.strip():
                if current_message:
                    completed_messages.append(current_message)

                current_message = {}
                continue

            if ":" in line:
                field, value = line.split(":", 1)
                value = value[1:] if value.startswith(" ") else value
                current_message[field] = value

        for i, message in enumerate(completed_messages):
            assert message == {
                "id": str(i),
                "event": "message",
                "data": "x" * 400,
            }
