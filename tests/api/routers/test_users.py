from http import HTTPStatus
from unittest.mock import patch

from httpx import AsyncClient

from app.core.config import settings
from app.models.user import User
from app.utils.security import create_access_token
from app.utils.security import create_email_token
from app.utils.security import create_refresh_token
from app.utils.security import verify_password
from tests.utils.utils import inactive_user_mock
from tests.utils.utils import random_email
from tests.utils.utils import random_integer
from tests.utils.utils import random_lower_string
from tests.utils.utils import user_mock

BASE_URL = f'{settings.API_V1_STR}/users'


async def test_register_user(client: AsyncClient) -> None:
    data = {
        'email': random_email(),
        'password': random_lower_string(),
        'first_name': random_lower_string(),
        'last_name': random_lower_string(),
    }
    r = await client.post(f'{BASE_URL}/register', json=data)
    created_user = r.json()

    assert r.status_code == HTTPStatus.CREATED
    assert created_user['email'] == data['email']
    assert created_user['first_name'] == data['first_name']
    assert created_user['last_name'] == data['last_name']


async def test_register_user_existing(client: AsyncClient) -> None:
    user = await user_mock()

    data = {
        'email': user.email,
        'password': random_lower_string(),
        'first_name': random_lower_string(),
        'last_name': random_lower_string(),
    }
    r = await client.post(f'{BASE_URL}/register', json=data)
    assert r.status_code == HTTPStatus.CONFLICT
    assert r.json()['detail'] == 'The user with this email already exists in the system'


