from http import HTTPStatus

from httpx import AsyncClient

from app.core.config import settings
from tests.utils.utils import inactive_user_mock
from tests.utils.utils import random_email
from tests.utils.utils import user_mock


async def test_health_check(client: AsyncClient) -> None:
    r = await client.get(f'{settings.API_V1_STR}/health-check')
    assert r.status_code == HTTPStatus.OK
    assert r.json() is True


async def test_utils_resend_verification(client: AsyncClient) -> None:
    user = await inactive_user_mock()

    r = await client.post(f'{settings.API_V1_STR}/resend-verification', json={'email': user.email})
    assert r.status_code == HTTPStatus.OK
    assert r.json() == {'message': 'Verification email sent. Please check your inbox'}


async def test_utils_resend_verification_not_found(client: AsyncClient) -> None:
    r = await client.post(f'{settings.API_V1_STR}/resend-verification', json={'email': random_email()})
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert HTTPStatus.NOT_FOUND.phrase == r.json()['detail']


async def test_utils_resend_verification_verified(client: AsyncClient) -> None:
    user = await user_mock()

    r = await client.post(f'{settings.API_V1_STR}/resend-verification', json={'email': user.email})
    assert r.status_code == HTTPStatus.GONE
    assert r.json()['detail'] == 'The user with this email is already verified'


async def test_utils_password_recovery(client: AsyncClient) -> None:
    user = await inactive_user_mock()

    r = await client.post(f'{settings.API_V1_STR}/password-recovery', json={'email': user.email})
    assert r.status_code == HTTPStatus.OK
    assert r.json() == {'message': 'Password recovery email sent. Please check your inbox'}


async def test_utils_password_recovery_not_found(client: AsyncClient) -> None:
    r = await client.post(f'{settings.API_V1_STR}/password-recovery', json={'email': random_email()})
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert HTTPStatus.NOT_FOUND.phrase == r.json()['detail']
