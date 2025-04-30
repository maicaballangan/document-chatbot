import pytest
from httpx import ASGITransport
from httpx import AsyncClient
from tortoise import Tortoise

from app.core.config import settings
from app.main import app
from app.main import MODELS
from app.models.chatsession import ChatSession
from app.models.document import Document
from app.models.policy import Policy
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_price import SubscriptionPrice
from app.models.user import User
from app.models.user import UserCreateAdmin
from app.utils.security import create_app_token
from tests.utils import utils
from tests.utils.utils import random_email
from tests.utils.utils import random_integer
from tests.utils.utils import random_lower_string

DB_URL = 'sqlite://:memory:'


async def init(db_url: str = DB_URL):
    """Initial database connection"""
    await Tortoise.init(db_url=db_url, modules={'app': MODELS}, _create_db=True)
    await Tortoise.generate_schemas()


@pytest.fixture(scope='session')
def anyio_backend():
    return 'asyncio'


@pytest.fixture(scope='session')
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client


@pytest.fixture(scope='session', autouse=True)
async def initialize_tests():
    await init()
    yield
    await Tortoise._drop_databases()


@pytest.fixture(scope='session')
async def normal_user():
    user_in = UserCreateAdmin(
        first_name=random_lower_string(),
        last_name=random_lower_string(),
        email=random_email(),
        password='mockpassword',
        is_active=True,
        stripe_customer_id=f'cus_{random_integer()}',
    )

    user = await User.create(user=user_in)
    return user


@pytest.fixture(scope='session')
async def super_user():
    user_in = UserCreateAdmin(
        first_name=random_lower_string(),
        last_name=random_lower_string(),
        email=random_email(),
        password='mockpassword',
        is_active=True,
        is_superuser=True,
    )

    user = await User.create(user=user_in)
    return user


@pytest.fixture(scope='session')
async def other_user():
    user_in = UserCreateAdmin(
        first_name=random_lower_string(),
        last_name=random_lower_string(),
        email=random_email(),
        password='mockpassword',
        is_active=True,
    )

    user = await User.create(user=user_in)
    return user


@pytest.fixture(scope='session')
async def superuser_token_headers(client: AsyncClient, super_user: User):
    data = {'username': super_user.email, 'password': 'mockpassword'}
    r = await client.post(f'{settings.API_V1_STR}/login', data=data)
    token = r.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture(scope='session')
async def normaluser_token_headers(client: AsyncClient, normal_user: User):
    data = {'username': normal_user.email, 'password': 'mockpassword'}
    r = await client.post(f'{settings.API_V1_STR}/login', data=data)

    token = r.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture(scope='session')
async def otheruser_token_headers(client: AsyncClient, other_user: User):
    data = {'username': other_user.email, 'password': 'mockpassword'}
    r = await client.post(f'{settings.API_V1_STR}/login', data=data)

    token = r.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture(scope='session')
async def media_processor_token_headers():
    token = create_app_token('media-processor')
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture(scope='function')
async def document_mock(normal_user) -> Document:  # type: ignore
    mock = await utils.document_mock(normal_user.id)
    yield mock
    await mock.delete()


@pytest.fixture(scope='function')
async def policy_mock(normal_user, document_mock) -> Policy:  # type: ignore
    mock = await utils.policy_mock(document_mock.id, normal_user.id)
    yield mock
    await mock.delete()


@pytest.fixture(scope='function')
async def policy_chatsession_mock(policy_mock, normal_user) -> ChatSession:  # type: ignore
    mock = await utils.policy_chatsession_mock(policy_mock.id, normal_user.id)
    yield mock
    await mock.delete()


@pytest.fixture(scope='function')
async def chat_mock(normal_user, policy_chatsession_mock) -> Policy:  # type: ignore
    mock = await utils.chat_mock(policy_chatsession_mock.id, normal_user.id)
    yield mock
    await mock.delete()


@pytest.fixture(scope='function')
async def subscription_plan_mock() -> SubscriptionPlan:  # type: ignore
    mock = await utils.subscription_plan_mock()
    yield mock
    await mock.delete()


@pytest.fixture(scope='function')
async def subscription_price_mock(subscription_plan_mock) -> SubscriptionPrice:  # type: ignore
    mock = await utils.subscription_price_mock(subscription_plan_mock.id)
    yield mock
    await mock.delete()


@pytest.fixture(scope='function')
async def subscription_mock(subscription_price_mock, normal_user) -> SubscriptionPrice:  # type: ignore
    mock = await utils.subscription_mock(subscription_price_mock.id, normal_user.id)
    yield mock
    await mock.delete()