async def test_create_user(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    with (
        patch('app.core.emails.send_email', return_value=None),
        patch('app.core.config.settings.SMTP_HOST', 'smtp.example.com'),
        patch('app.core.config.settings.SMTP_USER', 'admin@example.com'),
    ):
        data = {
            'email': random_email(),
            'password': random_lower_string(),
            'first_name': random_lower_string(),
            'last_name': random_lower_string(),
        }
        r = await client.post(
            BASE_URL,
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == HTTPStatus.CREATED
        created_user = r.json()
        user = await User.get_by_email(email=data['email'])
        assert user

        assert user.email == created_user['email']
        assert False is user.is_active
        assert False is user.is_staff
        assert False is user.is_superuser


async def test_create_user_forbidden(client: AsyncClient, normaluser_token_headers: dict[str, str]) -> None:
    data = {
        'email': random_email(),
        'password': random_lower_string(),
        'first_name': random_lower_string(),
        'last_name': random_lower_string(),
    }
    r = await client.post(
        BASE_URL,
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN


async def test_get_user(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    user = await user_mock()

    r = await client.get(
        f'{BASE_URL}/{user.id}',
        headers=superuser_token_headers,
    )
    api_user = r.json()

    assert r.status_code == HTTPStatus.OK
    assert user
    assert user.email == api_user['email']


async def test_get_user_nonexisting(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    r = await client.get(
        f'{BASE_URL}/{random_integer()}',
        headers=superuser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_get_user_forbidden(client: AsyncClient, normaluser_token_headers: dict[str, str]) -> None:
    user = await user_mock()
    r = await client.get(f'{BASE_URL}/{user.id}', headers=normaluser_token_headers)
    assert r.status_code == HTTPStatus.FORBIDDEN


async def test_create_user_existing(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    user = await user_mock()

    data = {
        'email': user.email,
        'password': random_lower_string(),
        'first_name': 'Maica',
        'last_name': 'Test',
    }
    r = await client.post(
        BASE_URL,
        headers=superuser_token_headers,
        json=data,
    )
    created_user = r.json()
    assert r.status_code == HTTPStatus.CONFLICT
    assert '_id' not in created_user


async def test_get_all_user(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    r = await client.get(BASE_URL, headers=superuser_token_headers)
    all_users = r.json()

    assert r.status_code == HTTPStatus.OK
    assert len(all_users['items']) > 1
    assert 'total' in all_users
    assert 'page' in all_users
    assert 'size' in all_users
    assert 'pages' in all_users

    for user in all_users['items']:
        assert 'email' in user
        assert 'first_name' in user
        assert 'last_name' in user
        assert 'id' in user
        assert 'is_active' in user
        assert 'is_superuser' in user
        assert 'invite_token' in user
        assert 'register_token' in user


async def test_get_all_user_forbidden(client: AsyncClient, normaluser_token_headers: dict[str, str]) -> None:
    r = await client.get(BASE_URL, headers=normaluser_token_headers)
    assert r.status_code == HTTPStatus.FORBIDDEN


async def test_update_user(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    user = await user_mock()

    data = {'first_name': 'Updated_first_name', 'last_name': user.last_name}
    r = await client.put(
        f'{BASE_URL}/{user.id}',
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.OK
    assert r.json()['first_name'] == data['first_name']

    updated = await User.get(id=user.id)
    assert data['first_name'] == updated.first_name
    assert user.last_name == updated.last_name


async def test_update_user_nonexisting(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    data = {'first_name': 'Updated_first_name', 'last_name': 'Updated_last_name'}
    r = await client.put(
        f'{BASE_URL}/000',
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_update_user_forbidden(client: AsyncClient, normaluser_token_headers: dict[str, str]) -> None:
    user = await user_mock()

    data = {'first_name': 'Updated_first_name', 'last_name': user.last_name}
    r = await client.put(
        f'{BASE_URL}/{user.id}',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN


async def test_remove_user(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    user = await user_mock()

    r = await client.delete(
        f'{BASE_URL}/{user.id}',
        headers=superuser_token_headers,
    )

    assert r.status_code == HTTPStatus.NO_CONTENT
    updated = await User.get_by_email(email=user.email)
    assert updated is None


async def test_remove_user_forbidden(client: AsyncClient, normaluser_token_headers: dict[str, str]) -> None:
    user = await user_mock()
    r = await client.delete(
        f'{BASE_URL}/{user.id}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN


async def test_remove_user_nonexisting(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    r = await client.delete(
        f'{BASE_URL}/1111',
        headers=superuser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_user_verify_email(client: AsyncClient) -> None:
    user = await inactive_user_mock()
    token = create_email_token(email=user.email)

    r = await client.post(f'{BASE_URL}/verify-email', params={'token': token})
    assert r.status_code == HTTPStatus.NO_CONTENT
    updated = await User.get(id=user.id)
    assert True is updated.is_active


async def test_user_verify_email_not_found(client: AsyncClient) -> None:
    token = create_email_token(email=random_email())
    r = await client.post(f'{BASE_URL}/verify-email', params={'token': token})
    assert r.status_code == HTTPStatus.UNAUTHORIZED
    assert r.json()['detail'] == HTTPStatus.UNAUTHORIZED.phrase


async def test_user_verify_email_invalid_token(client: AsyncClient) -> None:
    token = random_lower_string()
    r = await client.post(f'{BASE_URL}/verify-email', params={'token': token})
    assert r.status_code == HTTPStatus.UNAUTHORIZED
    assert r.json()['detail'] == HTTPStatus.UNAUTHORIZED.phrase


async def test_user_verify_email_verified(client: AsyncClient) -> None:
    user = await user_mock()
    token = create_email_token(email=user.email)
    r = await client.post(f'{BASE_URL}/verify-email', params={'token': token})
    assert r.status_code == HTTPStatus.GONE
    assert r.json()['detail'] == 'The user with this email is already verified'


async def test_user_reset_password(client: AsyncClient) -> None:
    user = await user_mock()
    token = create_email_token(email=user.email)
    r = await client.post(
        f'{BASE_URL}/reset-password',
        params={'token': token},
        json={'new_password_1': 'changethis', 'new_password_2': 'changethis'},
    )
    assert r.status_code == HTTPStatus.NO_CONTENT

    updated = await User.get(id=user.id)
    assert verify_password('changethis', updated.password)
    assert user.first_name == updated.first_name
    assert user.last_name == updated.last_name


async def test_user_reset_password_inactive(client: AsyncClient) -> None:
    user = await inactive_user_mock()
    token = create_email_token(email=user.email)
    r = await client.post(
        f'{BASE_URL}/reset-password',
        params={'token': token},
        json={'new_password_1': 'changethis', 'new_password_2': 'changethis'},
    )
    assert r.status_code == HTTPStatus.FORBIDDEN


async def test_user_reset_password_mismatch(client: AsyncClient) -> None:
    user = await user_mock()
    token = create_email_token(email=user.email)
    r = await client.post(
        f'{BASE_URL}/reset-password',
        params={'token': token},
        json={'new_password_1': 'changethis', 'new_password_2': 'notmatch'},
    )
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_user_reset_password_invalid_email(client: AsyncClient, normaluser_token_headers: dict[str, str]) -> None:
    token = create_email_token(email=random_email())

    r = await client.post(
        f'{BASE_URL}/reset-password',
        params={'token': token},
        headers=normaluser_token_headers,
        json={'new_password_1': 'changethis', 'new_password_2': 'changethis'},
    )
    response = r.json()

    assert 'detail' in response
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_user_reset_password_invalid_token(client: AsyncClient, normaluser_token_headers: dict[str, str]) -> None:
    r = await client.post(
        f'{BASE_URL}/reset-password',
        params={'token': random_lower_string()},
        headers=normaluser_token_headers,
        json={'new_password_1': 'changethis', 'new_password_2': 'changethis'},
    )
    response = r.json()

    assert 'detail' in response
    assert r.status_code == HTTPStatus.UNAUTHORIZED
    assert response['detail'] == HTTPStatus.UNAUTHORIZED.phrase


async def test_user_verify_delete(client: AsyncClient) -> None:
    user = await user_mock()
    token = create_email_token(email=user.email)

    r = await client.post(f'{BASE_URL}/verify-delete', params={'token': token})
    assert r.status_code == HTTPStatus.NO_CONTENT

    updated = await User.get_by_email(email=user.email)
    assert updated is None


async def test_user_verify_delete_not_found(client: AsyncClient) -> None:
    token = create_email_token(email=random_email())
    r = await client.post(f'{BASE_URL}/verify-delete', params={'token': token})
    assert r.status_code == HTTPStatus.UNAUTHORIZED
    assert r.json()['detail'] == HTTPStatus.UNAUTHORIZED.phrase


async def test_user_verify_delete_invalid_token(client: AsyncClient) -> None:
    token = random_lower_string()
    r = await client.post(f'{BASE_URL}/verify-delete', params={'token': token})
    assert r.status_code == HTTPStatus.UNAUTHORIZED
    assert r.json()['detail'] == HTTPStatus.UNAUTHORIZED.phrase


async def test_user_verify_wrong_payload(client: AsyncClient) -> None:
    user = await user_mock()
    token = create_access_token(user.id)
    r = await client.post(f'{BASE_URL}/verify-delete', params={'token': token})
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_user_verify_wrong_payload1(client: AsyncClient) -> None:
    user = await user_mock()
    token = create_refresh_token(user.email)
    r = await client.post(f'{BASE_URL}/verify-delete', params={'token': token})
    assert r.status_code == HTTPStatus.UNAUTHORIZED
