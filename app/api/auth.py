from fastapi import APIRouter
from starlette.responses import Response

from app.api.dependencies import DBDep, UserIdDep
from app.exceptions.auth import (
    UserAlreadyExistsError,
    UserAlreadyExistsHTTPError,
    UserNotFoundError,
    UserNotFoundHTTPError,
    InvalidPasswordError,
    InvalidPasswordHTTPError,
)
from app.schemes.users import SUserAddRequest, SUserAuth
from app.schemes.relations_users_roles import SUserGetWithRels
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Авторизация и аутентификация"])


@router.post("/register", summary="Регистрация нового пользователя")
async def register_user(
    db: DBDep,
    user_data: SUserAddRequest,
) -> dict[str, str]:
    try:
        await AuthService(db).register_user(user_data)
    except UserAlreadyExistsError:
        raise UserAlreadyExistsHTTPError
    return {"status": "OK"}


@router.post("/login", summary="Аутентификация пользователя")
async def login_user(
    db: DBDep,
    response: Response,
    user_data: SUserAuth,
) -> dict[str, str]:
    try:
        access_token: str = await AuthService(db).login_user(user_data)
    except UserNotFoundError:
        raise UserNotFoundHTTPError
    except InvalidPasswordError:
        raise InvalidPasswordHTTPError
    response.set_cookie("access_token", access_token)
    return {"access_token": access_token}


@router.get("/me", summary="Получение текущего пользователя для профиля")
async def get_me(db: DBDep, user_id: UserIdDep) -> SUserGetWithRels | None:
    try:
        user: None | SUserGetWithRels = await AuthService(db).get_me(user_id)
    except UserNotFoundError:
        raise UserNotFoundHTTPError
    return user


@router.post("/logout", summary="Выход пользователя из системы")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie("access_token")
    return {"status": "OK"}
