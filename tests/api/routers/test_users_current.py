from http import HTTPStatus

from httpx import AsyncClient

from app.core.config import settings
from app.models.user import User
from app.utils.security import create_access_token
from app.utils.security import create_email_token
from app.utils.security import create_refresh_token
from app.utils.security import verify_password
from tests.utils.utils import inactive_user_mock
from tests.utils.utils import random_lower_string

BASE_URL = f'{settings.API_V1_STR}/users/current'


async def test_get_current_user(
    client: AsyncClient, normal_user: User, normaluser_token_headers: dict[str, str]
) -> None:
    r = await client.get(BASE_URL, headers=normaluser_token_headers)
    assert r.status_code == HTTPStatus.OK
    assert r.json()['email'] == normal_user.email


async def test_get_current_user_no_token(client: AsyncClient) -> None:
    r = await client.get(BASE_URL)
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_current_inactive(client: AsyncClient) -> None:
    user = await inactive_user_mock()
    token = create_access_token(user.id)
    r = await client.get(BASE_URL, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_current_user_nonexisting(client: AsyncClient) -> None:
    token = create_access_token(1234)
    r = await client.get(BASE_URL, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_current_user_no_sub(client: AsyncClient) -> None:
    token = create_access_token(None)
    r = await client.get(BASE_URL, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_current_wrong_payload(client: AsyncClient, normal_user) -> None:
    token = create_refresh_token(normal_user.id)
    r = await client.get(BASE_URL, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_current_wrong_payload1(client: AsyncClient, normal_user) -> None:
    token = create_email_token(normal_user.email)
    r = await client.get(BASE_URL, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_update_current_user_password_same(
    client: AsyncClient, normal_user: User, normaluser_token_headers: dict[str, str]
) -> None:
    data = {
        'old_password': 'mockpassword',
        'new_password_1': 'mockpassword',
        'new_password_2': 'mockpassword',
    }
    r = await client.put(
        f'{BASE_URL}/password',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert r.json()['detail'][0]['msg'] == 'Value error, new password should not be the same current'

    updated = await User.get(id=normal_user.id)
    assert verify_password('mockpassword', updated.password)
    assert normal_user.first_name == updated.first_name
    assert normal_user.last_name == updated.last_name


async def test_update_current_user_password_mismatch(
    client: AsyncClient, normaluser_token_headers: dict[str, str]
) -> None:
    data = {
        'old_password': 'mockpassword',
        'new_password_1': random_lower_string(),
        'new_password_2': random_lower_string(),
    }
    r = await client.put(
        f'{BASE_URL}/password',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert r.json()['detail'][0]['msg'] == 'Value error, passwords do not match'


async def test_update_current_user_password_incorrect(
    client: AsyncClient, normaluser_token_headers: dict[str, str]
) -> None:
    data = {
        'old_password': random_lower_string(),
        'new_password_1': 'samepassword',
        'new_password_2': 'samepassword',
    }
    r = await client.put(
        f'{BASE_URL}/password',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.BAD_REQUEST
    assert r.json()['detail'] == 'Incorrect password'


async def test_update_current_user_password(client: AsyncClient, normaluser_token_headers: dict[str, str]) -> None:
    data = {
        'old_password': 'mockpassword',
        'new_password_1': 'mockpassword1',
        'new_password_2': 'mockpassword1',
    }
    r = await client.put(
        f'{BASE_URL}/password',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.NO_CONTENT


async def test_update_current_user(
    client: AsyncClient, normal_user: User, normaluser_token_headers: dict[str, str]
) -> None:
    data = {'first_name': 'Maica', 'last_name': 'Test'}
    r = await client.put(
        BASE_URL,
        headers=normaluser_token_headers,
        json=data,
    )

    updated_user = r.json()
    assert r.status_code == HTTPStatus.OK
    assert updated_user['email'] == normal_user.email
    assert updated_user['first_name'] == data['first_name']
    assert updated_user['last_name'] == data['last_name']

    updated = await User.get(id=normal_user.id)
    assert updated.email == normal_user.email
    assert updated.first_name == data['first_name']
    assert updated.last_name == data['last_name']


async def test_remove_current_user(
    client: AsyncClient, normal_user: User, normaluser_token_headers: dict[str, str]
) -> None:
    r = await client.delete(
        BASE_URL,
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.ACCEPTED

    updated = await User.get_by_email(email=normal_user.email)
    assert updated is not None
