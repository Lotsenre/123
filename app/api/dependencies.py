from typing import Annotated, Tuple

from fastapi import Depends, Request, HTTPException
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


def get_current_user_data(token: str = Depends(get_token)) -> Tuple[int, str]:
    """Возвращает (user_id, role) из токена"""
    try:
        data = AuthService.decode_token(token)
    except InvalidJWTTokenError:
        raise InvalidTokenHTTPError
    return data["user_id"], data.get("role", "user")


def require_admin(user_data: Tuple[int, str] = Depends(get_current_user_data)) -> int:
    """Проверяет что пользователь - админ. Возвращает user_id."""
    user_id, role = user_data
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Доступ запрещён. Требуются права администратора."
        )
    return user_id


UserIdDep = Annotated[int, Depends(get_current_user_id)]
UserDataDep = Annotated[Tuple[int, str], Depends(get_current_user_data)]
AdminDep = Annotated[int, Depends(require_admin)]


async def get_db():
    async with DBManager(session_factory=async_session_maker) as db:
        yield db


DBDep = Annotated[DBManager, Depends(get_db)]
