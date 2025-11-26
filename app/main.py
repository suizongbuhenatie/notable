from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings
from .dependencies import lifespan_context

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

settings = get_settings()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Simple request logging middleware."""

    async def dispatch(self, request: Request, call_next: Callable):  # type: ignore[override]
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "%s %s - status: %s - %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            process_time_ms,
        )
        return response


app = FastAPI(title=settings.app_name, lifespan=lifespan_context)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Basic health check endpoint."""

    return {"status": "ok"}
