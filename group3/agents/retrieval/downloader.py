import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx


class HttpRequestError(RuntimeError):
    """Safe, actionable terminal request error; no headers/body/query credentials."""
    def __init__(self, message, *, code, attempts, status_code=None, retry_after=None):
        super().__init__(message)
        self.code, self.attempts = code, attempts
        self.status_code, self.retry_after = status_code, retry_after


def retry_after_seconds(value, now=None):
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0, (parsed - (now or datetime.now(timezone.utc))).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return None


def safe_endpoint(url):
    parsed = httpx.URL(url)
    return str(parsed.copy_with(username="", password="", query=None, fragment=None))


class RequestGate:
    """Single connection and minimum start-to-start interval, including retries."""

    def __init__(self, interval: float, *, clock=time.monotonic, sleep=asyncio.sleep):
        self.interval = interval
        self.clock = clock
        self.sleep = sleep
        self.last: float | None = None
        self.lock = asyncio.Lock()

    async def call(self, operation: Callable[[], Awaitable[httpx.Response]]):
        async with self.lock:
            if self.last is not None:
                await self.sleep(max(0, self.interval - (self.clock() - self.last)))
            self.last = self.clock()
            return await operation()


class HttpTransport:
    def __init__(self, client: httpx.AsyncClient, gate: RequestGate, retries=2, sleep=asyncio.sleep):
        self.client, self.gate, self.retries, self.sleep = client, gate, retries, sleep

    async def request(self, method, url, **kwargs):
        for attempt in range(self.retries + 1):
            try:
                response = await self.gate.call(lambda: self.client.request(method, url, **kwargs))
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status != 429 and status < 500:
                    raise
                server_delay = retry_after_seconds(exc.response.headers.get("Retry-After"))
                delay = server_delay
                # No guessed rapid retries when the server rate-limits us. Long server
                # cooldowns are returned to callers instead of blocking the service.
                if (status == 429 and delay is None) or (delay is not None and delay > 60):
                    hint = f"Wait at least {delay:g} seconds before retrying." if delay is not None else "Retry-After was not provided; pause requests and retry later."
                    code = "rate_limited" if status == 429 else "server_cooldown"
                    raise HttpRequestError(f"HTTP {status}: {method} {safe_endpoint(url)}. {hint} Automatic retries stopped after {attempt + 1} attempt(s).",
                        code=code, attempts=attempt+1, status_code=status, retry_after=delay) from exc
                delay = delay if delay is not None else 2 ** attempt
                last_error, last_status, code = exc, status, "rate_limited" if status == 429 else "http_error"
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                delay = 2 ** attempt
                last_error, last_status = exc, None
                code = "timeout" if isinstance(exc,httpx.TimeoutException) else "network_error"
            if attempt == self.retries:
                reason = f"HTTP {last_status}" if last_status else type(last_error).__name__
                raise HttpRequestError(f"HTTP request exhausted {attempt + 1} attempts: {method} {safe_endpoint(url)} (last error: {reason})",
                    code=code, attempts=attempt+1, status_code=last_status, retry_after=server_delay if last_status else None) from last_error
            await self.sleep(delay)
