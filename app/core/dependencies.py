from __future__ import annotations

from typing import Annotated
import contextvars
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.domains.users.service import UserService

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
trace_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
path_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("path", default=None)
method_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("method", default=None)
user_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

async def get_user_service(session: SessionDep) -> UserService:
    return UserService.from_session(session)


def get_request_id(request: Request) -> str:
    request_id = request_id_ctx.get() or getattr(request.state, "request_id", "")
    return request_id

RequestId = Annotated[str, Depends(get_request_id)]

__all__ = [
    "SessionDep",
    "get_user_service",
    "RequestId",
    "request_id_ctx",
    "trace_id_ctx",
    "path_ctx",
    "method_ctx",
    "user_id_ctx",
]
