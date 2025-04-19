import typing

from .types import ASGIApp, Headers, Message, Receive, Scope, Send

DEFAULT_EXCLUDED_CONTENT_TYPES = ("text/event-stream",)


async def unattached_send(message: Message) -> typing.NoReturn:
    raise RuntimeError("send awaitable not set")  # pragma: no cover


class IdentityResponder:
    content_encoding: str

    def __init__(self, app: ASGIApp, minimum_size: int) -> None:
        self.app = app
        self.minimum_size = minimum_size
        self.send: Send = unattached_send
        self.initial_message: Message = {}
        self.started = False
        self.content_encoding_set = False
        self.content_type_is_excluded = False

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        self.send = send
        await self.app(scope, receive, self.send_with_compression)

    async def send_with_compression(self, message: Message) -> None:
        message_type = message["type"]
        if message_type == "http.response.start":
            # Don't send the initial message until we've determined how to
            # modify the outgoing headers correctly.
            self.initial_message = message
            headers = Headers(raw=self.initial_message["headers"])

            self.content_encoding_set = "content-encoding" in headers
            self.content_type_is_excluded = headers.get(
                "content-type", ""
            ).startswith(DEFAULT_EXCLUDED_CONTENT_TYPES)

        elif message_type == "http.response.body" and (
            self.content_encoding_set or self.content_type_is_excluded
        ):
            if not self.started:
                self.started = True
                await self.send(self.initial_message)
            await self.send(message)

        elif message_type == "http.response.body" and not self.started:
            self.started = True
            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            if len(body) < self.minimum_size and not more_body:
                # Don't apply compression to small outgoing responses.
                # Don't add Vary header for small responses
                await self.send(self.initial_message)
                await self.send(message)
            elif not more_body:
                # Standard response.
                body = self.apply_compression(body, more_body=False)

                headers = Headers(raw=self.initial_message["headers"])
                headers.add_vary_header("Accept-Encoding")

                if body != message["body"]:
                    headers["Content-Encoding"] = self.content_encoding
                    headers["Content-Length"] = str(len(body))
                    message["body"] = body

                self.initial_message["headers"] = headers.encode()
                await self.send(self.initial_message)
                await self.send(message)
            else:
                # Initial body in streaming response.
                body = self.apply_compression(body, more_body=True)

                headers = Headers(raw=self.initial_message["headers"])
                headers.add_vary_header("Accept-Encoding")

                if body != message["body"]:
                    headers["Content-Encoding"] = self.content_encoding
                    if "Content-Length" in headers:
                        del headers["Content-Length"]

                    message["body"] = body

                self.initial_message["headers"] = headers.encode()
                await self.send(self.initial_message)
                await self.send(message)
        elif message_type == "http.response.body":  # pragma: no branch
            # Remaining body in streaming response.
            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            message["body"] = self.apply_compression(body, more_body=more_body)
            await self.send(message)

    def apply_compression(self, body: bytes, *, more_body: bool) -> bytes:
        """Apply compression on the response body.

        If more_body is False, any compression file should be closed. If it
        isn't, it won't be closed automatically until all background tasks
        complete.
        """
        return body
