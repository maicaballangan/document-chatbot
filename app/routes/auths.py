from datetime import datetime
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.models.base import Token
from app.models.user import User
from app.utils import security
from app.utils.security import create_access_token
from app.utils.security import create_refresh_token
from app.utils.security import verify_token

router = APIRouter()


@router.post('/login', response_model=Token)
async def login_for_access_token(
    response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> dict[str, str]:
    user = await User.get_by_email(email=form_data.username)

    if user is None or user.is_active is False or security.verify_password(form_data.password, user.password) is False:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=HTTPStatus.UNAUTHORIZED.phrase)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite='Lax',
        max_age=max_age,
    )

    # Update last login
    user.last_login = datetime.now()
    await user.save()

    return Token(access_token=access_token)


@router.post('/login/refresh', response_model=Token)
async def refresh_access_token(request: Request) -> dict[str, str]:
    refresh_token = request.cookies.get('refresh_token')
    if not refresh_token:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=HTTPStatus.UNAUTHORIZED.phrase)

    user_id = verify_token(refresh_token, 'refresh')
    if not user_id:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=HTTPStatus.UNAUTHORIZED.phrase)

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=HTTPStatus.UNAUTHORIZED.phrase)

    new_access_token = create_access_token(user_id)
    return Token(access_token=new_access_token)


@router.post('/logout', status_code=HTTPStatus.OK)
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key='refresh_token')
    response.status_code = HTTPStatus.OK
    return response
