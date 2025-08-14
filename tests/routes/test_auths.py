from http import HTTPStatus

from httpx import AsyncClient

from app.core.config import settings
from app.models.user import User
from app.utils.security import create_access_token
from app.utils.security import create_email_token
from app.utils.security import create_refresh_token
from tests.utils.utils import random_lower_string
from tests.utils.utils import user_mock


async def test_login_access_token(client: AsyncClient, normal_user: User) -> None:
    login = {'username': normal_user.email, 'password': 'mockpassword'}

    r = await client.post(f'{settings.API_V1_STR}/login', data=login)

    assert r.status_code == HTTPStatus.OK
    assert r.json()['access_token']


async def test_login_access_token_incorrect_password(client: AsyncClient, normal_user: User) -> None:
    login_data = {'username': normal_user.email, 'password': 'incorrect'}
    r = await client.post(f'{settings.API_V1_STR}/login', data=login_data)
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_login_access_token_incorrect_email(client: AsyncClient) -> None:
    login_data = {'username': random_lower_string(), 'password': 'mockpassword'}
    r = await client.post(f'{settings.API_V1_STR}/login', data=login_data)
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_refresh(client: AsyncClient) -> None:
    user = await user_mock()
    refresh_token = create_refresh_token(user.id)
    r = await client.post(f'{settings.API_V1_STR}/login/refresh', cookies={'refresh_token': refresh_token})

    assert r.status_code == HTTPStatus.OK
    assert r.json()['access_token']


async def test_refresh_nonexisting(client: AsyncClient) -> None:
    refresh_token = create_refresh_token(1234)
    r = await client.post(f'{settings.API_V1_STR}/login/refresh', cookies={'refresh_token': refresh_token})
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_refresh_no_token(client: AsyncClient) -> None:
    r = await client.post(f'{settings.API_V1_STR}/login/refresh')
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_refresh_no_sub(client: AsyncClient) -> None:
    refresh_token = create_refresh_token(None)
    r = await client.post(f'{settings.API_V1_STR}/login/refresh', cookies={'refresh_token': refresh_token})
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_refresh_wrong_payload(client: AsyncClient) -> None:
    user = await user_mock()
    refresh_token = create_access_token(user.id)
    r = await client.post(f'{settings.API_V1_STR}/login/refresh', cookies={'refresh_token': refresh_token})
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_refresh_wrong_payload1(client: AsyncClient) -> None:
    user = await user_mock()
    refresh_token = create_email_token(user.email)
    r = await client.post(f'{settings.API_V1_STR}/login/refresh', cookies={'refresh_token': refresh_token})
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_logout(client: AsyncClient) -> None:
    r = await client.post(f'{settings.API_V1_STR}/logout')
    assert r.status_code == HTTPStatus.OK
