from typing import Annotated

from fastapi import Depends, Request
from pydantic import BaseModel, Field

from app.database.database import async_session_maker
from app.exceptions.auth import (
    InvalidJWTTokenError,
    InvalidTokenHTTPError,
    NoAccessTokenHTTPError,
)
from app.services.auth import AuthService
from app.database.db_manager import DBManager


class PaginationParams(BaseModel):
    page: int | None = Field(default=1, ge=1)
    per_page: int | None = Field(default=5, ge=1, le=30)


PaginationDep = Annotated[PaginationParams, Depends()]


def get_token(request: Request) -> str:
    # Сначала пытаемся получить токен из Authorization заголовка (Bearer token)
    auth_header = request.headers.get("Authorization", None)
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    
    # Если нет, пытаемся получить из cookies (для обратной совместимости)
    token = request.cookies.get("access_token", None)
    if token is not None:
        return token
    
    # Если нигде нет токена - ошибка
    raise NoAccessTokenHTTPError


def get_current_user_id(token: str = Depends(get_token)) -> int:
    try:
        data = AuthService.decode_token(token)
    except InvalidJWTTokenError:
        raise InvalidTokenHTTPError
    return data["user_id"]


UserIdDep = Annotated[int, Depends(get_current_user_id)]


async def get_db():
    async with DBManager(session_factory=async_session_maker) as db:
        yield db


DBDep = Annotated[DBManager, Depends(get_db)]
